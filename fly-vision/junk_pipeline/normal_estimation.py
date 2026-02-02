"""
v7.2: Boundary-Focused Normal Estimation

Optimized normal estimation for mask boundaries only.
Avoids expensive computation over entire 500K point cloud.
"""

import numpy as np
from scipy.spatial import cKDTree
from typing import Optional


def estimate_boundary_normals(
    points: np.ndarray,
    pixel_indices: np.ndarray,
    mask: np.ndarray,
    k: int = 12,
    max_samples: int = 5000
) -> tuple[np.ndarray, np.ndarray]:
    """
    Estimate normals at mask boundary points using local PCA.
    
    Performance optimization: Only processes boundary pixels, not interior.
    O(max_samples × k × log(N)) instead of O(N × k × log(N))
    
    Args:
        points: Nx3 array of 3D points
        pixel_indices: Nx2 array of (row, col) for each point
        mask: HxW boolean mask of segmentation
        k: Number of neighbors for PCA (default 12)
        max_samples: Maximum boundary points to sample (default 5000)
        
    Returns:
        sampled_points: Mx3 array of boundary points
        normals: Mx3 array of estimated normals
    """
    if points.shape[0] == 0 or mask is None:
        return np.array([]).reshape(0, 3), np.array([]).reshape(0, 3)
    
    H, W = mask.shape
    
    # Build pixel→point index lookup (sparse)
    pixel_to_point = {}
    for i, (r, c) in enumerate(pixel_indices):
        r, c = int(r), int(c)
        if 0 <= r < H and 0 <= c < W:
            pixel_to_point[(r, c)] = i
    
    # Extract boundary pixels (mask edge detection)
    from scipy.ndimage import binary_erosion
    interior = binary_erosion(mask, iterations=1)
    boundary_mask = mask & ~interior
    boundary_coords = np.argwhere(boundary_mask)
    
    if len(boundary_coords) == 0:
        return np.array([]).reshape(0, 3), np.array([]).reshape(0, 3)
    
    # Sample boundary pixels
    if len(boundary_coords) > max_samples:
        indices = np.random.choice(len(boundary_coords), max_samples, replace=False)
        boundary_coords = boundary_coords[indices]
    
    # Map boundary pixels to points
    boundary_point_indices = []
    for r, c in boundary_coords:
        idx = pixel_to_point.get((r, c))
        if idx is not None:
            boundary_point_indices.append(idx)
    
    if len(boundary_point_indices) == 0:
        return np.array([]).reshape(0, 3), np.array([]).reshape(0, 3)
    
    boundary_point_indices = np.array(boundary_point_indices)
    boundary_points = points[boundary_point_indices]
    
    # Build KD-tree for all points (once)
    tree = cKDTree(points)
    
    # Estimate normals using local PCA
    normals = np.zeros_like(boundary_points)
    
    for i, pt in enumerate(boundary_points):
        # Find k nearest neighbors
        dists, indices = tree.query(pt, k=min(k, len(points)))
        neighbors = points[indices]
        
        # Center the neighbors
        centered = neighbors - neighbors.mean(axis=0)
        
        # PCA: smallest eigenvector = surface normal
        if len(neighbors) >= 3:
            cov = np.cov(centered.T)
            eigenvalues, eigenvectors = np.linalg.eigh(cov)
            normal = eigenvectors[:, 0]  # Smallest eigenvalue
            
            # Orient normal upward (Y-up convention)
            if normal[1] < 0:
                normal = -normal
            
            normals[i] = normal
        else:
            normals[i] = np.array([0, 1, 0])  # Default to up
    
    return boundary_points, normals


def compute_verticality(normals: np.ndarray, up: np.ndarray = None) -> float:
    """
    Compute fraction of normals that are nearly horizontal (vertical surfaces).
    
    Args:
        normals: Nx3 array of unit normals
        up: Up direction (default Y-up: [0, 1, 0])
        
    Returns:
        Fraction of normals with |dot(n, up)| < 0.3 (≈73° from vertical)
    """
    if normals.shape[0] == 0:
        return 0.0
    
    if up is None:
        up = np.array([0, 1, 0])
    
    dots = np.abs(np.dot(normals, up))
    vertical_count = np.sum(dots < 0.3)  # Nearly horizontal = vertical surface
    
    return vertical_count / len(normals)
