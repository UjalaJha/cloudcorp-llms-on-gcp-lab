"""
CloudCorp Enterprise Vector Search Indexing Script
Author: Ujala Jha (https://ujalajha.me)

This script:
1. Downloads policy documents from GCS bucket.
2. Chunks documents along semantic section delimiters (\n---).
3. Generates 768-dimensional embeddings using text-embedding-004.
4. Uploads formatted embeddings JSONL to GCS for Vertex AI Vector Search.
5. Creates a Vertex AI Vector Search Tree-AH (ScaNN) Index.
6. Creates a MatchingEngineIndexEndpoint with public endpoint enabled.
7. Deploys the Index to the Endpoint and prints the configuration for Cloud Run.
"""

import os
import json
import time
import numpy as np
from google.cloud import storage
import vertexai
from vertexai.language_models import TextEmbeddingModel, TextEmbeddingInput
from google.cloud import aiplatform

PROJECT_ID = os.environ.get("PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT")
REGION = os.environ.get("REGION", "us-central1")
BUCKET_NAME = os.environ.get("BUCKET_NAME", f"{PROJECT_ID}-cloudcorp-policies")
INDEX_DISPLAY_NAME = "cloudcorp-policy-vector-index"
ENDPOINT_DISPLAY_NAME = "cloudcorp-vector-search-endpoint"
DEPLOYED_INDEX_ID = "cloudcorp_policy_deployed"

if not PROJECT_ID:
    raise ValueError("PROJECT_ID environment variable is required!")

print(f"===========================================================")
print(f"🚀 CloudCorp Vertex AI Vector Search Pipeline")
print(f"   Project:  {PROJECT_ID}")
print(f"   Region:   {REGION}")
print(f"   Bucket:   gs://{BUCKET_NAME}")
print(f"===========================================================\n")

# 1. Initialize Vertex AI and Cloud Storage
vertexai.init(project=PROJECT_ID, location=REGION)
aiplatform.init(project=PROJECT_ID, location=REGION)
storage_client = storage.Client(project=PROJECT_ID)
bucket = storage_client.bucket(BUCKET_NAME)

# 2. Chunking Logic
def chunk_document(source_name: str, text: str):
    sections = text.split("\n---")
    results = []
    for idx, sec in enumerate(sections):
        cleaned = sec.strip()
        if len(cleaned) > 20:
            results.append({
                "source": source_name,
                "chunk_id": f"{source_name}#sec{idx+1}",
                "text": cleaned
            })
    return results

print("1. Reading policy documents from GCS...")
blobs = [b for b in bucket.list_blobs() if b.name.endswith(".txt")]
if not blobs:
    raise RuntimeError(f"No policy text files found in gs://{BUCKET_NAME}. Run Section 1 first.")

all_chunks = []
for blob in blobs:
    content = blob.download_as_text()
    chunks = chunk_document(blob.name, content)
    all_chunks.extend(chunks)
    print(f"   • Loaded '{blob.name}' -> {len(chunks)} semantic chunks")

# Also save chunk text mapping to GCS so the microservice can reconstruct text from vector IDs
chunk_metadata = {c["chunk_id"]: {"source": c["source"], "text": c["text"]} for c in all_chunks}
meta_blob = bucket.blob("vector_search_metadata/chunks_meta.json")
meta_blob.upload_from_string(json.dumps(chunk_metadata, indent=2))
print(f"   ✅ Saved chunk text metadata to gs://{BUCKET_NAME}/vector_search_metadata/chunks_meta.json")

# 3. Generate Embeddings
print(f"\n2. Generating embeddings for {len(all_chunks)} chunks with text-embedding-004...")
embed_model = TextEmbeddingModel.from_pretrained("text-embedding-004")
doc_inputs = [TextEmbeddingInput(text=c["text"], task_type="RETRIEVAL_DOCUMENT") for c in all_chunks]
embeddings = embed_model.get_embeddings(doc_inputs)

