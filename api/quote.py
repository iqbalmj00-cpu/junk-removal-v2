from http.server import BaseHTTPRequestHandler
import json
import os
import io
import asyncio
import base64
import ast
import redis
import requests
from openai import AsyncOpenAI
from google import genai
from google.genai import types

# ==================== VISION WORKER (INLINED) ====================
# Florence-2 + Depth-Anything-V2 Integration using Replicate SDK

print("🔬 Loading Vision Pipeline...")

try:
    import replicate
    from PIL import Image, ImageDraw
    
    # Model versions (from official Replicate pages)
    FLORENCE_MODEL = "lucataco/florence-2-large:da53547e17d45b9cfb48174b2f18af8b83ca020fa76db62136bf9c6616762595"
    DEPTH_MODEL = "chenxwh/depth-anything-v2:b239ea33cff32bb7abb5db39ffe9a09c14cbc2894331d1ef66fe096eed88ebd4"
    
    # Anchor Trust Registry: trust tiers + validation rules
    ANCHOR_REGISTRY = {
        # HIGH trust - consistent, standardized sizes
        "door": {"size_inches": 80, "trust": "HIGH", "aspect_ratio": (0.3, 0.6), "aliases": ["door frame", "doorway"]},
        "standard door": {"size_inches": 80, "trust": "HIGH", "aspect_ratio": (0.3, 0.6)},
        # MEDIUM trust - common but variable sizes
        "person": {"size_inches": 66, "trust": "MEDIUM", "aspect_ratio": (0.25, 0.5), "size_range": (60, 76)},
        "wheelie bin": {"size_inches": 42, "trust": "MEDIUM", "aspect_ratio": (0.4, 0.8)},
        "trash can": {"size_inches": 36, "trust": "MEDIUM", "aspect_ratio": (0.5, 1.2)},
        # LOW trust - highly variable, use as fallback only
        "chair": {"size_inches": 32, "trust": "LOW", "aspect_ratio": (0.6, 1.4)},
        "bicycle": {"size_inches": 40, "trust": "LOW", "aspect_ratio": (0.6, 1.8)},
        "tv": {"size_inches": 24, "trust": "LOW", "aspect_ratio": (1.2, 2.5), "aliases": ["television", "monitor"]},
    }

    class VisionWorker:
        """Handles vision tasks using Florence-2 and Depth-Anything-V2."""
        
        def __init__(self):
            token = os.environ.get("REPLICATE_API_TOKEN")
            if not token:
                raise ValueError("REPLICATE_API_TOKEN environment variable not set")
            print(f"✅ VisionWorker initialized with token: {token[:8]}...")
        
        def validate_anchor(self, label: str, bbox: list) -> dict:
            """Validate an anchor by checking aspect ratio against expected range."""
            for anchor_name, config in ANCHOR_REGISTRY.items():
                names_to_check = [anchor_name] + config.get("aliases", [])
                if any(name in label.lower() for name in names_to_check):
                    width = bbox[2] - bbox[0]
                    height = bbox[3] - bbox[1]
                    if height <= 0:
                        continue
                    aspect = width / height
                    min_aspect, max_aspect = config["aspect_ratio"]
                    is_valid = min_aspect <= aspect <= max_aspect
                    
                    result = {
                        "anchor_name": anchor_name,
                        "size_inches": config["size_inches"],
                        "trust": config["trust"],
                        "aspect_valid": is_valid,
                        "aspect_ratio": round(aspect, 2),
                        "bbox_height_px": height
                    }
                    print(f"🔑 Anchor validated: {anchor_name} ({config['trust']} trust, aspect={result['aspect_ratio']}, valid={is_valid})")
                    return result
            return None
        
        def cross_validate_anchors(self, validated_anchors: list) -> dict:
            """Cross-validate multiple anchors to derive px_per_inch scale."""
            if not validated_anchors:
                return {"scale": None, "confidence": "NONE", "anchor_used": None}
            
            trust_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
            sorted_anchors = sorted(validated_anchors, key=lambda a: (trust_order.get(a["trust"], 3), not a["aspect_valid"]))
            
            best = sorted_anchors[0]
            if not best["aspect_valid"]:
                return {"scale": None, "confidence": "LOW", "reason": "No aspect-valid anchors", "anchor_used": best["anchor_name"]}
            
            px_per_inch = best["bbox_height_px"] / best["size_inches"]
            result = {
                "scale": round(px_per_inch, 3),
                "anchor_used": best["anchor_name"],
                "trust": best["trust"],
                "confidence": "HIGH" if best["trust"] == "HIGH" else "MEDIUM"
            }
            print(f"📐 Scale: {result['scale']} px/inch from {best['anchor_name']} ({result['confidence']} confidence)")
            return result
        
        def _base64_to_file(self, image_base64: str):
            img_bytes = base64.b64decode(image_base64)
            return io.BytesIO(img_bytes)
        
        def run_florence_detection(self, image_base64: str) -> dict:
            print("🔍 Running Florence-2 Object Detection...")
            try:
                img_file = self._base64_to_file(image_base64)
                output = replicate.run(
                    FLORENCE_MODEL,
                    input={"image": img_file, "task_input": "Object Detection"}
                )
                print(f"✅ Florence-2 output: {output}")
                return self._parse_florence_output(output)
            except Exception as e:
                print(f"❌ Florence-2 Error: {e}")
                return {"detections": [], "error": str(e)}
        
        def _parse_florence_output(self, raw_output) -> dict:
            """Parse Florence-2 output with anchor validation."""
            result = {"detections": [], "anchor_found": False, "anchor_scale_inches": None, "anchor_trust": None, "validated_anchors": []}
            
            try:
                if isinstance(raw_output, dict) and 'text' in raw_output:
                    text_str = raw_output['text']
                    print(f"🔬 Florence text field: {text_str[:200]}..." if len(text_str) > 200 else f"🔬 Florence text field: {text_str}")
                    
                    parsed = ast.literal_eval(text_str)
                    od_data = parsed.get('<OD>', {})
                    
                    if 'bboxes' in od_data and 'labels' in od_data:
                        bboxes = od_data['bboxes']
                        labels = od_data['labels']
                        
                        for i, bbox in enumerate(bboxes):
                            label = labels[i] if i < len(labels) else "unknown"
                            detection = {"label": label, "bbox": bbox, "type": "item"}
                            
                            # Use anchor validation with trust tiers
                            anchor_info = self.validate_anchor(label, bbox)
                            if anchor_info:
                                detection["type"] = "anchor"
                                detection["anchor_info"] = anchor_info
                                result["validated_anchors"].append(anchor_info)
                                
                                # Only set anchor_found if aspect is valid
                                if anchor_info["aspect_valid"]:
                                    result["anchor_found"] = True
                                    result["anchor_scale_inches"] = anchor_info["size_inches"]
                                    result["anchor_trust"] = anchor_info["trust"]
                            
                            result["detections"].append(detection)
                else:
                    print(f"⚠️ Unexpected Florence output format: {type(raw_output)}")
                    
            except Exception as e:
                print(f"❌ Florence parsing error: {e}")
                import traceback
                traceback.print_exc()
            
            print(f"📦 Parsed {len(result['detections'])} detections, {len(result['validated_anchors'])} anchors validated")
            return result
        
        def run_depth_estimation(self, image_base64: str) -> dict:
            """Run Depth-Anything-V2. Output is {'color_depth': <url>, 'grey_depth': <url>}."""
            print("🔍 Running Depth-Anything-V2...")
            try:
                img_file = self._base64_to_file(image_base64)
                output = replicate.run(
                    DEPTH_MODEL,
                    input={"image": img_file, "model_size": "Large"}
                )
                print(f"✅ Depth-Anything-V2 raw output: {output}")
                
                # Extract the color_depth URL from the output dict
                # Output format: {'color_depth': <FileOutput or URL>, 'grey_depth': <FileOutput or URL>}
                depth_url = None
                if isinstance(output, dict):
                    color_depth = output.get('color_depth')
                    if color_depth is not None:
                        # Handle both string URLs and FileOutput objects
                        depth_url = str(color_depth)
                        print(f"🔬 Extracted depth URL: {depth_url[:80]}..." if len(depth_url) > 80 else f"🔬 Extracted depth URL: {depth_url}")
                else:
                    print(f"⚠️ Unexpected depth output format: {type(output)}")
                
                if depth_url:
                    return {"depth_map_url": depth_url, "success": True}
                else:
                    return {"depth_map_url": None, "success": False, "error": "Could not extract depth URL"}
                    
            except Exception as e:
                print(f"❌ Depth Error: {e}")
                import traceback
                traceback.print_exc()
                return {"success": False, "error": str(e)}
        
        def create_visual_bridge(self, original_b64: str, detections: dict, depth_url: str = None) -> str:
            print("🎨 Creating Visual Bridge...")
            img_bytes = base64.b64decode(original_b64)
            original = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            annotated = original.copy()
            draw = ImageDraw.Draw(annotated)
            
            for det in detections.get("detections", []):
                bbox = det.get("bbox", [])
                if len(bbox) >= 4:
                    x1, y1, x2, y2 = bbox[:4]
                    color = "red" if det.get("type") == "anchor" else "blue"
                    draw.rectangle([x1, y1, x2, y2], outline=color, width=3)
                    draw.text((x1, y1 - 15), det.get("label", ""), fill=color)
            
            if depth_url:
                try:
                    resp = requests.get(depth_url, timeout=30)
                    depth_img = Image.open(io.BytesIO(resp.content)).convert("RGB").resize(annotated.size)
                    composite = Image.new("RGB", (annotated.width * 2, annotated.height))
                    composite.paste(annotated, (0, 0))
                    composite.paste(depth_img, (annotated.width, 0))
                    annotated = composite
                    print("✅ Side-by-side composite created")
                except Exception as e:
                    print(f"⚠️ Could not fetch depth map: {e}")
            
            buffer = io.BytesIO()
            annotated.save(buffer, format="JPEG", quality=85)
            return base64.b64encode(buffer.getvalue()).decode()
        
        def analyze_image(self, image_base64: str) -> dict:
            import time
            print("🚀 Starting Vision Pipeline...")
            detections = self.run_florence_detection(image_base64)
            
            # Rate limit: wait 12s between Replicate calls (burst limit = 1)
            print("   ⏳ Rate limit delay before depth (12s)...")
            time.sleep(12)
            
            depth_result = self.run_depth_estimation(image_base64)
            depth_url = depth_result.get("depth_map_url") if depth_result.get("success") else None
            visual_bridge = self.create_visual_bridge(image_base64, detections, depth_url)
            print(f"✅ Vision Complete: {len(detections.get('detections', []))} objects")
            return {
                "detections": detections,
                "visual_bridge_image": visual_bridge,
                "depth_map_url": depth_url,
                "depth_available": depth_result.get("success", False)
            }
        
        def fuse_detection_results(self, all_results: list) -> dict:
            """
            Merge detections from multiple images.
            Deduplicates by normalized label, keeping the largest bbox.
            """
            fused = {"detections": [], "anchor_found": False, "anchor_scale_inches": None}
            seen_labels = {}  # normalized_label -> {"det": detection, "area": float}
            
            for result in all_results:
                dets = result.get("detections", {})
                
                # Aggregate anchor across all images (first anchor wins)
                if dets.get("anchor_found") and not fused["anchor_found"]:
                    fused["anchor_found"] = True
                    fused["anchor_scale_inches"] = dets.get("anchor_scale_inches")
                
                for det in dets.get("detections", []):
                    norm_label = self._normalize_label(det["label"])
                    bbox = det.get("bbox", [0, 0, 0, 0])
                    area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]) if len(bbox) == 4 else 0
                    
                    if norm_label not in seen_labels or area > seen_labels[norm_label]["area"]:
                        seen_labels[norm_label] = {"det": det, "area": area}
            
            fused["detections"] = [v["det"] for v in seen_labels.values()]
            print(f"🔗 Fusion: {len(seen_labels)} unique labels from {len(all_results)} images")
            return fused
        
        def _normalize_label(self, label: str) -> str:
            """Normalize label for deduplication (lowercase, strip, remove plural 's')."""
            label = label.lower().strip()
            if label.endswith("s") and len(label) > 3:
                label = label[:-1]
            return label

    # Singleton
    _vision_worker = None
    def get_vision_worker():
        global _vision_worker
        if _vision_worker is None:
            _vision_worker = VisionWorker()
        return _vision_worker
    
    # Test initialization
    _test_worker = get_vision_worker()
    VISION_ENABLED = True
    VISION_ERROR = None
    print("✅ Vision Pipeline ENABLED (Replicate SDK)")

