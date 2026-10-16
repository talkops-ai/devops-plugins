# Amazon RDS for SQL Server & RDS Custom for SQL Server — HA Topologies, Native S3 Backup/Restore, Option Groups, tempdb & Licensing

## 1. Editions, Licensing Models & Multi-AZ Topologies

| Edition | Licensing on RDS | Multi-AZ Technology | Max Databases / Compute |
|---|---|---|---|
| **Enterprise Edition (`sqlserver-ee`)** | `license-included` or BYOL (via License Mobility on shared tenancy or Dedicated Hosts) | **Always On Availability Groups (AGs)** across AZs | Up to 100 databases per instance; supports Read Replicas (up to 5) and online index builds. |
| **Standard Edition (`sqlserver-se`)** | `license-included` or BYOL | **Database Mirroring (DBM)** or Basic AGs across AZs | Up to 100 databases (recommended $\le 50$ on Multi-AZ); up to 128 GB RAM / 24 cores per engine limits. |
| **Web Edition (`sqlserver-web`)** | `license-included` only | **Single-AZ only** (Multi-AZ not supported) | Public-facing web workloads only under Microsoft SPLA terms; up to 64 GB RAM / 16 cores. |
| **Express Edition (`sqlserver-ex`)** | `license-included` (no license fee) | **Single-AZ only** | Max 10 GB per database, 1 GB buffer pool RAM, 4 cores. |
| **RDS Custom for SQL Server** | `license-included` or BYOL | Multi-AZ Always On AGs | Full OS administrator (RDP/SSM) and `sysadmin` SQL role access for legacy CLR assemblies, linked servers, or custom agents. |

---

## 2. Native `.bak` Backup and Restore via Amazon S3 (`SQLSERVER_BACKUP_RESTORE`)

Unlike automated RDS snapshots (which back up the entire DB instance), **Native Backup and Restore** lets you export and import individual SQL Server databases as portable `.bak` files in Amazon S3 (ideal for migrating from on-premises SQL Server or refreshing individual databases).

### Step 1: Enable `SQLSERVER_BACKUP_RESTORE` in a Custom Option Group

```bash
aws rds add-option-to-option-group \
  --option-group-name prod-sqlserver-15-options \
  --options '[
    {
      "OptionName": "SQLSERVER_BACKUP_RESTORE",
      "OptionSettings": [
        {
          "Name": "IAM_ROLE_ARN",
          "Value": "arn:aws:iam::<account-id>:role/rds-sqlserver-s3-backup-role"
        }
      ]
    }
  ]' \
  --apply-immediately
```

### Step 2: Execute Native Full/Differential Backup & Restore (`msdb.dbo.rds_*`)

```sql
-- 1. Trigger an asynchronous native full backup to S3 ( optionally KMS-encrypted )
EXEC msdb.dbo.rds_backup_database
  @source_db_name='AppProdDB',
  @s3_arn_to_backup_to='arn:aws:s3:::my-sqlserver-backups/AppProdDB_20261015.bak',
  @kms_master_key_arn='arn:aws:kms:us-east-1:123456789012:key/12345678-xxxx',
  @overwrite_s3_backup_file=1,
  @type='FULL';

-- 2. Restore a .bak file from S3 into RDS for SQL Server
EXEC msdb.dbo.rds_restore_database
  @restore_db_name='AppStagingDB',
  @s3_arn_to_restore_from='arn:aws:s3:::my-sqlserver-backups/AppProdDB_20261015.bak',
  @kms_master_key_arn='arn:aws:kms:us-east-1:123456789012:key/12345678-xxxx',
  @with_norecovery=0;

-- 3. Poll task progress (% complete, status: CREATED, IN_PROGRESS, SUCCESS, ERROR)
EXEC msdb.dbo.rds_task_status
  @db_name='AppStagingDB',
  @task_id=0;
```

> **Multi-AZ Caveat during Restore:** When restoring a database onto a Multi-AZ RDS for SQL Server instance, RDS automatically adds the newly restored database to the Mirroring/Always On Availability Group asynchronously after restore completes. Avoid heavy bulk writes until `rds_task_status` shows `SUCCESS` (100%).

---

## 3. SSIS, SSRS, SSAS & TDE Option Groups

RDS for SQL Server supports running SQL Server Integration Services (`SSIS`), Reporting Services (`SSRS`), Analysis Services (`SSAS`), and Transparent Data Encryption (`TDE`) directly on the DB instance via custom Option Groups:
- **Prerequisites for `SSIS` / `SSRS` / `SSAS`:** The RDS for SQL Server instance **must be joined to an AWS Managed Microsoft AD (or self-managed AD via trust)** and run Standard or Enterprise Edition.
- **`SQLSERVER_AUDIT` Option:** Enables native SQL Server Audit writing `.sqlaudit` files to an S3 bucket with optional retention policies.

---

## 4. `tempdb` Contention & Performance Tuning on RDS for SQL Server

On high-concurrency OLTP workloads using temporary tables (`#temp`), table variables, `SNAPSHOT` isolation (RCSI), or large sorts/hashes, `tempdb` allocation bitmap contention (`PAGELATCH_UP` / `PAGELATCH_EX` on pages `2:1:1` PFS, `2:1:2` GAM, `2:1:3` SGAM) degrades throughput:

1. **Right-size `tempdb` data files to match vCPU count:** Ensure `tempdb` has 1 data file per vCPU up to 8 files (all identically sized with identical autogrowth increments so SQL Server's proportional fill algorithm distributes writes evenly):
   ```sql
   -- Inspect current tempdb file layout and sizes
   SELECT name, physical_name, size * 8 / 1024 AS size_mb, growth, is_percent_growth
   FROM sys.master_files
   WHERE database_id = DB_ID('tempdb');

   -- Modify tempdb file size on RDS for SQL Server
   ALTER DATABASE [tempdb] MODIFY FILE (NAME = N'tempdev', SIZE = 8192MB, FILEGROWTH = 512MB);
   ```
2. **Local NVMe Instance Store for `tempdb`:** On `db.r5d`, `db.m5d`, `db.r6id`, and `db.m6id` instance classes, RDS places `tempdb` on local NVMe SSD instance store automatically, dramatically reducing `PAGELATCH` and `WRITELOG` latency compared to remote EBS volumes.
3. **Multi-AZ Failover Stored Procedures (`rds_failover_db_instance`):** Note that `tempdb` is recreated at default startup sizes upon failover unless configured via startup parameters/procedures.

---

## 5. RDS Custom for SQL Server (CEVs & Support Perimeter)

When operating **Amazon RDS Custom for SQL Server**:
- Use `aws rds modify-db-instance --automation-mode all-paused --resume-full-automation-mode-minutes <60-1440>` before connecting via SSM Fleet Manager / RDP to install cumulative updates (CUs), configure SQL Server Linked Servers to non-SQL targets, or register unsafe CLR assemblies.
- Never alter the `RDSCustomSQLServerInstanceProfile` IAM permissions or delete the `do-not-delete-rds-custom-*` S3/SSM/Secrets Manager resources.
