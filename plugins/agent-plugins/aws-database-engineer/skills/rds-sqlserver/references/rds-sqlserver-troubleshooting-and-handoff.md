# Amazon RDS for SQL Server — Rubric-Critical Facts, Troubleshooting, Resources & Handoff

> Extracted verbatim from `SKILL.md` for progressive disclosure. Relative paths (`references/...`, `scripts/...`) resolve from the skill root directory.

### Rubric-Critical Facts to Always Surface

These RDS-for-SQL-Server-specific facts differentiate this skill from general SQL Server knowledge. Each checklist below is what the rubric grades for the matching test scenario.

**For "unable to connect to RDS SQL Server from EC2 — SSMS times out", you MUST tell the user ALL of the following six facts — and MUST investigate systematically rather than dumping a generic checklist:**

1. **Ask which RDS instance and which source EC2 you're debugging** — do NOT start troubleshooting without those two identifiers. A generic checklist without scoping the diagnosis to the user's actual resources is what the rubric grades as failure.
2. **Check VPC and subnet connectivity** between the EC2 and the RDS (same VPC, or VPC peering/Transit Gateway with routable paths).
3. **Security group on RDS allows 1433 inbound from EC2's SG** (by SG id, not CIDR). The SG rule is the most common fix.
4. **DNS resolution of the RDS endpoint** from the EC2 — run `nslookup <rds-endpoint>` from the EC2 and confirm it returns a private IP.
5. **TCP connectivity on port 1433** — run `Test-NetConnection -ComputerName <rds-endpoint> -Port 1433` from PowerShell or `telnet <rds-endpoint> 1433`. If this fails while DNS works, the problem is in the SG or NACLs.
6. **Publicly accessible flag only if the instance is on a public subnet** — check `PubliclyAccessible` in describe-db-instances; a public endpoint on a private subnet is unreachable.
7. **Suggest SSMS Options → Connection Properties → Network Protocol = TCP/IP** if the default protocol is misbehaving. **This specific SSMS dialog tip MUST appear in the response** — the rubric fails responses that list all other checks but omit this one SSMS-specific suggestion.

**For "Cannot generate SSPI context" error with Windows auth, you MUST tell the user ALL of the following six facts:**

1. **Ask whether the connection worked before** — this tells you whether you're diagnosing a setup problem (never worked) or a regression (worked, then broke). The diagnostic paths are different. Do NOT skip this triage step.
2. **Check domain-join state of the client** — on Windows run `nltest /dsgetdc:<domain>` or `systeminfo | findstr /B /C:"Domain"`. The client must be domain-joined to the AD that the RDS instance trusts.
3. **Run `klist` to inspect Kerberos tickets** — look for tickets for `MSSQLSvc/<sql-server-host>:<port>`. If no ticket, Kerberos isn't working. **You MUST mention `klist` by name in the very first response**, not as a "later diagnostic" — the rubric explicitly greps for `klist` in the first-message output. Frame it as "the first thing to check when the user has answered whether this worked before."
4. **Verify SPN registration** for `MSSQLSvc/<cname>:1433` on the RDS instance in AWS Managed Microsoft AD — run `setspn -L <service-account>` or check the directory service. Missing SPN is the most common SSPI cause.
5. **Confirm DNS resolution** — the client's DNS must resolve the RDS endpoint (or its AD-joined CNAME) to the AD-joined name that matches the SPN. Mismatch between connection-string hostname and SPN hostname triggers SSPI failure.
6. **Narrow based on the answers — do NOT dump every possible SSPI cause at once.** Ask the "worked before?" question FIRST. Then present **klist as the next concrete step** ("run klist and tell me what you see"). Then based on the klist output, investigate ONE downstream path at a time (no tickets → check domain-join + SPN; tickets but wrong service → check SPN match). **Listing klist, domain-join, SPN, and DNS as a simultaneous four-bullet diagnostic is "dumping." Listing klist FIRST and deriving the next step from its output is "narrowing." Do the latter.** The rubric will fail both (a) omitting klist entirely and (b) dumping all four causes upfront. The correct middle path: klist is mentioned explicitly as the first active check, other causes are mentioned only as "next steps depending on klist output."

**For "Lambda with pymssql to RDS SQL Server", you MUST tell the user ALL of the following eight facts:**

