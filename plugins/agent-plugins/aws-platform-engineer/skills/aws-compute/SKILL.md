---
name: aws-compute
description: "Provisions, scales, and operates Amazon EC2 virtual-machine workloads: instance-type selection (Graviton/Arm64, burstable T credits, GPU, instance store vs EBS), launch templates, Auto Scaling groups (scaling policies, instance refresh, mixed instances, Spot, warm pools, lifecycle hooks), IMDSv2, placement groups, Elastic IPs, AMI lifecycle, and Systems Manager fleet operations (Session Manager, Run Command, Patch Manager). Applies to EC2 instance and fleet questions, InsufficientInstanceCapacity, CPU-credit/surplus charges, IMDSv2 401s, instances stuck in Pending:Wait, ASG not replacing unhealthy instances, status-check failures, SSH refused/timed out, or instances missing as SSM managed nodes. For a single secure instance launch, the launching-ec2-instance-with-best-practices skill is more appropriate; for instance profiles, see setting-up-ec2-instance-profiles; for Image Builder, see amazon-ec2-image-builder. Does NOT cover Lambda, ECS/Fargate, EKS, VPC/ALB/NLB design, or IAM policy authoring."
metadata:
  version: "2"
---

# Amazon EC2 Compute

Best experience with the AWS MCP server; also works with the AWS CLI alone — no hard dependency on either.

## Critical Warnings

**Launch configurations are deprecated** and do not support current EC2 instance types; new accounts cannot create them. Use launch templates for every new Auto Scaling group. See [auto-scaling.md](references/auto-scaling.md).

**ASGs ignore ELB health checks by default**: An Auto Scaling group only uses EC2 status checks unless you set `--health-check-type ELB`. Without it, instances failing the load balancer's health check stay in service forever. See [auto-scaling.md](references/auto-scaling.md).

**IMDSv2 hop limit breaks containers**: the default `HttpPutResponseHopLimit` of 1 makes the IMDSv2 token PUT response fail to reach a containerized process (the extra hop exceeds the response TTL), so the token request times out. Set `HttpPutResponseHopLimit=2` for bridge/awsvpc container workloads. (If IMDSv2 is *required*, a subsequent tokenless GET returns `401`; if optional, it silently falls back to IMDSv1.) See [provisioning.md](references/provisioning.md).

**T3/T3a/T4g default to unlimited mode**: Unlike T2 (standard), these burst without throttling but bill surplus CPU credits when 24h-average CPU exceeds baseline — a silent cost leak. See [instance-selection.md](references/instance-selection.md).

**Instance store is ephemeral**: Data on instance store volumes is lost on stop, hibernate, terminate, instance-type change, and host failure — it survives only a reboot. Put anything durable on EBS/EFS/S3. See [instance-selection.md](references/instance-selection.md).

## Which do you need?

| If you're deciding... | Guidance |
|-----------------------|----------|
| Instance family / size / Graviton / GPU / burstable | [instance-selection.md](references/instance-selection.md) — start with the workload→family table |
| How to define instances once and reuse (launch template) | [provisioning.md](references/provisioning.md) |
| How to run many instances that scale automatically | [auto-scaling.md](references/auto-scaling.md) |
| How to access/patch/manage instances without SSH keys | [systems-manager.md](references/systems-manager.md) |

## Quick Navigation

