# Patterns for S3 Vectors at Scale

For current limits: search AWS docs for `"S3 Vectors limitations and restrictions"`

## When to Use S3 Vectors

Use S3 Vectors for large, long-term vector data that doesn't require the
high-throughput performance of in-memory vector databases. S3 Vectors provides a
cost-optimized data foundation with query performance optimized for long-term
storage and infrequent access of data. You also benefit from a storage
architecture with strong consistency guarantees, ensuring subsequent queries
always include your most recently added data.

S3 Vectors delivers subsecond latency for infrequent queries and as low as 100ms
for more frequent queries.

## Multi-Tenant Patterns

**Per-tenant index** (recommended for isolation):

- Each tenant gets their own index within a shared vector bucket
- Queries naturally scoped to one tenant
- Easy to delete a tenant's data (delete the index)
- Use when: tenants need strict isolation, different schemas, or independent scaling

**Single index with metadata filtering** (simpler):

- All tenants share one index, filter by `tenant_id` metadata
- Simpler to manage, single query endpoint
- Use when: tenants have identical schemas and moderate scale
- Risk: noisy neighbor if one tenant dominates the index

## Batch Ingestion Pattern

For large-scale ingestion (millions of vectors):

1. Batch vectors into groups of up to 500 per PutVectors call
2. Use parallel workers with backoff on `ServiceUnavailableException`
3. For sustained throughput beyond per-index limits, shard across multiple indexes
4. Search AWS docs for `"S3 Vectors limitations and restrictions"` for current per-call and per-second limits

## SSE-KMS Encryption

To create a vector bucket with SSE-KMS:

```bash
aws s3vectors create-vector-bucket \
  --vector-bucket-name <BUCKET_NAME> \
  --encryption-configuration '{"sseType":"aws:kms","kmsKeyArn":"arn:aws:kms:<REGION>:<ACCOUNT>:key/<KEY_ID>"}'
```

You MUST use the full KMS key ARN (not alias or key ID). The KMS key policy MUST grant
`kms:GenerateDataKey` and `kms:Decrypt` to the S3 Vectors service principal `indexing.s3vectors.amazonaws.com`.
Encryption cannot be changed after bucket or index creation.

For full KMS policy examples, search AWS docs for `"S3 Vectors data encryption KMS"`.

## Migration Pattern

When migrating from another vector DB (pgVector, AOSS, etc.):

1. Create vector bucket and index matching source dimensions + distance metric
2. Export vectors from source (with metadata)
3. Batch PutVectors into S3 Vectors
4. Verify with QueryVectors using known test vectors
5. S3 Vectors only supports `cosine` and `euclidean` — if source used dotProduct,
   use `cosine` on normalized vectors as equivalent

## Vector Store Selection Matrix: S3 Vectors vs OpenSearch Service k-NN vs Aurora PostgreSQL (`pgvector`)

| Dimension | Amazon S3 Vectors | Amazon OpenSearch Service k-NN | Amazon Aurora PostgreSQL (`pgvector`) |
|---|---|---|---|
| **Primary Use Case** | Cost-effective, massive-scale vector storage (10M–billions of vectors) with sub-second query latency and zero always-on cluster/OCU floor | Ultra-low-latency (`<10–20 ms` p99) hybrid lexical (`BM25`) + vector (`HNSW`/`FAISS`/`Lucene`) search at high QPS | Transactional applications needing strict ACID relational joins alongside vector similarity (`HNSW` / `IVFFlat`) in a single SQL query |
| **Compute / Cost Floor** | **Serverless pay-per-GB + pay-per-request** (up to ~90% lower storage cost than memory-resident vector indexes; `$0` idle compute floor) | Dedicated data nodes (`r7g`/`or1`) or OpenSearch Serverless Vector Search (`>= 2 OCU` minimum floor) | Provisioned instance (`db.r7g.*`) or Aurora Serverless v2 (`ACU` scaling) |
| **Tiered Hybrid Architecture** | Use **S3 Vectors** as the durable, low-cost cold/warm vector lake (`100M+` embeddings) and selectively tier or export hot high-QPS active tenant indexes to **OpenSearch Service** | Native integration with S3 Vectors to query or hydrate warm/hot indexes without keeping all historical vectors in RAM | Best for `<10M–20M` vectors tightly coupled to relational OLTP tables |

## Generating Embeddings with Amazon Bedrock (`amazon.titan-embed-text-v2:0`)

S3 Vectors stores and queries float32 vectors but does not generate embeddings itself. Generate embeddings via `bedrock-runtime` (`InvokeModel`) before calling `s3vectors:PutVectors` or `s3vectors:QueryVectors`:

```python
import json, boto3

bedrock = boto3.client("bedrock-runtime")
s3vectors = boto3.client("s3vectors")

def embed_text(text: str, dimensions: int = 1024) -> list[float]:
    resp = bedrock.invoke_model(
        modelId="amazon.titan-embed-text-v2:0",
        contentType="application/json",
        accept="application/json",
        body=json.dumps({"inputText": text, "dimensions": dimensions, "normalize": True}),
    )
    return json.loads(resp["body"].read())["embedding"]
```

## Destructive Operation Guardrails (`delete-index` / `delete-vector-bucket`)

- **Never execute `aws s3vectors delete-index` or `aws s3vectors delete-vector-bucket` without explicit operator approval (`aws-mutation-gate.py`)**.
- **Blast Radius**: Deleting a vector index permanently destroys all stored vector embeddings and metadata in that index; recovering requires re-chunking and re-embedding the original source corpus through your embedding model (incurring significant Bedrock token cost and ingestion time). Always prefer filtering by `doc_version` / `tenant_id` metadata or creating a new versioned index (`kb-chunks-v2`) and validating before retiring an old index.
