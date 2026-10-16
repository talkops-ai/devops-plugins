---
name: amazon-appstream-and-workspaces-web
description: "Design, deploy, and operate Amazon AppStream 2.0 (Always-On, On-Demand, and Elastic Fleets, Image Builder, Application Entitlements) and Amazon WorkSpaces Secure Browser (WorkSpaces Web) for zero-trust browser isolation."
---

# Amazon AppStream 2.0 & WorkSpaces Secure Browser Operations

Use this skill when designing or operating **Amazon AppStream 2.0** application/desktop streaming fleets or **Amazon WorkSpaces Secure Browser (WorkSpaces Web)** for secure enterprise browser access.

## 1. AppStream 2.0 Fleet Type Selection

| Fleet Type | Startup Latency | Cost Model | Best For |
| :--- | :--- | :--- | :--- |
| **Elastic Fleet** |Seconds (Serverless AWS-managed pool) | Pay per streaming second (no idle capacity cost) | Unpredictable traffic; apps packaged as **App Blocks (VHD)** on S3 |
| **On-Demand Fleet** | ~1–2 minutes cold start | Full rate while streaming + minimal stopped instance fee (~$0.025/hr) | Predictable business-hours workloads using custom Image Builder images |
| **Always-On Fleet** | Instant | Full instance rate 24/7 across configured capacity | Mission-critical apps requiring zero wait time |

## 2. AppStream 2.0 Scaling & Image Pipeline

1. **Image Builder & App Block Builder**:
   - Place Image Builder instances in private subnets with NAT Gateway or VPC Endpoints (`com.amazonaws.<region>.appstream.api`, `com.amazonaws.<region>.appstream.streaming`, `com.amazonaws.<region>.s3`).
   - Run `Image Assistant` CLI to optimize application launch performance before snapshotting.
2. **Application Auto Scaling**:
   - Configure step scaling policies on `CapacityUtilization`:
     - **Scale Out**: When `CapacityUtilization >= 75%` for 2 consecutive minutes, add 25% capacity.
     - **Scale In**: When `CapacityUtilization <= 25%` for 15 consecutive minutes, remove 10% capacity.

## 3. Amazon WorkSpaces Secure Browser (WorkSpaces Web)

- Provides isolated, ephemeral Chromium browser sessions running in AWS without managing images or fleets:
  - **Authentication**: Requires SAML 2.0 Identity Provider (IAM Identity Center, Okta, Entra ID).
  - **Data Loss Prevention (DLP)**: Configure `UserSettings` (`CopyAllowed`, `PasteAllowed`, `DownloadAllowed`, `UploadAllowed`, `PrintAllowed`, `ToolbarConfiguration`) and `BrowserSettings` (Managed Chrome policies JSON, URL allow/block lists).
  - **Private Network Access**: Attach the WorkSpaces Web Portal to private VPC subnets + Security Groups to access internal intranet apps without client VPNs.