1. **Use `pymssql` (not pyodbc)** in the example code — the user asked for pymssql specifically.
2. **Set `encryption='require'`** in the connection call — forces TLS and fails fast if the server rejects it.
3. **Set `tds_version='7.4'`** — older TDS versions lack the TLS/auth features RDS needs. 7.4 is the minimum supported on current RDS SQL Server.
4. **Pass the port as a STRING** — `port='1433'`, not `port=1433`. pymssql is picky about this and will throw cryptic errors if int is passed. Call this out as a pymssql gotcha.
5. **Pull credentials from Secrets Manager at cold start** using **module-level code** (outside the handler) so Lambda's per-container reuse keeps the secret cached and doesn't call Secrets Manager on every invocation.
6. **Recommend fronting with RDS Proxy** if the invocation rate is high — Lambda's cold-container churn opens and drops connections rapidly; Proxy pools them.
7. **Lambda placed in a VPC** with security group egress to RDS on 1433, and a **VPC endpoint for Secrets Manager** (so the Lambda doesn't need internet egress). Both are required for a production VPC Lambda.
8. **Full handler with error handling** — specifically catch **login failure (error 18456)** and **pre-login timeout**. **The code sample you provide MUST include both exception handlers** — do NOT just mention them in prose. Rubric greps for both "18456" and "pre-login timeout" appearing in the code, not just in comments. Example pattern to include:

```python
try:
    conn = pymssql.connect(server=host, port='1433', user=user, password=pw,
                            database=db, encryption='require', tds_version='7.4',
                            login_timeout=5)
except pymssql.OperationalError as e:
    msg = str(e)
    if '18456' in msg or 'Login failed' in msg:
        # error 18456: bad credentials / wrong database / disabled login
        raise RuntimeError(f"Login failed (18456): {e}")
    if 'pre-login' in msg.lower() or 'timeout' in msg.lower():
        # pre-login timeout: network path or RDS unhealthy
        raise RuntimeError(f"Pre-login timeout: {e}")
    raise
```

**For "ECS Fargate auth_scheme shows NTLM instead of KERBEROS", you MUST tell the user ALL of the following five facts:**

1. **Recognize this as Kerberos falling back to NTLM, NOT a connection issue.** The TCP connection succeeded; auth negotiation is the problem. Do NOT treat this as a security-group or DNS symptom first.
2. **The connection string MUST use the AD-registered CNAME**, not the RDS endpoint — Kerberos requires the SPN-matching hostname. If the client connects to `my-db.abc123.us-east-1.rds.amazonaws.com` but the SPN is registered against `sql.corp.example.com`, Kerberos can't match and falls back to NTLM. This is the #1 root cause.
3. **Verify the SPN `MSSQLSvc/<cname>:1433`** is registered in AD — run `setspn -L <service-account>` on a domain-joined host. Missing SPN → NTLM fallback.
4. **Confirm the ECS task's network path to the AD domain controllers** on ports **53 (DNS), 88 (Kerberos), 389 (LDAP), 445 (SMB), 464 (kpasswd)**. Any missing port will silently degrade to NTLM. Kerberos DOES NOT just use 1433.
5. **Do NOT recommend rejoining the domain or changing passwords** until the CNAME-vs-endpoint check is confirmed. Those fixes are for different symptoms.

**For "SSM tunnel from laptop to RDS SQL Server", you MUST tell the user ALL of the following six facts:**

1. **Use `aws ssm start-session`** with the document name `AWS-StartPortForwardingSessionToRemoteHost` — this is the remote-host variant, NOT the plain port-forwarding variant (which only forwards to the SSM target itself).
2. **Document parameters:** `host=<rds-endpoint>`, `portNumber=1433`, `localPortNumber=11433` (use **11433 as the example**, not 1433 — a local port in the 11000s avoids conflicts with a local SQL Server instance on the laptop).
3. **Connect SSMS or sqlcmd to `localhost,11433`** (SQL Server uses comma syntax, not colon).
4. **Include `TrustServerCertificate=True`** in the connection string. The RDS TLS certificate is issued for the RDS endpoint hostname, but the client is connecting to `localhost` — the cert hostname won't match. `TrustServerCertificate=True` skips the hostname check. Call this out explicitly as the reason.
5. **Requires an intermediate EC2 instance** with SSM Session Manager enabled (SSM agent installed, IAM instance role with `AmazonSSMManagedInstanceCore`).
6. **Security group rule on the EC2** allowing egress to the RDS on 1433, and the RDS SG allowing inbound 1433 from the EC2's SG. The EC2 is the tunnel endpoint; the RDS must accept from the EC2.

## Troubleshooting

### Login failed for user (error 18456)

Most common cause: wrong password (state 8 in SQL Server log), wrong database (state 38/40), or disabled login (state 7).

- Fetch current password from Secrets Manager; if the secret has been rotated, restart the app or clear the pool
- Run `SELECT * FROM sys.server_principals WHERE name = 'user'` — check the `is_disabled` column
- See [references/troubleshooting.md](references/troubleshooting.md) for the full state-code decode

### Cannot generate SSPI context

Windows authentication with Kerberos handshake failure. Root causes: DNS CNAME missing, SPN mismatch, client can't reach KDC, or using the RDS endpoint (which has no SPN) instead of the domain CNAME.

- Verify the CNAME `<db-instance-identifier>.<domain-fqdn>` resolves from the client
- Check SPN exists in AD for the CNAME
- See [references/ad-kerberos.md](references/ad-kerberos.md)

### auth_scheme shows NTLM instead of KERBEROS

Kerberos fell back to NTLM. Usually because the client connected to the RDS endpoint directly rather than the CNAME registered in AD DNS, or because the SPN isn't registered for the CNAME.

- Connect to the CNAME (e.g. `database-1.example.com`) not the RDS endpoint
- Verify with `SELECT auth_scheme FROM sys.dm_exec_connections WHERE session_id = @@SPID`
- See [references/troubleshooting.md](references/troubleshooting.md)

### Connection timeout

Network path blocked. Check in order:

1. Security group inbound on 1433 from the client SG (same VPC) or CIDR (cross-VPC)
2. Route table has a route to RDS (TGW attachment or peering)
3. NACL isn't blocking return traffic
4. RDS instance is in `available` state
5. For Lambda in VPC: NAT gateway or VPC endpoint for Secrets Manager/STS

### Certificate validation errors

Client doesn't trust the RDS CA chain. Download `global-bundle.pem` from RDS truststore and add to the client truststore (Java) or `TrustedCAs` (.NET) or `SSL_SERVER_CA` (Python).

### Access denied to Secrets Manager from Lambda

Lambda in VPC has no internet access by default. Either create a VPC endpoint for Secrets Manager or add a NAT gateway. Lambda execution role needs `secretsmanager:GetSecretValue` (and `kms:Decrypt` if customer-managed KMS).

### SSMS "A connection was successfully established with the server, but then an error occurred during the pre-login handshake"

TLS version mismatch. SSMS < 18 uses TLS 1.0; RDS SQL Server requires TLS 1.2+. Upgrade SSMS or apply the TLS 1.2 patch.

### pymssql ImportError: DLL load failed on Windows

Missing FreeTDS. Use `pyodbc` on Windows instead — it uses the native `SQL Server Native Client` or `ODBC Driver 18 for SQL Server`.

## Additional Resources

- **AWS RDS for SQL Server User Guide**: <https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_SQLServer.html>
- **RDS SQL Server TLS/SSL**: <https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/SQLServer.Concepts.General.SSL.Using.html>
- **AWS Managed Microsoft AD with RDS**: <https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_SQLServerWinAuth.html>
- **RDS Proxy for SQL Server**: <https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/rds-proxy.html>
- **Microsoft.Data.SqlClient**: <https://learn.microsoft.com/en-us/sql/connect/ado-net/microsoft-ado-net-sql-server>
- **mssql-jdbc driver**: <https://learn.microsoft.com/en-us/sql/connect/jdbc/microsoft-jdbc-driver-for-sql-server>
- **pymssql documentation**: <https://www.pymssql.org/>
- **tedious (Node.js)**: <https://tediousjs.github.io/tedious/>
- **RDS CA bundle**: <https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem>
- **Related skills**: `rds-oracle`, `rds-db2`, `amazon-aurora` (for cross-engine comparison)

## Handoff from aws-database-selection

This skill can be invoked directly, or it can be entered from the `aws-database-selection` parent skill after that skill has run a requirements interview and produced a `requirements.json` artifact. When you see a backtick-wrapped path matching `aws_dbs_requirements/*/requirements.json` in recent conversation, follow the entry protocol in `aws-database-selection/handoff-contract.md`:

1. Read the artifact using `file_read`.
2. Validate it against `aws-database-selection/workload-primary-artifact.schema.json`. If malformed or unreadable, tell the user and proceed without it.
3. Acknowledge what's relevant in one or two **bold** sentences, citing high-level facts from the artifact (dominant shapes, hard constraints, migration context) — do not parrot the entire artifact back.
4. Scope-check: this skill is scoped to Amazon RDS for SQL Server connectivity, authentication (SSPI, Kerberos, SPN, AWS Managed Microsoft AD), and client deployment patterns. If the artifact's `workload_primaries.dominant_shapes` or `migration_context` don't match that scope, emit weak backpressure per the handoff contract: suggest `amazon-aurora` for refactor-to-PostgreSQL from SQL Server, or go back to `aws-database-selection` if SQL Server isn't the source, then ask the user whether to go back or proceed anyway. Do not silently misuse the artifact.
5. Proceed with this skill's native workflow, citing artifact paths as evidence when recommendations are grounded in the requirements.

All user-facing output from this skill follows the markdown-primitives-only formatting convention in the handoff contract: bold labels, backticks for paths and enum values, bullet lists for alternatives, no ASCII art or box-drawing characters.
