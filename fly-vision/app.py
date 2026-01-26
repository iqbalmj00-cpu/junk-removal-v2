"""
Fly.io Vision Pipeline Service

FastAPI server running the v4 vision pipeline.
- POST /process - accepts images, returns quote JSON
- X-Internal-Token auth
- Concurrency limiting
"""

import os
import asyncio
import json
import time
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Concurrency semaphore (max 3 concurrent pipelines)
MAX_CONCURRENT = 3
pipeline_semaphore = asyncio.Semaphore(MAX_CONCURRENT)

# Auth token from env
INTERNAL_TOKEN = os.environ.get("INTERNAL_TOKEN", "dev-token-change-me")


# ==============================================================================
# Request/Response Models
# ==============================================================================

class ImageInput(BaseModel):
    id: str
    b64: str
    mime: Optional[str] = "image/jpeg"


class ProcessRequest(BaseModel):
    images: List[ImageInput]
    context: Optional[dict] = {}


class QuoteResponse(BaseModel):
    quote: dict
    debug: Optional[dict] = None


# ==============================================================================
# Lifespan
# ==============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Fly Vision Service starting...")
    yield
    print("👋 Fly Vision Service shutting down...")


# ==============================================================================
# App
# ==============================================================================

app = FastAPI(
    title="Junk Vision Pipeline",
    version="4.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_methods=["POST"],
    allow_headers=["*"],
)


# ==============================================================================
# Auth Middleware
# ==============================================================================

def verify_token(x_internal_token: Optional[str] = Header(None)):
    """Verify internal token for Vercel → Fly auth."""
    if x_internal_token != INTERNAL_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True


# ==============================================================================
# Health Check
# ==============================================================================

@app.get("/health")
async def health():
    return {"status": "ok", "concurrent_slots": MAX_CONCURRENT}


# ==============================================================================
# Main Endpoint
# ==============================================================================

@app.post("/process", response_model=QuoteResponse)
async def process_images(
    request: ProcessRequest,
    x_internal_token: Optional[str] = Header(None)
):
    """
    Process images through the v4 vision pipeline.
    
    Args:
        images: List of {id, b64, mime}
        context: Optional context like {zip, mode}
    
    Returns:
        {quote: {...}, debug: {...}}
    """
    # Auth check
    verify_token(x_internal_token)
    
    # Validate payload size (max 10 images, each ~10MB)
    if len(request.images) > 10:
        raise HTTPException(status_code=400, detail="Max 10 images allowed")
    
    for img in request.images:
        if len(img.b64) > 15_000_000:  # ~10MB after base64 encoding
            raise HTTPException(status_code=400, detail=f"Image {img.id} too large")
    
    start_time = time.time()
    
    # Acquire semaphore (wait if at capacity)
    async with pipeline_semaphore:
        print(f"📥 Processing {len(request.images)} images...")
        
        try:
            # Run pipeline in thread pool (it's sync code)
            quote_result = await asyncio.to_thread(
                run_pipeline,
                [img.b64 for img in request.images],
                request.context
            )
            
            elapsed = time.time() - start_time
            print(f"✅ Pipeline complete in {elapsed:.1f}s")
            
            # Build response
            include_debug = request.context.get("debug", False)
            
            return QuoteResponse(
                quote=quote_result.get("quote", quote_result),
                debug=quote_result.get("debug") if include_debug else None
            )
            
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"❌ Pipeline failed after {elapsed:.1f}s: {e}")
            raise HTTPException(status_code=500, detail=str(e))


# ==============================================================================
# Pipeline Runner
# ==============================================================================

def run_pipeline(base64_images: List[str], context: dict) -> dict:
    """
    Run the v4 vision pipeline synchronously.
    
    This imports the pipeline modules and runs them.
    """
    # Import here to avoid loading at module level
    from vision_v4.orchestrator import process_quote_v4
    
    mode = context.get("mode", "pile")
    
    # Run the pipeline
    result = process_quote_v4(base64_images, mode=mode)
    
    return result


# ==============================================================================
# Run
# ==============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
