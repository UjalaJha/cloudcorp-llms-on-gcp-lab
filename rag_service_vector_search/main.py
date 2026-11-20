"""
CloudCorp Enterprise RAG Microservice with Vertex AI Vector Search
Author: Ujala Jha (https://ujalajha.me)

This production FastAPI service connects to a Vertex AI MatchingEngineIndexEndpoint
(ScaNN Approximate Nearest Neighbor) to retrieve policy chunks from millions/billions
of enterprise embeddings with sub-10ms P99 latency.
"""

import os
import json
import traceback
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google.cloud import storage
import vertexai
from vertexai.language_models import TextEmbeddingModel, TextEmbeddingInput
from vertexai.generative_models import GenerativeModel
from google.cloud import aiplatform

app = FastAPI(
    title="CloudCorp Enterprise Vector Search RAG Service",
    description="Production-grade RAG microservice backed by Vertex AI Vector Search (Matching Engine)"
)

PROJECT_ID = os.environ.get("PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT")
REGION = os.environ.get("REGION", "us-central1")
BUCKET_NAME = os.environ.get("BUCKET_NAME") or f"{PROJECT_ID}-cloudcorp-policies"
INDEX_ENDPOINT_ID = os.environ.get("INDEX_ENDPOINT_ID", "")
DEPLOYED_INDEX_ID = os.environ.get("DEPLOYED_INDEX_ID", "cloudcorp_policy_deployed")
GENAI_LOCATION = os.environ.get("GENAI_LOCATION", "global")
GENERATIVE_MODEL_NAME = os.environ.get("GENERATIVE_MODEL", "gemini-3.5-flash-lite")

EMBED_MODEL = None
LLM_MODEL = None
INDEX_ENDPOINT = None
CHUNK_METADATA = {}

def get_models():
    """Lazily initialize Vertex AI models and Vector Search Endpoint."""
    global EMBED_MODEL, LLM_MODEL, INDEX_ENDPOINT, CHUNK_METADATA
    
    if EMBED_MODEL is None:
        vertexai.init(project=PROJECT_ID, location=REGION)
        aiplatform.init(project=PROJECT_ID, location=REGION)
        EMBED_MODEL = TextEmbeddingModel.from_pretrained("text-embedding-004")
        
    if LLM_MODEL is None:
        vertexai.init(project=PROJECT_ID, location=GENAI_LOCATION)
        LLM_MODEL = GenerativeModel(GENERATIVE_MODEL_NAME)
        
    if INDEX_ENDPOINT is None and INDEX_ENDPOINT_ID:
        try:
            INDEX_ENDPOINT = aiplatform.MatchingEngineIndexEndpoint(
                index_endpoint_name=INDEX_ENDPOINT_ID,
                project=PROJECT_ID,
                location=REGION
            )
        except Exception as e:
            print(f"⚠️ Warning: Could not connect to Vector Search Endpoint '{INDEX_ENDPOINT_ID}': {e}")

    if not CHUNK_METADATA:
        try:
            storage_client = storage.Client(project=PROJECT_ID)
            bucket = storage_client.bucket(BUCKET_NAME)
            blob = bucket.blob("vector_search_metadata/chunks_meta.json")
            if blob.exists():
                CHUNK_METADATA = json.loads(blob.download_as_text())
                print(f"✅ Loaded metadata for {len(CHUNK_METADATA)} policy chunks from GCS.")
        except Exception as e:
            print(f"⚠️ Could not load chunk metadata from GCS: {e}")

    return EMBED_MODEL, LLM_MODEL, INDEX_ENDPOINT

class QueryRequest(BaseModel):
    query: str
    top_k: int = 3

