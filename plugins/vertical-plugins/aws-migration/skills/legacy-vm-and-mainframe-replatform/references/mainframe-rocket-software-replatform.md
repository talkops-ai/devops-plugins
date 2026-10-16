# Mainframe Replatforming with Rocket Software (Micro Focus)

## 1. Overview

Replatforming mainframes using **Rocket Software Enterprise Server** (formerly Micro Focus) enables enterprises to migrate mission-critical COBOL and PL/I applications to AWS compute while preserving the original source code. This approach minimizes code modification risk and drastically accelerates time-to-market compared to full refactoring.

---

## 2. Core Replatforming Primitives

### 2.1 COBOL Compiler & Runtime on AWS
- Rocket Enterprise Server compiles legacy COBOL (OS/VS COBOL, VS COBOL II, Enterprise COBOL) and PL/I for execution on Linux (Amazon Linux 2023 or RHEL) on Amazon EC2 or Amazon ECS containers.
- Supports both x86_64 and **AWS Graviton (ARM64)** processors for optimal cost performance.

### 2.2 EBCDIC-to-ASCII Character Encoding Conversion
Mainframe workloads use EBCDIC collation where lowercase letters, uppercase letters, and digits have different relative sort order than ASCII (in EBCDIC, numbers sort AFTER letters, whereas in ASCII, numbers sort BEFORE letters).
- Rocket Software provides configurable collation tables (`COLLSEQ=EBCDIC` or `COLLSEQ=ASCII`) to maintain binary sort-order parity during online transactions and batch sorting (`DFSORT` equivalents).

### 2.3 Packed Decimal Precision (`COMP-3` / `COMPUTATIONAL-3`)
- COBOL `COMP-3` stores two decimal digits per byte, with the half-byte (nibble) holding the sign (`C` for positive, `D` for negative, `F` for unsigned).
- Rocket Software runtime provides native binary math libraries to ensure that arithmetic precision matches mainframe hardware down to 31 decimal digits without floating-point rounding errors.

### 2.4 Dataset & File System Mappings (VSAM)
- Mainframe datasets (KSDS, ESDS, RRDS, and sequential files) are mapped to Rocket Software indexed files (`FILESYS=IDXFORMAT8`) hosted on:
  - **Amazon EFS**: For shared multi-instance access across ECS tasks or EC2 auto-scaling groups.
  - **Amazon FSx for OpenZFS / NetApp ONTAP**: For sub-millisecond sequential IOPS and multi-gigabyte throughput.
  - Relational mapping: Exposing VSAM datasets as virtual relational tables over Amazon Aurora PostgreSQL via ODBC/JDBC connectors.

---

## 3. High-Availability Target Architecture on AWS

```
                    +------------------------------------+
                    |     Network Load Balancer (NLB)    |
                    | (TN3270 / Port 23 & Web Services)  |
                    +------------------------------------+
                                       |
                   +-------------------+-------------------+
                   |                                       |
                   v                                       v
    +-----------------------------+         +-----------------------------+
    | EC2 Instance / ECS Fargate  |         | EC2 Instance / ECS Fargate  |
    | (AZ 1)                      |         | (AZ 2)                      |
    |                             |         |                             |
    | Rocket Enterprise Server    |         | Rocket Enterprise Server    |
    | - CICS Emulation Region     |         | - CICS Emulation Region     |
    | - Batch Execution Initiator |         | - Batch Execution Initiator |
    +-----------------------------+         +-----------------------------+
                   \                                       /
                    \                                     /
                     +-----------------------------------+
                     |      Shared Persistent Storage    |
                     |   Amazon EFS / Amazon FSx Multi-AZ|
                     | (VSAM Datasets & Catalogs)        |
                     +-----------------------------------+
```
