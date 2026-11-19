#!/usr/bin/env bash
# ==============================================================================
# CloudCorp Production Deployment: Serverless Microservices Track
# Deploys:
#   1. Cloud Run RAG Service (Knowledge Layer)
#   2. Cloud Functions 2nd Gen IT Ticket Tool (Action Layer)
#   3. Cloud Workflows Intent Router (Orchestration Layer)
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
    echo "   Please set PROJECT_ID in your .env file or run: export PROJECT_ID='your-gcp-project-id'"
    exit 1
fi

# Auto-create .env file if it does not exist (e.g. fresh clone in Cloud Shell)
if [ ! -f .env ]; then
    echo "📄 Creating default .env for project $PROJECT_ID..."
    cat << EOF > .env
PROJECT_ID=${PROJECT_ID}
REGION=${REGION}
BUCKET_NAME=${BUCKET_NAME}
EMBEDDING_MODEL=text-embedding-004
GENERATIVE_MODEL=gemini-3.5-flash-lite
EOF
fi

echo "=================================================================="
echo "🚀 DEPLOYING CLOUDCORP PRODUCTION SERVERLESS MICROSERVICES"
echo "   Project ID      : $PROJECT_ID"
echo "   Region          : $REGION"
echo "   GCS Bucket      : gs://$BUCKET_NAME"
echo "   Service Account : $SERVICE_ACCOUNT"
echo "=================================================================="

# Ensure required GCP APIs are enabled (including Cloud Build and Artifact Registry)
echo "Verifying enabled GCP APIs..."
gcloud services enable \
    aiplatform.googleapis.com \
    storage.googleapis.com \
    run.googleapis.com \
    cloudfunctions.googleapis.com \
    workflows.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    --quiet

# Verify or create the lab Service Account
echo "Verifying lab service account: $SERVICE_ACCOUNT..."
if ! gcloud iam service-accounts describe "$SERVICE_ACCOUNT" --project="$PROJECT_ID" >/dev/null 2>&1; then
    echo "Creating service account $SERVICE_ACCOUNT..."
    gcloud iam service-accounts create cloudcorp-lab-sa \
        --display-name="CloudCorp Lab Service Account" \
        --project="$PROJECT_ID" \
        --quiet
    
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:$SERVICE_ACCOUNT" \
        --role="roles/editor" \
        --quiet
fi

# Step 2.5 Early: Grant Project-Level Invoker & Token Creator Roles
# Note: In student/sandbox projects (e.g. NuveLabs/UpGrad), service-level setIamPolicy is denied.
# Project-level IAM bindings grant the necessary permissions across all Cloud Run and Cloud Function resources.
echo "Authorizing service account to invoke Cloud Run and generate workflow OIDC tokens..."
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/run.invoker" \
    --quiet || true

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/iam.serviceAccountTokenCreator" \
    --quiet || true

# Step 1: Deploy Cloud Run RAG Microservice
echo ""
echo "------------------------------------------------------------------"
echo "📦 1/3: Deploying Cloud Run RAG Service (Knowledge Layer)..."
echo "------------------------------------------------------------------"
gcloud run deploy cloudcorp-rag-service \
    --source=rag_service \
    --region="$REGION" \
    --service-account="$SERVICE_ACCOUNT" \
    --no-allow-unauthenticated \
    --set-env-vars="PROJECT_ID=${PROJECT_ID},BUCKET_NAME=${BUCKET_NAME},REGION=${REGION},GENERATIVE_MODEL=gemini-3.5-flash-lite,GENAI_LOCATION=global" \
    --quiet || {
        echo "⚠️ Note: Notice received during Cloud Run IAM setting (normal in student sandboxes)."
    }

RAG_SERVICE_URL=$(gcloud run services describe cloudcorp-rag-service --region="$REGION" --format='value(status.url)')
export RAG_SERVICE_URL
echo "✅ Cloud Run RAG URL: $RAG_SERVICE_URL"

# Step 2: Deploy Cloud Function IT Helpdesk Tool
echo ""
echo "------------------------------------------------------------------"
echo "⚡ 2/3: Deploying Cloud Function IT Tool (Action Layer)..."
echo "------------------------------------------------------------------"
gcloud functions deploy cloudcorp-ticket-tool \
    --gen2 \
    --runtime=python311 \
    --source=ticket_tool \
    --entry-point=handle_it_ticket \
    --trigger-http \
    --service-account="$SERVICE_ACCOUNT" \
    --no-allow-unauthenticated \
    --region="$REGION" \
    --quiet || {
        echo "⚠️ Note: Service-level IAM notice received (expected in student sandboxes; project-level binding takes effect)."
    }

TICKET_TOOL_URL=$(gcloud functions describe cloudcorp-ticket-tool --region="$REGION" --format='value(serviceConfig.uri)')
export TICKET_TOOL_URL
echo "✅ Cloud Function Tool URL: $TICKET_TOOL_URL"

# Step 3: Deploy Cloud Workflows Intent Router
echo ""
echo "------------------------------------------------------------------"
echo "🔀 3/3: Deploying Cloud Workflows Intent Router..."
echo "------------------------------------------------------------------"
# Note: Cloud Workflows uses --location, NOT --region
gcloud workflows deploy cloudcorp-agent-workflow \
    --source=workflows/workflow.yaml \
    --location="${REGION}" \
    --service-account="cloudcorp-lab-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
    --set-env-vars="RAG_SERVICE_URL=${RAG_SERVICE_URL},TICKET_TOOL_URL=${TICKET_TOOL_URL}" \
    --quiet

echo "✅ Cloud Workflows is LIVE: cloudcorp-agent-workflow"

# Step 4: Verification Tests Across the 3 Scenarios
echo ""
echo "=================================================================="
echo "🧪 RUNNING PRODUCTION VERIFICATION TESTS"
echo "=================================================================="

echo "Test 1: Scenario 1 - Pure Policy QA..."
gcloud workflows run cloudcorp-agent-workflow \
    --location="$REGION" \
    --data='{"query": "What is remote work policy?"}'

echo ""
echo "Test 2: Scenario 2 - Hardware Malfunction -> RAG + Ticket Creation..."
gcloud workflows run cloudcorp-agent-workflow \
    --location="$REGION" \
    --data='{"query": "My laptop screen is broken and flickering, what should I do?"}'

echo ""
echo "Test 3: Scenario 3 - Incident Status Lookup..."
gcloud workflows run cloudcorp-agent-workflow \
    --location="$REGION" \
    --data='{"query": "What is the status of my ticket INC-501?", "ticket_id": "INC-501"}'

echo ""
echo "=================================================================="
echo "🎉 PRODUCTION DEPLOYMENT COMPLETE!"
echo "   • Cloud Run Service URL   : $RAG_SERVICE_URL"
echo "   • Cloud Function Tool URL : $TICKET_TOOL_URL"
echo "   • Cloud Workflow          : cloudcorp-agent-workflow"
echo "=================================================================="
