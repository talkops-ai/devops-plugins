# Distributed Data Patterns for Monolith Decomposition

## Overview

When breaking apart a monolithic relational database into microservices, applications lose distributed ACID transactions. To maintain consistency, reliability, and loose coupling, modern AWS architectures implement four core patterns:
1. **Database-per-Service**
2. **Transactional Outbox with Change Data Capture (CDC)**
3. **Saga Pattern (Orchestrated with AWS Step Functions)**
4. **Idempotent Consumers & Circuit Breakers**

---

## 1. Database-per-Service Architecture

- **Principle**: A microservice owns its private schema and tables. No foreign service may directly execute SQL (`SELECT`, `INSERT`, `UPDATE`, `JOIN`) against another service's database.
- **Cross-Service Data Access**:
  - Synchronous queries: REST API or GraphQL endpoints exposed over Amazon VPC Lattice.
  - Asynchronous queries / Read replicas: Data published as domain events and consumed into a local read-optimized view (CQRS).

---

## 2. Transactional Outbox Pattern

To avoid dual-write inconsistencies (e.g., database commit succeeds but message publishing to Kafka/EventBridge fails), write business entities and outbox events in a single local database transaction.

### Schema Definition (PostgreSQL / Aurora DSQL)

```sql
CREATE TABLE orders (
    order_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL,
    total_amount NUMERIC(12, 2) NOT NULL,
    status VARCHAR(32) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT clock_timestamp()
);

CREATE TABLE outbox_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aggregate_type VARCHAR(64) NOT NULL,
    aggregate_id VARCHAR(64) NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT clock_timestamp(),
    processed BOOLEAN DEFAULT FALSE
);
```

### Application Transaction (Java / JPA Example)

```java
@Transactional
public Order createOrder(CreateOrderRequest req) {
    Order order = new Order(req.getCustomerId(), req.getTotalAmount(), "PENDING");
    orderRepository.save(order);

    OutboxEvent event = new OutboxEvent(
        "Order",
        order.getId().toString(),
        "OrderCreated",
        objectMapper.writeValueAsString(order)
    );
    outboxRepository.save(event);

    return order;
}
```

### Event Relay Worker (AWS Lambda or Debezium CDC)

1. Debezium connector on Amazon MSK Connect streams changes from `outbox_events` directly to Amazon MSK / Apache Kafka.
2. Alternatively, an event-driven AWS Lambda function triggered on Aurora PostgreSQL `pg_notify` or a periodic DynamoDB Streams consumer dispatches events to **Amazon EventBridge**.

---

## 3. Saga Pattern: Orchestrated with AWS Step Functions

When an operation spans multiple services (e.g., Order -> Payment -> Inventory), implement an orchestrator Saga in AWS Step Functions with compensating actions.

```
       [ Start Order Saga ]
               |
               v
     +-------------------+
     |  Process Payment  | ----(Fails)----> [ Fail & Exit ]
     +-------------------+
               | (Succeeds)
               v
     +-------------------+
     | Reserve Inventory | ----(Fails)----> +-------------------+
     +-------------------+                  |   Refund Payment  | (Compensating)
               | (Succeeds)                 +-------------------+
               v                                      |
     +-------------------+                            v
     | Dispatch Shipment | ----(Fails)----> +-------------------+
     +-------------------+                  | Release Inventory | (Compensating)
               | (Succeeds)                 +-------------------+
               v                                      |
       [ Order Complete ]                             v
                                            +-------------------+
                                            |   Refund Payment  | (Compensating)
                                            +-------------------+
                                                      |
                                                      v
                                              [ Order Cancelled ]
```

### Step Functions ASL Definition (Excerpt)

```json
{
  "Comment": "Order Placement Saga with Compensating Actions",
  "StartAt": "ProcessPayment",
  "States": {
    "ProcessPayment": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "Parameters": {
        "FunctionName": "arn:aws:lambda:us-east-1:123456789012:function:process-payment",
        "Payload.$": "$"
      },
      "Next": "ReserveInventory",
      "Catch": [
        {
          "ErrorEquals": ["PaymentFailedException"],
          "Next": "OrderFailed"
        }
      ]
    },
    "ReserveInventory": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "Parameters": {
        "FunctionName": "arn:aws:lambda:us-east-1:123456789012:function:reserve-inventory",
        "Payload.$": "$"
      },
      "Next": "OrderComplete",
      "Catch": [
        {
          "ErrorEquals": ["OutOfStockException", "States.ALL"],
          "Next": "CompensateRefundPayment"
        }
      ]
    },
    "CompensateRefundPayment": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "Parameters": {
        "FunctionName": "arn:aws:lambda:us-east-1:123456789012:function:refund-payment",
        "Payload.$": "$"
      },
      "Next": "OrderCancelled"
    },
    "OrderComplete": {
      "Type": "Succeed"
    },
    "OrderFailed": {
      "Type": "Fail",
      "Cause": "Payment Processing Failed"
    },
    "OrderCancelled": {
      "Type": "Fail",
      "Cause": "Inventory Reservation Failed, Payment Refunded"
    }
  }
}
```

---

## 4. Idempotent Consumers & Circuit Breakers

### Idempotency via Amazon DynamoDB

Every incoming event message has an `idempotency_key`. The consumer writes a conditional put item to DynamoDB:

```python
import boto3
from botocore.exceptions import ClientError

dynamodb = boto3.resource("dynamodb")
idempotency_table = dynamodb.Table("idempotency_records")

def process_event_idempotently(event):
    key = event["idempotency_key"]
    try:
        # Atomic lock with TTL (e.g., 24 hours = 86400 seconds)
        idempotency_table.put_item(
            Item={
                "idempotency_key": key,
                "status": "PROCESSING",
                "ttl": int(time.time()) + 86400
            },
            ConditionExpression="attribute_not_exists(idempotency_key)"
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            print(f"Duplicate event ignored: {key}")
            return {"status": "SKIPPED_DUPLICATE"}
        raise

    # Execute business mutation
    execute_order_creation(event)

    idempotency_table.update_item(
        Key={"idempotency_key": key},
        UpdateExpression="SET #s = :completed",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":completed": "COMPLETED"}
    )
    return {"status": "SUCCESS"}
```

### Resilience: Circuit Breaker Pattern

Use libraries like Resilience4j (Java), Polly (.NET), or Cockatiel (Node.js) wrapped around outbound downstream HTTP/Lattice calls. If the downstream service error rate exceeds 50% across a 10-second sliding window, open the circuit and return cached fallback responses or queue requests into an Amazon SQS dead-letter queue (DLQ).
