#!/usr/bin/env bash
# ==============================================================================
# CloudCorp Teardown: Complete Resource & IAM Cleanup Script
# Deletes all deployed lab resources, IAM bindings, and artifacts to ensure
# zero ongoing cloud charges and complete project hygiene.
#
# Author: Ujala Jha (https://ujalajha.me)
# ==============================================================================

set -eo pipefail

# 1. Automatically load configuration from .env if present
for env_file in .env ../.env; do
    if [ -f "$env_file" ]; then
        echo "📄 Loading configuration from $env_file..."
        set -a
        # shellcheck disable=SC1090
        source "$env_file"
        set +a
        break
    fi
done

# 2. Environment & Project Resolution
PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null || echo "")}"
REGION="${REGION:-us-central1}"
BUCKET_NAME="${BUCKET_NAME:-${PROJECT_ID}-cloudcorp-policies}"
SERVICE_ACCOUNT="cloudcorp-lab-sa@${PROJECT_ID}.iam.gserviceaccount.com"

if [ -z "$PROJECT_ID" ] || [ "$PROJECT_ID" == "(unset)" ]; then
    echo "❌ Error: PROJECT_ID is not defined."
    echo "   Please set PROJECT_ID or run: export PROJECT_ID='your-gcp-project-id'"
    exit 1
fi

echo "=================================================================="
echo "🧹 STARTING COMPLETE CLOUDCORP LAB TEARDOWN"
echo "   Project ID      : $PROJECT_ID"
echo "   Region          : $REGION"
echo "   GCS Bucket      : gs://$BUCKET_NAME"
echo "   Service Account : $SERVICE_ACCOUNT"
echo "=================================================================="

# 1. Delete Serverless Microservices
echo ""
echo "1/7: Deleting Cloud Workflows orchestration..."
gcloud workflows delete cloudcorp-agent-workflow \
    --location="$REGION" \
    --quiet 2>/dev/null || echo "   Cloud Workflow already removed or not found."

echo ""
echo "2/7: Deleting Cloud Functions IT helpdesk tool..."
gcloud functions delete cloudcorp-ticket-tool \
    --region="$REGION" \
    --quiet 2>/dev/null || echo "   Cloud Function already removed or not found."

echo ""
echo "3/7: Deleting Cloud Run RAG service..."
gcloud run services delete cloudcorp-rag-service \
    --region="$REGION" \
    --quiet 2>/dev/null || echo "   Cloud Run service already removed or not found."

gcloud run services delete cloudcorp-rag-service-vector-search \
    --region="$REGION" \
    --quiet 2>/dev/null || true

# If Vector Search teardown script exists, run it safely
if [ -f "rag_service_vector_search/cleanup_vector_search.sh" ]; then
    bash rag_service_vector_search/cleanup_vector_search.sh 2>/dev/null || true
fi

# 2. Delete Artifact Registry Repositories (Built by source deploys)
echo ""
echo "4/7: Deleting Artifact Registry container repositories..."
gcloud artifacts repositories delete cloud-run-source-deploy \
    --location="$REGION" \
    --quiet 2>/dev/null || echo "   Repository 'cloud-run-source-deploy' already removed or not found."

gcloud artifacts repositories delete gcf-artifacts \
    --location="$REGION" \
    --quiet 2>/dev/null || echo "   Repository 'gcf-artifacts' already removed or not found."

# 3. Delete Cloud Storage Bucket & Data
echo ""
echo "5/7: Emptying and removing Google Cloud Storage bucket..."
gcloud storage rm -r "gs://${BUCKET_NAME}" 2>/dev/null || \
    gsutil rm -r "gs://${BUCKET_NAME}" 2>/dev/null || \
    echo "   GCS bucket 'gs://$BUCKET_NAME' already removed or not found."

# 4. Remove Project-Level IAM Role Bindings
echo ""
echo "6/7: Revoking IAM role bindings for $SERVICE_ACCOUNT..."
echo "   - Removing roles/run.invoker..."
gcloud projects remove-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/run.invoker" \
    --quiet 2>/dev/null || echo "     roles/run.invoker binding already removed."

echo "   - Removing roles/iam.serviceAccountTokenCreator..."
gcloud projects remove-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/iam.serviceAccountTokenCreator" \
    --quiet 2>/dev/null || echo "     roles/iam.serviceAccountTokenCreator binding already removed."

echo "   - Removing roles/editor..."
gcloud projects remove-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/editor" \
    --quiet 2>/dev/null || echo "     roles/editor binding already removed."

# 5. Delete Service Account & Local Credentials
echo ""
echo "7/7: Deleting Service Account and local key files..."
gcloud iam service-accounts delete "$SERVICE_ACCOUNT" \
    --quiet 2>/dev/null || echo "   Service Account '$SERVICE_ACCOUNT' already removed or not found."

# Delete optional Secret Manager secret if created
gcloud secrets delete cloudcorp-agent-key --quiet 2>/dev/null || true

# Clean up local key file if present
if [ -f "gcp-key.json" ]; then
    rm -f gcp-key.json
    echo "   Removed local 'gcp-key.json'."
fi

echo ""
echo "=================================================================="
echo "✅ TEARDOWN COMPLETE! ALL LAB RESOURCES & IAM ROLES CLEANED UP."
echo "   Your total billing has ceased and the environment is clean."
echo "=================================================================="

