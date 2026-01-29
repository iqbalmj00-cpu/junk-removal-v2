"""
Fly.io Vision Pipeline Service v2.0

FastAPI server running the 7-stage 3D volumetric pipeline.
- POST /process - accepts images, returns quote JSON
- X-Internal-Token auth
- Concurrency limiting
- GPU scale-to-zero enabled
"""

import os
import asyncio
import json
import time
import tempfile
from pathlib import Path
from typing import List, Optional
from contextlib import asynccontextmanager
import base64

from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Register HEIC opener for iPhone photos
import pillow_heif
pillow_heif.register_heif_opener()

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
    Run the v2.0 7-stage 3D volumetric pipeline.
    
    Converts base64 images to temp files, runs pipeline, cleans up.
    """
    temp_paths = []
    
    try:
        # Convert base64 images to temp files (new pipeline expects file paths)
        for i, b64 in enumerate(base64_images):
            # Handle data URI format if present
            if "," in b64:
                b64 = b64.split(",", 1)[1]
            
            # Decode and save to temp file
            img_data = base64.b64decode(b64)
            
            # Create temp file
            fd, temp_path = tempfile.mkstemp(suffix=".jpg")
            os.close(fd)
            
            with open(temp_path, "wb") as f:
                f.write(img_data)
            
            temp_paths.append(temp_path)
        
        # Import and run the new pipeline
        from junk_pipeline.orchestrator import run_pipeline as run_junk_pipeline
        
        result = run_junk_pipeline(temp_paths)
        
        # Transform result to quote format expected by frontend
        quote = {
            "final_volume_cy": result.get("final_volume_cy", 0),
            "uncertainty_range": result.get("uncertainty_range", [0, 0]),
            "confidence_score": result.get("confidence_score", 0.5),
            "line_items": result.get("line_items", []),
            "flags": result.get("flags", []),
            "debug": result.get("debug", {}),
        }
        
        return {"quote": quote, "debug": result.get("debug")}
        
    finally:
        # Clean up temp files
        for p in temp_paths:
            try:
                Path(p).unlink(missing_ok=True)
            except Exception:
                pass


# ==============================================================================
# Run
# ==============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
