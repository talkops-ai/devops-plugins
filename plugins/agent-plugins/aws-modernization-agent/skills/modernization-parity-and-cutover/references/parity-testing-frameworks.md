# Parity Testing Frameworks & Verification Architecture

## 1. Overview

Ensuring functional and behavioral equivalence between legacy systems and modernized AWS cloud workloads requires rigorous, automated verification across multiple layers:
1. **Integration Testing with Testcontainers**: Ephemeral, production-identical database and message broker containers in CI/CD.
2. **Contract Testing**: REST API schema and behavior validation using Pact and OpenAPI / Prism.
3. **Event Schema Validation**: Asynchronous event contract integrity using JSON Schema and Apache Avro registries.
4. **Mainframe Record-Replay Equivalence Testing**: Automated comparison of batch dataset outputs and online screen flows, accounting for EBCDIC vs. ASCII collation and packed decimal (`COMP-3`) precision.

---

## 2. Testcontainers Integration Testing

Using shared or mock databases in CI/CD introduces false confidence and environment drift. Testcontainers runs real Docker containers that start before tests and tear down immediately after, ensuring tests run against the exact target database engine (e.g., PostgreSQL 16) and messaging middleware (e.g., Apache Kafka).

### 2.1 Java / Spring Boot Testcontainers Suite

```java
package com.talkops.modernization.parity;

import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.containers.KafkaContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.utility.DockerImageName;

import java.math.BigDecimal;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.Statement;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
@Testcontainers
class ModernizedDataParityTest {

    @Container
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16.2-alpine")
            .withDatabaseName("modernized_parity_db")
            .withUsername("modernization_admin")
            .withPassword("secure_test_password")
            .withInitScript("db/init-parity-schema.sql");

    @Container
    static KafkaContainer kafka = new KafkaContainer(
            DockerImageName.parse("confluentinc/cp-kafka:7.5.0")
    );

    @DynamicPropertySource
    static void configureProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", postgres::getJdbcUrl);
        registry.add("spring.datasource.username", postgres::getUsername);
        registry.add("spring.datasource.password", postgres::getPassword);
        registry.add("spring.kafka.bootstrap-servers", kafka::getBootstrapServers);
    }

    @Test
    @DisplayName("Verify sequence generation and COMP-3 numeric precision in PostgreSQL")
    void verifyNumericAndSequenceParity() throws Exception {
        try (Connection conn = DriverManager.getConnection(
                postgres.getJdbcUrl(), postgres.getUsername(), postgres.getPassword())) {
            
            Statement stmt = conn.createStatement();
            
            // Execute migrated insertion with high-precision financial calculation
            stmt.executeUpdate(
                "INSERT INTO accounts (account_number, balance, status) " +
                "VALUES ('ACC-98765', 123456789012345.67, 'ACTIVE');"
            );
            
            ResultSet rs = stmt.executeQuery(
                "SELECT account_id, balance FROM accounts WHERE account_number = 'ACC-98765';"
            );
            
            assertTrue(rs.next(), "Account record should be inserted and retrieved");
            long generatedId = rs.getLong("account_id");
            BigDecimal retrievedBalance = rs.getBigDecimal("balance");
            
            assertTrue(generatedId > 0, "Sequence must assign a positive 64-bit BIGSERIAL ID");
            assertEquals(new BigDecimal("123456789012345.67"), retrievedBalance, 
                "Numeric scale and precision must match legacy mainframe COMP-3 specification");
        }
    }
}
```

### 2.2 Node.js / TypeScript Testcontainers Suite

```typescript
import { PostgreSqlContainer, StartedPostgreSqlContainer } from '@testcontainers/postgresql';
import { KafkaContainer, StartedKafkaContainer } from '@testcontainers/kafka';
import { Client } from 'pg';

describe('Modernized Service Contract & Data Parity', () => {
  let pgContainer: StartedPostgreSqlContainer;
  let kafkaContainer: StartedKafkaContainer;
  let pgClient: Client;

  beforeAll(async () => {
    pgContainer = await new PostgreSqlContainer('postgres:16.2-alpine')
      .withDatabase('testdb')
      .withUsername('testuser')
      .withPassword('testpass')
      .start();

    kafkaContainer = await new KafkaContainer().start();

    pgClient = new Client({
      connectionString: pgContainer.getConnectionUri(),
    });
    await pgClient.connect();
    await pgClient.query(`
      CREATE TABLE orders (
        order_id BIGSERIAL PRIMARY KEY,
        customer_id VARCHAR(50) NOT NULL,
        total_amount NUMERIC(18, 4) NOT NULL,
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
      );
    `);
  }, 60000);

  afterAll(async () => {
    await pgClient.end();
    await pgContainer.stop();
    await kafkaContainer.stop();
  });

  test('Validates ANSI timestamp and numeric scale parity', async () => {
    const insertRes = await pgClient.query(
      `INSERT INTO orders (customer_id, total_amount) VALUES ($1, $2) RETURNING *`,
      ['CUST-1001', '1250000.4500']
    );
    expect(insertRes.rows[0].customer_id).toBe('CUST-1001');
    expect(insertRes.rows[0].total_amount).toBe('1250000.4500');
  });
});
```

---

## 3. Contract Testing: REST APIs & Asynchronous Events

### 3.1 REST Contract Testing with OpenAPI & Prism Mocking

Use consumer-driven contract testing to ensure microservices extract from the monolith adhere to API contracts without breaking front-end or upstream callers.

```bash
# Validate OpenAPI 3.1 schema specification against linting rules
npx @stoplight/spectral-cli lint specs/order-service-api.yaml

# Run mock API server matching contract to test consumer clients
npx @stoplight/prism-cli mock specs/order-service-api.yaml --port 4010
```

