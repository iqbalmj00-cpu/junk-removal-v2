"""
Modal Deployment for Junk Vision Pipeline
GPU-accelerated 3D volumetric engine with scale-to-zero
Uses Grounding DINO + SAM2 for bulk segmentation (same as Lang-SAM)

v6.7.2: Added direct multipart upload endpoint for HEIC support
"""

import modal

# Create Modal app
app = modal.App("junk-vision")

# Define the container image
image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("libgl1", "libglib2.0-0", "git", "libimage-exiftool-perl")  # v6.7.0: Added ExifTool
    .env({"PYTHONUNBUFFERED": "1"})  # Ensure logs appear immediately
    # Install PyTorch 2.7 with CUDA 12.6
    .pip_install(
        "torch==2.7.0",
        "torchvision",
        "torchaudio",
        extra_index_url="https://download.pytorch.org/whl/cu126",
    )
    # Install other dependencies
    .pip_install(
        "fastapi>=0.109.0",
        "uvicorn[standard]>=0.27.0",
        "pydantic>=2.5.0",
        "python-multipart>=0.0.6",
        "openai>=1.12.0",
        "replicate>=0.23.0",
        "httpx>=0.26.0",
        "requests>=2.31.0",
        "pillow>=10.2.0",
        "pillow-heif>=0.13.0",
        "numpy>=1.24.0",
        "scipy>=1.10.0",
        "transformers>=4.47.0",  # Grounding DINO + SAM + Qwen2.5-VL via HuggingFace
        "timm>=0.9.0",
        "ultralytics>=8.3.0",  # YOLO11 for Lane A
        "accelerate>=0.26.0",  # v6.9.0: Required for Qwen2.5-VL model loading
        "qwen-vl-utils>=0.0.8",  # v6.9.0: Qwen2.5-VL utilities
    )
    .add_local_dir("junk_pipeline", remote_path="/root/junk_pipeline")
)

# Volume for caching models
model_cache = modal.Volume.from_name("model-cache", create_if_missing=True)


