"""
Qwen3-VL-8B-Instruct Inference via Replicate API

Uses Replicate API for inference - no local GPU required.
"""

import os
import base64
import io
from PIL import Image
from typing import Optional, List

# =============================================================================
# CONFIGURATION
# =============================================================================

REPLICATE_MODEL = "lucataco/qwen3-vl-8b-instruct:39e893666996acf464cff75688ad49ac95ef54e9f1c688fbc677330acc478e11"
MAX_NEW_TOKENS = 1024  # Increased for thinking mode output

# =============================================================================
# STUB FUNCTIONS (for compatibility with orchestrator)
# =============================================================================

def load_qwen():
    """No-op for Replicate - no model to load."""
    print("[QWEN_REPLICATE] Using Replicate API (no local model)")

def unload_qwen():
    """No-op for Replicate - no model to unload."""
    pass

def is_loaded() -> bool:
    """Always ready with Replicate."""
    return True


# =============================================================================
# HELPERS
# =============================================================================

def _pil_to_data_uri(img: Image.Image, max_dim: int = 1024) -> str:
    """Convert PIL image to data URI for Replicate."""
    # Resize if needed
    if max(img.size) > max_dim:
        ratio = max_dim / max(img.size)
        new_size = (int(img.width * ratio), int(img.height * ratio))
        img = img.resize(new_size, Image.LANCZOS)
    
    # Convert to base64 data URI
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}"


def parse_thinking_response(response: str) -> tuple:
    """Extract thinking and final answer from Qwen3 thinking mode response.
    
    Returns:
        (thinking_content, final_answer)
    """
    if "</think>" in response:
        parts = response.split("</think>", 1)
        thinking = parts[0].replace("<think>", "").strip()
        answer = parts[1].strip()
        return thinking, answer
    return "", response


# =============================================================================
# INFERENCE
# =============================================================================

def run_inference(image_pil: Image.Image, prompt: str) -> str:
    """
    Run Qwen3-VL inference via Replicate API.
    
    Args:
        image_pil: PIL Image to analyze
        prompt: Text prompt for the model
        
    Returns:
        Model's text response
    """
    import replicate
    
    # Convert image to data URI
    media_uri = _pil_to_data_uri(image_pil)
    
    print(f"[QWEN_REPLICATE] Calling Replicate API...")
    
    try:
        output = replicate.run(
            REPLICATE_MODEL,
            input={
                "media": media_uri,  # API uses 'media' not 'image'
                "prompt": prompt,
                "max_new_tokens": MAX_NEW_TOKENS,
                "temperature": 0,  # Deterministic (API default is 0.7)
                "top_p": 0.9,
            }
        )
        
        # Output may be a generator or string
        if hasattr(output, '__iter__') and not isinstance(output, str):
            result = "".join(output)
        else:
            result = str(output)
        
        print(f"[QWEN_REPLICATE] Response received ({len(result)} chars)")
        return result
        
    except Exception as e:
        print(f"[QWEN_REPLICATE] Error: {e}")
        raise


def run_inference_multi(images: List[Image.Image], prompt: str) -> str:
    """
    Run Qwen3-VL inference with multiple images via Replicate API.
    
    Note: This API only supports single media input, so we'll use the first image.
    
    Args:
        images: List of PIL Images to analyze
        prompt: Text prompt for the model
        
    Returns:
        Model's text response
    """
    if images:
        return run_inference(images[0], prompt)
    raise ValueError("No images provided")
