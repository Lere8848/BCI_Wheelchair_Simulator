
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Given Unity-exported obstacles.json (position/size/rotation) and a trial trajectory_*.json
(points with positions), build an occupancy grid on the same 2D plane (x-z), inflate obstacles
geometrically (polygon-level expansion), run 8-connected A*, and compute L_ideal (the shortest
feasible path length under the same obstacle + wheelchair size constraints).

Dependencies: numpy; matplotlib (optional, for visualization). No third-party geometry library.

Usage example:
python compute_L_ideal.py 
  --obstacles obstacles.json 
  --trajectory trajectory_20250815_145355.json 
  --resolution 0.08 
  --wheel_radius 0.31 
  --safety_margin 0.01 
  --padding 0.1 
  --out_png ideal_path_vis.png

Output: print L_ideal (meters) to stdout, and optionally save a visualization PNG.
"""

# --resolution: 0.03–0.1 m/px (smaller is more accurate but slower)
# --wheel_radius: set to the outer radius of the wheelchair base
# --safety_margin: typically 0.1–0.2 m
# --padding: world-bound margin; increase if the path hugs the boundary or A* fails

import json
import math
import argparse
from dataclasses import dataclass
from typing import List, Tuple, Optional
import numpy as np

try:
    import matplotlib.pyplot as plt
    HAS_PLT = True
except Exception:
    HAS_PLT = False


# =========================
# Utility: quaternion -> rotation matrix
# =========================
def quat_to_rotmat(qx, qy, qz, qw):
    """Convert quaternion to a 3x3 rotation matrix (right-handed).
    Reference: standard formula."""
    x, y, z, w = qx, qy, qz, qw
    xx, yy, zz = x*x, y*y, z*z
    xy, xz, yz = x*y, x*z, y*z
    wx, wy, wz = w*x, w*y, w*z
    R = np.array([
        [1 - 2*(yy + zz),     2*(xy - wz),         2*(xz + wy)    ],
        [2*(xy + wz),         1 - 2*(xx + zz),     2*(yz - wx)    ],
        [2*(xz - wy),         2*(yz + wx),         1 - 2*(xx + yy)]
    ], dtype=np.float64)
    return R


# =========================
# Data structures
# =========================
@dataclass
class Obstacle:
    name: str
    center: Tuple[float, float]  # (x, z)
    size_x: float               # Unity local x size (m)
    size_z: float               # Unity local z size (m)
    rotmat: np.ndarray          # 3x3 rotation matrix (world)


# =========================
# Parse obstacles.json
# =========================
def load_obstacles(path: str) -> List[Obstacle]:
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    obs_list = []
    for o in data.get("obstacles", []):
        name = o.get("name", "obs")
        px = float(o["position"]["x"])
        pz = float(o["position"]["z"])
        sx = float(o["size"]["x"])
        sz = float(o["size"]["z"])
        qx = float(o["rotation"]["x"])
        qy = float(o["rotation"]["y"])
        qz = float(o["rotation"]["z"])
        qw = float(o["rotation"]["w"])
        R = quat_to_rotmat(qx, qy, qz, qw)
        obs_list.append(Obstacle(name=name, center=(px, pz), size_x=sx, size_z=sz, rotmat=R))
    return obs_list


# =========================
# Parse trajectory.json: start/goal
# =========================
def load_start_goal_from_trajectory(path: str) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    pts = data.get("points", [])
    if len(pts) < 2:
        raise ValueError("trajectory points < 2")
    sx = float(pts[0]["position"]["x"])
    sz = float(pts[0]["position"]["z"])
    gx = float(pts[-1]["position"]["x"])
    gz = float(pts[-1]["position"]["z"])
    return (sx, sz), (gx, gz)


# =========================
# Convert obstacle to a polygon projected on the x-z plane (rotated rectangle corners).
# We use the full quaternion rotation: transform local x/z axes to world, then take
# the x/z components as 2D basis vectors.
# =========================
def obstacle_footprint_poly(obs: Obstacle, extra_margin: float) -> np.ndarray:
    """
    Return polygon vertices (N,2) as the four corners around center (x,z).

    We project the rotated local x/z axes onto the x-z plane and apply a geometric inflation:
    add extra_margin to the half-extents along both local axes. This is equivalent to a
    Minkowski sum with a square (a simple, effective approximation of circular inflation).
    """
    cx, cz = obs.center
    # Local half-extents
    hx = obs.size_x * 0.5 + extra_margin
    hz = obs.size_z * 0.5 + extra_margin

    # Local x/z axes in world coordinates
    ex_world = obs.rotmat @ np.array([1.0, 0.0, 0.0], dtype=np.float64)
    ez_world = obs.rotmat @ np.array([0.0, 0.0, 1.0], dtype=np.float64)

    # Project to x-z plane (drop y) and normalize
    ex2 = np.array([ex_world[0], ex_world[2]], dtype=np.float64)
    ez2 = np.array([ez_world[0], ez_world[2]], dtype=np.float64)
    # Fallback if near-zero vector
    def safe_unit(v: np.ndarray) -> np.ndarray:
        n = np.linalg.norm(v)
        if n < 1e-8:
            return np.array([1.0, 0.0], dtype=np.float64)
        return v / n
    ex2 = safe_unit(ex2)
    ez2 = safe_unit(ez2)

    # Four corners (center +/- hx*ex2 +/- hz*ez2)
    c = np.array([cx, cz], dtype=np.float64)
    p1 = c + hx*ex2 + hz*ez2
    p2 = c - hx*ex2 + hz*ez2
    p3 = c - hx*ex2 - hz*ez2
    p4 = c + hx*ex2 - hz*ez2
    poly = np.vstack([p1, p2, p3, p4])
    return poly


# =========================
# Grid bounds and mapping
# =========================
@dataclass
class GridSpec:
    origin: Tuple[float, float]   # (min_x, min_z) world coordinates
    resolution: float             # meters/pixel
    width: int
    height: int


def compute_bounds(obstacles: List[Obstacle],
                   start: Tuple[float, float],
                   goal: Tuple[float, float],
                   padding: float,
                   extra_margin: float) -> Tuple[float, float, float, float]:
    """Compute world bounds (with padding) given inflated obstacles and start/goal."""
    xs, zs = [], []
    for obs in obstacles:
        poly = obstacle_footprint_poly(obs, extra_margin)
        xs.extend(poly[:,0].tolist())
        zs.extend(poly[:,1].tolist())
    xs.extend([start[0], goal[0]])
    zs.extend([start[1], goal[1]])
    min_x, max_x = min(xs)-padding, max(xs)+padding
    min_z, max_z = min(zs)-padding, max(zs)+padding
    return min_x, min_z, max_x, max_z


def world_to_grid(x: float, z: float, spec: GridSpec) -> Tuple[int, int]:
    """World (x,z) -> grid indices (col,row). Note: row corresponds to z axis."""
    cx = (x - spec.origin[0]) / spec.resolution
    cz = (z - spec.origin[1]) / spec.resolution
    j = int(round(cz))  # row (y方向索引)
    i = int(round(cx))  # col (x方向索引)
    return i, j


def poly_to_pixels(poly: np.ndarray, spec: GridSpec) -> np.ndarray:
    """Map polygon vertices (world) to pixel coords (ints), returns (N,2) of (i,j)."""
    pts = [world_to_grid(x, z, spec) for x, z in poly]
    return np.array(pts, dtype=np.int32)


# =========================
# Polygon rasterization (scan pixel centers; mark occupied if inside polygon)
# Uses ray casting / even-odd rule point-in-polygon test.
# For efficiency, only scan within the polygon's pixel bounding box.
# =========================
def point_in_poly(x: float, y: float, poly: np.ndarray) -> bool:
    """Even-odd point-in-polygon test (poly is (N,2); cw/ccw both OK)."""
    inside = False
    n = poly.shape[0]
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i+1) % n]
        # Check whether the edge crosses y
        if ((y1 > y) != (y2 > y)):
            # Intersection x
            xin = (x2 - x1) * (y - y1) / (y2 - y1 + 1e-12) + x1
            if xin >= x:
                inside = not inside
    return inside


def rasterize_polygons(polys_world: List[np.ndarray], spec: GridSpec) -> np.ndarray:
    """Rasterize world polygons into an occupancy grid (1=obstacle, 0=free)."""
    occ = np.zeros((spec.height, spec.width), dtype=np.uint8)
    # Test at pixel centers
    for poly in polys_world:
        # World bounding box -> pixel range
        minx, minz = poly[:,0].min(), poly[:,1].min()
        maxx, maxz = poly[:,0].max(), poly[:,1].max()
        min_i, min_j = world_to_grid(minx, minz, spec)
        max_i, max_j = world_to_grid(maxx, maxz, spec)
        # Clamp
        min_i = max(min_i-1, 0); min_j = max(min_j-1, 0)
        max_i = min(max_i+1, spec.width-1); max_j = min(max_j+1, spec.height-1)
        # Scan pixel centers
        for j in range(min_j, max_j+1):
            cz = spec.origin[1] + j * spec.resolution
            for i in range(min_i, max_i+1):
                cx = spec.origin[0] + i * spec.resolution
                if point_in_poly(cx, cz, poly):
                    occ[j, i] = 1
    return occ


# =========================
# A* search (8-connected)
# =========================
from heapq import heappush, heappop

def astar_8conn(occ: np.ndarray, start_ij: Tuple[int,int], goal_ij: Tuple[int,int]) -> Optional[List[Tuple[int,int]]]:
    """Run 8-connected A* on a binary occupancy grid. occ=1 means obstacle.
    Returns pixel path including start and goal."""
    H, W = occ.shape
    si, sj = start_ij
    gi, gj = goal_ij
    if not (0 <= si < W and 0 <= sj < H and 0 <= gi < W and 0 <= gj < H):
        return None
    if occ[sj, si] == 1 or occ[gj, gi] == 1:
        return None

    # 8-connected neighbors and costs
    nbrs = [(-1, -1, math.sqrt(2)), (0, -1, 1.0), (1, -1, math.sqrt(2)),
            (-1,  0, 1.0),                        (1,  0, 1.0),
            (-1,  1, math.sqrt(2)), (0,  1, 1.0), (1,  1, math.sqrt(2))]

    # Heuristic: Euclidean distance
    def h(i, j):
        return math.hypot(i - gi, j - gj)

    open_heap = []
    gscore = np.full((H, W), np.inf, dtype=np.float64)
    came = dict()

    gscore[sj, si] = 0.0
    heappush(open_heap, (h(si, sj), 0.0, (si, sj)))

    visited = np.zeros((H, W), dtype=np.uint8)

    while open_heap:
        f, g, (ci, cj) = heappop(open_heap)
        if visited[cj, ci]:
            continue
        visited[cj, ci] = 1

        if (ci, cj) == (gi, gj):
            # Backtrack path
            path = [(ci, cj)]
            while (ci, cj) != (si, sj):
                ci, cj = came[(ci, cj)]
                path.append((ci, cj))
            path.reverse()
            return path

        for di, dj, w in nbrs:
            ni, nj = ci + di, cj + dj
            if not (0 <= ni < W and 0 <= nj < H):
                continue
            if occ[nj, ni] == 1:
                continue
            ng = gscore[cj, ci] + w
            if ng < gscore[nj, ni]:
                gscore[nj, ni] = ng
                came[(ni, nj)] = (ci, cj)
                heappush(open_heap, (ng + h(ni, nj), ng, (ni, nj)))
    return None


# =========================
# Main pipeline
# =========================
def compute_L_ideal(obstacles_path: str,
                    trajectory_path: str,
                    resolution: float = 0.05,
                    wheel_radius: float = 0.35,
                    safety_margin: float = 0.15,
                    padding: float = 1.0,
                    out_png: Optional[str] = None) -> float:
    """Compute L_ideal (meters)."""
    # 1) Load data
    obstacles = load_obstacles(obstacles_path)
    start, goal = load_start_goal_from_trajectory(trajectory_path)

    # 2) Compute bounds and build grid
    extra = wheel_radius + safety_margin  # geometric inflation (m)
    min_x, min_z, max_x, max_z = compute_bounds(obstacles, start, goal, padding, extra)
    width = int(math.ceil((max_x - min_x) / resolution)) + 1
    height = int(math.ceil((max_z - min_z) / resolution)) + 1
    spec = GridSpec(origin=(min_x, min_z), resolution=resolution, width=width, height=height)

    # 3) Inflate obstacles (world polygons)
    polys = [obstacle_footprint_poly(obs, extra) for obs in obstacles]

    # 4) Rasterize to occupancy grid
    occ = rasterize_polygons(polys, spec)

    # 5) Map start/goal to pixels
    si, sj = world_to_grid(start[0], start[1], spec)
    gi, gj = world_to_grid(goal[0], goal[1], spec)

    # 6) A* shortest path
    path = astar_8conn(occ, (si, sj), (gi, gj))
    if path is None or len(path) < 2:
        raise RuntimeError("A* failed: no feasible path found. Check inflation params, resolution, or padding.")

    # 7) Pixel-path length (sum step lengths)
    length_px = 0.0
    for k in range(len(path) - 1):
        (i1, j1), (i2, j2) = path[k], path[k+1]
        di, dj = i2 - i1, j2 - j1
        step = math.sqrt(di*di + dj*dj)
        length_px += step
    L_ideal = length_px * resolution

    # 8) Optional visualization
    if out_png and HAS_PLT:
        fig, ax = plt.subplots(figsize=(8, 8))
        # Show occupancy grid
        ax.imshow(occ, origin='lower', cmap='gray_r',
                  extent=[spec.origin[0], spec.origin[0]+spec.width*spec.resolution,
                          spec.origin[1], spec.origin[1]+spec.height*spec.resolution])
        # Start/goal
        ax.plot([start[0]], [start[1]], 'go', label='start')
        ax.plot([goal[0]], [goal[1]], 'ro', label='goal')
        # Path (pixel -> world)
        xs = [spec.origin[0] + i*spec.resolution for (i, j) in path]
        zs = [spec.origin[1] + j*spec.resolution for (i, j) in path]
        ax.plot(xs, zs, '-', lw=2, label='A* path')
        ax.set_title(f"L_ideal = {L_ideal:.3f} m")
        ax.set_xlabel("X (m)")
        ax.set_ylabel("Z (m)")
        ax.legend(loc='best')
        fig.tight_layout()
        fig.savefig(out_png, dpi=200)
        plt.close(fig)

    return L_ideal


def parse_args():
    ap = argparse.ArgumentParser(description="Compute L_ideal (shortest feasible path length) from Unity logs.")
    ap.add_argument('--obstacles', type=str, required=True, help='Path to obstacles.json')
    ap.add_argument('--trajectory', type=str, required=True, help='Path to trajectory_*.json (to get start & goal)')
    ap.add_argument('--resolution', type=float, default=0.05, help='Grid resolution (m/pixel)')
    ap.add_argument('--wheel_radius', type=float, default=0.35, help='Wheelchair outer radius (m)')
    ap.add_argument('--safety_margin', type=float, default=0.15, help='Extra safety margin (m)')
    ap.add_argument('--padding', type=float, default=1.0, help='World bounds padding (m)')
    ap.add_argument('--out_png', type=str, default=None, help='Optional output visualization PNG path')
    return ap.parse_args()


def main():
    args = parse_args()
    L = compute_L_ideal(
        obstacles_path=args.obstacles,
        trajectory_path=args.trajectory,
        resolution=args.resolution,
        wheel_radius=args.wheel_radius,
        safety_margin=args.safety_margin,
        padding=args.padding,
        out_png=args.out_png
    )
    print(f"L_ideal = {L:.6f} m")


if __name__ == "__main__":
    main()
