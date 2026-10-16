# Mainframe Automated Refactoring with AWS Blu Age

## 1. Overview

AWS Blu Age automates the refactoring of legacy mainframe applications (written in COBOL, PL/I, RPG, Natural, or CICS) into modern, cloud-native Java and Spring Boot microservices. Orchestrated via **AWS Transform for mainframe (`aws-transform-mcp`)**, Blu Age decomposes monolithic legacy codebases while preserving business logic and functional parity.

---

## 2. Transformation Pipeline Stages

```
[ Step 1: Pre-Transformation Analysis ]
       | Ingest COBOL programs, copybooks, CICS BMS maps, and JCL batch streams.
       | Generate dependency graphs and analyze cyclomatic complexity.
       v
[ Step 2: Automated Refactoring Engine ]
       | Convert procedural COBOL/PL/I code to object-oriented Java 17/21.
       | Map CICS transactional logic into Spring MVC / REST controllers.
       | Convert BMS green-screen maps into Angular or React web components.
       v
[ Step 3: Database & Dataset Modernization ]
       | Map VSAM KSDS/ESDS/RRDS and Db2 for z/OS tables to Amazon Aurora PostgreSQL.
       | Convert EBCDIC data files and COMP-3 packed decimals into ASCII numeric types.
       v
[ Step 4: Batch Stream Orchestration ]
       | Translate JCL job steps into AWS Step Functions workflows or Amazon MWAA (Airflow).
       | Replace IDCAMS, SORT, and IEBGENER utilities with AWS Glue or Python utilities.
       v
[ Step 5: Target Cloud-Native Deployment ]
       | Package Spring Boot microservices into container images deployed to Amazon ECS
       | Fargate or Amazon EKS (Standard / Auto Mode).
```

---

## 3. Architecture Blueprint: Refactored Spring Boot Architecture

### CICS Online Transactions to REST Microservices
- **Input**: CICS `EXEC CICS RECEIVE`, `EXEC CICS SEND MAP`, `EXEC CICS READ`.
- **Output**: Spring Boot `@RestController` with `@PostMapping` and JPA repository calls.

```java
@RestController
@RequestMapping("/api/v1/customers")
public class CustomerInquiryController {

    private final CustomerService customerService;

    public CustomerInquiryController(CustomerService customerService) {
        this.customerService = customerService;
    }

    @GetMapping("/{accountNumber}")
    public ResponseEntity<CustomerResponse> getCustomerInquiry(@PathVariable String accountNumber) {
        // Business logic converted from COBOL program CUSTINQ01
        CustomerDto customer = customerService.findCustomerByAccount(accountNumber);
        return ResponseEntity.ok(CustomerMapper.toResponse(customer));
    }
}
```

### JCL Batch Jobs to AWS Step Functions
Batch job dependencies previously managed by mainframe schedulers (CA-7, Tivoli Workload Scheduler) are converted into AWS Step Functions state machines invoking ECS Fargate tasks or AWS Batch jobs.
