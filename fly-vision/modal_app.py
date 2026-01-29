"""
Modal Deployment for Junk Vision Pipeline
GPU-accelerated 3D volumetric engine with scale-to-zero
Uses Grounding DINO + SAM2 for bulk segmentation (same as Lang-SAM)
"""

import modal

# Create Modal app
app = modal.App("junk-vision")

# Define the container image
image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("libgl1", "libglib2.0-0", "git")
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
        "transformers>=4.47.0",  # Grounding DINO + SAM via HuggingFace
        "timm>=0.9.0",
        "ultralytics>=8.3.0",  # YOLO11 for Lane A
    )
    .add_local_dir("junk_pipeline", remote_path="/root/junk_pipeline")
)

# Volume for caching models
model_cache = modal.Volume.from_name("model-cache", create_if_missing=True)


@app.function(
    image=image,
    gpu="A10G",
    timeout=600,
    volumes={"/models": model_cache},
    secrets=[
        modal.Secret.from_name("replicate-api-key"),  # For Lane C
        modal.Secret.from_name("huggingface-secret"),  # For SAM3
    ],
)
@modal.fastapi_endpoint(method="POST")
def process(request: dict):
    """Process images through the 3D volumetric pipeline."""
    import os
    import sys
    import base64
    import tempfile
    from pathlib import Path
    
    # Set environment for model caching
    os.environ["HF_HOME"] = "/models/hf_cache"
    os.environ["TRANSFORMERS_CACHE"] = "/models/hf_cache"
    
    # Add pipeline to path
    sys.path.insert(0, "/root")
    
    # Import pipeline
    from junk_pipeline.orchestrator import run_pipeline
    
    # Extract images from request
    images = request.get("images", [])
    if not images:
        return {"error": "No images provided"}
    
    temp_paths = []
    try:
        # Convert base64 images to temp files
        for i, img in enumerate(images):
            b64 = img.get("b64", img) if isinstance(img, dict) else img
            
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
        result = run_pipeline(temp_paths)
        
        # Build response
        quote = {
            "final_volume_cy": result.get("final_volume_cy", 0),
            "uncertainty_range": result.get("uncertainty_range", [0, 0]),
            "confidence_score": result.get("confidence_score", 0.5),
            "line_items": result.get("line_items", []),
            "flags": result.get("flags", []),
        }
        
        return {"quote": quote, "debug": result.get("debug")}
        
    finally:
        # Cleanup temp files
        for p in temp_paths:
            try:
                Path(p).unlink(missing_ok=True)
            except:
                pass


@app.function(image=image)
@modal.fastapi_endpoint(method="GET")
def health():
    """Health check endpoint."""
    return {"status": "ok", "gpu": "A10G", "sam3": True}


# Local entrypoint for testing
@app.local_entrypoint()
def main():
    print("Junk Vision Pipeline deployed!")
    print(f"Health endpoint: {health.web_url}")
    print(f"Process endpoint: {process.web_url}")