### 3.2 Pact Consumer-Driven Contract Verification (Java)

```java
@PactConsumerTest
@PactTestFor(providerName = "LegacyOrderService", port = "8080")
public class OrderServiceContractTest {

    @Pact(consumer = "FrontendWebClient")
    public RequestResponsePact createPact(PactDslWithProvider builder) {
        return builder
            .given("Order 1001 exists")
            .uponReceiving("A request for order details")
            .path("/api/v1/orders/1001")
            .method("GET")
            .headers("Accept", "application/json")
            .willRespondWith()
            .status(200)
            .body(new PactDslJsonBody()
                .stringValue("orderId", "1001")
                .stringValue("status", "SHIPPED")
                .decimalType("totalAmount", 249.99)
                .stringType("currency", "USD")
            )
            .toPact();
    }
}
```

---

## 4. Mainframe Record-Replay Equivalence Testing

Mainframe modernization (via AWS Blu Age refactoring or Rocket Software replatforming) requires validating that batch jobs produce byte-for-byte or semantically identical output files compared to IBM z/OS execution.

### 4.1 Architecture of Record-Replay Verification

```
+---------------------------------------------------------------------------------------------------+
| Legacy Mainframe (IBM z/OS)                                                                      |
| Input Dataset (VSAM / Sequential) ---> Batch Job (COBOL) ---> Golden Output Dataset (EBCDIC)     |
+---------------------------------------------------------------------------------------------------+
                                                                          |
                                                                          v [EBCDIC-to-ASCII Normalization]
                                                                          v
+---------------------------------------------------------------------------------------------------+
| Modernized AWS Target (AWS Blu Age / Rocket Software)                   |
| Same Input Dataset (Converted)   ---> Target Job (Java/Spring)  ---> Modernized Output (ASCII)    |
+---------------------------------------------------------------------------------------------------+
                                                                          |
                                                                          v
                                                               [ Parity Diff Engine ]
                                                               - Collation Order Check
                                                               - COMP-3 Sign/Scale Check
                                                               - Field-by-Field Semantic Match
```

### 4.2 Collation Normalization: EBCDIC vs. ASCII

In EBCDIC, characters sort in the following sequence:
1. Special characters / spaces
2. Lowercase letters (`a-z`)
3. Uppercase letters (`A-Z`)
4. Digits (`0-9`)

In ASCII / UTF-8, characters sort in a different sequence:
1. Special characters / spaces
2. Digits (`0-9`)
3. Uppercase letters (`A-Z`)
4. Lowercase letters (`a-z`)

#### Normalization Script (`scripts/verify-collation-parity.py`)

```python
#!/usr/bin/env python3
"""Compare batch sort output between legacy mainframe and modernized AWS target."""

import sys
import codecs

def normalize_ebcdic_to_ascii(ebcdic_bytes: bytes) -> str:
    """Decode IBM037 EBCDIC byte stream to UTF-8 string."""
    return codecs.decode(ebcdic_bytes, "cp037")

def compare_file_records(legacy_path: str, modernized_path: str, is_legacy_ebcdic: bool = True):
    print(f"Comparing {legacy_path} with {modernized_path}...")
    
    with open(legacy_path, "rb" if is_legacy_ebcdic else "r", encoding=None if is_legacy_ebcdic else "utf-8") as f_leg, \
         open(modernized_path, "r", encoding="utf-8") as f_mod:
        
        legacy_lines = [normalize_ebcdic_to_ascii(l).rstrip() for l in f_leg.readlines()] if is_legacy_ebcdic else [l.rstrip() for l in f_leg.readlines()]
        mod_lines = [l.rstrip() for l in f_mod.readlines()]
        
        if len(legacy_lines) != len(mod_lines):
            print(f"FAILED: Record count mismatch! Legacy={len(legacy_lines)}, Modernized={len(mod_lines)}")
            sys.exit(1)
            
        mismatches = 0
        for idx, (leg, mod) in enumerate(zip(legacy_lines, mod_lines), start=1):
            if leg != mod:
                print(f"Mismatch at record {idx}:")
                print(f"  Legacy:     '{leg}'")
                print(f"  Modernized: '{mod}'")
                mismatches += 1
                if mismatches > 10:
                    print("Too many mismatches. Halting diff.")
                    break
                    
        if mismatches == 0:
            print("SUCCESS: 100% record and collation parity achieved.")
        else:
            print(f"FAILED: {mismatches} records differed.")
            sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 verify-collation-parity.py <legacy_file> <modernized_file>")
        sys.exit(1)
    compare_file_records(sys.argv[1], sys.argv[2])
```

### 4.3 Packed Decimal (`COMP-3`) Precision Verification

COBOL `COMP-3` stores numbers as 2 packed BCD digits per byte, plus a sign nibble in the final half-byte:
- `C` (`0x0C`): Positive signed
- `D` (`0x0D`): Negative signed
- `F` (`0x0F`): Unsigned

When modernized to Java / Spring Boot, every `COMP-3` variable must be mapped to `java.math.BigDecimal` with explicit `RoundingMode.UNNECESSARY` or `RoundingMode.HALF_UP` matching mainframe hardware arithmetic:

```java
// Mainframe: 05 ACCOUNT-BALANCE PIC S9(13)V99 COMP-3.
// Equivalent Java Modernization mapping:
public class AccountRecord {
    // 13 integer digits + 2 decimal digits = 15 total precision, scale 2
    private BigDecimal accountBalance;

    public void setAccountBalance(BigDecimal balance) {
        if (balance.precision() > 15 || balance.scale() > 2) {
            throw new ArithmeticException("Precision/scale overflow for COMP-3 S9(13)V99 field");
        }
        this.accountBalance = balance;
    }
}
```
