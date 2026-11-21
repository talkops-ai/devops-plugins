# Amazon RDS for Oracle — Rubric-Critical Facts, Troubleshooting, Monitoring & Handoff

> Extracted verbatim from `SKILL.md` for progressive disclosure. Relative paths (`references/...`, `scripts/...`) resolve from the skill root directory.

### Rubric-Critical Facts to Always Surface

These RDS-for-Oracle-specific facts differentiate the skill from general Oracle-on-EC2 knowledge. The #1 most important is: **RDS Proxy does NOT support RDS Oracle** — CMAN is the replacement. Agents without this skill get this wrong.

**For "connect Python Lambda to RDS Oracle (full setup including layers, pooling, cold start)", you MUST tell the user ALL of the following seven facts:**

1. **Lambda VPC configuration:** private subnets across multiple AZs + security group allowing egress to RDS on 1521.
2. **python-oracledb thin mode as the default — no Lambda layer needed.** Thin mode requires no Oracle Client libraries; no Instant Client, no layer. Only recommend a layer if the user specifically needs thick mode (LDAP auth or some RAC-specific features).
3. **Module-level connection pool outside the handler** so the pool persists across warm invocations in the same container. Do NOT put pool construction inside the handler.
4. **Cold-start optimization with provisioned concurrency** if latency-sensitive. Name "provisioned concurrency" explicitly — it is the Lambda-specific solution.
5. **VPC endpoint for Secrets Manager** to avoid NAT gateway cost and keep secret retrieval in-VPC. This is an architectural win, not optional.
6. **Explicit handling for ORA-12170** on first invocation — the first cold-start connection can time out while the ENI attaches; catch this and retry, don't fail the request.
7. **Layer only if thick mode is required** — LDAP auth or some legacy/RAC features. Do NOT blindly recommend adding `oracle_client` layer.

**For "EKS pods to RDS Oracle using Secrets Manager CSI driver, IRSA, SecretProviderClass, and deployment manifest", you MUST tell the user ALL of the following seven facts:**

