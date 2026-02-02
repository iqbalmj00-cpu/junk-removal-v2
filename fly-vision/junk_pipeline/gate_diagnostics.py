"""
Gate Attribution Diagnostics (v6.8.0)

Provides per-frame diagnostic report for all pipeline gates that can
cause frame elimination or weight reduction.

Purpose: Distinguish between three root causes:
1. B is root: floor genuinely not visible in many real shots
2. C→B coupling: segmentation/semantic steps cause artificial "no floor"
3. Scene mismatch: curb/grass/multi-plane + glare makes floor model brittle
"""

from dataclasses import dataclass, field
from typing import Optional
import numpy as np
import json


@dataclass
class GateAttributionReport:
    """
    Per-frame diagnostic report for gate decisions.
    
    Collected after perception and geometry stages to enable
    root cause analysis of frame elimination.
    """
    # Frame identity
    frame_id: str
    
    # === Gate 1: Floor Visibility (orchestrator) ===
    bulk_area_ratio: float = 0.0          # Lane B mask coverage of image
    bottom_35_clear_pct: float = 100.0    # % of bottom 35% NOT covered by mask
    gate1_passed: bool = True             # Did Gate 1 pass?
    gate1_fail_reason: str = ""           # If failed, why?
    
    # === Gate 2: Floor Quality (geometry + fusion) ===
    geometry_ran: bool = False            # Did geometry stage run?
    depth_valid_pct: float = 0.0          # % of pixels with valid depth
    inlier_ratio: float = 0.0             # RANSAC inlier ratio
    yfl95: float = 0.0                    # Floor flatness P95(|Y|) in meters
    plane_angle_deg: float = 0.0          # Angle from vertical (0° = perfect horizontal floor)
    floor_quality: str = "unknown"        # "good", "noisy", "failed"
    gate2_passed: bool = True             # Would this frame be eligible?
    gate2_fail_reason: str = ""           # If failed, why?
    
    # === Semantic Filtering Impact (orchestrator) ===
    semantic_removed_pct: float = 0.0     # % of mask removed by semantic subtraction
    semantic_labels_removed: list = field(default_factory=list)
    
    # === Output Metrics ===
    frame_volume_cy: float = 0.0          # Volume produced by this frame
    
    # === Diagnostic Flags ===
    suspected_mask_leakage: bool = False  # Mask appears to cover ground
    suspected_multi_surface: bool = False # Scene has curb/grass/multi-plane
    suspected_glare: bool = False         # Depth quality suggests glare issue
    
    def to_dict(self) -> dict:
        """Convert to dict for JSON serialization."""
        return {
            "frame_id": self.frame_id[:8] if len(self.frame_id) > 8 else self.frame_id,
            "gate1": {
                "passed": self.gate1_passed,
                "bulk_area_ratio": round(self.bulk_area_ratio, 3),
                "bottom_35_clear_pct": round(self.bottom_35_clear_pct, 1),
                "fail_reason": self.gate1_fail_reason or None
            },
            "gate2": {
                "passed": self.gate2_passed,
                "inlier_ratio": round(self.inlier_ratio, 3),
                "yfl95": round(self.yfl95, 3),
                "plane_angle_deg": round(self.plane_angle_deg, 1),
                "floor_quality": self.floor_quality,
                "fail_reason": self.gate2_fail_reason or None
            },
            "semantic": {
                "removed_pct": round(self.semantic_removed_pct * 100, 1),
                "labels": self.semantic_labels_removed[:3]  # Top 3
            },
            "output": {
                "volume_cy": round(self.frame_volume_cy, 3),
                "geometry_ran": self.geometry_ran
            },
            "suspected_issues": {
                "mask_leakage": self.suspected_mask_leakage,
                "multi_surface": self.suspected_multi_surface,
                "glare": self.suspected_glare
            }
        }


