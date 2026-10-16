---
name: amazon-workspaces-administration
description: "Provision, administer, and optimize Amazon WorkSpaces Personal and WorkSpaces Pools fleets: directory services (AWS Managed Microsoft AD, AD Connector, IAM Identity Center), custom bundles and image lifecycle, WorkSpaces Streaming Protocol (WSP), AutoStop vs AlwaysOn cost optimization, and multi-region standby DR."
---

# Amazon WorkSpaces Personal & WorkSpaces Pools Administration

Use this skill for end-to-end architecture, provisioning, directory integration, and fleet operations of **Amazon WorkSpaces Personal** (persistent desktops) and **Amazon WorkSpaces Pools** (non-persistent pooled virtual desktops).

## 1. Architecture & Directory Selection Matrix

| Directory Option | Supported WorkSpaces | Use Case & Trade-offs |
| :--- | :--- | :--- |
| **AWS Managed Microsoft AD** | Personal & Pools | Native cloud AD, GPO support, trusts with on-prem AD, seamless FSx for Windows File Server integration |
| **AD Connector** | Personal & Pools | Proxy to existing on-premises Active Directory over Direct Connect / Site-to-Site VPN (requires low-latency DNS/LDAPS/Kerberos) |
| **IAM Identity Center (IdC) + WorkSpaces Pools / Personal** | Pools (SAML 2.0) & Entra ID-joined Personal | Cloud-native identity without managing domain controllers; ideal for modern SaaS/cloud-first fleets |

## 2. Fleet Provisioning & Bundle Sizing Best Practices

- **Protocol**: Always standardize on **WSP (WorkSpaces Streaming Protocol)** (`UserVolumeEncryptionEnabled=true`, `RootVolumeEncryptionEnabled=true` with customer-managed KMS keys) for adaptive UDP/TCP streaming, webcam/USB redirection, and smart card support.
- **Running Mode & Cost Optimization**:
  - **AutoStop** (hourly billing + small monthly storage fee): Best for part-time, contractor, or burst users (<80 hours/month). Configure `RunningModeAutoStopTimeoutInMinutes` (e.g., `60`).
  - **AlwaysOn** (flat monthly rate): Best for full-time employees (>80 hours/month).
  - Run **WorkSpaces Cost Optimizer** (or evaluate CloudWatch `UserConnected` metrics over 30 days) to automatically convert WorkSpaces between `AUTO_stop` and `ALWAYS_ON` based on actual monthly usage thresholds.

## 3. Core CLI Operations (`aws workspaces`)

```bash
# List directories registered for WorkSpaces
aws workspaces describe-workspace-directories

# Inspect WorkSpaces fleet connection status and running modes
aws workspaces describe-workspaces \
  --query "WorkSpaces[*].{Id:WorkspaceId,User:UserName,State:State,Bundle:BundleId,Mode:WorkspaceProperties.RunningMode}"

# Check connection health and last known user connection
aws workspaces describe-workspaces-connection-status \
  --workspace-ids <ws-id>

# Reboot, Rebuild, or Migrate a WorkSpace
aws workspaces reboot-workspaces --reboot-workspace-requests WorkspaceId=<ws-id>
```

## 4. Multi-Region Resilience
- For **WorkSpaces Personal**, deploy **Multi-Region Resilience (Standby WorkSpaces)** paired with **Route 53 DNS failover** on the registration code FQDN and **Amazon FSx for Windows File Server** (with AWS Backup cross-region copy) for user profile containers (FSLogix).
