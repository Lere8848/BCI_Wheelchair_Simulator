
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于 Unity 导出的 obstacles.json（包含 position/size/rotation）和一次 trial 的 trajectory_*.json（包含points的position），
在同一 2D 平面（x-z）下构建占据网格，进行形态学“几何级”膨胀（在多边形层面扩边），执行 8 邻接 A*，
计算 L_ideal（同一障碍与轮椅尺寸约束下的最短可行路径长度）。
依赖：numpy、matplotlib（可选，用于可视化）。无需第三方几何库。

用法示例：
python compute_L_ideal.py 
  --obstacles obstacles.json 
  --trajectory trajectory_20250815_145355.json 
  --resolution 0.08 
  --wheel_radius 0.31 
  --safety_margin 0.01 
  --padding 0.1 
  --out_png ideal_path_vis.png

输出：在控制台打印 L_ideal（米），以及可选保存可视化 PNG。
"""

#--resolution：0.03–0.1 m/px（越小越精细，越慢）。
#--wheel_radius：按你轮椅底盘外接半径设定。
#--safety_margin：建议 0.1–0.2 m。
#--padding：外边框余量，路径贴边或 A* 失败可适当加大

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
# 工具函数：四元数 -> 旋转矩阵
# =========================
def quat_to_rotmat(qx, qy, qz, qw):
    """将四元数转换为 3x3 旋转矩阵（右手坐标系）。
    参考：标准公式。"""
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
# 数据结构
# =========================
@dataclass
class Obstacle:
    name: str
    center: Tuple[float, float]  # (x, z)
    size_x: float               # Unity local x size (米)
    size_z: float               # Unity local z size (米)
    rotmat: np.ndarray          # 3x3 旋转矩阵（世界系）


# =========================
# 解析 obstacles.json
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
# 解析 trajectory.json：取起点/终点
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
# 将障碍转换为“投影到 x-z 平面”的多边形（旋转矩形四角）
# 这里使用完整四元数：取局部 x 轴与 z 轴方向变换到世界系，
# 只取其 x、z 分量作为 2D 平面上的基向量。
# =========================
def obstacle_footprint_poly(obs: Obstacle, extra_margin: float) -> np.ndarray:
    """
    返回多边形顶点 (N,2)，顺序为四角，围绕中心 (x,z)。
    我们把局部 x、z 两条轴经过旋转投影到 x-z 平面，
    然后使用“几何级膨胀”：在这两条局部轴向上把半边长各加上 extra_margin。
    这样相当于对矩形做 Minkowski sum with a square（近似圆形膨胀，简单有效）。
    """
    cx, cz = obs.center
    # 局部半边长
    hx = obs.size_x * 0.5 + extra_margin
    hz = obs.size_z * 0.5 + extra_margin

    # 世界系中，局部 x 轴与 z 轴
    ex_world = obs.rotmat @ np.array([1.0, 0.0, 0.0], dtype=np.float64)
    ez_world = obs.rotmat @ np.array([0.0, 0.0, 1.0], dtype=np.float64)

    # 投影到 x-z 平面（丢弃 y 分量），并单位化，避免斜切缩放
    ex2 = np.array([ex_world[0], ex_world[2]], dtype=np.float64)
    ez2 = np.array([ez_world[0], ez_world[2]], dtype=np.float64)
    # 若异常接近零向量，回退为轴对齐
    def safe_unit(v: np.ndarray) -> np.ndarray:
        n = np.linalg.norm(v)
        if n < 1e-8:
            return np.array([1.0, 0.0], dtype=np.float64)
        return v / n
    ex2 = safe_unit(ex2)
    ez2 = safe_unit(ez2)

    # 四个角（中心 +/- hx*ex2 +/- hz*ez2）
    c = np.array([cx, cz], dtype=np.float64)
    p1 = c + hx*ex2 + hz*ez2
    p2 = c - hx*ex2 + hz*ez2
    p3 = c - hx*ex2 - hz*ez2
    p4 = c + hx*ex2 - hz*ez2
    poly = np.vstack([p1, p2, p3, p4])
    return poly


# =========================
# 建立网格边界与映射
# =========================
@dataclass
class GridSpec:
    origin: Tuple[float, float]   # (min_x, min_z) 世界坐标
    resolution: float             # 米/像素
    width: int
    height: int


def compute_bounds(obstacles: List[Obstacle],
                   start: Tuple[float, float],
                   goal: Tuple[float, float],
                   padding: float,
                   extra_margin: float) -> Tuple[float, float, float, float]:
    """根据障碍（考虑几何膨胀）、起终点，计算世界范围边界（含 padding）。"""
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
    """世界坐标 (x,z) -> 网格索引 (col,row)，注意行对应 z 轴。"""
    cx = (x - spec.origin[0]) / spec.resolution
    cz = (z - spec.origin[1]) / spec.resolution
    j = int(round(cz))  # row (y方向索引)
    i = int(round(cx))  # col (x方向索引)
    return i, j


def poly_to_pixels(poly: np.ndarray, spec: GridSpec) -> np.ndarray:
    """将多边形顶点（世界系）映射到像素坐标（整数），返回 (N,2) 的 (i,j)。"""
    pts = [world_to_grid(x, z, spec) for x, z in poly]
    return np.array(pts, dtype=np.int32)


# =========================
# 多边形填充（扫描像素中心点，点在多边形内则置 1）
# 采用射线法/奇偶规则进行点在多边形测试。
# 为了效率，只在多边形像素包围盒内扫描。
# =========================
def point_in_poly(x: float, y: float, poly: np.ndarray) -> bool:
    """奇偶规则点测（多边形 poly 须为 (N,2)，按顺时针/逆时针均可）。"""
    inside = False
    n = poly.shape[0]
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i+1) % n]
        # 检查边跨越 y 的情况
        if ((y1 > y) != (y2 > y)):
            # 计算交点的 x 坐标
            xin = (x2 - x1) * (y - y1) / (y2 - y1 + 1e-12) + x1
            if xin >= x:
                inside = not inside
    return inside


def rasterize_polygons(polys_world: List[np.ndarray], spec: GridSpec) -> np.ndarray:
    """将多个世界坐标多边形栅格化到占据网格（1=障碍，0=可行）。"""
    occ = np.zeros((spec.height, spec.width), dtype=np.uint8)
    # 为避免重复 world->grid 误差累积，点在像素中心进行测试：
    for poly in polys_world:
        # 计算世界坐标包围盒 -> 映射为像素范围
        minx, minz = poly[:,0].min(), poly[:,1].min()
        maxx, maxz = poly[:,0].max(), poly[:,1].max()
        min_i, min_j = world_to_grid(minx, minz, spec)
        max_i, max_j = world_to_grid(maxx, maxz, spec)
        # clamp
        min_i = max(min_i-1, 0); min_j = max(min_j-1, 0)
        max_i = min(max_i+1, spec.width-1); max_j = min(max_j+1, spec.height-1)
        # 扫描像素中心点
        for j in range(min_j, max_j+1):
            cz = spec.origin[1] + j * spec.resolution
            for i in range(min_i, max_i+1):
                cx = spec.origin[0] + i * spec.resolution
                if point_in_poly(cx, cz, poly):
                    occ[j, i] = 1
    return occ


# =========================
# A* 寻路（8 邻接）
# =========================
from heapq import heappush, heappop

def astar_8conn(occ: np.ndarray, start_ij: Tuple[int,int], goal_ij: Tuple[int,int]) -> Optional[List[Tuple[int,int]]]:
    """在二值占据网格上执行 8 邻接 A*。occ=1 表示障碍。返回像素路径（含起终点）。"""
    H, W = occ.shape
    si, sj = start_ij
    gi, gj = goal_ij
    if not (0 <= si < W and 0 <= sj < H and 0 <= gi < W and 0 <= gj < H):
        return None
    if occ[sj, si] == 1 or occ[gj, gi] == 1:
        return None

    # 8 邻接及其代价
    nbrs = [(-1, -1, math.sqrt(2)), (0, -1, 1.0), (1, -1, math.sqrt(2)),
            (-1,  0, 1.0),                        (1,  0, 1.0),
            (-1,  1, math.sqrt(2)), (0,  1, 1.0), (1,  1, math.sqrt(2))]

    # 启发函数：欧氏距离
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
            # 回溯路径
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
# 主流程
# =========================
def compute_L_ideal(obstacles_path: str,
                    trajectory_path: str,
                    resolution: float = 0.05,
                    wheel_radius: float = 0.35,
                    safety_margin: float = 0.15,
                    padding: float = 1.0,
                    out_png: Optional[str] = None) -> float:
    """计算 L_ideal（米）。"""
    # 1) 读取数据
    obstacles = load_obstacles(obstacles_path)
    start, goal = load_start_goal_from_trajectory(trajectory_path)

    # 2) 计算边界并建立网格
    extra = wheel_radius + safety_margin  # 几何级膨胀量（米）
    min_x, min_z, max_x, max_z = compute_bounds(obstacles, start, goal, padding, extra)
    width = int(math.ceil((max_x - min_x) / resolution)) + 1
    height = int(math.ceil((max_z - min_z) / resolution)) + 1
    spec = GridSpec(origin=(min_x, min_z), resolution=resolution, width=width, height=height)

    # 3) 将所有障碍转换为“已膨胀”的四边形（世界系）
    polys = [obstacle_footprint_poly(obs, extra) for obs in obstacles]

    # 4) 栅格化为占据网格
    occ = rasterize_polygons(polys, spec)

    # 5) 起终点映射到像素
    si, sj = world_to_grid(start[0], start[1], spec)
    gi, gj = world_to_grid(goal[0], goal[1], spec)

    # 6) A* 最短路
    path = astar_8conn(occ, (si, sj), (gi, gj))
    if path is None or len(path) < 2:
        raise RuntimeError("A* failed: no feasible path found. 请检查膨胀参数、分辨率或边界 padding 是否过小。")

    # 7) 计算像素路径长度（像素单位步长累加）
    length_px = 0.0
    for k in range(len(path) - 1):
        (i1, j1), (i2, j2) = path[k], path[k+1]
        di, dj = i2 - i1, j2 - j1
        step = math.sqrt(di*di + dj*dj)
        length_px += step
    L_ideal = length_px * resolution  # 转换为米

    # 8) 可选：保存可视化
    if out_png and HAS_PLT:
        fig, ax = plt.subplots(figsize=(8, 8))
        # 显示占据网格（黑=障碍）
        ax.imshow(occ, origin='lower', cmap='gray_r',
                  extent=[spec.origin[0], spec.origin[0]+spec.width*spec.resolution,
                          spec.origin[1], spec.origin[1]+spec.height*spec.resolution])
        # 画起终点
        ax.plot([start[0]], [start[1]], 'go', label='start')
        ax.plot([goal[0]], [goal[1]], 'ro', label='goal')
        # 画路径（把像素坐标转世界）
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