| You want to... | Go to |
|----------------|-------|
| Pick an instance type, Graviton vs x86, burstable credits, GPU, instance store vs EBS | [instance-selection.md](references/instance-selection.md) |
| Create a launch template, user data, key pairs, IMDSv2, placement groups, Elastic IPs | [provisioning.md](references/provisioning.md) |
| Set up or fix an Auto Scaling group, scaling policies, instance refresh, Spot, lifecycle hooks | [auto-scaling.md](references/auto-scaling.md) |
| Get SSH-less access, patch a fleet, or fix an instance not showing as a managed node | [systems-manager.md](references/systems-manager.md) |
| Create, share, or retire (deprecate/disable/deregister) an AMI | [ami-management.md](references/ami-management.md) |
| Fix something broken (can't connect, status-check fail, capacity error, stuck instances) | [troubleshooting.md](references/troubleshooting.md) |

## Common Workflows

**"Stand up an autoscaling web fleet"** → Create a launch template (AMI, type, IMDSv2), then an ASG referencing it with `--health-check-type ELB` and a target-tracking policy, see [auto-scaling.md](references/auto-scaling.md). For the public entry point, secure the load balancer (TLS/ACM, WAF, security response headers) per the Security Considerations below and the load-balancer notes in [auto-scaling.md](references/auto-scaling.md) — the load-balancer build itself belongs to `aws-networking`.

**"Roll out a new AMI to my fleet"** → New launch template version → instance refresh; pin a numeric launch-template version so rollback works, see [auto-scaling.md](references/auto-scaling.md).

**"Connect to a private instance without a bastion"** → Give the instance SSM permissions (an instance profile with `AmazonSSMManagedInstanceCore`, or account-level DHMC) plus a network path, then use Session Manager, see [systems-manager.md](references/systems-manager.md).

**"Cut EC2 cost"** → Right-size (burstable vs fixed-performance), Graviton where the app supports Arm64, Spot with `price-capacity-optimized` for fault-tolerant fleets, release idle Elastic IPs, see [instance-selection.md](references/instance-selection.md).

## Troubleshooting

| Symptom | Likely cause | Quick fix |
|---------|-------------|-----------|
| SSH "Connection timed out" | Network path (SG/NACL/route/no public IP) | Open TCP 22 from your IP; check route to IGW; verify public IP — see [troubleshooting.md](references/troubleshooting.md) |
| SSH "Connection refused" | Host: sshd down or still booting | Wait for boot; check sshd/port via Session Manager or serial console |
| `InsufficientInstanceCapacity` | AWS lacks capacity of that type in the AZ (NOT a quota) | Try another AZ / instance type / retry; don't request a quota increase |
| `InstanceLimitExceeded` | vCPU quota reached (this IS a quota) | Request a Service Quotas increase for the instance family |
| ASG never replaces LB-unhealthy instances | Health check type still EC2 | Set `--health-check-type ELB` |
| Instances stuck in `Pending:Wait`, terminated after ~1h | Lifecycle hook never completed (heartbeat 3600s, default ABANDON) | Call `complete-lifecycle-action` CONTINUE, or set DefaultResult CONTINUE |
| System status check failed | AWS host/hardware | Stop/start to migrate to new hardware (reboot won't) |
| Instance status check failed | Instance OS/network config | Reboot or fix the OS/network config |

Full tables and more errors in [troubleshooting.md](references/troubleshooting.md).

## Security Considerations

- **Enforce IMDSv2** (`HttpTokens=required`) on launch templates to block SSRF-based credential theft; set the account-level default per Region (applies to new launches only).
- **Prefer Session Manager over inbound SSH** — no open port 22, no key management, and a CloudTrail record of session API calls; enable Session Manager session logging to CloudWatch Logs/S3 (off by default) to capture the in-session commands themselves — see [systems-manager.md](references/systems-manager.md).
- **Use instance profiles, never embedded credentials**; scope the role to least privilege.
- **Encrypt EBS/AMIs**; to share an encrypted AMI cross-account, re-encrypt under a customer-managed KMS key (the default `aws/ebs` key can't be shared).
- **Enable CloudTrail** in all Regions to audit EC2/ASG/SSM API activity, and alarm on sensitive actions (security-group changes, `RunInstances`/`TerminateInstances` from unexpected principals) so unauthorized changes surface.
- **For public-facing web fleets**, encrypt traffic in transit with an ACM certificate on the load balancer's HTTPS listener and add AWS WAF for defense in depth against common web exploits — the load-balancer/WAF setup itself lives in `aws-networking`.
- For hardening beyond this guidance, see [AWS EC2 security best practices](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-security.html) and CIS Benchmarks for the guest OS.

## Not Covered By This Skill

- **Launching a single hardened instance with best-practice defaults** → use the `launching-ec2-instance-with-best-practices` skill
- **Creating IAM roles / instance profiles for EC2** → use the `setting-up-ec2-instance-profiles` skill
- **Building AMIs with an Image Builder pipeline** → use the `amazon-ec2-image-builder` skill
- **Lambda / serverless** → `aws-serverless`; **ECS/Fargate** → `aws-containers`; **EKS/Kubernetes** → `kubernetes`
- **VPC, subnets, ALB/NLB, endpoints** → `aws-networking` or built-in knowledge
- **IAM policy logic and CloudWatch dashboards/agent setup** → `aws-iam`, `aws-observability`

## MCP-First Execution, Guardrails & `awsknowledge` Fallback

- **MCP-Only Execution (Zero Raw AWS CLI in Shell)**: When querying live AWS state, EC2 instances, Auto Scaling groups, CloudWatch metrics, pricing, or IaC compliance, always use connected MCP tools (`aws-mcp` `aws___run_script` / `aws___call_aws`, `cloudwatch`, `awspricing`, `awsiac`, `awsknowledge`) in strictly read-only mode. NEVER execute raw `aws` CLI commands via `run_command` / `Bash`.
- **Honest Zero-Resource Reporting**: If `0` EC2 instances or Auto Scaling groups exist in the queried region, report `0` matching resources accurately without fabricating instance IDs (`i-...`), ASG ARNs, or CloudWatch datapoints, and then provide the complete architecture or diagnostic runbook.
- **Graviton4 / Graviton3 & T3/T4g Unlimited Cost Guardrails**: Compare current-generation AWS Graviton4 (`m8g`, `c8g`, `r8g`) and Graviton3 (`m7g`, `c7g`, `r7g`) against x86 (`m7i`, `c7i`, `r7i`) using `awspricing` (`AmazonEC2` in the target region with specific `instanceType`, `operatingSystem="Linux"`, `tenancy="Shared"`, `capacitystatus="Used"` filters — max 2–3 calls). Flag sustained high CPU (e.g., 80% average CPU) on `t3`/`t3a`/`t4g` with `CpuCredits=unlimited` as a silent `CPUSurplusCreditsCharged` bill spike and recommend fixed-performance `c7g`/`c8g`/`m7g`/`m8g`.
- **Vague Workload Sizing & Cost Guard**: If the user asks for exact EC2 instance types, ASG `MinSize`/`MaxSize`/`DesiredCapacity`, or a monthly dollar cost estimate without providing workload telemetry (CPU utilization, memory footprint GiB, network/disk IOPS, or traffic RPS), refuse to fabricate or guess specific sizing numbers or monthly dollar totals and list the required CloudWatch metrics (`CPUUtilization`, `CPUSurplusCreditsCharged`, CloudWatch Agent `mem_used_percent`).
- **Read-Only & Secret Safety (`aws-mutation-gate.py`, `secret-safety.py`)**: Never run mutating commands (`ec2 terminate-instances`, `ec2 run-instances`, `autoscaling update-auto-scaling-group`, `autoscaling delete-auto-scaling-group`, `ssm send-command`) or fetch plaintext secrets (`secretsmanager get-secret-value`, `ssm get-parameter --with-decryption`); recommend `DescribeSecret` metadata checks and runtime secret fetching via Instance Profiles.
- **`awsknowledge` Edge-Case Fallback**: If **no** local `references/*.md` file covers the user's specific edge-case question (e.g., EC2 Capacity Blocks for ML, AWS Nitro Enclaves cryptographic attestation, or EC2 Fast Snapshot Restore), immediately query the connected `awsknowledge` MCP server (`aws___search_documentation` and `aws___read_documentation` — 1–2 focused searches) and answer directly.
