# Flyway and Liquibase CI/CD Migration Pipelines

## 1. Overview

Schema migrations must be versioned, immutable, and deployed automatically via CI/CD pipelines. Never run manual DDL modifications against staging or production databases. Converted DDL from `dms-schema-conversion` and application-layer incremental changes must be packaged into standard migration frameworks.

---

## 2. Flyway Migration Structure & Best Practices

### 2.1 File Naming Convention
Flyway scripts reside in `src/main/resources/db/migration` (Java) or `db/migrations` (.NET/Node/Python):

- `V<Version>__<Description>.sql` — Versioned migration (applied once, checksum tracked in `flyway_schema_history`).
- `R__<Description>.sql` — Repeatable migration (re-applied whenever file checksum changes, e.g., views, functions, stored procedures).

```
db/migration/
├── V1.0.0__initial_schema_baseline_from_dms.sql
├── V1.1.0__add_order_outbox_table.sql
├── V1.2.0__create_customer_indexes.sql
└── R__view_active_orders_summary.sql
```

### 2.2 Baseline Configuration (`application.yml` or `flyway.conf`)

```yaml
spring:
  flyway:
    enabled: true
    baseline-on-migrate: true
    baseline-version: 1.0.0
    validate-on-migrate: true
    out-of-order: false
    schemas: public
```

---

## 3. Liquibase Migration Structure & Best Practices

### 3.1 Master Changelog & Changesets

Liquibase formats can be XML, YAML, or SQL. Formatted SQL allows developers to write native PostgreSQL DDL with Liquibase metadata headers:

```sql
--liquibase formatted sql

--changeset architect:v1.0.0-initial-orders-table failOnError:true
--comment: Converted from Oracle ORDERS table via DMS SC
CREATE TABLE orders (
    order_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id BIGINT NOT NULL,
    total_amount NUMERIC(12, 2) NOT NULL,
    status VARCHAR(32) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT clock_timestamp()
);

--rollback DROP TABLE orders;

--changeset architect:v1.1.0-add-orders-idx failOnError:true
CREATE INDEX idx_orders_customer_status ON orders (customer_id, status);
--rollback DROP INDEX idx_orders_customer_status;
```

---

## 4. Automated CI/CD Pipeline (GitHub Actions Example)

Securely execute migrations inside private AWS VPC subnets using GitHub Actions self-hosted runners or ephemeral runner containers:

```yaml
name: Deploy Database Migrations to Aurora PostgreSQL

on:
  push:
    branches:
      - main
    paths:
      - 'db/migration/**'

permissions:
  id-token: write   # OIDC AWS Authentication
  contents: read

jobs:
  migrate:
    runs-on: [self-hosted, linux, vpc-runner]
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Configure AWS Credentials (OIDC)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/GitHubActionsFlywayMigrationRole
          aws-region: us-east-1

      - name: Fetch Database Credentials from AWS Secrets Manager
        id: db_creds
        run: |
          SECRET_JSON=$(aws secretsmanager get-secret-value \
            --secret-id "aurora/production/migration-user" \
            --query "SecretString" --output text)
          echo "::add-mask::$(echo "$SECRET_JSON" | jq -r .password)"
          echo "DB_USER=$(echo "$SECRET_JSON" | jq -r .username)" >> $GITHUB_ENV
          echo "DB_PASS=$(echo "$SECRET_JSON" | jq -r .password)" >> $GITHUB_ENV
          echo "DB_URL=$(echo "$SECRET_JSON" | jq -r .jdbc_url)" >> $GITHUB_ENV

      - name: Run Flyway Migration
        uses: flyway/flyway-action@v9
        with:
          command: migrate
          url: ${{ env.DB_URL }}
          user: ${{ env.DB_USER }}
          password: ${{ env.DB_PASS }}
          locations: filesystem:db/migration
```

### Least-Privilege IAM Policy for Secrets Retrieval
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowSecretsManagerGetSecretValue",
      "Effect": "Allow",
      "Action": "secretsmanager:GetSecretValue",
      "Resource": "arn:aws:secretsmanager:us-east-1:123456789012:secret:aurora/production/migration-user-*"
    }
  ]
}
```