def log_gate_attribution_report(report: GateAttributionReport) -> None:
    """Log a formatted gate attribution report."""
    print(f"\n{'='*60}")
    print(f"[GATE_REPORT] Frame {report.frame_id[:8]}")
    print(f"{'='*60}")
    
    # Gate 1
    g1_status = "✓ PASS" if report.gate1_passed else "✗ FAIL"
    print(f"[Gate 1: Floor Visibility] {g1_status}")
    print(f"  bulk_area_ratio: {report.bulk_area_ratio:.1%}")
    print(f"  bottom_35_clear_pct: {report.bottom_35_clear_pct:.1f}%")
    if report.gate1_fail_reason:
        print(f"  reason: {report.gate1_fail_reason}")
    
    # Gate 2
    if report.geometry_ran:
        g2_status = "✓ PASS" if report.gate2_passed else "✗ FAIL"
        print(f"[Gate 2: Floor Quality] {g2_status}")
        print(f"  inlier_ratio: {report.inlier_ratio:.3f}")
        print(f"  yfl95: {report.yfl95:.3f}m")
        print(f"  plane_angle_deg: {report.plane_angle_deg:.1f}°")
        print(f"  floor_quality: {report.floor_quality}")
        if report.gate2_fail_reason:
            print(f"  reason: {report.gate2_fail_reason}")
    else:
        print(f"[Gate 2: Floor Quality] SKIPPED (no geometry)")
    
    # Semantic
    print(f"[Semantic Filtering]")
    print(f"  removed: {report.semantic_removed_pct:.1%}")
    if report.semantic_labels_removed:
        print(f"  labels: {report.semantic_labels_removed[:3]}")
    
    # Output
    print(f"[Output]")
    print(f"  volume_cy: {report.frame_volume_cy:.3f}")
    
    # Suspected issues
    issues = []
    if report.suspected_mask_leakage:
        issues.append("MASK_LEAKAGE")
    if report.suspected_multi_surface:
        issues.append("MULTI_SURFACE")
    if report.suspected_glare:
        issues.append("GLARE")
    if issues:
        print(f"[Suspected Issues] {', '.join(issues)}")
    
    print(f"{'='*60}\n")


def log_gate_attribution_summary(reports: list) -> None:
    """Log a summary table of all frame reports."""
    print(f"\n{'='*80}")
    print(f"[GATE_ATTRIBUTION_SUMMARY] {len(reports)} frames")
    print(f"{'='*80}")
    print(f"{'Frame':<10} {'G1':>4} {'G2':>4} {'Bulk%':>6} {'Bot%':>5} {'Inlier':>7} {'YFL95':>6} {'Sem%':>5} {'Vol':>6}")
    print(f"{'-'*80}")
    
    for r in reports:
        g1 = "✓" if r.gate1_passed else "✗"
        g2 = "✓" if r.gate2_passed else ("✗" if r.geometry_ran else "-")
        print(
            f"{r.frame_id[:8]:<10} "
            f"{g1:>4} {g2:>4} "
            f"{r.bulk_area_ratio*100:>5.1f}% "
            f"{r.bottom_35_clear_pct:>4.1f}% "
            f"{r.inlier_ratio:>6.3f} "
            f"{r.yfl95:>5.3f}m "
            f"{r.semantic_removed_pct*100:>4.1f}% "
            f"{r.frame_volume_cy:>5.2f}"
        )
    
    # Summary stats
    g1_pass = sum(1 for r in reports if r.gate1_passed)
    g2_pass = sum(1 for r in reports if r.gate2_passed and r.geometry_ran)
    geom_ran = sum(1 for r in reports if r.geometry_ran)
    
    print(f"{'-'*80}")
    print(f"Gate 1 passed: {g1_pass}/{len(reports)}")
    print(f"Geometry ran: {geom_ran}/{len(reports)}")
    print(f"Gate 2 passed: {g2_pass}/{geom_ran if geom_ran > 0 else 1} (of frames with geometry)")
    
    # Suspected issues
    mask_leak = sum(1 for r in reports if r.suspected_mask_leakage)
    multi_surf = sum(1 for r in reports if r.suspected_multi_surface)
    glare = sum(1 for r in reports if r.suspected_glare)
    print(f"\nSuspected issues:")
    print(f"  Mask leakage: {mask_leak}")
    print(f"  Multi-surface: {multi_surf}")
    print(f"  Glare: {glare}")
    print(f"{'='*80}\n")