except Exception as e:
    VISION_ENABLED = False
    VISION_ERROR = f"{type(e).__name__}: {e}"
    print(f"❌ Vision Pipeline DISABLED: {VISION_ERROR}")
    
    def get_vision_worker():
        raise RuntimeError(f"Vision Pipeline not available: {VISION_ERROR}")

# ==================== END VISION WORKER ====================

# Heavy Material Surcharge Tiers
HEAVY_SURCHARGES = {
    "none": 0,
    "some": 0,
    "mixed": 50,
    "mostly": 100,
    "all": 200
}

class PricingEngine:
    def __init__(self):
        # 1. Initialize Google Client (Sync client, wrapped in async later)
        self.google_client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))
        
        # 2. Initialize OpenAI Client (Async)
        self.openai_client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

        # 3. Initialize Redis (for Rate Limiting)
        try:
            self.redis_client = redis.from_url(os.environ.get('REDIS_URL'))
            # Test connection lightly
            self.redis_client.ping()
            print("✅ REDIS CONNECTED")
        except Exception as e:
            print(f"⚠️ REDIS CONNECTION FAILED: {e}")
            self.redis_client = None

    def check_rate_limit(self, user_ip):
        """Enforce 5 requests per hour limit using Redis."""
        if not self.redis_client:
            return True # Fail open

        key = f"rate_limit:{user_ip}"
        try:
            # Atomic increment
            request_count = self.redis_client.incr(key)
            
            # If this is the first request, set expiry to 1 hour (3600 seconds)
            if request_count == 1:
                self.redis_client.expire(key, 3600)
                
            print(f"🛡️ RATE LIMIT: IP {user_ip} is at {request_count}/50 requests.")

            if request_count > 50:
                # Temporarily raised to 50 for testing (was 5)
                return False
            
            return True
        except Exception as e:
            print(f"⚠️ RATE LIMIT ERROR: {e}")
            return True

    def _get_system_prompt(self):
        return """
        You are a Veteran Junk Removal Load Master. Output JSON ONLY.
        Your Goal: Calculate the *Billable Truck Space* (Total Cubic Feet) required for this job.

        ### PHASE 1: ANCHOR LOCK (CRITICAL)
        - **Primary Anchor:** The Mattress (Standard 80" tall) or The Pallets (Standard 40" x 48").
        - **Secondary Anchor:** Wheelie Bin (42" tall).
        - **FORBIDDEN:** Do NOT use cars, houses, garage doors, or windows in the background. They are distant and will distort scale.
        - **Fallback:** If no standard scale exists, assume the tallest item in the pile is 6ft (approx human height).

        ### PHASE 2: CALCULATION STRATEGY (The "Sum of Parts" Protocol)
        Do NOT draw a giant bounding box around a scattered pile (this captures too much air).
        Instead, calculate by **SUMMATION**:
        1. **Identify the "Big 3":** Find the 3 largest distinct items (e.g., Mattress, Sofa, Shelf).
        2. **Calculate their tight volume:** (L x W x H) for each.
        3. **Add the "Scatter":** Estimate the volume of the remaining loose bags/boxes and add it to the total.
        4. **Apply Physics:**
           - **Compressible items (Bags):** Reduce volume by 30%.
           - **Irregular items (Bikes/Brush):** Add 15% "Void Space" for stacking inefficiency.

        ### PHASE 3: REALITY CHECK
        - **Heuristic:** Most residential driveway piles are between 3 and 6 cubic yards.
        - If your calculation exceeds 10 yards, re-evaluate: Did you include the driveway width in the pile? Did you use a background house for scale?

        ### PHASE 4: FINAL OUTPUT
        Output the dimensions of the final theoretical stack in DECIMAL FEET.

        ### OUTPUT JSON:
        {
          "packed_dimensions": {
              "l": 0.0,
              "w": 0.0,
              "h": 0.0
          },
          "confidence_score": 1.0, 
          "risk_factor": "String",
          "density": 1.0,
          "debug_items": "String (List the 'Big 3' items used for scale)",
          "anchor_used": "String"
        }
        """
    
    def _get_vision_enhanced_prompt(self):
        """GPT prompt for annotated visual bridge images."""
        return """
        You are a Logistics Physics Engine analyzing an ANNOTATED junk removal image.
        
        **IMAGE LAYOUT:**
        - LEFT SIDE: Annotated View with bounding boxes
          - RED boxes = Scale ANCHORS (door frames, bins) with known sizes
          - BLUE boxes = Detected items (furniture, appliances)
        - RIGHT SIDE: Depth Heatmap (White=Near/Shallow, Black=Far/Deep)
        
        **YOUR MISSION (The Subtraction Waterfall):**
        
        1. **Anchor Validation:** Look at RED boxes. Use their known scale:
           - Door frame = 80 inches tall
           - Wheelie bin = 42 inches tall
           - If NO red boxes, use Scene Heuristic (assume 6ft reference)
        
        2. **Depth Analysis:** Check the heatmap:
           - Is the pile SHALLOW (bright/white) or DEEP (dark)?
           - Estimate depth in feet based on anchor scale
        
        3. **Item Verification:** Confirm BLUE boxes are valid items
           - Are they actually junk or false positives?
           - Estimate each item's volume using anchor scale
        
        4. **Liquid Density:** For areas NOT covered by BLUE boxes:
           - Is it loose/fluffy (0.5-0.7 density) or dense (0.8-1.0)?
        
        5. **Volume Calculation:**
           - Sum BLUE box item volumes
           - Add remaining "liquid" pile volume × density
        
        ### OUTPUT JSON:
        {
          "packed_dimensions": { "l": 0.0, "w": 0.0, "h": 0.0 },
          "confidence_score": 1.0,
          "anchor_used": "String",
          "anchor_scale_inches": 0,
          "depth_estimate_ft": 0.0,
          "density": 1.0,
          "detected_items": ["item1", "item2"],
          "debug_reasoning": "String"
        }
        """

    async def ask_gemini(self, images):
        try:
            # Gemini 3 Pro Preview
            # Wrap synchronous call in thread for async compatibility
            prompt = self._get_system_prompt()
            
            def _call():
                return self.google_client.models.generate_content(
                    model='gemini-3-pro-preview',
                    contents=[prompt, *images],
                    config=types.GenerateContentConfig(
                        temperature=0.0,
                        response_mime_type='application/json'
                    )
                )

            response = await asyncio.to_thread(_call)
            return json.loads(response.text)
        except Exception as e:
            print(f"❌ GEMINI ERROR: {e}")
            return None

    async def ask_gpt(self, base64_images):
        try:
            content = [{"type": "text", "text": self._get_system_prompt()}]
            for img_b64 in base64_images:
                 content.append({
                    "type": "image_url", 
                    "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}
                })

            response = await self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": content}],
                temperature=0.0,
                max_tokens=300,
                response_format={"type": "json_object"}
            )
            
            raw_content = response.choices[0].message.content
             # Cleanup markdown
            if raw_content.startswith("```json"):
                raw_content = raw_content[7:]
            if raw_content.endswith("```"):
                raw_content = raw_content[:-3]
                
            return json.loads(raw_content)
        except Exception as e:
            print(f"❌ GPT ERROR: {e}")
            return None
    
    async def ask_gemini_with_vision(self, visual_bridge_b64: str, detections: dict) -> dict:
        """
        Send annotated visual bridge image to Gemini 3 Pro for enhanced analysis.
        Uses vision-specific prompt that understands RED/BLUE boxes and depth heatmap.
        """
        try:
            # Build context from detections
            detection_context = ""
            if detections.get("anchor_found"):
                detection_context += f"ANCHOR DETECTED: {detections.get('anchor_scale_inches')} inches scale available.\n"
            detection_context += f"Items detected: {len(detections.get('detections', []))}\n"
            
            # Build Gemini-compatible prompt
            prompt = f"{self._get_vision_enhanced_prompt()}\n\nPRE-ANALYSIS CONTEXT:\n{detection_context}"
            
            # Decode base64 image for Gemini
            img_bytes = base64.b64decode(visual_bridge_b64)
            image_part = types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")
            
            def _call():
                return self.google_client.models.generate_content(
                    model='gemini-3-pro-preview',
                    contents=[prompt, image_part],
                    config=types.GenerateContentConfig(
                        temperature=0.0,
                        response_mime_type='application/json'
                    )
                )

            response = await asyncio.to_thread(_call)
            print(f"✅ Gemini Vision Response: {response.text[:200]}..." if len(response.text) > 200 else f"✅ Gemini Vision Response: {response.text}")
            return json.loads(response.text)
        except Exception as e:
            print(f"❌ GEMINI VISION ERROR: {e}")
            import traceback
            traceback.print_exc()
            return None

    def calculate_volume(self, json_data):
        if not json_data or 'packed_dimensions' not in json_data: 
            return 0.0
        d = json_data['packed_dimensions']
        return (d.get('l', 0) * d.get('w', 0) * d.get('h', 0)) / 27.0

    async def process_quote(self, images, base64_images, heavy_level='none'):
        print("🚀 STARTING DUAL-MODEL CONSENSUS (Async)...")
        
        # Heavy Surcharge from user selection
        heavy_surcharge = HEAVY_SURCHARGES.get(heavy_level, 0)
        print(f"📦 Heavy Material Level: {heavy_level} -> +${heavy_surcharge}")
        
        # 1. Prepare Gemini Inputs
        gemini_inputs = []
        for img_bytes in images:
             gemini_inputs.append(types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"))

        # 2. Parallel Execution (Survivor Protocol)
        results = await asyncio.gather(
            self.ask_gemini(gemini_inputs),
            self.ask_gpt(base64_images),
            return_exceptions=True
        )
        
        res_gemini = results[0] if not isinstance(results[0], Exception) else None
        res_gpt = results[1] if not isinstance(results[1], Exception) else None

        if isinstance(results[0], Exception): print(f"❌ Gemini Exception: {results[0]}")
        if isinstance(results[1], Exception): print(f"❌ GPT Exception: {results[1]}")

        # 3. Fail-Over Check
        if not res_gemini and not res_gpt:
            return {"status": "SHADOW_MODE", "message": "Both Models Failed", "reason": "System Outage"}
        
        # Use survivor if one failed
        if not res_gemini:
            res_gemini = res_gpt
            print("⚠️ Gemini failed, mirroring GPT data.")
        if not res_gpt:
            res_gpt = res_gemini
            print("⚠️ GPT failed, mirroring Gemini data.")

        # 4. Confidence Gate
        conf_gemini = res_gemini.get('confidence_score', 0)
        conf_gpt = res_gpt.get('confidence_score', 0)
        
        if conf_gemini < 0.5 and conf_gpt < 0.5:
             return {"status": "SHADOW_MODE", "message": "Image Unclear", "debug": f"Conf: G{conf_gemini}|O{conf_gpt}"}

        # 5. Variance Check
        vol_gemini = self.calculate_volume(res_gemini)
        vol_gpt = self.calculate_volume(res_gpt)
        
        # Filter out invalid volumes (0.0 usually means parsing error or empty response)
        if vol_gemini <= 0: vol_gemini = vol_gpt
        if vol_gpt <= 0: vol_gpt = vol_gemini

        diff = abs(vol_gemini - vol_gpt)
        avg_vol = (vol_gemini + vol_gpt) / 2
        variance = (diff / avg_vol) if avg_vol > 0 else 0
        
        print(f"🧮 MATH: Gemini({vol_gemini:.2f}) | GPT({vol_gpt:.2f}) | Diff({diff:.2f}) | Var({variance:.1%})")

        final_vol = 0.0
        
        # Small Load Exception
        if diff < 1.5:
            final_vol = avg_vol
            print("✅ SMALL LOAD EXCEPTION: Using Average")
        elif variance < 0.20:
             # High Agreement
             final_vol = avg_vol
             print("✅ HIGH AGREEMENT: Using Average")
        elif variance <= 0.40:
             # Moderate Disagreement -> Be Conservative (Min)
             final_vol = min(vol_gemini, vol_gpt)
             print("⚠️ MODERATE DISAGREEMENT: Using Minimum")
        else:
             # High Variance
             return {
                 "status": "SHADOW_MODE", 
                 "message": "High Variance Detected", 
                 "debug": f"Variance {variance:.1%}. Gemini: {vol_gemini} vs GPT: {vol_gpt}"
             }

        # 6. Pricing Math
        final_vol = round(final_vol, 1)
        base_price = max(95, final_vol * 35) # $35/yd, $95 min
        
        # Apply heavy surcharge
        total_base = base_price + heavy_surcharge
        min_price = max(95, round(total_base * 0.90))
        max_price = round(total_base * 1.10)
        
        # Pretty Rounding
        def round_pretty(p):
            if p > 100: return 5 * round(p / 5)
            return round(p)

        min_price = round_pretty(min_price)
        max_price = round_pretty(max_price)

        return {
            "status": "SUCCESS",
            "volume_yards": final_vol,
            "min_price": min_price,
            "max_price": max_price,
            "price": round(total_base, 2),
            "heavy_surcharge": heavy_surcharge,
            "debug": {
                "gemini_vol": vol_gemini,
                "gpt_vol": vol_gpt,
                "variance": f"{variance:.1%}",
                "gemini_raw": res_gemini,
                "gpt_raw": res_gpt,
                "heavy_level": heavy_level
            }
        }
    
    async def process_quote_with_vision(self, base64_images, heavy_level='none'):
        """
        Vision-only quote processing using Florence-2 + Depth-Anything-V2.
        Uses Replicate SDK for model inference.
        """
        print("🔬 STARTING VISION-ENHANCED ANALYSIS...")
        
        # Heavy Surcharge from user selection
        heavy_surcharge = HEAVY_SURCHARGES.get(heavy_level, 0)
        print(f"📦 Heavy Material Level: {heavy_level} -> +${heavy_surcharge}")
        
        try:
            # 1. Run Vision Pipeline on ALL images
            vision_worker = get_vision_worker()
            
            # Process ALL images through vision pipeline
            all_vision_results = []
            print(f"📸 Processing {len(base64_images)} image(s)...")
            
            for i, img_b64 in enumerate(base64_images):
                # Rate limit: wait 12s between images to respect Replicate burst limits
                if i > 0:
                    import time
                    print(f"   ⏳ Rate limit delay (12s)...")
                    time.sleep(12)
                
                print(f"🔍 Analyzing image {i+1}/{len(base64_images)}...")
                try:
                    result = vision_worker.analyze_image(img_b64)
                    result["image_index"] = i
                    det_count = len(result.get("detections", {}).get("detections", []))
                    anchor = result.get("detections", {}).get("anchor_found", False)
                    depth = result.get("depth_available", False)
                    print(f"   ✅ Image {i+1}: {det_count} detections, anchor={anchor}, depth={depth}")
                    all_vision_results.append(result)
                except Exception as img_error:
                    print(f"   ⚠️ Image {i+1} failed: {img_error}")
            
            # Check for minimum success
            if not all_vision_results:
                raise ValueError("All image analyses failed")
            
            print(f"✅ Successfully analyzed {len(all_vision_results)}/{len(base64_images)} images")
            
            # Phase 2: Fuse detections from all images
            detections = vision_worker.fuse_detection_results(all_vision_results)
            
            # Use visual bridge from image with anchor, or first image
            visual_bridge = None
            for result in all_vision_results:
                if result.get("detections", {}).get("anchor_found"):
                    visual_bridge = result.get("visual_bridge_image")
                    print(f"📍 Using visual bridge from image {result['image_index']+1} (has anchor)")
                    break
            if not visual_bridge:
                visual_bridge = all_vision_results[0].get("visual_bridge_image")
            
            print(f"👁️ Vision: Anchor={detections.get('anchor_found')}, Items={len(detections.get('detections', []))}")
            
            if not visual_bridge:
                raise ValueError("Vision pipeline failed to create visual bridge")
            
            # 2. Send visual bridge to GPT for reasoning
            gemini_result = await self.ask_gemini_with_vision(visual_bridge, detections)
            
            if not gemini_result:
                raise ValueError("Gemini vision analysis failed")
            
            # 3. Calculate Volume
            final_vol = self.calculate_volume(gemini_result)
            
            if final_vol <= 0:
                raise ValueError("Invalid volume from vision pipeline")
            
            # 4. Pricing Math
            final_vol = round(final_vol, 1)
            base_price = max(95, final_vol * 35)
            
            total_base = base_price + heavy_surcharge
            min_price = max(95, round(total_base * 0.90))
            max_price = round(total_base * 1.10)
            
            def round_pretty(p):
                if p > 100: return 5 * round(p / 5)
                return round(p)
            
            min_price = round_pretty(min_price)
            max_price = round_pretty(max_price)
            
            return {
                "status": "SUCCESS",
                "volume_yards": final_vol,
                "min_price": min_price,
                "max_price": max_price,
                "price": round(total_base, 2),
                "heavy_surcharge": heavy_surcharge,
                "vision_enhanced": True,
                "anchor_found": detections.get("anchor_found", False),
                "anchor_scale_inches": detections.get("anchor_scale_inches"),
                "detected_items": gemini_result.get("detected_items", []),
                "debug": {
                    "gemini_raw": gemini_result,
                    "detections_count": len(detections.get("detections", [])),
                    "depth_available": any(r.get("depth_available", False) for r in all_vision_results),
                    "heavy_level": heavy_level
                }
            }
            
        except Exception as e:
            print(f"❌ VISION PIPELINE ERROR: {e}")
            import traceback
            traceback.print_exc()
            # No fallback - return error to user
            return {
                "status": "VISION_ERROR",
                "message": str(e),
                "vision_error": VISION_ERROR
            }

# --- Serverless Handler ---
engine = PricingEngine()

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # 1. Rate Limit
        x_forwarded_for = self.headers.get('x-forwarded-for')
        if x_forwarded_for:
            user_ip = x_forwarded_for.split(',')[0].strip()
        else:
            user_ip = self.client_address[0]
            
        if not engine.check_rate_limit(user_ip):
            self.send_response(429)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Rate limit exceeded. Maximum 5 quotes per hour."}).encode('utf-8'))
            return

        # 2. Parse Body
        content_len = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_len)
        data = json.loads(body)
        images_b64 = data.get('images', [])
        heavy_level = data.get('heavyMaterialLevel', 'none')

        try:
             # Prepare inputs
            base64_imgs = [img.split(",")[1] if "," in img else img for img in images_b64]
            
            # 3. Run Vision-Only Mode
            if not VISION_ENABLED:
                raise ValueError(f"Vision Pipeline not available: {VISION_ERROR}")
            
            print("� Vision Mode Active (Florence-2 + Depth-Anything-V2)")
            result = asyncio.run(engine.process_quote_with_vision(base64_imgs, heavy_level))
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode('utf-8'))
            
        except Exception as e:
            print(f"Server Error: {e}")
            self.send_error(500, str(e))
