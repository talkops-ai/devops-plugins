# Amazon RDS for Oracle & RDS Custom for Oracle — Lifecycle, CDB/PDB, Option Groups, S3 Data Pump & Licensing

## 1. Licensing Models & Edition Selection

| Edition | Licensing Model | Key Capabilities & Constraints |
|---|---|---|
| **Oracle Enterprise Edition (EE)** | **BYOL** (Bring Your Own License) | Supports Multi-AZ, Read Replicas (Active Data Guard), Oracle Connection Manager (CMAN), Transparent Data Encryption (TDE), Partitioning, Diagnostics/Tuning Packs (AWR), and up to 64 TiB storage. |
| **Oracle Standard Edition 2 (SE2)** | **License Included** (`license-included`) or **BYOL** | AWS hourly rate includes Oracle licensing in `license-included` mode (no separate Oracle contract needed). Capped at 2 sockets / 16 vCPUs max capacity (`db.r6i.4xlarge` / `db.m6i.4xlarge`); uses Statspack instead of AWR; no Active Data Guard read replicas. |
| **RDS Custom for Oracle** | **BYOL** (EE or SE2) | Grants underlying EC2 OS access (SSH/SSM) and `SYSDBA` privileges for legacy apps requiring custom patches, GoldenGate agents, or file-system access. Uses Custom Engine Versions (CEVs). |
| **Oracle Database@AWS (`odb-aws`)** | **OCI-Managed Exadata** in AWS AZs | Use when the workload requires Real Application Clusters (RAC), Exadata Smart Scan, or $>64\text{ TiB}$ scale. |

---

## 2. Container Database (CDB) / Pluggable Database (PDB) Architecture

Oracle 19c and 21c on RDS support single-tenant and multi-tenant CDB/PDB architectures:

- **Master user privilege model:** RDS for Oracle does **not** grant `SYS` or `SYSTEM` directly; the master user receives the `DBA` role and executes privileged operations via AWS-supplied `rdsadmin.rdsadmin_util` PL/SQL packages.
- **Common administrative commands via `rdsadmin`:**
  ```sql
  -- Switch system checkpoint or alter global parameters
  EXEC rdsadmin.rdsadmin_util.checkpoint;
  EXEC rdsadmin.rdsadmin_util.switch_logfile;

  -- Enable supplemental logging for AWS DMS CDC
  EXEC rdsadmin.rdsadmin_util.alter_supplemental_logging('ADD');
  EXEC rdsadmin.rdsadmin_util.alter_supplemental_logging('ADD', 'PRIMARY KEY');

  -- Resize or add online redo log files (default 4 x 128 MB is often too small for write-heavy OLTP)
  EXEC rdsadmin.rdsadmin_util.add_logfile(p_size => '1G');
  -- Drop old small inactive logfiles after switching:
  -- EXEC rdsadmin.rdsadmin_util.drop_logfile(grp => 1);

  -- Kill a runaway session (replacement for ALTER SYSTEM KILL SESSION)
  EXEC rdsadmin.rdsadmin_util.kill(sid => <sid>, serial => <serial#>, method => 'IMMEDIATE');
  ```

---

## 3. Option Groups (`TDE`, `NNE`, `SSL`, `S3_INTEGRATION`, `Statspack`, `OEM`)

Never modify a default Option Group. Create a custom Option Group matching the engine (`oracle-ee` or `oracle-se2`) and major version (`19`):

```bash
aws rds create-option-group \
  --option-group-name prod-oracle-19-options \
  --engine-name oracle-ee \
  --major-engine-version 19 \
  --option-group-description "Production Oracle 19c Option Group (NNE, S3 Integration, TDE, Statspack)" \
  --tags Key=created_by,Value=rds-oracle-skill Key=generation_model,Value=claude
```

