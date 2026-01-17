from http.server import BaseHTTPRequestHandler
import json
import os
import asyncio
import hashlib
import base64
import re
from openai import OpenAI
from google import genai
from google.genai import types

class PricingEngine:
    def __init__(self):
        # 1. Initialize New Google Client
        self.google_client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))
        
        # 2. Initialize OpenAI
        self.openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

        # 3. Simple Cache
        self.cache = {} 

    def _generate_fingerprint(self, images):
        """Creates a deterministic hash based on input image bytes."""
        combined_data = b""
        for img in images:
            if hasattr(img, 'read'):
                img.seek(0)
                combined_data += img.read()
                img.seek(0)
            else:
                combined_data += img
        return hashlib.sha256(combined_data).hexdigest()

    def _get_mental_tetris_prompt(self):
        return """
        You are a Professional Junk Removal Estimator. Output JSON ONLY.
        Your Goal: Estimate the volume of this pile as if it were loaded into a standard Dump Truck.

        CRITICAL INSTRUCTION:
        Do NOT measure the "Bounding Box" of the pile on the ground (this captures too much air).
        Instead, perform a "Mental Tetris" simulation:
        1. Imagine chopping up long items (like carpets/lumber).
        2. Imagine stacking all items tightly into a cube.
        3. Estimate the dimensions of that *TIGHTLY PACKED* cube in FEET.

        OUTPUT JSON ONLY:
        {
          "packed_dimensions": {
              "l": float, // Length of the compacted cube in FEET
              "w": float, // Width of the compacted cube in FEET
              "h": float  // Height of the compacted cube in FEET
          },
          "debug_summary": "Brief list of items found"
        }
        """

    def ask_gemini(self, images):
        try:
            # NEW SDK SYNTAX with GEMINI 3 PREVIEW
            response = self.google_client.models.generate_content(
                model='gemini-3-pro-preview', # STRICTLY THIS STRING
                contents=[self._get_mental_tetris_prompt(), *images],
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    response_mime_type='application/json'
                )
            )
            return json.loads(response.text)
        except Exception as e:
            print(f"❌ GEMINI ERROR: {e}")
            return None

    def ask_gpt(self, base64_images):
        try:
            content = [{"type": "text", "text": self._get_mental_tetris_prompt()}]
            for img_b64 in base64_images:
                 content.append({
                    "type": "image_url", 
                    "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}
                })

            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": content}],
                temperature=0.0,
                max_tokens=300,
                response_format={"type": "json_object"} # FORCE JSON MODE
            )
            
            raw_content = response.choices[0].message.content
            
            # Remove Markdown if present
            if raw_content.startswith("```json"):
                raw_content = raw_content[7:]
            if raw_content.endswith("```"):
                raw_content = raw_content[:-3]
                
            return json.loads(raw_content)
        except Exception as e:
            print(f"❌ GPT ERROR: {e}")
            return None

    def calculate_volume(self, json_data):
        if not json_data or 'packed_dimensions' not in json_data: 
            return 0.0
        d = json_data['packed_dimensions']
        return (d.get('l', 0) * d.get('w', 0) * d.get('h', 0)) / 27.0

    def process_quote(self, images, base64_images):
        # 1. CACHE CHECK
        fingerprint = self._generate_fingerprint(images)
        if fingerprint in self.cache:
            print("✅ CACHE HIT: Returning saved quote.")
            return self.cache[fingerprint]

        # 2. RUN AI MODELS
        print("⚠️ CACHE MISS: Running Analysis...")
        
        # Prepare content parts for Gemini New SDK
        gemini_inputs = []
        for img_bytes in images:
             gemini_inputs.append(types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"))

        # Parallel Execution (Simulated here via sequential call for simplicity in class, but Vercel handles async)
        # Note: In a real async environment we'd use await, but this class is synchronous logic wrapped in handler.
        # Ideally we make these async, but requests library is sync. 
        # The Google SDK 'client.models.generate_content' is synchronous.
        # OpenAI 'client.chat.completions.create' is synchronous.
        # To keep it simple and robust per request, we keep sync calls. Vercel Function will handle the request time.
        
        res_gemini = self.ask_gemini(gemini_inputs)
        res_gpt = self.ask_gpt(base64_images)

        # 3. CONSENSUS LOGIC
        vol_gemini = self.calculate_volume(res_gemini)
        vol_gpt = self.calculate_volume(res_gpt)

        # --- VISIBILITY LOGGING ---
        diff = abs(vol_gemini - vol_gpt)
        print(f"🧮 MATH DUMP: Gemini({vol_gemini:.2f}yd) | GPT({vol_gpt:.2f}yd) | Diff({diff:.2f}yd)")

        if vol_gemini == 0 or vol_gpt == 0:
            return {"status": "SHADOW_MODE", "reason": "AI Blindness"}

        avg_vol = (vol_gemini + vol_gpt) / 2
        variance = (diff / avg_vol) if avg_vol > 0 else 0
        is_safe = False

        # --- THE SAFETY GATES (UPDATED TO 3.0) ---
        # "Small Load Exception": If models differ by < 3.0 yards, APPROVE IT.
        if diff < 3.0: 
            is_safe = True
        # "Percentage Guardrail": For huge jobs, ensure 25% agreement.
        elif variance <= 0.25: 
            is_safe = True

        if not is_safe:
            print(f"⛔ BLOCKED: Variance {diff:.2f} > 3.0")
            return {
                "status": "SHADOW_MODE", 
                "message": "High Variance", 
                "debug": f"Gemini: {vol_gemini:.1f} vs GPT: {vol_gpt:.1f}"
            }

        # 4. PRICING MATH
        final_vol = round(avg_vol, 1)
        price = max(95, final_vol * 35)

        result = {
            "status": "SUCCESS",
            "volume_yards": final_vol,
            "price": round(price, 2),
            "quote_id": fingerprint,
            "items": res_gemini.get('debug_summary', 'Mixed Junk')
        }

        # 5. UPDATE CACHE
        self.cache[fingerprint] = result
        return result

# --- Vercel Handler Integration ---
# Instantiate globally to persist cache across warm starts
engine = PricingEngine()

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_len = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_len)
        data = json.loads(body)
        images_b64 = data.get('images', []) 

        try:
            # Prepare inputs
            # 1. Base64 Strings (for GPT)
            base64_imgs = []
            for img in images_b64:
                 # Strip header if present to get clean base64
                 clean = img.split(",")[1] if "," in img else img
                 base64_imgs.append(clean)

            # 2. Bytes (for Gemini & Hashing)
            bytes_imgs = [base64.b64decode(b64) for b64 in base64_imgs]

            # Process
            result = engine.process_quote(bytes_imgs, base64_imgs)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode('utf-8'))
        except Exception as e:
            self.send_error(500, str(e))
