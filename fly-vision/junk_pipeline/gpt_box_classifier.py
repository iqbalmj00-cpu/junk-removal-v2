"""
GPT-4o-mini Box Classifier for junk-aware box labeling.
Replaces Florence-2 with a model that understands junk criteria.

v9.6: Uses gpt-4o-mini for cost-effective junk classification
"""

import openai
import base64
from PIL import Image
from io import BytesIO
import json
import os


# Classification prompt
BOX_CLASSIFICATION_PROMPT = """You are a junk removal assistant classifying image regions.

## Your Task
Look at this cropped image region and:
1. Describe what you see in 5-10 words
2. Classify it as JUNK or NOT_JUNK

## What IS Junk (classify as JUNK):
- CUT logs, stumps, wood rounds — disconnected from any tree, lying on ground
- CUT branches, palm fronds, brush piles — removed vegetation on ground
- Dried leaves, yard waste, mulch — collected debris
- Garbage bags, trash, debris piles
- Furniture, mattresses, appliances
- Construction waste, lumber, pallets, drywall
- Boxes, cardboard, household items
- Dumpsters/trailers FULL of debris
- Tarp-covered piles (likely junk underneath)
- Fallen/cut trees lying on ground

## What is NOT Junk (classify as NOT_JUNK):
- Living trees — trunk rooted in ground, leaves/branches extending upward
- Tree canopy — branches/foliage of a standing tree
- Standing structures — fences, decks, sheds, buildings
- Vehicles (empty) — cars, trucks, trailers (unless full of junk)
- Ground/lawn — empty grass, dirt, pavement
- Sky, background — buildings, streets, other scenery
- People, animals
- Attached vegetation — plants/shrubs still growing

## Decision Guide
Ask yourself: "Is this material DISCONNECTED and ready to be HAULED AWAY?"
- YES → JUNK
- NO (still attached, living, or permanent structure) → NOT_JUNK

## Output Format
Return ONLY valid JSON, no markdown:
{"classification": "JUNK", "description": "brief description", "confidence": "HIGH"}"""


class GPTBoxClassifier:
    """Classifier for box regions using GPT-4o-mini."""
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.model = "gpt-4o-mini"
    
    def _image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL image to base64 for OpenAI API."""
        buffered = BytesIO()
        image.save(buffered, format="JPEG", quality=85)
        return base64.b64encode(buffered.getvalue()).decode()
    
    def _classify_region(self, image: Image.Image) -> dict:
        """Classify a cropped region using GPT-4o-mini."""
        try:
            base64_image = self._image_to_base64(image)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": BOX_CLASSIFICATION_PROMPT
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                    "detail": "low"  # Use low detail for speed/cost
                                }
                            }
                        ]
                    }
                ],
                max_tokens=100,
                temperature=0.1  # Low temp for consistent classifications
            )
            
            content = response.choices[0].message.content.strip()
            
            # Parse JSON response
            # Handle potential markdown code blocks
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            result = json.loads(content)
            return {
                "classification": result.get("classification", "JUNK"),
                "description": result.get("description", "unknown")[:100],
                "confidence": result.get("confidence", "MEDIUM")
            }
            
        except json.JSONDecodeError as e:
            print(f"[GPT-Classifier] JSON parse error: {e}, content: {content[:100]}")
            return {"classification": "JUNK", "description": "parse error - defaulting to junk", "confidence": "LOW"}
        except Exception as e:
            print(f"[GPT-Classifier] API error: {e}")
            return {"classification": "JUNK", "description": "api error - defaulting to junk", "confidence": "LOW"}
    
    def classify_boxes(
        self, 
        image: Image.Image, 
        boxes: list[dict]
    ) -> list[dict]:
        """
        Classify DINO boxes using GPT-4o-mini.
        
        Args:
            image: Full PIL image
            boxes: List of DINO detection boxes with 'box' and 'label' keys
            
        Returns:
            Same boxes list with updated labels and classification info
        """
        print(f"[GPT-Classifier] Classifying {len(boxes)} boxes with gpt-4o-mini...")
        
        for i, box in enumerate(boxes):
            coords = box['box']  # [x1, y1, x2, y2]
            crop = image.crop(coords)
            
            # Skip tiny crops
            if crop.width < 32 or crop.height < 32:
                continue
            
            result = self._classify_region(crop)
            
            old_label = box.get('label', 'unknown')
            box['label'] = result['description']
            box['original_dino_label'] = old_label
            box['gpt_classification'] = result['classification']
            box['gpt_confidence'] = result['confidence']
            
            # Filter out NOT_JUNK boxes
            if result['classification'] == 'NOT_JUNK':
                box['tree_filtered'] = True
                print(f"[GPT-Classifier] Box {i+1}: '{old_label}' → '{result['description']}' [NOT_JUNK]")
            else:
                print(f"[GPT-Classifier] Box {i+1}: '{old_label}' → '{result['description']}' [JUNK]")
        
        return boxes


# Singleton instance
_classifier = None


def get_gpt_classifier() -> GPTBoxClassifier:
    """Get singleton GPTBoxClassifier instance."""
    global _classifier
    if _classifier is None:
        _classifier = GPTBoxClassifier()
    return _classifier
