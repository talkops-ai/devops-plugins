# VPC Perimeter, PrivateLink Endpoint Policies, Transit Gateway & DNS/Network Firewall Audit

Use this reference when auditing internal segmentation, VPC Endpoint policies, Transit Gateway inspection architectures, AWS Network Firewall, Route 53 Resolver DNS Firewall, or Systems Manager Session Manager configuration.

---

## 1. VPC Endpoints & PrivateLink Data Perimeter Audit (`EC2.10`)

Gateway Endpoints (`s3`, `dynamodb`) and Interface Endpoints (`sts`, `kms`, `secretsmanager`, `ecr.api`, `ecr.dkr`, `ssm`, `ssmmessages`, `logs`, `bedrock-runtime`) keep AWS API traffic off the public Internet. However, **by default, a newly created VPC Endpoint has a wildcard `"Principal": "*", "Action": "*", "Resource": "*"` policy!**

### 1.1 Risk of Unconstrained VPC Endpoints
If an attacker compromises an EC2 instance or container inside your VPC, an unconstrained S3 or Secrets Manager VPC Endpoint allows them to **exfiltrate corporate data into an attacker-owned S3 bucket or Secrets Manager secret in an external AWS account** right over the VPC Endpoint!

### 1.2 Auditing VPC Endpoints (`ec2:DescribeVpcEndpoints`)
1. Check `VpcEndpointType` (`Gateway` vs. `Interface`), `State`, `PrivateDnsEnabled` (should be `true` for Interface Endpoints), and `SecurityGroups` (Interface Endpoint SGs should allow `TCP 443` only from the VPC CIDR or workload SGs, never `0.0.0.0/0`).
2. Inspect `PolicyDocument`:
   - Enforce the **Resource Perimeter** on VPC Endpoints by restricting `aws:ResourceOrgID` (and `aws:PrincipalOrgID`) to your AWS Organization (`o-xxxxxxxxxx`), with required exemptions for AWS-owned public buckets (`arn:aws:s3:::prod-<region>-starport-layer-bucket/*` for ECR layers, Amazon Linux yum repos, CloudWatch agent downloads):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "RestrictEndpointToOrgPrincipalsAndOrgResources",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "*",
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:PrincipalOrgID": "o-exampleorgid",
          "aws:ResourceOrgID": "o-exampleorgid"
        }
      }
    },
    {
      "Sid": "AllowECRContainerLayerDownloads",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::prod-*-starport-layer-bucket/*"
    }
  ]
}
```

---

## 2. Transit Gateway & AWS Network Firewall Inspection Architecture

### 2.1 Transit Gateway Route Table Segmentation (`ec2:DescribeTransitGatewayRouteTables`)
1. Check `DefaultAssociationRouteTable` and `DefaultPropagationRouteTable` on `ec2:DescribeTransitGateways`:
   - **Best Practice:** Both `AutoAcceptSharedAttachments`, `DefaultRouteTableAssociation`, and `DefaultRouteTablePropagation` should be `"disable"` so prod, non-prod, and inspection VPCs are isolated into explicit TGW Route Tables (`tgw-rtb-*`).
2. **Appliance Mode Check (CRITICAL for Stateful Firewall Inspection):**
   - Call `ec2:DescribeTransitGatewayVpcAttachments` on the Inspection/Firewall VPC attachment.
   - Verify `Options.ApplianceModeSupport == "enable"`. If `"disable"`, cross-AZ return traffic between spoke VPCs can bypass the Network Firewall AZ endpoint, causing asymmetric stateful packet drops!

### 2.2 AWS Network Firewall Audit (`network-firewall:DescribeFirewallPolicy`)
1. Verify `StatelessDefaultActions` and `StatelessFragmentDefaultActions` forward all packets to stateful inspection (`["aws:forward_to_sfe"]`).
2. Verify `StatefulEngineOptions.RuleOrder == "STRICT_ORDER"` with `StatefulDefaultActions` set to `["aws:drop_established", "aws:alert_established"]` (default-deny egress).
3. Call `network-firewall:DescribeLoggingConfiguration`: ensure both `FLOW` and `ALERT` logs are delivered to CloudWatch Logs or S3.

---

## 3. Route 53 Resolver DNS Firewall & GuardDuty DNS Protection

1. Call `route53resolver:ListFirewallRuleGroupAssociations` for each VPC:
   - Verify association with AWS Managed Domain Lists (`AWSManagedDomainsMalwareDomainList`, `AWSManagedDomainsBotnetCommandAndControl`, `AWSManagedDomainsAggregateThreatList`) with `Action == "BLOCK"`.
2. Verify `FailOpen` posture (`MutationProtection == "ENABLED"` on rule groups).

---

## 4. Systems Manager Session Manager Hardening vs. SSH/RDP Bastions

When recommending replacing port `22`/`3389` ingress with Systems Manager Session Manager, audit the account's `SSM-SessionManagerRunShell` preferences (`ssm:GetDocument --name SSM-SessionManagerRunShell`):

1. `kmsKeyId`: Must be populated with a Customer Managed KMS key so interactive terminal streams are encrypted end-to-end.
2. `s3BucketName` + `s3EncryptionEnabled: true` OR `cloudWatchLogGroupName` + `cloudWatchEncryptionEnabled: true`: Must be configured so every command typed during an interactive session is recorded to an immutable audit log.
3. `runAsEnabled`: Should map sessions to an unprivileged OS user (rather than default `ssm-user` with passwordless `sudo ALL=(ALL) NOPASSWD:ALL` in `/etc/sudoers.d/ssm-agent-users`).

---

## 5. VPC Traffic Mirroring for Out-of-Band IDS & Forensic Packet Capture

While VPC Flow Logs capture L3/L4 5-tuple metadata, **VPC Traffic Mirroring** copies full raw network packets (encapsulated in VXLAN UDP port `4789`) from a Nitro instance's Elastic Network Interface (ENI) to an out-of-band NIDS appliance (Suricata, Zeek, Snort behind a Network Load Balancer or Gateway Load Balancer) or a forensic packet-capture host:

1. **Read-Only Audit (`ec2:DescribeTrafficMirrorSessions`, `DescribeTrafficMirrorFilters`, `DescribeTrafficMirrorTargets`):**
   - Verify critical ingress/egress ENIs or compromised instances Under Investigation have a `TrafficMirrorSession` active.
   - Check `PacketLength`: ensure full packet payload capture (or truncated header-only capture when avoiding PII payload storage) aligns with the forensic mandate.
   - Verify the target NLB/GWLB security group allows **UDP 4789 (VXLAN)** only from the mirrored source ENI security groups or subnet CIDRs—never `0.0.0.0/0`.
2. **Tactical Incident Response Packet Capture Proposal (`approval_required: true`):**
   - During live C2 or data-exfiltration triage (`security-incident-triage`), propose creating a `TrafficMirrorSession` on the suspect ENI (`--network-interface-id eni-...`) forwarding ingress/egress TCP/UDP traffic to the dedicated IR packet-capture target before isolating the host.

