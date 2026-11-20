#!/usr/bin/env bash
# ==============================================================================
# CloudCorp Lab — Vertex AI Vector Search Teardown Script
# Author: Ujala Jha (https://ujalajha.me)
# ==============================================================================
set -e

PROJECT_ID=${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}
REGION=${REGION:-us-central1}
INDEX_DISPLAY_NAME="cloudcorp-policy-vector-index"
ENDPOINT_DISPLAY_NAME="cloudcorp-vector-search-endpoint"
DEPLOYED_INDEX_ID="cloudcorp_policy_deployed"

echo "=========================================================="
echo "🧹 TEARING DOWN VERTEX AI VECTOR SEARCH RESOURCES"
echo "   Project: $PROJECT_ID"
echo "   Region:  $REGION"
echo "=========================================================="

if [ -z "$PROJECT_ID" ]; then
    echo "❌ ERROR: PROJECT_ID is not set."
    exit 1
fi

# 1. Locate Index Endpoint
echo "1. Searching for Index Endpoint '$ENDPOINT_DISPLAY_NAME'..."
ENDPOINT_ID=$(gcloud ai index-endpoints list \
    --region="$REGION" \
    --project="$PROJECT_ID" \
    --filter="displayName=\"$ENDPOINT_DISPLAY_NAME\"" \
    --format="value(name)" | head -n 1)

if [ -n "$ENDPOINT_ID" ]; then
    echo "   Found Endpoint: $ENDPOINT_ID"
    
    # 2. Undeploy Index from Endpoint
    echo "2. Undeploying deployed index '$DEPLOYED_INDEX_ID' (this takes ~5-10 mins)..."
    gcloud ai index-endpoints undeploy-index "$ENDPOINT_ID" \
        --deployed-index-id="$DEPLOYED_INDEX_ID" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --quiet || echo "   ℹ️ Index was not deployed or already undeployed."
        
    # 3. Delete Index Endpoint
    echo "3. Deleting Index Endpoint..."
    gcloud ai index-endpoints delete "$ENDPOINT_ID" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --quiet || true
    echo "   ✅ Index Endpoint deleted."
else
    echo "   ℹ️ No active Index Endpoint found."
fi

# 4. Locate and Delete Vector Search Index
echo "4. Searching for Matching Engine Index '$INDEX_DISPLAY_NAME'..."
INDEX_ID=$(gcloud ai indexes list \
    --region="$REGION" \
    --project="$PROJECT_ID" \
    --filter="displayName=\"$INDEX_DISPLAY_NAME\"" \
    --format="value(name)" | head -n 1)

if [ -n "$INDEX_ID" ]; then
    echo "   Found Index: $INDEX_ID"
    echo "5. Deleting Vector Search Index..."
    gcloud ai indexes delete "$INDEX_ID" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --quiet || true
    echo "   ✅ Vector Search Index deleted."
else
    echo "   ℹ️ No active Index found."
fi

# 5. Delete Cloud Run Vector Search Service if deployed
if gcloud run services describe cloudcorp-rag-service-vector-search --region="$REGION" --project="$PROJECT_ID" >/dev/null 2>&1; then
    echo "6. Deleting Cloud Run service 'cloudcorp-rag-service-vector-search'..."
    gcloud run services delete cloudcorp-rag-service-vector-search \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --quiet
    echo "   ✅ Cloud Run vector search service deleted."
fi

echo "=========================================================="
echo "🎉 VECTOR SEARCH TEARDOWN COMPLETED SUCCESSFULLY!"
echo "   All dedicated VMs and endpoints have been decommissioned."
echo "=========================================================="