Add options with `aws rds add-option-to-option-group`:
- **`S3_INTEGRATION`** (version `1.0`): Enables transferring Data Pump `.dmp` and RMAN backup files directly between the RDS `DATA_PUMP_DIR` directory and an Amazon S3 bucket.
- **`TDE`** (Enterprise Edition): Enables Oracle Transparent Data Encryption for tablespace/column encryption (distinct from EBS/KMS storage-at-rest encryption).
- **`Timezone`**: Sets the database OS timezone (e.g., `UTC`).
- **`STATSPACK`**: Mandatory on Standard Edition 2 (`oracle-se2`) where Oracle AWR/ASH licensing is unavailable.

---

## 4. Oracle Data Pump & RMAN Integration with Amazon S3

To migrate data into or out of RDS for Oracle using native Oracle Data Pump (`.dmp` files):

### Step 1: Attach an IAM Role for `S3_INTEGRATION`

```bash
aws rds add-role-to-db-instance \
  --db-instance-identifier <instance-id> \
  --feature-name S3_INTEGRATION \
  --role-arn arn:aws:iam::<account-id>:role/rds-oracle-s3-integration-role
```

### Step 2: Export Schema via `DBMS_DATAPUMP` and Upload to S3

```sql
-- 1. Export schema to local DATA_PUMP_DIR on the RDS instance
DECLARE
  hdnl NUMBER;
BEGIN
  hdnl := DBMS_DATAPUMP.OPEN(operation => 'EXPORT', job_mode => 'SCHEMA', job_name => NULL);
  DBMS_DATAPUMP.ADD_FILE(
    handle    => hdnl,
    filename  => 'app_schema_exp.dmp',
    directory => 'DATA_PUMP_DIR',
    filetype  => dbms_datapump.ku$_file_type_dump_file
  );
  DBMS_DATAPUMP.ADD_FILE(
    handle    => hdnl,
    filename  => 'app_schema_exp.log',
    directory => 'DATA_PUMP_DIR',
    filetype  => dbms_datapump.ku$_file_type_log_file
  );
  DBMS_DATAPUMP.METADATA_FILTER(hdnl, 'SCHEMA_EXPR', 'IN (''APP_SCHEMA'')');
  DBMS_DATAPUMP.START_JOB(hdnl);
END;
/

-- 2. Upload the dump file from DATA_PUMP_DIR to S3 (returns a task_id)
SELECT rdsadmin.rdsadmin_s3_tasks.upload_to_s3(
  p_bucket_name    => 'my-oracle-backups-bucket',
  p_prefix         => 'app_schema_exp',
  p_s3_prefix      => 'exports/2026/',
  p_directory_name => 'DATA_PUMP_DIR'
) AS task_id FROM DUAL;

-- 3. Monitor S3 transfer log using the returned task_id
SELECT text FROM table(rdsadmin.rds_file_util.read_text_file('BDUMP', 'dbtask-<task_id>.log'));
```

*(To import from S3, call `rdsadmin.rdsadmin_s3_tasks.download_from_s3` into `DATA_PUMP_DIR`, monitor `dbtask-<task_id>.log`, and run `DBMS_DATAPUMP.OPEN(operation => 'IMPORT', ...)`.)*

---

## 5. RDS Custom for Oracle (CEVs & Support Perimeter)

When operating **Amazon RDS Custom for Oracle** (`oracle-custom-ee` / `oracle-custom-se2`):
1. **Custom Engine Versions (CEVs):** Upload Oracle installation media + Release Update (RU) patches to S3, register the CEV via `aws rds create-custom-db-engine-version`, and upgrade instances by modifying `--engine-version` to the new CEV.
2. **Support Perimeter (`automation-mode`):** Before applying manual OS changes, GoldenGate maintenance, or PSU patches over SSH/SSM on the underlying EC2 host, pause RDS Custom automation for a bounded window (`60`–`1440` minutes) so RDS Custom health checks do not trigger an unintended host replacement:
   ```bash
   aws rds modify-db-instance \
     --db-instance-identifier <custom-instance-id> \
     --automation-mode all-paused \
     --resume-full-automation-mode-minutes 120
   ```
3. **Never delete `do-not-delete-rds-custom-*` resources:** RDS Custom relies on S3 buckets, KMS keys, SSM VPC endpoints, and Secrets Manager secrets prefixed with `do-not-delete-rds-custom-`. Modifying or deleting these breaks the support perimeter.
