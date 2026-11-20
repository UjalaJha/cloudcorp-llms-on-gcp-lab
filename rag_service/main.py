import os
import traceback
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google.cloud import storage
import vertexai
from vertexai.language_models import TextEmbeddingModel, TextEmbeddingInput
from vertexai.generative_models import GenerativeModel

app = FastAPI(
    title="CloudCorp RAG Service",
    description="Production-grade lightweight RAG microservice on Cloud Run"
)

PROJECT_ID = os.environ.get("PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT")
REGION = os.environ.get("REGION", "us-central1")
BUCKET_NAME = os.environ.get("BUCKET_NAME") or f"{PROJECT_ID}-cloudcorp-policies"

EMBED_MODEL = None
LLM_MODEL = None
CHUNKS = []

def get_models():
    """Lazily initialize Vertex AI models upon first request to ensure fast container startup."""
    global EMBED_MODEL, LLM_MODEL
    if EMBED_MODEL is None:
        vertexai.init(project=PROJECT_ID, location=REGION)
        EMBED_MODEL = TextEmbeddingModel.from_pretrained("text-embedding-004")
    if LLM_MODEL is None:
        vertexai.init(project=PROJECT_ID, location=os.environ.get("GENAI_LOCATION", "global"))
        LLM_MODEL = GenerativeModel(os.environ.get("GENERATIVE_MODEL", "gemini-3.5-flash-lite"))
    return EMBED_MODEL, LLM_MODEL

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

def load_and_index():
    global CHUNKS
    if CHUNKS:
        return
    
    embed_model, _ = get_models()
    client = storage.Client(project=PROJECT_ID)
    bucket = client.bucket(BUCKET_NAME)
    
    all_chunks = []
    blobs = list(bucket.list_blobs())
    for blob in blobs:
        if blob.name.endswith(".txt"):
            text = blob.download_as_text()
            chunks = chunk_document(blob.name, text)
            all_chunks.extend(chunks)
            
    if all_chunks:
        doc_inputs = [
            TextEmbeddingInput(text=c["text"], task_type="RETRIEVAL_DOCUMENT")
            for c in all_chunks
        ]
        embeddings = embed_model.get_embeddings(doc_inputs)
        for i, emb in enumerate(embeddings):
            all_chunks[i]["vector"] = np.array(emb.values)
            
    CHUNKS = all_chunks

class QueryRequest(BaseModel):
    query: str
    top_k: int = 3

@app.get("/")
def root():
    return {
        "status": "healthy",
        "service": "CloudCorp RAG Microservice",
        "project_id": PROJECT_ID,
        "region": REGION,
        "bucket_name": BUCKET_NAME
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "project_id": PROJECT_ID,
        "region": REGION,
        "bucket_name": BUCKET_NAME
    }

@app.post("/ask")
def ask_policy(req: QueryRequest):
    try:
        load_and_index()
        if not CHUNKS:
            return {
                "answer": f"No policy documents found in GCS bucket gs://{BUCKET_NAME}.",
                "sources": [],
                "retrieved_chunks": []
            }
        
        embed_model, llm = get_models()
        
        # Asymmetric query embedding with task_type="RETRIEVAL_QUERY"
        vertexai.init(project=PROJECT_ID, location=REGION)
        query_input = TextEmbeddingInput(text=req.query, task_type="RETRIEVAL_QUERY")
        q_vec = np.array(embed_model.get_embeddings([query_input])[0].values)
        
        # Calculate cosine similarity across all policy chunks
        scored = []
        for chunk in CHUNKS:
            dot_product = np.dot(q_vec, chunk["vector"])
            norm = np.linalg.norm(q_vec) * np.linalg.norm(chunk["vector"])
            similarity = float(dot_product / norm) if norm > 0 else 0.0
            scored.append((similarity, chunk))
            
        scored.sort(key=lambda x: x[0], reverse=True)
        top_hits = scored[:req.top_k]
        
        # Construct grounded prompt with retrieved chunks
        context_blocks = [
            f"--- Source: {item[1]['source']} (Chunk: {item[1]['chunk_id']}) ---\n{item[1]['text']}"
            for item in top_hits
        ]
        context = "\n\n".join(context_blocks)
        
        prompt = (
            "You are CloudCorp's enterprise policy assistant. "
            "Answer the user's question accurately, concisely, and strictly based on the provided policy context. "
            "Cite the relevant policy section or document when answering. If the context does not contain the answer, "
            "state that clearly rather than hallucinating.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {req.query}\n\n"
            "Answer:"
        )
        
        vertexai.init(project=PROJECT_ID, location=os.environ.get("GENAI_LOCATION", "global"))
        resp = llm.generate_content(prompt)
        
        return {
            "answer": resp.text.strip(),
            "sources": list(set([item[1]["source"] for item in top_hits])),
            "retrieved_chunks": [
                {
                    "chunk_id": item[1]["chunk_id"],
                    "score": round(item[0], 4),
                    "snippet": item[1]["text"][:150] + "..."
                }
                for item in top_hits
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
                "bucket_name": BUCKET_NAME
            }
        )
