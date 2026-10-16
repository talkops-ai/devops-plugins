---
name: amazon-eventbridge-scheduler-and-pipes
description: Architect and implement time-based serverless jobs using Amazon EventBridge Scheduler (one-time at() timers, timezone-aware cron(), flexible time windows, universal targets, auto-delete) and point-to-point streaming integrations using Amazon EventBridge Pipes (Source -> Filter -> Enrich -> Target) and EventBridge Schema Registry (list_registries, search_schema, describe_schema).
---

# Amazon EventBridge Scheduler, Pipes & Schema Registry

Build scalable time-based schedules with **Amazon EventBridge Scheduler** and zero-glue point-to-point streaming pipelines with **Amazon EventBridge Pipes**, backed by strongly-typed schemas from `aws-serverless-mcp` (`list_registries`, `search_schema`, `describe_schema`).

## When to Use

- Scheduling recurring `cron()` / `rate()` jobs with explicit IANA timezones (e.g., `America/New_York`) and automatic Daylight Saving Time (DST) handling
- Creating thousands or millions of dynamic one-time timers (`at(yyyy-mm-ddThh:mm:ss)`) such as cart abandonment, trial expiration, or user reminders with automatic post-execution cleanup (`ActionAfterCompletion: DELETE`)
- Connecting a single stream or queue source (DynamoDB Streams, Kinesis, SQS, MSK, MQ) to a single target (Step Functions, EventBridge Bus, SQS, SNS, Kinesis, API Destination) with optional filtering and enrichment via **EventBridge Pipes**
- Discovering exact AWS service event structures using the EventBridge Schema Registry MCP tools

---

## 1. EventBridge Scheduler vs. EventBridge Rules vs. EventBridge Pipes

| Capability | EventBridge Scheduler (`AWS::Scheduler::Schedule`) | EventBridge Event Bus Rule (`AWS::Events::Rule`) | EventBridge Pipes (`AWS::Pipes::Pipe`) |
|---|---|---|---|
| **Primary Purpose** | Time-based `cron()`, `rate()`, and one-time `at()` schedules at massive scale | Many-to-many event routing across microservices, AWS services, and SaaS | 1-to-1 ordered point-to-point connector (`Source -> Filter -> Enrich -> Target`) |
| **Scale Quota** | **1,000,000+ schedules per account** | 300 rules per bus (soft limit) | 1,000 pipes per account (soft limit) |
| **Timezone & DST** | **Native IANA Timezones** (`ScheduleExpressionTimezone: America/Chicago`) | UTC only | N/A (event-driven) |
| **One-Time Auto-Delete** | **`ActionAfterCompletion: DELETE`** | Not supported (requires manual cleanup) | N/A |
| **Thundering Herd Jitter** | **`FlexibleTimeWindow`** (`Mode: FLEXIBLE`, `MaximumWindowInMinutes`) | Not supported | Controlled via batch size & concurrency |
| **Target Coverage** | **>270 AWS services / >6,000 API actions** via Universal Targets (`arn:aws:scheduler:::aws-sdk:...`) | ~20 built-in target types | 15+ native targets with built-in enrichment step |

> **Architectural Rule:** Always prefer **EventBridge Scheduler (`AWS::Scheduler::Schedule` or SAM `ScheduleV2`)** over legacy `AWS::Events::Rule` `ScheduleExpression` for all new scheduled workloads.

---

## 2. Production EventBridge Scheduler Patterns

### Key Best Practices
1. **Schedule Groups (`AWS::Scheduler::ScheduleGroup`)**: Group schedules by tenant, environment, or microservice (`GroupName: billing-schedules`). Deleting a Schedule Group cleanly deletes all schedules inside it.
2. **Flexible Time Windows**: Unless a job must fire at the exact second, set `FlexibleTimeWindow: { Mode: FLEXIBLE, MaximumWindowInMinutes: 5 }` to spread downstream database/API load.
3. **Auto-Delete One-Time Timers**: Always set `ActionAfterCompletion: DELETE` on `at(...)` schedules so completed schedules do not accumulate against account quotas.
4. **Always Configure `RetryPolicy` and `DeadLetterConfig`**: Set `MaximumRetryAttempts` (`3–10`), `MaximumEventAgeInSeconds` (`3600`), and attach an SQS Dead-Letter Queue (`DeadLetterConfig.Arn`).

