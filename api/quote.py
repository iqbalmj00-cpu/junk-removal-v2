from http.server import BaseHTTPRequestHandler
import json
import os
import asyncio
import google.generativeai as genai
from openai import AsyncOpenAI
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# 1. CONFIGURATION (You need BOTH keys now)
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
openai_client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# 2. SAFETY SETTINGS
SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
}

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_len = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_len)
        data = json.loads(body)
        images_b64 = data.get('images', []) 

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.process_images(images_b64))
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode('utf-8'))
        except Exception as e:
            self.send_error(500, str(e))

    async def process_images(self, images_b64):
        # Prepare for Gemini (Needs raw base64)
        gemini_imgs = [{'mime_type': 'image/jpeg', 'data': img.split(",")[1] if "," in img else img} for img in images_b64]
        
        # Prepare for GPT-5 Nano (Needs Data URL with header)
        gpt_imgs = []
        for img in images_b64:
            # Ensure proper Data URL format
            url = img if "data:image" in img else f"data:image/jpeg;base64,{img}"
            gpt_imgs.append({"type": "image_url", "image_url": {"url": url}})

        # --- PARALLEL EXECUTION ---
        # Model A: Gemini (The Expert)
        task_gemini = self.ask_gemini(gemini_imgs)
        
        # Model B: GPT-5 Nano (The Auditor)
        task_gpt = self.ask_gpt_nano(gpt_imgs)
        
        # Run together
        res_gemini, res_gpt = await asyncio.gather(task_gemini, task_gpt)
        
        # --- CONSENSUS LOGIC ---
        vol_gemini = self.calculate_volume(res_gemini)
        vol_gpt = self.calculate_volume(res_gpt)
        
        # Safety Check
        if vol_gemini == 0 or vol_gpt == 0:
            return {"status": "SHADOW_MODE", "reason": "AI failed to quantify"}

        # Compare (15% Variance Limit)
        diff = abs(vol_gemini - vol_gpt)
        avg_vol = (vol_gemini + vol_gpt) / 2
        variance = diff / avg_vol if avg_vol > 0 else 0

        if variance > 0.15:
            return {"status": "SHADOW_MODE", "message": "High Variance Detected"}
        
        # SUCCESS
        final_vol = round(avg_vol, 1)
        price = max(95, final_vol * 35) # $95 min or $35/yard

        return {
            "status": "SUCCESS",
            "volume_yards": final_vol,
            "price": round(price, 2)
        }

    def calculate_volume(self, json_data):
        if not json_data or 'dimensions' not in json_data: return 0.0
        d = json_data['dimensions']
        # (L x W x H * Density) / 27
        return (d.get('l',0) * d.get('w',0) * d.get('h',0) * json_data.get('density', 1.0)) / 27.0

    async def ask_gemini(self, images):
        try:
            # Change this to 'gemini-3.0-pro' when available to you
            model = genai.GenerativeModel('gemini-3-pro-preview') 
            prompt = """
            You are a Spatial Surveyor. Output JSON ONLY.
            1. Estimate bounding box (l, w, h) in FEET.
            2. Estimate Density (0.0 to 1.0).
            Format: {"dimensions": {"l": float, "w": float, "h": float}, "density": float}
            """
            response = await model.generate_content_async(
                [prompt, *images],
                generation_config={"response_mime_type": "application/json"},
                safety_settings=SAFETY_SETTINGS
            )
            return json.loads(response.text)
        except: return {}

    async def ask_gpt_nano(self, images):
        try:
            content = [{"type": "text", "text": "Output JSON: {'dimensions': {'l': float, 'w': float, 'h': float}, 'density': float} (Estimate bounding box in feet)"}]
            content.extend(images)
            
            response = await openai_client.chat.completions.create(
                model="gpt-5-nano-2025-08-07", # YOUR SPECIFIC MODEL
                messages=[{"role": "user", "content": content}],
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except: return {}
