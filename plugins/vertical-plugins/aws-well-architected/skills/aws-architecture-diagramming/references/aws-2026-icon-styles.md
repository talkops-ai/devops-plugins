# AWS 2026 Official draw.io (`mxgraph.aws4.*`) Icon & Boundary Style Reference

## 1. Hierarchical Group Boundary Containers

Always nest containers accurately (`parent="<parent_cell_id>"`) using official AWS Architecture Center border and fill styles:

| Boundary Type | `style` String | Recommended Color |
|---|---|---|
| **AWS Cloud** | `points=[[0,0],[0.25,0],[0.5,0],[0.75,0],[1,0],[1,0.25],[1,0.5],[1,0.75],[1,1],[0.75,1],[0.5,1],[0.25,1],[0,1],[0,0.75],[0,0.5],[0,0.25]];outlineConnect=0;gradientColor=none;html=1;whiteSpace=wrap;fontSize=12;fontStyle=1;container=1;pointerEvents=0;collapsible=0;recursiveResize=0;shape=mxgraph.aws4.group;grIcon=mxgraph.aws4.group_aws_cloud_alt;strokeColor=#232F3E;fillColor=none;verticalAlign=top;align=left;spacingLeft=30;fontColor=#232F3E;dashed=0;` | `#232F3E` (Squid Ink) |
| **AWS Account** | `outlineConnect=0;gradientColor=none;html=1;whiteSpace=wrap;fontSize=12;fontStyle=1;container=1;pointerEvents=0;collapsible=0;recursiveResize=0;shape=mxgraph.aws4.group;grIcon=mxgraph.aws4.group_account;strokeColor=#CD2264;fillColor=none;verticalAlign=top;align=left;spacingLeft=30;fontColor=#CD2264;dashed=0;` | `#CD2264` (Pink) |
| **AWS Region** | `outlineConnect=0;gradientColor=none;html=1;whiteSpace=wrap;fontSize=12;fontStyle=1;container=1;pointerEvents=0;collapsible=0;recursiveResize=0;shape=mxgraph.aws4.group;grIcon=mxgraph.aws4.group_region;strokeColor=#00A4A6;fillColor=none;verticalAlign=top;align=left;spacingLeft=30;fontColor=#147EBA;dashed=1;` | `#00A4A6` (Teal Dashed) |
| **VPC** | `outlineConnect=0;gradientColor=none;html=1;whiteSpace=wrap;fontSize=12;fontStyle=1;container=1;pointerEvents=0;collapsible=0;recursiveResize=0;shape=mxgraph.aws4.group;grIcon=mxgraph.aws4.group_vpc2;strokeColor=#8C4FFF;fillColor=none;verticalAlign=top;align=left;spacingLeft=30;fontColor=#8C4FFF;dashed=0;` | `#8C4FFF` (Networking Purple) |
| **Availability Zone** | `fillColor=none;strokeColor=#147EBA;dashed=1;verticalAlign=top;fontStyle=1;fontColor=#147EBA;whiteSpace=wrap;html=1;container=1;pointerEvents=0;collapsible=0;` | `#147EBA` (Blue Dashed) |
| **Public Subnet** | `outlineConnect=0;gradientColor=none;html=1;whiteSpace=wrap;fontSize=12;fontStyle=1;container=1;pointerEvents=0;collapsible=0;recursiveResize=0;shape=mxgraph.aws4.group;grIcon=mxgraph.aws4.group_security_group;grStroke=0;strokeColor=#7AA116;fillColor=#F2F6E8;verticalAlign=top;align=left;spacingLeft=30;fontColor=#248814;dashed=0;` | `#248814` (Green) |
| **Private Subnet** | `outlineConnect=0;gradientColor=none;html=1;whiteSpace=wrap;fontSize=12;fontStyle=1;container=1;pointerEvents=0;collapsible=0;recursiveResize=0;shape=mxgraph.aws4.group;grIcon=mxgraph.aws4.group_security_group;grStroke=0;strokeColor=#00A4A6;fillColor=#E6F6F7;verticalAlign=top;align=left;spacingLeft=30;fontColor=#147EBA;dashed=0;` | `#147EBA` (Teal/Blue) |
| **Security Group** | `fillColor=none;strokeColor=#DD344C;dashed=1;verticalAlign=top;fontStyle=0;fontColor=#DD344C;whiteSpace=wrap;html=1;container=1;pointerEvents=0;collapsible=0;` | `#DD344C` (Security Red Dashed) |

## 2. Canonical `mxgraph.aws4.*` Service Icons (60x60 Vertex)

Base style template for any AWS service icon vertex (`width="60" height="60"`):
```text
sketch=0;outlineConnect=0;fontColor=#232F3E;gradientColor=none;fillColor=<CATEGORY_HEX>;strokeColor=#ffffff;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;fontSize=11;fontStyle=0;aspect=fixed;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.<ICON_NAME>;
```

| Category | `fillColor` | Verified `resIcon=mxgraph.aws4.<ICON_NAME>` |
|---|---|---|
| **Compute & Containers** | `#ED7100` | `ec2`, `lambda`, `ecs`, `eks`, `fargate`, `auto_scaling2`, `elastic_beanstalk` |
| **Networking & Edge** | `#8C4FFF` | `vpc`, `transit_gateway`, `elastic_load_balancing`, `cloudfront`, `route_53`, `api_gateway`, `privatelink`, `direct_connect`, `site_to_site_vpn`, `client_vpn` |
| **Storage** | `#7AA116` | `s3`, `efs`, `ebs`, `fsx`, `backup`, `storage_gateway`, `datasync` |
| **Database & Cache** | `#C925D1` | `rds`, `aurora`, `dynamodb`, `elasticache`, `memorydb_for_redis`, `neptune`, `documentdb_with_mongodb_compatibility`, `keyspaces` |
| **Application Integration** | `#E7157B` | `sqs`, `sns`, `eventbridge`, `step_functions`, `mq`, `appsync` |
| **Analytics & Lakehouse** | `#8C4FFF` | `athena`, `glue`, `kinesis_data_streams`, `kinesis_data_firehose`, `managed_streaming_for_apache_kafka`, `redshift`, `opensearch_service`, `emr`, `lake_formation` |
| **Security & Identity** | `#DD344C` | `identity_and_access_management`, `cognito`, `secrets_manager`, `key_management_service`, `waf`, `shield`, `security_hub`, `guardduty`, `inspector`, `certificate_manager`, `network_firewall` |
| **Management & Observability** | `#E7157B` | `cloudwatch`, `cloudtrail`, `Config`, `systems_manager`, `cloudformation`, `organizations`, `control_tower`, `managed_service_for_prometheus` |
| **AI & Machine Learning** | `#01A88D` | `bedrock`, `sagemaker`, `comprehend`, `textract`, `rekognition` |