# 4. Format JSONL for Vertex AI Vector Search
# Format: {"id": "chunk_id", "embedding": [float, ...]}
jsonl_lines = []
for chunk, emb in zip(all_chunks, embeddings):
    record = {
        "id": chunk["chunk_id"],
        "embedding": [float(x) for x in emb.values]
    }
    jsonl_lines.append(json.dumps(record))

jsonl_content = "\n".join(jsonl_lines)
gcs_data_dir = "vector_search_data"
gcs_data_file = f"{gcs_data_dir}/embeddings.json"
blob = bucket.blob(gcs_data_file)
blob.upload_from_string(jsonl_content)
gcs_uri = f"gs://{BUCKET_NAME}/{gcs_data_dir}"
print(f"   ✅ Uploaded {len(jsonl_lines)} vector records to {gcs_uri}/embeddings.json")

# 5. Create or Get Vertex AI Vector Search Index (Tree-AH / ScaNN)
print("\n3. Creating Vertex AI Vector Search Index (Tree-AH)...")
existing_indexes = aiplatform.MatchingEngineIndex.list(filter=f'display_name="{INDEX_DISPLAY_NAME}"')

if existing_indexes:
    index = existing_indexes[0]
    print(f"   ℹ️ Using existing Index: {index.resource_name}")
else:
    print(f"   ⏳ Initiating Index build from {gcs_uri} (this takes ~15-20 mins in GCP)...")
    index = aiplatform.MatchingEngineIndex.create_tree_ah_index(
        display_name=INDEX_DISPLAY_NAME,
        contents_delta_uri=gcs_uri,
        dimensions=768,
        approximate_neighbors_count=10,
        distance_measure_type="DOT_PRODUCT_DISTANCE",
        description="CloudCorp Policy Vector Search Index",
        sync=True
    )
    print(f"   ✅ Created Vector Search Index: {index.resource_name}")

# 6. Create or Get Vector Search Index Endpoint
print("\n4. Configuring Matching Engine Index Endpoint...")
existing_endpoints = aiplatform.MatchingEngineIndexEndpoint.list(
    filter=f'display_name="{ENDPOINT_DISPLAY_NAME}"'
)

if existing_endpoints:
    endpoint = existing_endpoints[0]
    print(f"   ℹ️ Using existing Endpoint: {endpoint.resource_name}")
else:
    print("   ⏳ Creating new Index Endpoint with public endpoint enabled...")
    endpoint = aiplatform.MatchingEngineIndexEndpoint.create(
        display_name=ENDPOINT_DISPLAY_NAME,
        description="CloudCorp Public Index Endpoint for Cloud Run Microservice",
        public_endpoint_enabled=True,
        sync=True
    )
    print(f"   ✅ Created Index Endpoint: {endpoint.resource_name}")

# 7. Deploy Index to Endpoint
print("\n5. Deploying Index to Endpoint...")
deployed_indexes = [d.id for d in endpoint.deployed_indexes]
if DEPLOYED_INDEX_ID in deployed_indexes:
    print(f"   ℹ️ Index already deployed under id: '{DEPLOYED_INDEX_ID}'.")
else:
    print(f"   ⏳ Deploying index with e2-standard-2 node (takes ~15-20 mins)...")
    endpoint.deploy_index(
        index=index,
        deployed_index_id=DEPLOYED_INDEX_ID,
        display_name="cloudcorp_policy_deployed",
        machine_type="e2-standard-2",
        min_replica_count=1,
        max_replica_count=1,
        sync=True
    )
    print(f"   ✅ Index deployed successfully!")

print("\n" + "=" * 60)
print("🎉 VERTEX AI VECTOR SEARCH SETUP COMPLETE!")
print(f"   INDEX_ENDPOINT_ID={endpoint.name}")
print(f"   DEPLOYED_INDEX_ID={DEPLOYED_INDEX_ID}")
print("\nCopy these to your .env or Cloud Run environment variables:")
print(f"INDEX_ENDPOINT_ID={endpoint.name}")
print(f"DEPLOYED_INDEX_ID={DEPLOYED_INDEX_ID}")
print("=" * 60)