def detect_suspected_issues(
    report: GateAttributionReport,
    lane_d_ground_area_ratio: float = 0.0,
    depth_confidence: float = 1.0
) -> None:
    """
    Detect suspected root causes and update report flags.
    
    Called after all metrics are populated.
    """
    # Suspected mask leakage: Gate 1 failed with low clear %, but Lane D shows ground
    if not report.gate1_passed and lane_d_ground_area_ratio > 0.10:
        # Lane D sees ground, but Gate 1 says no floor visible
        # This suggests Lane B mask is covering the ground
        report.suspected_mask_leakage = True
    
    # Suspected multi-surface: High YFL95 but decent inlier ratio
    # (floor looks OK but isn't flat)
    if report.yfl95 > 0.12 and report.inlier_ratio > 0.5:
        report.suspected_multi_surface = True
    
    # Suspected glare: Low depth confidence or very low inlier ratio
    if depth_confidence < 0.5 or (report.geometry_ran and report.inlier_ratio < 0.2):
        report.suspected_glare = True


# =============================================================================
# VISUAL OVERLAY GENERATION (B5)
# =============================================================================

def generate_gate_overlays(
    frame_id: str,
    original_image: "PIL.Image.Image",
    bulk_mask_np: np.ndarray = None,
    bulk_mask_clean_np: np.ndarray = None,
    ground_mask_np: np.ndarray = None,
    floor_inlier_mask: np.ndarray = None,
    output_dir: str = "/tmp/gate_overlays"
) -> dict:
    """
    Generate visual overlay images for gate debugging.
    
    Returns dict of {overlay_name: filepath}.
    
    Generates:
    1. bulk_mask_overlay: Lane B mask in red semi-transparent over original
    2. bottom_band_overlay: Bottom 35% highlighted with clear pixels in green
    3. semantic_comparison: Side-by-side raw vs cleaned mask
    4. floor_mask_overlay: Lane D ground mask in green
    5. combined_overlay: All masks combined with color coding
    """
    from PIL import Image, ImageDraw, ImageFont
    import os
    
    os.makedirs(output_dir, exist_ok=True)
    frame_short = frame_id[:8]
    result_paths = {}
    
    # Get dimensions
    img_w, img_h = original_image.size
    
    # Helper to create overlay
    def create_overlay(base_img, mask, color, alpha=0.4):
        """Create semi-transparent colored overlay."""
        if mask is None:
            return base_img.copy()
        
        # Ensure mask is same size as image
        mask_h, mask_w = mask.shape[:2]
        if (mask_w, mask_h) != (img_w, img_h):
            # Resize mask to match image
            from PIL import Image as PILImage
            mask_pil = PILImage.fromarray((mask.astype(np.uint8) * 255))
            mask_pil = mask_pil.resize((img_w, img_h), PILImage.NEAREST)
            mask = np.array(mask_pil) > 128
        
        overlay = base_img.copy().convert("RGBA")
        color_layer = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
        
        # Create colored mask
        for y in range(img_h):
            for x in range(img_w):
                if mask[y, x]:
                    color_layer.putpixel((x, y), (*color, int(255 * alpha)))
        
        overlay = Image.alpha_composite(overlay, color_layer)
        return overlay.convert("RGB")
    
    # Faster overlay using numpy
    def create_overlay_fast(base_img, mask, color, alpha=0.4):
        """Create semi-transparent colored overlay (vectorized)."""
        if mask is None:
            return base_img.copy()
        
        base_arr = np.array(base_img.convert("RGB")).astype(np.float32)
        
        # Ensure mask is same size as image
        mask_h, mask_w = mask.shape[:2]
        if (mask_w, mask_h) != (img_w, img_h):
            from PIL import Image as PILImage
            mask_pil = PILImage.fromarray((mask.astype(np.uint8) * 255))
            mask_pil = mask_pil.resize((img_w, img_h), PILImage.NEAREST)
            mask = np.array(mask_pil) > 128
        
        # Apply color where mask is true
        color_arr = np.array(color, dtype=np.float32)
        mask_3d = np.stack([mask] * 3, axis=-1)
        
        result = np.where(
            mask_3d,
            base_arr * (1 - alpha) + color_arr * alpha,
            base_arr
        )
        
        return Image.fromarray(result.astype(np.uint8))
    
    # 1. Bulk mask overlay (red)
    if bulk_mask_np is not None:
        overlay = create_overlay_fast(original_image, bulk_mask_np, (255, 0, 0), 0.4)
        
        # Add bottom 35% line
        draw = ImageDraw.Draw(overlay)
        bottom_start = int(img_h * 0.65)
        draw.line([(0, bottom_start), (img_w, bottom_start)], fill=(0, 0, 255), width=3)
        
        # Add label
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
        except:
            font = ImageFont.load_default()
        draw.text((10, 10), f"Lane B Mask (red) | Bottom 35% line (blue)", fill=(255, 255, 255), font=font)
        
        path = f"{output_dir}/{frame_short}_bulk_mask.png"
        overlay.save(path)
        result_paths["bulk_mask_overlay"] = path
        print(f"[OVERLAY] Saved: {path}")
    
    # 2. Bottom band visualization
    if bulk_mask_np is not None:
        overlay = original_image.copy().convert("RGBA")
        bottom_start = int(img_h * 0.65)
        
        # Create color layer for bottom band
        color_layer = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
        
        # Ensure mask is same size
        mask = bulk_mask_np
        mask_h, mask_w = mask.shape[:2]
        if (mask_w, mask_h) != (img_w, img_h):
            mask_pil = Image.fromarray((mask.astype(np.uint8) * 255))
            mask_pil = mask_pil.resize((img_w, img_h), Image.NEAREST)
            mask = np.array(mask_pil) > 128
        
        color_arr = np.zeros((img_h, img_w, 4), dtype=np.uint8)
        # Bottom band: green for clear, red for masked
        for y in range(bottom_start, img_h):
            for x in range(img_w):
                if mask[y, x]:
                    color_arr[y, x] = [255, 0, 0, 128]  # Red = masked
                else:
                    color_arr[y, x] = [0, 255, 0, 128]  # Green = clear
        
        color_layer = Image.fromarray(color_arr, "RGBA")
        overlay = Image.alpha_composite(overlay, color_layer)
        
        # Add line at boundary
        draw = ImageDraw.Draw(overlay)
        draw.line([(0, bottom_start), (img_w, bottom_start)], fill=(255, 255, 0), width=2)
        
        # Calculate clear percentage
        bottom_band = mask[bottom_start:, :]
        clear_pct = (1 - np.mean(bottom_band)) * 100
        
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
        except:
            font = ImageFont.load_default()
        draw.text((10, 10), f"Bottom 35%: {clear_pct:.1f}% clear (need ≥8%)", fill=(255, 255, 255), font=font)
        status = "✓ PASS" if clear_pct >= 8 else "✗ FAIL"
        draw.text((10, 35), f"Gate 1: {status}", fill=(0, 255, 0) if clear_pct >= 8 else (255, 0, 0), font=font)
        
        path = f"{output_dir}/{frame_short}_bottom_band.png"
        overlay.convert("RGB").save(path)
        result_paths["bottom_band_overlay"] = path
        print(f"[OVERLAY] Saved: {path}")
    
    # 3. Semantic comparison (side by side)
    if bulk_mask_np is not None and bulk_mask_clean_np is not None:
        raw_overlay = create_overlay_fast(original_image, bulk_mask_np, (255, 165, 0), 0.5)  # Orange
        clean_overlay = create_overlay_fast(original_image, bulk_mask_clean_np, (0, 255, 0), 0.5)  # Green
        
        # Create side-by-side
        combined = Image.new("RGB", (img_w * 2, img_h))
        combined.paste(raw_overlay, (0, 0))
        combined.paste(clean_overlay, (img_w, 0))
        
        draw = ImageDraw.Draw(combined)
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
        except:
            font = ImageFont.load_default()
        
        removed_pct = 1.0 - (bulk_mask_clean_np.sum() / max(1, bulk_mask_np.sum()))
        draw.text((10, 10), "RAW Lane B Mask", fill=(255, 255, 255), font=font)
        draw.text((img_w + 10, 10), f"AFTER Semantic Filter (-{removed_pct*100:.1f}%)", fill=(255, 255, 255), font=font)
        
        path = f"{output_dir}/{frame_short}_semantic_compare.png"
        combined.save(path)
        result_paths["semantic_comparison"] = path
        print(f"[OVERLAY] Saved: {path}")
    
    # 4. Ground mask overlay (Lane D - green)
    if ground_mask_np is not None:
        overlay = create_overlay_fast(original_image, ground_mask_np, (0, 255, 0), 0.4)
        
        draw = ImageDraw.Draw(overlay)
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
        except:
            font = ImageFont.load_default()
        draw.text((10, 10), "Lane D Ground Mask (green)", fill=(255, 255, 255), font=font)
        
        path = f"{output_dir}/{frame_short}_ground_mask.png"
        overlay.save(path)
        result_paths["ground_mask_overlay"] = path
        print(f"[OVERLAY] Saved: {path}")
    
    # 5. Combined diagnostic overlay
    if bulk_mask_np is not None:
        base = np.array(original_image.convert("RGB")).astype(np.float32)
        
        # Resize masks if needed
        def resize_mask(m):
            if m is None:
                return None
            mh, mw = m.shape[:2]
            if (mw, mh) != (img_w, img_h):
                m_pil = Image.fromarray((m.astype(np.uint8) * 255))
                m_pil = m_pil.resize((img_w, img_h), Image.NEAREST)
                return np.array(m_pil) > 128
            return m
        
        bulk_resized = resize_mask(bulk_mask_np)
        ground_resized = resize_mask(ground_mask_np) if ground_mask_np is not None else None
        
        # Red for bulk mask
        if bulk_resized is not None:
            bulk_3d = np.stack([bulk_resized] * 3, axis=-1)
            base = np.where(bulk_3d, base * 0.6 + np.array([255, 0, 0]) * 0.4, base)
        
        # Green for ground (where not bulk)
        if ground_resized is not None:
            ground_only = ground_resized & (~bulk_resized if bulk_resized is not None else np.ones_like(ground_resized, dtype=bool))
            ground_3d = np.stack([ground_only] * 3, axis=-1)
            base = np.where(ground_3d, base * 0.6 + np.array([0, 255, 0]) * 0.4, base)
        
        overlay = Image.fromarray(base.astype(np.uint8))
        
        # Add bottom band line
        draw = ImageDraw.Draw(overlay)
        bottom_start = int(img_h * 0.65)
        draw.line([(0, bottom_start), (img_w, bottom_start)], fill=(255, 255, 0), width=2)
        
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
        except:
            font = ImageFont.load_default()
        draw.text((10, 10), "Red=Bulk Mask | Green=Ground | Yellow=35% line", fill=(255, 255, 255), font=font)
        
        path = f"{output_dir}/{frame_short}_combined.png"
        overlay.save(path)
        result_paths["combined_overlay"] = path
        print(f"[OVERLAY] Saved: {path}")
    
    return result_paths


def log_overlay_paths(all_paths: dict) -> None:
    """Log summary of generated overlay paths."""
    if not all_paths:
        print("[OVERLAYS] No overlays generated")
        return
    
    print(f"\n{'='*60}")
    print(f"[GATE_OVERLAYS] Generated {len(all_paths)} overlay sets")
    print(f"{'='*60}")
    for frame_id, paths in all_paths.items():
        print(f"\n{frame_id[:8]}:")
        for name, path in paths.items():
            print(f"  {name}: {path}")
    print(f"{'='*60}\n")