# Mount the FastAPI app to Modal
@app.function(
    image=image,
    gpu="A10G",
    timeout=600,
    volumes={"/models": model_cache},
    secrets=[
        modal.Secret.from_name("replicate-api-key"),
        modal.Secret.from_name("huggingface-secret"),
        modal.Secret.from_name("chatgpt"),
    ],
)
@modal.asgi_app()
def fastapi_app():
    """Create and return FastAPI app (runs inside container)."""
    import os
    import sys
    import json
    import hashlib
    import base64
    import tempfile
    from pathlib import Path
    
    from fastapi import FastAPI, File, UploadFile, Form, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    
    # Set environment for model caching
    os.environ["HF_HOME"] = "/models/hf_cache"
    os.environ["TRANSFORMERS_CACHE"] = "/models/hf_cache"
    
    # Add pipeline to path
    sys.path.insert(0, "/root")
    
    # Create FastAPI app with CORS
    web_app = FastAPI(title="Junk Vision Pipeline")
    web_app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "https://junkqt.com",
            "https://www.junkqt.com",
            "https://jamals-junk-v2.vercel.app",
            "http://localhost:3000",
            "http://localhost:3001",
        ],
        allow_origin_regex=r"https://jamals-junk-v2-.*\.vercel\.app",  # Preview deployments
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
    
    def _run_pipeline(temp_paths: list, exif_data: list) -> dict:
        """Common pipeline execution logic."""
        from junk_pipeline.orchestrator import run_pipeline
        from junk_pipeline.pricing import volume_to_price
        
        result = run_pipeline(temp_paths, exif_data=exif_data)
        
        # Check for FATAL_ERROR flags
        if "error" in result and "FATAL_ERROR" in result.get("flags", []):
            print(f"[PIPELINE] Fatal Error: {result['error']}")
            return {
                "quote": {
                    "final_volume_cy": 0,
                    "confidence_score": 0,
                    "min_price": 0,
                    "max_price": 0,
                    "base_price": 0,
                    "line_items": [],
                    "flags": ["ERROR", result.get("error", "Unknown Fault")]
                },
                "debug": {"error_details": result.get("details")}
            }
        
        # Get volume and convert to price
        final_volume = result.get("final_volume_cy", 0)
        min_price, base_price, max_price = volume_to_price(final_volume)
        
        # Build response
        quote = {
            "final_volume_cy": final_volume,
            "uncertainty_range": result.get("uncertainty_range", [0, 0]),
            "confidence_score": result.get("confidence_score", 0.5),
            "min_price": min_price,
            "max_price": max_price,
            "base_price": base_price,
            "line_items": result.get("line_items", []),
            "flags": result.get("flags", []),
        }
        
        return {"quote": quote, "debug": result.get("debug")}
    
    # ========================================================================
    # MULTIPART ENDPOINT - Direct browser upload with HEIC support
    # ========================================================================
    @web_app.post("/upload")
    async def process_multipart(
        files: list[UploadFile] = File(default=[]),
        exif: list[str] = Form(default=[]),
    ):
        """Process images uploaded directly from browser via multipart/form-data."""
        print(f"[MULTIPART] Received {len(files)} files, {len(exif)} EXIF entries", flush=True)
        
        if not files:
            return JSONResponse({"error": "No files provided"}, status_code=400)
        
        # Parse EXIF metadata
        exif_data = []
        for e in exif:
            try:
                exif_data.append(json.loads(e) if e else {})
            except:
                exif_data.append({})
        
        temp_paths = []
        # v6.7.2: Build exif lookup keyed by server-computed sha (authoritative)
        exif_with_server_sha = []
        
        try:
            for i, upload_file in enumerate(files):
                raw_bytes = await upload_file.read()
                
                # Preserve original extension (.heic, .jpg, etc.)
                original_name = upload_file.filename or f"image_{i}"
                ext = Path(original_name).suffix.lower() or '.jpg'
                
                # v6.7.2: Server-computed sha is the authoritative key
                full_sha = hashlib.sha256(raw_bytes).hexdigest()
                sha_prefix = full_sha[:16]
                temp_path = f"/tmp/{sha_prefix}{ext}"
                
                Path(temp_path).write_bytes(raw_bytes)
                temp_paths.append(temp_path)
                
                # Add server sha to exif entry for matching in ingestion
                entry = exif_data[i] if i < len(exif_data) else {}
                entry["serverSha256"] = full_sha  # Full sha for matching
                exif_with_server_sha.append(entry)
                
                print(f"[MULTIPART] File {i}: {original_name} → {temp_path} ({len(raw_bytes):,} bytes)")
                print(f"[MULTIPART] Registered EXIF: sha={sha_prefix}... make={entry.get('make')} model={entry.get('model')}")
            
            # Run pipeline with server-keyed EXIF
            result = _run_pipeline(temp_paths, exif_with_server_sha)
            return result
            
        except Exception as e:
            print(f"[MULTIPART] Error: {e}")
            import traceback
            traceback.print_exc()
            return JSONResponse({"error": str(e)}, status_code=500)
            
        finally:
            # Cleanup temp files
            for p in temp_paths:
                try:
                    Path(p).unlink(missing_ok=True)
                except:
                    pass
    
    # ========================================================================
    # JSON ENDPOINT - Backward compatible (base64 encoded)
    # ========================================================================
    @web_app.post("/")
    async def process_json(request: Request):
        """Process images from JSON request (base64 encoded)."""
        body = await request.json()
        images = body.get("images", [])
        
        if not images:
            return JSONResponse({"error": "No images provided"}, status_code=400)
        
        temp_paths = []
        exif_data = []
        
        try:
            for i, img in enumerate(images):
                b64 = img.get("b64", img) if isinstance(img, dict) else img
                
                # Extract EXIF if provided
                if isinstance(img, dict) and "exif" in img:
                    frame_exif = img["exif"]
                    exif_data.append(frame_exif)
                    if frame_exif.get("make") or frame_exif.get("model"):
                        print(f"[FRONTEND_EXIF] Frame {i}: make={frame_exif.get('make')}, model={frame_exif.get('model')}")
                else:
                    exif_data.append({})
                
                # Handle data URI format
                if isinstance(b64, str) and "," in b64:
                    b64 = b64.split(",", 1)[1]
                
                # Decode and save
                img_data = base64.b64decode(b64)
                fd, temp_path = tempfile.mkstemp(suffix=".jpg")
                os.close(fd)
                
                with open(temp_path, "wb") as f:
                    f.write(img_data)
                
                temp_paths.append(temp_path)
            
            # Run pipeline
            result = _run_pipeline(temp_paths, exif_data)
            return result
            
        except Exception as e:
            print(f"[JSON] Error: {e}")
            import traceback
            traceback.print_exc()
            return JSONResponse({"error": str(e)}, status_code=500)
            
        finally:
            # Cleanup temp files
            for p in temp_paths:
                try:
                    Path(p).unlink(missing_ok=True)
                except:
                    pass
    
    @web_app.get("/health")
    async def health():
        """Health check endpoint."""
        return {"status": "ok", "gpu": "A10G", "multipart": True}
    
    @web_app.get("/overlays/{job_id}")
    async def get_overlays(job_id: str):
        """
        v7.2: Download debug overlays as a ZIP file.
        
        Usage: GET /overlays/{job_id}
        Returns: ZIP file with all overlay PNGs for that job
        """
        import zipfile
        import io
        import os
        from fastapi.responses import StreamingResponse
        
        overlay_dir = f"/tmp/gate_overlays/{job_id}"
        
        if not os.path.exists(overlay_dir):
            return {"error": f"No overlays found for job {job_id}"}
        
        # Create ZIP in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for filename in os.listdir(overlay_dir):
                if filename.endswith('.png'):
                    filepath = os.path.join(overlay_dir, filename)
                    zf.write(filepath, filename)
        
        zip_buffer.seek(0)
        
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename=overlays_{job_id}.zip"}
        )
    
    @web_app.get("/overlay/{job_id}/{filename}")
    async def get_single_overlay(job_id: str, filename: str):
        """
        v8.2.1: Download a single overlay file.
        
        Usage: GET /overlay/{job_id}/{frame_id}_ground_mask.png
        Returns: PNG image file
        """
        import os
        from fastapi.responses import FileResponse
        
        filepath = f"/tmp/gate_overlays/{job_id}/{filename}"
        
        if not os.path.exists(filepath):
            return JSONResponse(
                {"error": f"File not found: {filename}", "job_id": job_id},
                status_code=404
            )
        
        return FileResponse(filepath, media_type="image/png")
    
    return web_app


# Local entrypoint for testing
@app.local_entrypoint()
def main():
    print("Junk Vision Pipeline deployed!")
    print("Endpoints:")
    print("  POST /upload  - Multipart (HEIC support)")
    print("  POST /        - JSON (backward compat)")
    print("  GET  /health  - Health check")
