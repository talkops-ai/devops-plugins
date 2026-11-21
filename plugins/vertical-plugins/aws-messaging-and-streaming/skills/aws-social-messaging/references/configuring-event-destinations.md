# Configuring Event Destinations

> **Security:** Encrypt SNS topics with KMS; callbacks may contain recipient metadata. See [SKILL.md — Security Considerations](../SKILL.md#security-considerations).

## Contents

- [Overview](#overview)
- [Configure Event Destination](#configure-event-destination)
- [Prerequisites](#prerequisites)
- [Verify Configuration](#verify-configuration)
- [Event Payload Examples](#event-payload-examples)

## Overview

Event destinations deliver real-time notifications for:

- Message delivery status (sent, delivered, read, failed)
- Template status changes (approved, rejected)
- Template reclassification (UTILITY → MARKETING)

Without event destinations, delivery failures and reclassifications are invisible.

## Configure Event Destination

A WABA can only have **one** event destination at a time (calling `put-whatsapp-business-account-event-destinations` replaces any existing destination).

Supported `eventDestinationArn` target services:
1. **Amazon EventBridge** (`arn:aws:events:<region>:<account>:event-bus/<bus-name>`) — IAM role needs `events:PutEvents`
2. **Amazon SNS** (`arn:aws:sns:<region>:<account>:<topic-name>`) — IAM role needs `sns:Publish`
3. **Amazon Kinesis Data Streams** (`arn:aws:kinesis:<region>:<account>:stream/<stream-name>`) — IAM role needs `kinesis:PutRecord`, `kinesis:PutRecords`
4. **Amazon Data Firehose** (`arn:aws:firehose:<region>:<account>:deliverystream/<stream-name>`) — IAM role needs `firehose:PutRecord`, `firehose:PutRecordBatch`
5. **Amazon CloudWatch Logs** (`arn:aws:logs:<region>:<account>:log-group:<log-group-name>`) — IAM role needs `logs:CreateLogStream`, `logs:PutLogEvents`, `logs:DescribeLogStreams`

```bash
aws socialmessaging put-whatsapp-business-account-event-destinations \
  --id "waba-XXXXXXXXXXXXXXXXXXXX" \
  --event-destinations '[{"eventDestinationArn":"arn:aws:sns:us-east-1:123456789012:whatsapp-events","roleArn":"arn:aws:iam::123456789012:role/WhatsAppEventDeliveryRole"}]'
```

### Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--id` | Yes | WABA ID (format: `waba-XXXX`) |
| `--event-destinations` | Yes | Array with one entry: target ARN (EventBridge, SNS, Kinesis, Firehose, or CloudWatch Logs) + IAM role ARN |

## Prerequisites

### 1. SNS Topic

Create an SNS topic with KMS encryption:

```bash
aws sns create-topic --name whatsapp-events --attributes '{"KmsMasterKeyId":"alias/aws/sns"}'

```

### 2. IAM Role

The role must:

- Trust `social-messaging.amazonaws.com` in its assume-role policy
- Have `sns:Publish` permission on the SNS topic

Trust policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "social-messaging.amazonaws.com"},
    "Action": "sts:AssumeRole",
    "Condition": {
      "StringEquals": {"aws:SourceAccount": "123456789012"},
      "ArnLike": {"aws:SourceArn": "arn:aws:social-messaging:*:123456789012:*"}
    }
  }]
}

```

Permission policy (attach to the role):

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": "sns:Publish",
    "Resource": "arn:aws:sns:us-east-1:123456789012:whatsapp-events"
  }]
}

```

### 3. SNS Topic Policy

Add a resource policy to allow `social-messaging.amazonaws.com` to publish, with condition keys to prevent confused deputy:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "AllowSocialMessagingPublish",
    "Effect": "Allow",
    "Principal": {"Service": "social-messaging.amazonaws.com"},
    "Action": "sns:Publish",
    "Resource": "arn:aws:sns:us-east-1:123456789012:whatsapp-events",
    "Condition": {
      "StringEquals": {"aws:SourceAccount": "123456789012"},
      "ArnLike": {"aws:SourceArn": "arn:aws:social-messaging:*:123456789012:*"}
    }
  },
  {
    "Sid": "DenyNonSSL",
    "Effect": "Deny",
    "Principal": "*",
    "Action": "sns:Publish",
    "Resource": "arn:aws:sns:us-east-1:123456789012:whatsapp-events",
    "Condition": {
      "Bool": {"aws:SecureTransport": "false"}
    }
  }]
}

```

## Verify Configuration

Check SNS subscriptions are confirmed:

```bash
aws sns list-subscriptions-by-topic \
  --topic-arn "arn:aws:sns:us-east-1:123456789012:whatsapp-events"

```

Subscriptions must show `"SubscriptionArn"` (not `"PendingConfirmation"`).

Verify SNS subscription endpoints are authorized personnel/systems — use access policies to restrict who can subscribe. Use HTTPS-only endpoints for encryption in transit.

## Event Payload Examples

AWS End User Messaging Social delivers a top-level JSON envelope containing `context` (`MetaWabaIds`, `MetaPhoneNumberIds`) and a JSON-stringified `whatsAppWebhookEntry` field (which downstream consumers parse a second time with `JSON.parse` / `json.loads` to access `changes[].value.messages` for inbound messages and `changes[].value.statuses` for delivery receipts and `statuses[].errors`):

```json
{
  "context": {
    "MetaWabaIds": ["123456789012345"],
    "MetaPhoneNumberIds": ["987654321098765"]
  },
  "whatsAppWebhookEntry": "{\"id\":\"123456789012345\",\"changes\":[{\"field\":\"messages\",\"value\":{\"messaging_product\":\"whatsapp\",\"metadata\":{\"display_phone_number\":\"15550199999\",\"phone_number_id\":\"987654321098765\"},\"messages\":[{\"from\":\"14155551234\",\"id\":\"wamid.XXXX\",\"timestamp\":\"1710000000\",\"type\":\"text\",\"text\":{\"body\":\"Hello\"}}],\"statuses\":[{\"id\":\"wamid.YYYY\",\"status\":\"delivered\",\"timestamp\":\"1710000005\",\"recipient_id\":\"14155551234\"}]}}]}"
}
```

Delivery receipt:

```json
{
  "eventType": "MESSAGE_STATUS_UPDATE",
  "messageId": "wamid.XXXX",
  "status": "delivered",
  "recipientId": "+14155551234"
}

```

Template reclassification:

```json
{
  "eventType": "TEMPLATE_STATUS_UPDATE",
  "templateName": "order_update",
  "previousCategory": "UTILITY",
  "newCategory": "MARKETING"
}
```