### AWS SAM Template: Timezone-Aware Recurring Schedule + Universal SDK Target

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Resources:
  BillingScheduleGroup:
    Type: AWS::Scheduler::ScheduleGroup
    Properties:
      Name: billing-schedules

  SchedulerDlq:
    Type: AWS::SQS::Queue
    Properties:
      QueueName: billing-scheduler-dlq
      SqsManagedSseEnabled: true

  NightlyReconciliationSchedule:
    Type: AWS::Scheduler::Schedule
    Properties:
      Name: nightly-billing-reconciliation
      GroupName: !Ref BillingScheduleGroup
      ScheduleExpression: "cron(0 2 * * ? *)"
      ScheduleExpressionTimezone: "America/New_York"
      FlexibleTimeWindow:
        Mode: FLEXIBLE
        MaximumWindowInMinutes: 10
      State: ENABLED
      Target:
        Arn: !GetAtt ReconciliationStateMachine.Arn
        RoleArn: !GetAtt SchedulerExecutionRole.Arn
        Input: '{"jobType": "NIGHTLY_RECONCILIATION"}'
        RetryPolicy:
          MaximumEventAgeInSeconds: 3600
          MaximumRetryAttempts: 3
        DeadLetterConfig:
          Arn: !GetAtt SchedulerDlq.Arn
```

---

## 3. Production EventBridge Pipes Patterns (`Source -> Filter -> Enrich -> Target`)

Use **EventBridge Pipes** instead of writing a custom consumer Lambda whenever you need to move records from a stream/queue to another AWS service while preserving per-shard or per-message-group ordering.

### The 4 Stages of an EventBridge Pipe
1. **Source**: DynamoDB Stream, Kinesis Data Stream, SQS (Standard or FIFO), Amazon MSK, Self-Managed Kafka, or Amazon MQ.
2. **Filtering (Optional, Free)**: Drops non-matching events before enrichment or target invocation—saving enrichment compute and target charges.
3. **Enrichment (Optional)**: Calls a Lambda function, Step Functions **Express** workflow (synchronous), API Gateway, or EventBridge API Destination to hydrate or transform the filtered batch.
4. **Target**: Delivers the enriched payload (with optional `InputTemplate` transformation) to Step Functions, EventBridge Bus, SQS, SNS, Kinesis, Firehose, Lambda, or API Destination.

### AWS SAM Template: DynamoDB Stream -> EventBridge Pipe -> EventBridge Bus

```yaml
Resources:
  OrderEventsPipeRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: pipes.amazonaws.com
            Action: sts:AssumeRole
      Policies:
        - PolicyName: PipeSourceAndTargetPermissions
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Sid: ReadDynamoDBStream
                Effect: Allow
                Action:
                  - dynamodb:DescribeStream
                  - dynamodb:GetRecords
                  - dynamodb:GetShardIterator
                  - dynamodb:ListStreams
                Resource: !GetAtt OrdersTable.StreamArn
              - Sid: SendFailedRecordsToDlq
                Effect: Allow
                Action: sqs:SendMessage
                Resource: !GetAtt PipeDlq.Arn
              - Sid: PublishToDomainEventBus
                Effect: Allow
                Action: events:PutEvents
                Resource: !GetAtt DomainEventBus.Arn

  OrdersCdcPipe:
    Type: AWS::Pipes::Pipe
    Properties:
      Name: orders-cdc-to-domain-bus
      RoleArn: !GetAtt OrderEventsPipeRole.Arn
      Source: !GetAtt OrdersTable.StreamArn
      SourceParameters:
        DynamoDBStreamParameters:
          StartingPosition: LATEST
          BatchSize: 50
          MaximumBatchingWindowInSeconds: 2
          MaximumRetryAttempts: 3
          OnPartialBatchItemFailure: AUTOMATIC_BISECT
          DeadLetterConfig:
            Arn: !GetAtt PipeDlq.Arn
        FilterCriteria:
          Filters:
            - Pattern: '{"eventName": ["INSERT", "MODIFY"], "dynamodb": {"NewImage": {"status": {"S": ["PAID", "SHIPPED"]}}}}'
      Target: !GetAtt DomainEventBus.Arn
      TargetParameters:
        EventBridgeEventBusParameters:
          DetailType: OrderStatusChanged
          Source: com.acme.orders
        InputTemplate: |
          {
            "orderId": "<$.dynamodb.Keys.PK.S>",
            "status": "<$.dynamodb.NewImage.status.S>",
            "updatedAt": "<$.dynamodb.NewImage.updatedAt.S>"
          }
      LogConfiguration:
        Level: ERROR
        CloudWatchLogsLogDestination:
          LogGroupArn: !GetAtt PipeLogGroup.Arn
```

---

## 4. Schema Discovery via `aws-serverless-mcp`

Never guess the nested field structure of AWS events when writing `FilterCriteria` or `InputTemplate` expressions:
1. Call **`list_registries`** to view available registries (`aws.events`, `discovered-schemas`, custom registries).
2. Call **`search_schema`** (e.g., `registry_name: "aws.events"`, `keywords: "s3"` or `"dynamodb"`).
3. Call **`describe_schema`** to retrieve the exact OpenAPI / JSONSchema definition and construct guaranteed-valid filter patterns.
