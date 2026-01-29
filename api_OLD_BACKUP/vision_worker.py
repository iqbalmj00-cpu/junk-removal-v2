"""
Vision Worker - Florence-2 + Depth-Anything-V2 Integration
Uses official Replicate Python SDK
"""

import os
import io
import base64
import replicate
from PIL import Image, ImageDraw

# Model versions (from official Replicate pages)
FLORENCE_MODEL = "lucataco/florence-2-large:da53547e17d45b9cfb48174b2f18af8b83ca020fa76db62136bf9c6616762595"
DEPTH_MODEL = "chenxwh/depth-anything-v2:b239ea33cff32bb7abb5db39ffe9a09c14cbc2894331d1ef66fe096eed88ebd4"


class VisionWorker:
    """
    Handles computer vision tasks using Florence-2 and Depth-Anything-V2.
    Uses official Replicate SDK for API calls.
    """
    
    def __init__(self):
        # Replicate SDK reads REPLICATE_API_TOKEN from environment automatically
        token = os.environ.get("REPLICATE_API_TOKEN")
        if not token:
            raise ValueError("REPLICATE_API_TOKEN environment variable not set")
        print(f"✅ VisionWorker initialized with Replicate token: {token[:8]}...")
    
    def _base64_to_file(self, image_base64: str):
        """Convert base64 string to file-like object for Replicate."""
        img_bytes = base64.b64decode(image_base64)
        return io.BytesIO(img_bytes)
    
    def run_florence_detection(self, image_base64: str) -> dict:
        """
        Run Florence-2 object detection.
        Returns detected objects with bounding boxes.
        """
        print("🔍 Running Florence-2 Object Detection...")
        
        try:
            img_file = self._base64_to_file(image_base64)
            
            output = replicate.run(
                FLORENCE_MODEL,
                input={
                    "image": img_file,
                    "task_input": "Object Detection"
                }
            )
            
            print(f"✅ Florence-2 output: {output}")
            return self._parse_florence_output(output)
            
        except Exception as e:
            print(f"❌ Florence-2 Error: {e}")
            return {"detections": [], "error": str(e)}
    
    def _parse_florence_output(self, raw_output) -> dict:
        """Parse Florence-2 output into standardized format."""
        result = {
            "detections": [],
            "anchor_found": False,
            "anchor_scale_inches": None
        }
        
        # Anchor objects and their known sizes in inches
        ANCHOR_SIZES = {
            "door": 80,
            "door frame": 80,
            "doorframe": 80,
            "wheelie bin": 42,
            "trash can": 36,
            "garbage bin": 36,
            "car": 60,
            "person": 66,  # Average height
        }
        
        # Florence-2 returns different formats based on task
        # Object Detection typically returns: {"<OD>": {"bboxes": [...], "labels": [...]}}
        if isinstance(raw_output, dict):
            # Check for OD format
            od_data = raw_output.get("<OD>", raw_output)
            
            if "bboxes" in od_data and "labels" in od_data:
                bboxes = od_data["bboxes"]
                labels = od_data["labels"]
                
                for i, bbox in enumerate(bboxes):
                    label = labels[i] if i < len(labels) else "unknown"
                    label_lower = label.lower()
                    
                    detection = {
                        "label": label,
                        "bbox": bbox,
                        "type": "item"
                    }
                    
                    # Check if this is an anchor
                    for anchor_name, size in ANCHOR_SIZES.items():
                        if anchor_name in label_lower:
                            detection["type"] = "anchor"
                            result["anchor_found"] = True
                            result["anchor_scale_inches"] = size
                            break
                    
                    result["detections"].append(detection)
        
        print(f"📦 Parsed {len(result['detections'])} detections, anchor_found={result['anchor_found']}")
        return result
    
    def run_depth_estimation(self, image_base64: str) -> dict:
        """
        Run Depth-Anything-V2 to get depth heatmap.
        Returns URL to depth map image.
        """
        print("🔍 Running Depth-Anything-V2...")
        
        try:
            img_file = self._base64_to_file(image_base64)
            
            output = replicate.run(
                DEPTH_MODEL,
                input={
                    "image": img_file,
                    "model_size": "Large"
                }
            )
            
            print(f"✅ Depth-Anything-V2 output: {output}")
            
            # Output is typically a URL to the depth map image
            depth_url = output if isinstance(output, str) else str(output)
            
            return {
                "depth_map_url": depth_url,
                "success": True
            }
            
        except Exception as e:
            print(f"❌ Depth-Anything-V2 Error: {e}")
            return {"success": False, "error": str(e)}
    
    def create_visual_bridge(
        self, 
        original_image_b64: str,
        detections: dict,
        depth_map_url: str = None
    ) -> str:
        """
        Create annotated composite image for GPT reasoning.
        - RED boxes around anchors
        - BLUE boxes around detected items
        - Side-by-side with depth heatmap (if available)
        
        Returns base64 encoded composite image.
        """
        print("🎨 Creating Visual Bridge...")
        
        # Decode original image
        img_bytes = base64.b64decode(original_image_b64)
        original = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        
        # Create annotated copy
        annotated = original.copy()
        draw = ImageDraw.Draw(annotated)
        
        # Draw bounding boxes
        for det in detections.get("detections", []):
            bbox = det.get("bbox", [])
            if len(bbox) >= 4:
                x1, y1, x2, y2 = bbox[:4]
                
                if det.get("type") == "anchor":
                    color = "red"
                    label_prefix = "ANCHOR: "
                else:
                    color = "blue"
                    label_prefix = ""
                
                # Draw rectangle
                draw.rectangle([x1, y1, x2, y2], outline=color, width=3)
                
                # Draw label
                label = f"{label_prefix}{det.get('label', '')}"
                draw.text((x1, y1 - 15), label, fill=color)
        
        # If we have a depth map URL, fetch and stitch side-by-side
        if depth_map_url:
            try:
                import requests
                resp = requests.get(depth_map_url, timeout=30)
                depth_img = Image.open(io.BytesIO(resp.content)).convert("RGB")
                depth_img = depth_img.resize(annotated.size)
                
                # Create side-by-side composite
                composite_width = annotated.width * 2
                composite = Image.new("RGB", (composite_width, annotated.height))
                composite.paste(annotated, (0, 0))
                composite.paste(depth_img, (annotated.width, 0))
                
                # Add labels
                comp_draw = ImageDraw.Draw(composite)
                comp_draw.text((10, 10), "ANNOTATED VIEW", fill="white")
                comp_draw.text((annotated.width + 10, 10), "DEPTH MAP (White=Near)", fill="white")
                
                annotated = composite
                print("✅ Visual Bridge: Side-by-side composite created")
            except Exception as e:
                print(f"⚠️ Could not fetch depth map for composite: {e}")
        
        # Encode to base64
        buffer = io.BytesIO()
        annotated.save(buffer, format="JPEG", quality=85)
        result_b64 = base64.b64encode(buffer.getvalue()).decode()
        
        print(f"✅ Visual Bridge created: {len(result_b64)} chars")
        return result_b64
    
    def analyze_image(self, image_base64: str) -> dict:
        """
        Full vision pipeline:
        1. Run Florence-2 for object detection
        2. Run Depth-Anything-V2 for depth
        3. Create visual bridge
        """
        print("🚀 Starting Vision Pipeline...")
        
        # Step 1: Object Detection
        detections = self.run_florence_detection(image_base64)
        
        # Step 2: Depth Estimation
        depth_result = self.run_depth_estimation(image_base64)
        
        # Step 3: Create Visual Bridge
        depth_url = depth_result.get("depth_map_url") if depth_result.get("success") else None
        visual_bridge = self.create_visual_bridge(image_base64, detections, depth_url)
        
        result = {
            "detections": detections,
            "visual_bridge_image": visual_bridge,
            "depth_map_url": depth_url,
            "depth_available": depth_result.get("success", False)
        }
        
        print(f"✅ Vision Pipeline Complete: {len(detections.get('detections', []))} objects detected")
        return result


# Singleton instance
_vision_worker = None

def get_vision_worker() -> VisionWorker:
    global _vision_worker
    if _vision_worker is None:
        _vision_worker = VisionWorker()
    return _vision_worker
