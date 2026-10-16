# Microsoft SQL Server (T-SQL) to Aurora PostgreSQL: Comprehensive SQL Rewrite Guide

## 1. Top & Pagination (`SELECT TOP`)

### Problem
T-SQL uses `TOP (n)` immediately following `SELECT`, whereas PostgreSQL uses `LIMIT n` or `FETCH FIRST n ROWS ONLY` at the end of the statement.

### T-SQL Pattern
```sql
SELECT TOP (25) WITH TIES order_id, customer_id, order_date, total_amount
FROM orders
WHERE status = 'PAID'
ORDER BY total_amount DESC;
```

### PostgreSQL Rewrite
```sql
-- Standard PostgreSQL equivalent (WITH TIES supported in Postgres 13+)
SELECT order_id, customer_id, order_date, total_amount
FROM orders
WHERE status = 'PAID'
ORDER BY total_amount DESC
FETCH FIRST 25 ROWS WITH TIES;

-- Simple Top without ties:
-- SELECT order_id, customer_id, order_date, total_amount
-- FROM orders
-- WHERE status = 'PAID'
-- ORDER BY total_amount DESC
-- LIMIT 25;
```

---

## 2. Null Handling (`ISNULL`)

### T-SQL Pattern
```sql
SELECT 
    order_id,
    ISNULL(shipping_fee, 0.00) AS effective_shipping,
    ISNULL(notes, 'N/A') AS order_notes
FROM orders;
```

### PostgreSQL Rewrite
```sql
SELECT 
    order_id,
    COALESCE(shipping_fee, 0.00) AS effective_shipping,
    COALESCE(notes, 'N/A') AS order_notes
FROM orders;
```

---

## 3. Identity Columns (`IDENTITY(1,1)` & `SCOPE_IDENTITY()`)

### T-SQL Pattern
```sql
-- DDL
CREATE TABLE customers (
    customer_id INT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(100) NOT NULL
);

-- DML with Scope Identity
INSERT INTO customers (name) VALUES ('Acme Corp');
SELECT SCOPE_IDENTITY() AS new_customer_id;
```

### PostgreSQL Rewrite
```sql
-- DDL: SQL standard IDENTITY
CREATE TABLE customers (
    customer_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);

-- DML: RETURNING clause (Single network round-trip)
INSERT INTO customers (name) 
VALUES ('Acme Corp')
RETURNING customer_id;
```

---

## 4. Affected Row Count (`@@ROWCOUNT`)

### T-SQL Pattern
```sql
UPDATE orders SET status = 'CANCELLED' WHERE status = 'PENDING' AND order_date < DATEADD(day, -30, GETDATE());
IF @@ROWCOUNT = 0
BEGIN
    PRINT 'No eligible pending orders found.';
END
```

### PostgreSQL Rewrite
In PL/pgSQL procedures or functions:
```sql
DO $$
DECLARE
    v_affected INT;
BEGIN
    UPDATE orders 
    SET status = 'CANCELLED' 
    WHERE status = 'PENDING' 
      AND order_date < clock_timestamp() - INTERVAL '30 days';
      
    GET DIAGNOSTICS v_affected = ROW_COUNT;
    
    IF v_affected = 0 THEN
        RAISE NOTICE 'No eligible pending orders found.';
    END IF;
END $$;
```
In client-side application code (C# / Java / Python / Node.js):
- Use the integer return value from `command.ExecuteNonQuery()`, `statement.executeUpdate()`, or cursor rowcount.

---

## 5. Table Variables & Temporary Tables

### T-SQL Pattern
```sql
DECLARE @FilteredOrders TABLE (
    order_id INT,
    total DECIMAL(10,2)
);

INSERT INTO @FilteredOrders
SELECT order_id, total_amount FROM orders WHERE status = 'PROCESSED';

SELECT c.customer_name, f.total
FROM customers c
INNER JOIN @FilteredOrders f ON c.customer_id = f.order_id;
```

### PostgreSQL Rewrite (Common Table Expression or Temporary Table)
```sql
-- Option A: Common Table Expression (CTE) - in-memory, highly optimized
WITH filtered_orders AS (
    SELECT order_id, total_amount AS total 
    FROM orders 
    WHERE status = 'PROCESSED'
)
SELECT c.customer_name, f.total
FROM customers c
INNER JOIN filtered_orders f ON c.customer_id = f.order_id;

-- Option B: Temporary Table (for multi-step procedural logic)
CREATE TEMPORARY TABLE temp_filtered_orders (
    order_id INT,
    total NUMERIC(10,2)
) ON COMMIT DROP;

INSERT INTO temp_filtered_orders
SELECT order_id, total_amount FROM orders WHERE status = 'PROCESSED';
```

---

## 6. Date Functions (`DATEADD`, `DATEDIFF`, `GETDATE`)

| T-SQL Function | PostgreSQL Equivalent |
|---|---|
| `GETDATE()` | `clock_timestamp()` |
| `DATEADD(day, 10, col)` | `col + INTERVAL '10 days'` |
| `DATEADD(month, 2, col)` | `col + INTERVAL '2 months'` |
| `DATEDIFF(day, date1, date2)` | `(date2::date - date1::date)` |
| `DATEDIFF(second, date1, date2)` | `EXTRACT(EPOCH FROM (date2 - date1))` |
| `CONVERT(VARCHAR(10), date_col, 120)` | `to_char(date_col, 'YYYY-MM-DD')` |