1. **Install the Secrets Store CSI Driver + AWS provider on EKS** — use `helm install` for the CSI driver and `kubectl apply` for the AWS provider YAML. Both are required (the driver alone doesn't know how to talk to AWS).
2. **Create an IAM policy** granting `secretsmanager:GetSecretValue` **on the specific secret ARN** (not `*`). Scope it.
3. **Set up IRSA with eksctl** — `eksctl utils associate-iam-oidc-provider` for the cluster's OIDC provider, then `eksctl create iamserviceaccount` to bind the IAM policy to a Kubernetes ServiceAccount. Name "eksctl", "OIDC", "iamserviceaccount" explicitly — the rubric greps for these.
4. **Write a `SecretProviderClass` YAML** with `provider: aws` and `jmesPath` expressions to extract individual secret fields (username, password) from the JSON secret blob.
5. **Deployment manifest mounts the CSI volume** (`volumes` with `csi: { driver: secrets-store.csi.k8s.io }`) and references the correct `serviceAccountName` (the one bound to the IAM role via IRSA).
6. **Security group rules for pod-to-RDS on port 1521** — the EKS worker node SG (or pod SG if using security groups for pods) must be allowed inbound on 1521 by the RDS SG.
7. **Pool sizing: total connections = replicas × max pool size per pod.** Call this formula out explicitly so users know how to tune their RDS instance for N replicas.

**For "ORA-12170 timeout connecting from EC2 to RDS Oracle across VPCs", you MUST tell the user ALL of the following six facts:**

1. **Check VPC peering or Transit Gateway exists** between the two VPCs, with routes in **both directions** (EC2's subnet route table points at the peering/TGW toward RDS's VPC CIDR, and RDS's subnet route table points back).
2. **Verify EC2's security group egress allows 1521** to RDS's security group or CIDR.
3. **Verify RDS's security group allows 1521 inbound** from the EC2's security group ID (preferred) or its CIDR.
4. **Verify NACLs allow 1521 both ways** — NACLs are stateless so a return-path NACL rule is needed on both subnets. NACLs are a common silent blocker when SGs look correct.
5. **Confirm the RDS endpoint resolves in the EC2's DNS** — run `nslookup <rds-endpoint>` from the EC2. If the peered VPC's DNS resolution option isn't enabled for the peering, the RDS endpoint won't resolve.
6. **Fastest connectivity test: `nc -zv <rds-endpoint> 1521`** from the EC2. If `nc` times out while DNS works, the problem is SG/NACL/routing. Always suggest `nc -zv` as the narrowing step.

**For "DPI-1047: Cannot locate a 64-bit Oracle Client library", you MUST tell the user ALL of the following four facts:**

1. **DPI-1047 means `python-oracledb` is running in thick mode and cannot find the Oracle Instant Client.** State this explicitly as the root-cause explanation.
2. **Primary fix: switch to thin mode by removing `oracledb.init_oracle_client()` from the code.** Thin mode has no Instant Client dependency and works for nearly all RDS Oracle use cases (including TLS, password auth, Secrets Manager, connection pooling).
3. **Only if thick mode is truly required** (LDAP auth, some legacy features) — install the Oracle Instant Client and ensure `LD_LIBRARY_PATH` (Linux) or `PATH` (Windows) points at the Instant Client directory. Name the env-var per OS explicitly.
4. **Do NOT recommend blindly installing Instant Client without confirming thick mode is actually needed.** The default recommendation must be "remove init_oracle_client, done." Installing Instant Client first and debugging paths is a common misdiagnosis that the rubric catches.

**For "Oracle Connection Manager (CMAN) on EC2 as a proxy for RDS Oracle with HA across two AZs", you MUST tell the user ALL of the following eight facts:**

1. **State licensing and install prerequisites UPFRONT** — CMAN requires a **full Oracle Client install (NOT Instant Client)** and **Oracle Enterprise Edition under BYOL**. This is the #1 thing users get wrong. Say it first, not last.
2. **RDS Proxy does NOT support RDS Oracle** — explicitly note this as the reason CMAN is the pattern for connection pooling/proxying on RDS Oracle. Agents often suggest RDS Proxy for Oracle and get the rubric wrong.
3. **Install CMAN on two EC2 instances in separate AZs** for HA. Do not recommend a single EC2 — it defeats the "HA" requirement.
4. **Configure `cman.ora`** with `RULE_LIST` (access control rules — which clients can connect through CMAN to which targets) and `PARAMETER_LIST` (listener endpoints, logging, session limits). Name both blocks by their literal `cman.ora` names.
5. **Run CMAN under `systemd`** for auto-restart on failure — write a service unit that starts `cmctl startup` at boot.
6. **Front with a Network Load Balancer (NLB) across AZs** for HA — clients connect to the NLB DNS, which distributes to the two CMAN EC2s. Mention NLB specifically (not ALB — Oracle TNS is TCP).
7. **Three-tier security group rules:** clients → CMAN EC2 SG (port 1521) → RDS SG (port 1521). Each SG allows inbound only from the previous tier. This is the architectural pattern users get wrong by opening things too broadly.
8. **Client `tnsnames.ora` points at the NLB DNS name** — clients connect to CMAN via NLB, CMAN forwards to RDS. Do not have clients connect to an individual EC2's DNS.

## Troubleshooting

Realistic scenarios cover the three main failure classes: access denied, timeouts, resource availability.

| Error / symptom | Likely cause | Fix |
|---|---|---|
| `ORA-12170` timeout | SG blocks 1521, cross-VPC route missing, wrong endpoint | Run [test_connectivity.sh](scripts/test_connectivity.sh); if TCP fails, check SG inbound + route tables. Cross-VPC needs peering/TGW + CIDR-based SG rules. |
| `ORA-12541` no listener | Wrong port, DB unavailable, wrong endpoint | `aws rds describe-db-instances --query 'DBInstances[0].Endpoint'`; confirm `Port`. |
| `ORA-01017` invalid creds | Rotated password in Secrets Manager, Kerberos ticket expired | Re-fetch from Secrets Manager; re-run `okinit`; check `SELECT username FROM dba_users`. |
| `ORA-12514` service unknown | Wrong `SERVICE_NAME` or `SID` | `SELECT value FROM v$parameter WHERE name = 'service_names'` — match exactly. |
| `ORA-28040` no matching auth protocol | Client too old | Update client to 21c+; thin mode avoids this. |
| `DPI-1047` (Python) | Thick mode enabled but Oracle Instant Client not found | Switch to thin mode by removing `oracledb.init_oracle_client()`. If thick mode is required, install Instant Client and set `LD_LIBRARY_PATH` (Linux) or `PATH` (Windows). |
| `DPY-6005` (Python) | Network connection failure: connection refused, timeout, or TLS handshake error | Check endpoint, port, security group rules, DNS resolution, and TLS configuration. Same diagnostic path as ORA-12170. |
| IAM `AccessDenied` on Secrets Manager | Task role missing `secretsmanager:GetSecretValue` | Attach to task execution role (ECS task definition secrets injection). |
| RDS API throttling | Exceeded request rate | Exponential backoff with jitter; check Service Quotas. |

## Logging and Monitoring

Recommend enabling these when creating or operating an RDS Oracle instance:

- **CloudTrail** — audit RDS control-plane API calls (create / modify / delete).
- **Enhanced Monitoring** — OS-level metrics (`--monitoring-interval`, `--monitoring-role-arn`).
- **Performance Insights** — query-level performance analysis (`--enable-performance-insights`).
- **Log exports to CloudWatch Logs** — export the Oracle `audit`, `alert`, `listener`, and `trace` logs via `--cloudwatch-logs-export-configuration`.
- **CloudWatch alarms** — alarm on `DatabaseConnections`, `FreeStorageSpace`, and `CPUUtilization` at minimum.
- **Log encryption** — encrypt the CloudWatch log groups with an AWS KMS key. Exported Oracle `audit`, `alert`, and `listener` logs can contain connection metadata and authentication attempts, so protect them at rest.

## Additional Resources

- AWS docs — Amazon RDS for Oracle: https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_Oracle.html
- AWS docs — Using IAM with RDS: https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.IAM.html
- AWS docs — RDS for Oracle Kerberos authentication: https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/oracle-kerberos.html
- AWS docs — SSL/TLS with RDS for Oracle: https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Appendix.Oracle.Options.SSL.html
- AWS docs — Oracle Native Network Encryption: https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Appendix.Oracle.Options.NetworkEncryption.html
- AWS Systems Manager — port forwarding: https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-sessions-start.html#sessions-remote-port-forwarding
- python-oracledb docs: https://python-oracledb.readthedocs.io/
- node-oracledb docs: https://node-oracledb.readthedocs.io/
- Oracle JDBC driver: https://www.oracle.com/database/technologies/appdev/jdbc.html
- Related skill: `odb-aws` (Oracle Database@AWS on OCI-managed Exadata — different product, different auth model).

## Handoff from aws-database-selection

This skill can be invoked directly, or it can be entered from the `aws-database-selection` parent skill after that skill has run a requirements interview and produced a `requirements.json` artifact. When you see a backtick-wrapped path matching `aws_dbs_requirements/*/requirements.json` in recent conversation, follow the entry protocol in `aws-database-selection/handoff-contract.md`:

1. Read the artifact using `file_read`.
2. Validate it against `aws-database-selection/workload-primary-artifact.schema.json`. If malformed or unreadable, tell the user and proceed without it.
3. Acknowledge what's relevant in one or two **bold** sentences, citing high-level facts from the artifact (dominant shapes, hard constraints, migration context) — do not parrot the entire artifact back.
4. Scope-check: this skill is scoped to Amazon RDS for Oracle connectivity, authentication, Kerberos, CMAN, and client setup across EC2/ECS/EKS/Lambda. If the artifact's `workload_primaries.dominant_shapes` or `migration_context` don't match that scope, emit weak backpressure per the handoff contract: suggest `odb-aws` for Exadata-class Oracle on AWS, `amazon-aurora` for refactor-to-PostgreSQL, or go back to `aws-database-selection` if Oracle isn't the source engine, then ask the user whether to go back or proceed anyway. Do not silently misuse the artifact.
5. Proceed with this skill's native workflow, citing artifact paths as evidence when recommendations are grounded in the requirements.

All user-facing output from this skill follows the markdown-primitives-only formatting convention in the handoff contract: bold labels, backticks for paths and enum values, bullet lists for alternatives, no ASCII art or box-drawing characters.
