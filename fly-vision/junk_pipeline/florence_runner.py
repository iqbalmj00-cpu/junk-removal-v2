"""
Florence-2 via Replicate API for box re-labeling.
Replaces local HuggingFace loading (broken due to transformers version incompatibility).

v9.5: Uses lucataco/florence-2-large on Replicate
"""

import replicate
from PIL import Image
from io import BytesIO
import base64
import ast


class FlorenceRunner:
    """Runner for Florence-2 box re-labeling via Replicate API."""
    
    MODEL_ID = "lucataco/florence-2-large:da53547e17d45b9cfb48174b2f18af8b83ca020fa76db62136bf9c6616762595"
    
    def _image_to_data_uri(self, image: Image.Image) -> str:
        """Convert PIL image to data URI for Replicate."""
        buffered = BytesIO()
        image.save(buffered, format="JPEG", quality=85)
        b64 = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/jpeg;base64,{b64}"
    
    def _parse_caption(self, output) -> str:
        """Parse Replicate response to extract caption."""
        # Response format: {'img': None, 'text': "{'<CAPTION>': 'description'}"}
        raw = None
        
        # Handle dict with 'text' key
        if isinstance(output, dict):
            if 'text' in output:
                raw = output['text']
            elif '<CAPTION>' in output:
                return str(output['<CAPTION>'])[:100]
            else:
                return str(output)[:100]
        elif hasattr(output, 'text'):
            raw = output.text
        else:
            raw = str(output)
        
        # Parse "{'<CAPTION>': '...'}" string format
        try:
            parsed = ast.literal_eval(raw)
            if isinstance(parsed, dict) and '<CAPTION>' in parsed:
                return str(parsed['<CAPTION>'])[:100]
        except:
            pass
        
        return raw.strip()[:100] if raw else ""
    
    def _caption_region(self, image: Image.Image) -> str:
        """Get caption for cropped region via Replicate API."""
        try:
            output = replicate.run(
                self.MODEL_ID,
                input={
                    "image": self._image_to_data_uri(image),
                    "task_input": "Caption"  # Verified parameter from cog source
                }
            )
            return self._parse_caption(output)
        except Exception as e:
            print(f"[Florence-2] API error: {e}")
            return ""
    
    def relabel_boxes(
        self, 
        image: Image.Image, 
        boxes: list[dict]
    ) -> list[dict]:
        """
        Re-label DINO boxes with Florence-2 captions.
        
        Args:
            image: Full PIL image
            boxes: List of DINO detection boxes with 'box' and 'label' keys
            
        Returns:
            Same boxes list with updated 'label' and 'original_dino_label' keys
        """
        print(f"[Florence-2] Relabeling {len(boxes)} boxes via Replicate...")
        
        for i, box in enumerate(boxes):
            coords = box['box']  # [x1, y1, x2, y2]
            crop = image.crop(coords)
            
            # Skip tiny crops
            if crop.width < 32 or crop.height < 32:
                continue
            
            caption = self._caption_region(crop)
            if caption:
                old_label = box.get('label', 'unknown')
                box['label'] = caption
                box['original_dino_label'] = old_label
                
                # v9.5: Filter out boxes where Florence describes a living tree
                if self._is_tree_caption(caption):
                    box['tree_filtered'] = True
                    print(f"[Florence-2] Box {i+1}: '{old_label}' → '{caption}' [TREE_FILTERED]")
                else:
                    print(f"[Florence-2] Box {i+1}: '{old_label}' → '{caption}'")
        
        return boxes
    
    def _is_tree_caption(self, caption: str) -> bool:
        """
        Check if Florence caption describes a living tree (not cut material).
        
        Returns True for captions like:
        - "a tree in front of a building"
        - "a large tree in the middle of a yard"
        
        Returns False for:
        - "a pile of logs" (cut wood)
        - "a pile of branches" (cut branches)
        """
        lower = caption.lower()
        
        # Patterns indicating the SUBJECT is a tree (not cut material)
        tree_patterns = [
            'a tree in',        # "a tree in front of...", "a tree in the middle..."
            'the tree in',
            'a large tree',
            'a tall tree',
            'trees in front',
            'tree standing',
        ]
        
        for pattern in tree_patterns:
            if pattern in lower:
                return True
        
        return False


# Singleton instance
_runner = None


def get_florence_runner() -> FlorenceRunner:
    """Get singleton FlorenceRunner instance."""
    global _runner
    if _runner is None:
        _runner = FlorenceRunner()
    return _runner
