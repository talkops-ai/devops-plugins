# AWS Pricing Lookup & BCM Pricing Calculator (`awspricing`, `billing:aws-pricing`, `billing:bcm-pricing-calc`)

Price List API service codes differ from Cost Explorer service names. Use these exact codes.

## Common Service Codes

| Service | Price List Code | Cost Explorer Name |
|---------|----------------|-------------------|
| EC2 | `AmazonEC2` | `Amazon Elastic Compute Cloud - Compute` |
| Lambda | `AWSLambda` | `AWS Lambda` |
| S3 | `AmazonS3` | `Amazon Simple Storage Service` |
| RDS / Aurora | `AmazonRDS` | `Amazon Relational Database Service` |
| DynamoDB | `AmazonDynamoDB` | `Amazon DynamoDB` |
| ElastiCache | `AmazonElastiCache` | `Amazon ElastiCache` |
| Redshift | `AmazonRedshift` | `Amazon Redshift` |
| ECS / Fargate | `AmazonECS` | `Amazon Elastic Container Service` |
| EKS | `AmazonEKS` | `Amazon Elastic Kubernetes Service` |
| CloudFront | `AmazonCloudFront` | `Amazon CloudFront` |
| Bedrock | `AmazonBedrock` | `Amazon Bedrock` |
| OpenSearch | `AmazonES` | `Amazon OpenSearch Service` |

---

## Choosing Between `awspricing`, `billing:aws-pricing`, and `billing:bcm-pricing-calc`

1. **`awspricing:get_pricing` (`awslabs.aws-pricing-mcp-server` — Recommended for Multi-Region & Payload Compaction):**
   - Supports querying **multiple regions in a single call** (`region=["us-east-1", "us-west-2", "eu-west-1"]`).
   - Supports advanced filter match modes: `EQUALS`, `ANY_OF`, `CONTAINS`, and `NONE_OF`.
   - Supports `output_options={"pricing_terms": ["OnDemand", "Reserved"]}` and `exclude_free_products=True`, shrinking Price List JSON payloads by **~80%**.
   - Provides `generate_cost_report` (renders Markdown/CSV estimates), `get_bedrock_patterns`, and `get_price_list_urls`.
2. **`billing:aws-pricing` (`awslabs.billing-cost-management-mcp-server`):**
   - 4-step workflow: `get_service_codes` → `get_service_attributes` → `get_attribute_values` → `get_pricing_from_api`.
3. **`billing:bcm-pricing-calc` (AWS Billing & Cost Management Pricing Calculator):**
   - Inspects saved **Workload Estimates** (`list_workload_estimates`, `get_workload_estimate`, `list_workload_estimate_usage`) and **Bill Estimates** (`list_bill_estimates`, `get_bill_estimate`, `list_bill_estimate_line_items`, `list_bill_estimate_commitments`) that incorporate the organization's private EDP/PPA discounts and existing Savings Plans/RIs.

---

## EC2 Pricing Attributes

- Filter instances: `productFamily: "Compute Instance"`, `tenancy: "Shared"`, `operatingSystem: "Linux"`, `preInstalledSw: "NA"`, `capacitystatus: "Used"`
- Reserved Instances: `termType: "Reserved"`, check `LeaseContractLength`, `OfferingClass`, `PurchaseOption`
- Spot and Capacity Block pricing are NOT in the Price List API (use `aws ec2 describe-spot-price-history` via `aws___call_aws` for Spot rates)

## S3 Pricing Attributes

Filter storage: `productFamily: "Storage"`. Use `volumeType` (NOT `storageClass`):

| Storage Class | `volumeType` Value |
|--------------|-----------------|
| Standard | `"Standard"` |
| Infrequent Access | `"Standard - Infrequent Access"` |
| One Zone IA | `"One Zone - Infrequent Access"` |
| Glacier Instant Retrieval | `"Glacier Instant Retrieval"` |
| Glacier Flexible | `"Amazon Glacier"` |
| Glacier Deep Archive | `"Glacier Deep Archive"` |
| Intelligent-Tiering | `"Intelligent-Tiering"` |

**Intelligent-Tiering has 5 sub-tiers** with distinct `volumeType` values: `"Intelligent-Tiering Frequent Access"`, `"Intelligent-Tiering Infrequent Access"`, `"Intelligent-Tiering Archive Instant Access"`, `"IntelligentTieringArchiveAccess"`, `"IntelligentTieringDeepArchiveAccess"`. For complete IT cost analysis, also query monitoring fee (`feeCode: "S3-Monitoring and Automation-ObjectCount"`) and transition costs (`operation: "S3-INTTransition"`).

API requests: `productFamily: "API Request"`, check `group` for request type (`PUT`, `GET`).

## RDS Pricing Attributes

- `databaseEngine`: `"MySQL"`, `"PostgreSQL"`, `"MariaDB"`, `"Aurora MySQL"`, `"Aurora PostgreSQL"`, `"SQL Server"`, `"Oracle"`, `"Db2"`
- `deploymentOption`: `"Single-AZ"`, `"Multi-AZ"`, `"Multi-AZ (readable standbys)"`
- `databaseEdition`: for Oracle/SQL Server — `"Standard"`, `"Enterprise"`, `"Express"`, `"Web"`
- `licenseModel`: important for Oracle and SQL Server (`"License included"` vs `"Bring your own license"`)
- Instances: `productFamily: "Database Instance"`. Storage: `"Database Storage"`. Aurora Serverless: `"Serverless"` or `"ServerlessV2"`

## General Rules

- **Price List API control plane is only available in `us-east-1`, `eu-central-1`, and `ap-south-1`** — always specify `--region us-east-1` when calling CLI `aws pricing`
- AWS uses binary system: 1 KB = 1,024 bytes (1 GiB = 1,073,741,824 bytes)
- Monthly calculations: use **730 hours/month**
- Volume-based tiered pricing: check `beginRange` and `endRange` in `priceDimensions`
- Price List API returns public On-Demand and public RI rates only — use `billing:bcm-pricing-calc` when modeling private EDP/commitment discounts

```bash
# List available service codes
aws pricing describe-services --region us-east-1

# Get attribute values for a service
aws pricing get-attribute-values \
  --service-code AmazonEC2 --attribute-name instanceType --region us-east-1

# Get pricing for specific product
aws pricing get-products \
  --service-code AmazonEC2 --region us-east-1 \
  --filters Type=TERM_MATCH,Field=instanceType,Value=m7g.xlarge \
            Type=TERM_MATCH,Field=location,Value="US East (N. Virginia)" \
            Type=TERM_MATCH,Field=operatingSystem,Value=Linux \
            Type=TERM_MATCH,Field=tenancy,Value=Shared \
            Type=TERM_MATCH,Field=preInstalledSw,Value=NA \
            Type=TERM_MATCH,Field=capacitystatus,Value=Used
```
