---
name: euc-observability-and-troubleshooting
description: "Diagnose and remediate AWS End User Computing (WorkSpaces, AppStream 2.0, WorkSpaces Secure Browser) issues: in-session latency, unhealthy workspace states, Active Directory join and GPO failures, FSLogix profile mount errors, and CloudWatch/EventBridge session telemetry."
---

# EUC Observability & Troubleshooting Runbook

Use this skill to systematically triage and resolve operational issues across Amazon WorkSpaces, AppStream 2.0, and WorkSpaces Secure Browser.

## 1. Critical CloudWatch Metrics & Thresholds

| Namespace | Metric | Warning / Critical Threshold | Root Cause & Remediation |
| :--- | :--- | :--- | :--- |
| `AWS/WorkSpaces` | `Unhealthy` | `>= 1` for 5 mins | Agent heartbeat lost, OS hang, or ENI/Security Group block on ports 4172/4195. Run `reboot-workspaces` or inspect OS event logs. |
| `AWS/WorkSpaces` | `InSessionLatency` | `> 100 ms` (warn) / `> 250 ms` (crit) | User geographically distant from region, UDP 4195 blocked falling back to TCP, or ISP packet loss. Enable **WorkSpaces Global Accelerator** or verify UDP 4195 egress. |
| `AWS/WorkSpaces` | `CPUUsage` / `MemoryUsage` | `> 85%` sustained | Under-sized bundle (e.g., Standard vs Performance/Power). Modify workspace bundle via `modify-workspace-properties`. |
| `AWS/AppStream` | `InsufficientCapacityError` | `>= 1` | Fleet `MaxUserSessions` exhausted before Auto Scaling scaled out. Increase `MinCapacity` during morning login spikes via scheduled scaling. |
| `AWS/AppStream` | `CapacityUtilization` | `> 85%` | Fleet nearing saturation; adjust target tracking or step scaling policy. |

## 2. 5-Step Triage for WorkSpaces Registration & Launch Failures

1. **Check Directory & Subnet Capacity**:
   - Verify the target VPC subnets have available IPv4 addresses (`AvailableIpAddressCount` in `describe-subnets`).
2. **Verify Management & Streaming Security Groups**:
   - Customer ENI (`eth1`) must allow outbound DNS (UDP/TCP 53), Kerberos (88), LDAP (389/636), and SMB (445) to the Active Directory domain controllers.
3. **Inspect AD Service Account & OU Permissions**:
   - Ensure the AD Connector service account has `Create/Delete Computer Objects` and `Reset Password` permissions on the target Organizational Unit (OU), and that the OU path exists.
4. **Check KMS Key Policy**:
   - If volume encryption is enabled, verify the KMS key policy grants `kms:CreateGrant`, `kms:Encrypt`, `kms:Decrypt`, and `kms:GenerateDataKeyWithoutPlaintext` to `workspaces.amazonaws.com`.
5. **Stream Session Events to CloudWatch Logs**:
   - Create an Amazon EventBridge rule matching `"source": ["aws.workspaces", "aws.appstream"]` to capture `WorkSpaces Access` and `AppStream 2.0 Session State Change` events for forensic auditing.
