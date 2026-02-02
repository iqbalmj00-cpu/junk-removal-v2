"""
Bundle Builder - Constructs CalibrationBundle from extracted EXIF.

This is the main entry point for calibration during ingestion.
"""

from typing import Optional

from .calibration_bundle import CalibrationBundle, scale_intrinsics
from .exif_extractor import (
    extract_exif_with_exiftool,
    decode_and_orient,
    identify_lens,
    compute_fx_diagonal,
    apply_zoom_policy,
    compute_confidence
)


def build_calibration_bundle(
    raw_bytes: bytes,
    model_width: int,
    model_height: int,
    frontend_exif: Optional[dict] = None,
    frame_id: str = ""
) -> CalibrationBundle:
    """
    Build complete CalibrationBundle from raw image bytes.
    
    Args:
        raw_bytes: Original image bytes (HEIC/JPEG)
        model_width: DepthPro input width
        model_height: DepthPro input height
        frontend_exif: Optional browser-extracted EXIF (convenience fallback)
        frame_id: For logging
    
    Returns:
        CalibrationBundle with all intrinsics computed
    """
    bundle = CalibrationBundle()
    bundle.model_input_width = model_width
    bundle.model_input_height = model_height
    
    # =========================================================================
    # 1. EXIF EXTRACTION - FRONTEND IS PRIMARY (server gets compressed JPEGs)
    # =========================================================================
    # Frontend extracts EXIF from original bytes before compression
    # Server receives already-compressed JPEG with stripped EXIF
    # So frontend EXIF is our primary source, server is backup
    
    server_exif = extract_exif_with_exiftool(raw_bytes)
    
    # Merge: frontend takes priority since it has original file access
    combined_exif = {}
    if frontend_exif:
        # Normalize frontend EXIF keys to match server format
        combined_exif = {
            'Make': frontend_exif.get('make'),
            'Model': frontend_exif.get('model'),
            'FocalLength': frontend_exif.get('focalLength'),
            'FocalLengthIn35mmFilm': frontend_exif.get('focalLength35mm'),
            'Orientation': frontend_exif.get('orientation', 1),
            'LensModel': frontend_exif.get('lensModel'),
            'ImageWidth': frontend_exif.get('imageWidth'),
            'ImageHeight': frontend_exif.get('imageHeight'),
        }
        bundle.exif_from_frontend = True
        print(f"[BUNDLE] Using frontend EXIF: {combined_exif.get('Make')} {combined_exif.get('Model')}")
    
    # Merge server EXIF (fills in gaps)
    for key, val in server_exif.items():
        if val is not None and combined_exif.get(key) is None:
            combined_exif[key] = val
    
    bundle.exif_from_server = bool(server_exif.get('Make') or server_exif.get('Model'))
    server_exif = combined_exif  # Use merged exif going forward
    
    # =========================================================================
    # 2. DECODE + ORIENT PIXELS
    # =========================================================================
    try:
        img_oriented, dims = decode_and_orient(raw_bytes)
        bundle.decoded_raw_width = dims['decoded_raw_width']
        bundle.decoded_raw_height = dims['decoded_raw_height']
        bundle.decoded_oriented_width = dims['decoded_oriented_width']
        bundle.decoded_oriented_height = dims['decoded_oriented_height']
    except Exception as e:
        print(f"[BUNDLE] Decode failed: {e}")
        bundle.calib_warnings.append(f"decode_failed:{str(e)[:50]}")
        return bundle
    
    # =========================================================================
    # 3. EXTRACT CAMERA INFO
    # =========================================================================
    bundle.make = server_exif.get('Make')
    bundle.model = server_exif.get('Model')
    bundle.lens_model = server_exif.get('LensModel')
    bundle.focal_length_mm = server_exif.get('FocalLength')
    bundle.focal_length_35mm = server_exif.get('FocalLengthIn35mmFilm')
    bundle.orientation = server_exif.get('Orientation', 1)
    
    # =========================================================================
    # 4. IDENTIFY LENS
    # =========================================================================
    lens_id, lens_reason, lens_source = identify_lens(
        server_exif, bundle.make, bundle.model
    )
    bundle.lens_id = lens_id
    bundle.lens_id_reason = lens_reason
    bundle.lens_id_source = lens_source
    
    # =========================================================================
    # 5. ZOOM POLICY
    # =========================================================================
    raw_zoom = server_exif.get('DigitalZoomRatio')
    effective_zoom, anchoring_mult, zoom_warnings = apply_zoom_policy(raw_zoom)
    bundle.digital_zoom_ratio = effective_zoom
    bundle.anchoring_mult = anchoring_mult
    bundle.calib_warnings.extend(zoom_warnings)
    
    # =========================================================================
    # 6. DERIVE FOCAL_35MM IF MISSING (from focal_mm + device crop factor)
    # =========================================================================
    # iPhone crop factors (main lens): sensor diagonal ratio to 35mm
    DEVICE_CROP_FACTORS = {
        # iPhone 12 series: 1/1.7" sensor → crop ~5.1x
        'iPhone 12': 5.1, 'iPhone 12 Pro': 5.1, 'iPhone 12 Pro Max': 5.1,
        # iPhone 13 series: larger sensor
        'iPhone 13': 4.8, 'iPhone 13 Pro': 4.8, 'iPhone 13 Pro Max': 4.8,
        # iPhone 14/15 series
        'iPhone 14': 4.5, 'iPhone 14 Pro': 4.5, 'iPhone 14 Pro Max': 4.5,
        'iPhone 15': 4.3, 'iPhone 15 Pro': 4.3, 'iPhone 15 Pro Max': 4.3,
    }
    
    focal_35mm_effective = bundle.focal_length_35mm
    if not focal_35mm_effective and bundle.focal_length_mm and bundle.model:
        # Try to derive from physical focal length + device crop
        for device_key, crop in DEVICE_CROP_FACTORS.items():
            if device_key.lower() in bundle.model.lower():
                focal_35mm_effective = bundle.focal_length_mm * crop
                bundle.calib_warnings.append(f"focal_35mm_derived:{focal_35mm_effective:.0f}")
                print(f"[BUNDLE] Derived focal_35mm={focal_35mm_effective:.0f}mm from {bundle.focal_length_mm}mm × {crop}x crop")
                break
    
    # =========================================================================
    # 7. COMPUTE BASE INTRINSICS (at decoded_oriented)
    # =========================================================================
    fx_base, fy_base, fx_warnings = compute_fx_diagonal(
        focal_35mm_effective,
        bundle.decoded_oriented_width,
        bundle.decoded_oriented_height,
        bundle.digital_zoom_ratio
    )
    bundle.fx_base = fx_base
    bundle.fy_base = fy_base
    bundle.cx_base = bundle.decoded_oriented_width / 2
    bundle.cy_base = bundle.decoded_oriented_height / 2
    bundle.calib_warnings.extend(fx_warnings)
    
    # Determine source
    if 'fallback_fov_60' in fx_warnings:
        bundle.calib_source = 'fallback'
    else:
        bundle.calib_source = 'exif'
    
    # =========================================================================
    # 7. SCALE TO MODEL INTRINSICS (what DepthPro sees)
    # =========================================================================
    fx, fy, cx, cy = scale_intrinsics(
        bundle.fx_base, bundle.fy_base,
        bundle.cx_base, bundle.cy_base,
        bundle.decoded_oriented_width, bundle.decoded_oriented_height,
        bundle.model_input_width, bundle.model_input_height
    )
    bundle.fx = fx
    bundle.fy = fy
    bundle.cx = cx
    bundle.cy = cy
    
    # =========================================================================
    # 8. COMPUTE CONFIDENCE
    # =========================================================================
    bundle.calib_confidence = compute_confidence(
        bundle.exif_from_server,
        bundle.make,
        bundle.model,
        bundle.lens_id,
        bundle.calib_source
    )
    
    # Log
    bundle.log_chain(frame_id)
    
    return bundle
