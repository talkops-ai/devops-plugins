# Oracle to Aurora PostgreSQL: Comprehensive SQL & PL/SQL Rewrite Guide

## 1. Pagination & Row Limiting (`ROWNUM`)

### Problem
Oracle uses the pseudo-column `ROWNUM` evaluated during row filtering before sorting, requiring nested subqueries for pagination.

### Oracle Pattern
```sql
-- Oracle 11g/12c legacy pagination
SELECT * FROM (
    SELECT a.*, ROWNUM rnum FROM (
        SELECT order_id, customer_id, order_date, total_amount
        FROM orders
        WHERE status = 'ACTIVE'
        ORDER BY order_date DESC
    ) a WHERE ROWNUM <= :offset + :limit
) WHERE rnum > :offset;
```

### PostgreSQL Rewrite
```sql
-- Standard PostgreSQL / Aurora DSQL
SELECT order_id, customer_id, order_date, total_amount
FROM orders
WHERE status = 'ACTIVE'
ORDER BY order_date DESC
OFFSET :offset LIMIT :limit;

-- Or ANSI standard:
-- OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY;
```

---

## 2. Date Arithmetic & Timestamp Functions

### Oracle Pattern
```sql
-- Adding 7 days in Oracle
SELECT order_id, order_date + 7 AS delivery_due
FROM orders
WHERE order_date > SYSDATE - 30;

-- Month addition and truncation
SELECT ADD_MONTHS(SYSDATE, 3), TRUNC(SYSDATE, 'MM') FROM DUAL;
```

### PostgreSQL Rewrite
```sql
-- PostgreSQL interval arithmetic
SELECT order_id, order_date + INTERVAL '7 days' AS delivery_due
FROM orders
WHERE order_date > CURRENT_TIMESTAMP - INTERVAL '30 days';

-- Date truncation and month addition
SELECT CURRENT_TIMESTAMP + INTERVAL '3 months', date_trunc('month', CURRENT_TIMESTAMP);
```

---

## 3. Null Handling & Conditional Logic (`NVL`, `DECODE`, `NVL2`)

### Oracle Pattern
```sql
SELECT 
    NVL(discount, 0) AS safe_discount,
    NVL2(shipping_address, 'SHIPPED', 'PICKUP') AS ship_status,
    DECODE(tier, 1, 'PLATINUM', 2, 'GOLD', 3, 'SILVER', 'STANDARD') AS tier_name
FROM customers;
```

### PostgreSQL Rewrite
```sql
SELECT 
    COALESCE(discount, 0) AS safe_discount,
    CASE WHEN shipping_address IS NOT NULL THEN 'SHIPPED' ELSE 'PICKUP' END AS ship_status,
    CASE tier
        WHEN 1 THEN 'PLATINUM'
        WHEN 2 THEN 'GOLD'
        WHEN 3 THEN 'SILVER'
        ELSE 'STANDARD'
    END AS tier_name
FROM customers;
```

---

## 4. Hierarchical Queries (`CONNECT BY PRIOR`)

### Oracle Pattern
```sql
SELECT employee_id, manager_id, first_name, LEVEL
FROM employees
START WITH manager_id IS NULL
CONNECT BY PRIOR employee_id = manager_id
ORDER SIBLINGS BY first_name;
```

### PostgreSQL Rewrite (Recursive CTE)
```sql
WITH RECURSIVE employee_hierarchy AS (
    -- Anchor member
    SELECT employee_id, manager_id, first_name, 1 AS level,
           ARRAY[first_name] AS path
    FROM employees
    WHERE manager_id IS NULL
    
    UNION ALL
    
    -- Recursive member
    SELECT e.employee_id, e.manager_id, e.first_name, eh.level + 1,
           eh.path || e.first_name
    FROM employees e
    INNER JOIN employee_hierarchy eh ON e.manager_id = eh.employee_id
)
SELECT employee_id, manager_id, first_name, level
FROM employee_hierarchy
ORDER BY path;
```

---

## 5. Sequences & Surrogate Keys

### Oracle Pattern
```sql
-- Oracle NEXTVAL / CURRVAL
INSERT INTO orders (order_id, order_code)
VALUES (order_seq.NEXTVAL, 'ORD-' || TO_CHAR(order_seq.CURRVAL));
```

### PostgreSQL Rewrite
```sql
-- PostgreSQL function syntax
INSERT INTO orders (order_id, order_code)
VALUES (nextval('order_seq'), 'ORD-' || currval('order_seq')::text);

-- Modern identity column (preferred):
-- CREATE TABLE orders (
--     order_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
--     ...
-- );
```

---

## 6. String Concatenation & Dual Table

### Oracle Pattern
```sql
SELECT 'Customer: ' || first_name || ' ' || last_name FROM customers WHERE ROWNUM = 1;
SELECT 1 + 1 FROM DUAL;
```

### PostgreSQL Rewrite
```sql
SELECT 'Customer: ' || first_name || ' ' || last_name FROM customers LIMIT 1;
-- Or using CONCAT() to handle nulls:
SELECT CONCAT('Customer: ', first_name, ' ', last_name) FROM customers LIMIT 1;

-- DUAL table is unnecessary in PostgreSQL:
SELECT 1 + 1;
```
