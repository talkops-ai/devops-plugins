# ORM Framework Migration: Hibernate/JPA, MyBatis, Entity Framework & SQLSTATE Handling

## 1. Hibernate & JPA (Java / Spring Boot)

When transitioning persistence tiers from Oracle or SQL Server to Amazon Aurora PostgreSQL, update `application.yml` and JPA Entity definitions.

### 1.1 Dialect & Driver Configuration

```yaml
# application.yml
spring:
  datasource:
    url: jdbc:postgresql://aurora-cluster.cluster-xyz.us-east-1.rds.amazonaws.com:5432/appdb?sslmode=verify-full&sslrootcert=/certs/global-bundle.pem
    username: app_user
    driver-class-name: org.postgresql.Driver
    hikari:
      maximum-pool-size: 20
      minimum-idle: 5
      connection-timeout: 30000
      idle-timeout: 600000
      max-lifetime: 1800000
  jpa:
    database-platform: org.hibernate.dialect.PostgreSQLDialect
    hibernate:
      ddl-auto: validate # Never use update in production
    properties:
      hibernate:
        jdbc:
          batch_size: 50
          order_inserts: true
          order_updates: true
        temp:
          use_jdbc_metadata_defaults: false
```

### 1.2 Sequence & ID Generation Remediation

In Oracle, developers frequently use `allocationSize = 1` or high preallocation pools that cause ID jumps. In PostgreSQL, tune `allocationSize` to match sequence cache:

```java
// Before (Oracle)
@Id
@GeneratedValue(strategy = GenerationType.SEQUENCE, generator = "order_seq_gen")
@SequenceGenerator(name = "order_seq_gen", sequenceName = "ORDER_SEQ", allocationSize = 1)
private Long id;

// After (Aurora PostgreSQL - Identity or Pooled Sequence)
@Id
@GeneratedValue(strategy = GenerationType.IDENTITY) // Uses GENERATED ALWAYS AS IDENTITY
private Long id;

// Alternatively, for high-throughput batch insert performance:
@Id
@GeneratedValue(strategy = GenerationType.SEQUENCE, generator = "order_seq_gen")
@SequenceGenerator(name = "order_seq_gen", sequenceName = "order_seq", allocationSize = 50)
private Long id;
```

---

## 2. Entity Framework Core (.NET 8/10)

### 2.1 Package References & DbContext Configuration

In your `.csproj`:
```xml
<!-- Remove Microsoft.EntityFrameworkCore.SqlServer / Oracle.EntityFrameworkCore -->
<PackageReference Include="Npgsql.EntityFrameworkCore.PostgreSQL" Version="8.0.4" />
```

In `Program.cs`:
```csharp
builder.Services.AddDbContext<AppDbContext>(options =>
    options.UseNpgsql(
        builder.Configuration.GetConnectionString("AuroraPostgres"),
        npgsqlOptions =>
        {
            npgsqlOptions.EnableRetryOnFailure(
                maxRetryCount: 3,
                maxRetryDelay: TimeSpan.FromSeconds(5),
                errorCodesToAdd: null);
            npgsqlOptions.UseQuerySplittingBehavior(QuerySplittingBehavior.SplitQuery);
        })
);
```

### 2.2 Model Mapping Conversions

```csharp
protected override void OnModelCreating(ModelBuilder modelBuilder)
{
    base.OnModelCreating(modelBuilder);

    // Convert SQL Server default values
    modelBuilder.Entity<Order>()
        .Property(o => o.CreatedAt)
        .HasDefaultValueSql("clock_timestamp()"); // Replaces GETDATE()

    // Configure Identity column
    modelBuilder.Entity<Order>()
        .Property(o => o.Id)
        .UseIdentityAlwaysColumn(); // Replaces UseIdentityColumn()
}
```

---

## 3. MyBatis (Java / Kotlin)

In MyBatis XML mappers, replace vendor-specific `<selectKey>` tags with PostgreSQL-native `RETURNING` or standard sequence syntax:

```xml
<!-- Before (Oracle) -->
<insert id="insertCustomer" parameterType="Customer">
    <selectKey keyProperty="id" resultType="long" order="BEFORE">
        SELECT customer_seq.NEXTVAL FROM DUAL
    </selectKey>
    INSERT INTO customers (id, name, email) VALUES (#{id}, #{name}, #{email})
</insert>

<!-- After (Aurora PostgreSQL with RETURNING) -->
<insert id="insertCustomer" parameterType="Customer" useGeneratedKeys="true" keyProperty="id" keyColumn="id">
    INSERT INTO customers (name, email)
    VALUES (#{name}, #{email})
</insert>
```

---

## 4. PostgreSQL SQLSTATE Error Code Handling

Proprietary database exception mappers (catching `ORA-00001` or SQL Server error `2627`) will fail to trap exceptions in PostgreSQL. Re-map error handlers to **PostgreSQL 5-character SQLSTATE codes**:

| Vendor Code | PostgreSQL SQLSTATE | Class / Condition Name | Remediation Action |
|---|---|---|---|
| `ORA-00001` / MSSQL `2627` | `23505` | `unique_violation` | Catch duplicate key exception; return HTTP 409 Conflict. |
| `ORA-02291` / MSSQL `547` | `23503` | `foreign_key_violation` | Catch invalid parent reference; return HTTP 400 Bad Request. |
| `ORA-01407` / MSSQL `515` | `23502` | `not_null_violation` | Catch missing mandatory field. |
| `ORA-00054` / MSSQL `1222` | `55P03` | `lock_not_available` | Handle lock timeout (`NOWAIT`); implement exponential backoff. |
| `ORA-00060` / MSSQL `1205` | `40P01` | `deadlock_detected` | Catch deadlock; retry transaction up to 3 times. |
| `ORA-08177` / MSSQL `3960` | `40001` | `serialization_failure` | Retry serializable transaction with randomized jitter. |

### Spring Boot / Java Exception Translator Example

```java
@ExceptionHandler(DataIntegrityViolationException.class)
public ResponseEntity<ErrorResponse> handleDataIntegrityViolation(DataIntegrityViolationException ex) {
    Throwable rootCause = ex.getRootCause();
    if (rootCause instanceof org.postgresql.util.PSQLException psqlEx) {
        String sqlState = psqlEx.getSQLState();
        if ("23505".equals(sqlState)) { // unique_violation
            return ResponseEntity.status(HttpStatus.CONFLICT)
                .body(new ErrorResponse("RESOURCE_CONFLICT", "A record with this identifier already exists."));
        } else if ("23503".equals(sqlState)) { // foreign_key_violation
            return ResponseEntity.status(HttpStatus.BAD_REQUEST)
                .body(new ErrorResponse("INVALID_REFERENCE", "Referenced parent entity does not exist."));
        }
    }
    return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
        .body(new ErrorResponse("DATABASE_ERROR", "An unexpected database error occurred."));
}
```