@app.get("/")
def root():
    return {
        "status": "healthy",
        "service": "CloudCorp Enterprise Vector Search RAG Microservice",
        "backend": "Vertex AI Vector Search (Matching Engine)",
        "project_id": PROJECT_ID,
        "region": REGION,
        "bucket_name": BUCKET_NAME,
        "index_endpoint_id": INDEX_ENDPOINT_ID or "NOT_CONFIGURED",
        "deployed_index_id": DEPLOYED_INDEX_ID
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "project_id": PROJECT_ID,
        "index_endpoint_configured": bool(INDEX_ENDPOINT_ID)
    }

@app.post("/ask")
def ask_policy(req: QueryRequest):
    try:
        embed_model, llm, endpoint = get_models()
        
        # Asymmetric query embedding with task_type="RETRIEVAL_QUERY"
        vertexai.init(project=PROJECT_ID, location=REGION)
        query_input = TextEmbeddingInput(text=req.query, task_type="RETRIEVAL_QUERY")
        q_vec = [float(x) for x in embed_model.get_embeddings([query_input])[0].values]

        retrieved_items = []
        
        # 1. Query Vertex AI Vector Search Endpoint if configured
        if endpoint and DEPLOYED_INDEX_ID:
            response = endpoint.find_neighbors(
                deployed_index_id=DEPLOYED_INDEX_ID,
                queries=[q_vec],
                num_neighbors=req.top_k
            )
            
            if response and len(response) > 0:
                for neighbor in response[0]:
                    chunk_id = neighbor.id
                    distance = getattr(neighbor, "distance", 0.0)
                    meta = CHUNK_METADATA.get(chunk_id, {
                        "source": chunk_id.split("#")[0] if "#" in chunk_id else "policy",
                        "text": f"Policy content for chunk {chunk_id}"
                    })
                    retrieved_items.append({
                        "chunk_id": chunk_id,
                        "source": meta.get("source", "unknown"),
                        "text": meta.get("text", ""),
                        "distance": round(float(distance), 4)
                    })
        else:
            # Fallback note if Vector Search Index Endpoint is not yet deployed
            return {
                "answer": (
                    "ℹ️ [Vertex AI Vector Search Info]: The Vector Search Index Endpoint is not yet deployed. "
                    "Run 'python rag_service_vector_search/index_policies.py' to build and deploy the Tree-AH index, "
                    "or deploy the primary in-memory Cloud Run service (rag_service/) for zero-cost operation."
                ),
                "backend": "Vertex AI Vector Search (Not Deployed)",
                "sources": [],
                "retrieved_chunks": []
            }

        if not retrieved_items:
            return {
                "answer": "No relevant policy documents found in the Vector Search index.",
                "sources": [],
                "retrieved_chunks": []
            }

        # 2. Construct Grounded Prompt with Vector Search Context
        context_blocks = [
            f"--- Source: {item['source']} (Chunk: {item['chunk_id']}) ---\n{item['text']}"
            for item in retrieved_items
        ]
        context = "\n\n".join(context_blocks)

        prompt = (
            "You are CloudCorp's enterprise policy assistant. "
            "Answer the user's question accurately, concisely, and strictly based on the provided policy context retrieved "
            "via Vertex AI Vector Search. "
            "Cite the relevant policy section or document when answering. If the context does not contain the answer, "
            "state that clearly rather than hallucinating.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {req.query}\n\n"
            "Answer:"
        )

        vertexai.init(project=PROJECT_ID, location=GENAI_LOCATION)
        resp = llm.generate_content(prompt)

        return {
            "answer": resp.text.strip(),
            "backend": "Vertex AI Vector Search (Tree-AH / ScaNN)",
            "sources": list(set([item["source"] for item in retrieved_items])),
            "retrieved_chunks": [
                {
                    "chunk_id": item["chunk_id"],
                    "distance": item["distance"],
                    "snippet": item["text"][:150] + "..." if len(item["text"]) > 150 else item["text"]
                }
                for item in retrieved_items
            ]
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "type": type(e).__name__,
                "project_id": PROJECT_ID,
                "index_endpoint_id": INDEX_ENDPOINT_ID
            }
        )

