#!/usr/bin/env python3
"""
Metric F: Path Efficiency Visualization
Path efficiency visualization: compare the ideal path (A*) vs the actual trajectory.

Features:
1. Create a visualization per trial
2. Plot L_ideal and L_actual on the obstacle map
3. Compute and display path efficiency
4. Use different styles for ideal vs actual paths
"""

import json
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import matplotlib.transforms as transforms
import numpy as np
import math
from scipy.spatial.transform import Rotation as R
import os
import csv
from pathlib import Path
import pandas as pd
from dataclasses import dataclass
from typing import List, Tuple, Optional
from heapq import heappush, heappop

# =========================
# User-configurable settings
# =========================
LOG_PATH = r"d:\UnityProject\wheelchair_sim\Assets\Logs\0820_use_this"
OUTPUT_PATH = Path(__file__).parent

class PathEfficiencyVisualizer:
    def __init__(self, log_base_path: str, output_path: str = None):
        """
        Initialize the path efficiency visualizer.
        
        Args:
            log_base_path: Root directory that contains the log folders
            output_path: Output directory; defaults to this script directory
        """
        self.log_base_path = Path(log_base_path)
        self.output_path = Path(output_path) if output_path else Path(__file__).parent
        self.output_path.mkdir(exist_ok=True)
        
        # A* parameters
        self.resolution = 0.05  # 网格分辨率 (m/pixel)
        self.wheel_radius = 0.35  # 轮椅外半径 (m)
        self.safety_margin = 0.23  # 安全边距 (m)
        self.padding = 1.0  # 世界边界填充 (m)
        
        # Visualization config
        self.path_colors = {
            'actual': {'color': '#2E86AB', 'label': 'Actual Path (L_actual)', 'linewidth': 3, 'alpha': 0.8},
            'ideal': {'color': '#A23B72', 'label': 'Ideal Path (L_ideal, A*)', 'linewidth': 3, 'alpha': 0.8, 'linestyle': '--'}
        }
    
    # ==================== Reused A* implementation ====================
    
    @dataclass
    class Obstacle:
        name: str
        center: Tuple[float, float]
        size_x: float
        size_z: float
        rotmat: np.ndarray

    @dataclass
    class GridSpec:
        origin: Tuple[float, float]
        resolution: float
        width: int
        height: int
    
    def quaternion_to_yaw(self, q):
        """Convert Unity quaternion (x, y, z, w) to yaw (rotation around Y axis)."""
        r = R.from_quat([q["x"], q["y"], q["z"], q["w"]])
        yaw = r.as_euler('xyz', degrees=True)[1]
        return yaw
    
    def quat_to_rotmat(self, qx, qy, qz, qw):
        """Convert quaternion to a 3x3 rotation matrix."""
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
    
    def load_obstacles(self, obstacles_file: Path) -> List['PathEfficiencyVisualizer.Obstacle']:
        """Load obstacles from obstacles.json."""
        try:
            with open(obstacles_file, 'r', encoding='utf-8') as f:
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
                R_mat = self.quat_to_rotmat(qx, qy, qz, qw)
                obs_list.append(self.Obstacle(name=name, center=(px, pz), size_x=sx, size_z=sz, rotmat=R_mat))
            return obs_list
        except Exception as e:
            print(f"Error loading obstacles from {obstacles_file}: {e}")
            return []
    
    def obstacle_footprint_poly(self, obs: 'PathEfficiencyVisualizer.Obstacle', extra_margin: float) -> np.ndarray:
        """Convert an obstacle into an inflated footprint polygon."""
        cx, cz = obs.center
        hx = obs.size_x * 0.5 + extra_margin
        hz = obs.size_z * 0.5 + extra_margin

        ex_world = obs.rotmat @ np.array([1.0, 0.0, 0.0], dtype=np.float64)
        ez_world = obs.rotmat @ np.array([0.0, 0.0, 1.0], dtype=np.float64)

        ex2 = np.array([ex_world[0], ex_world[2]], dtype=np.float64)
        ez2 = np.array([ez_world[0], ez_world[2]], dtype=np.float64)
        
        def safe_unit(v: np.ndarray) -> np.ndarray:
            n = np.linalg.norm(v)
            if n < 1e-8:
                return np.array([1.0, 0.0], dtype=np.float64)
            return v / n
        
        ex2 = safe_unit(ex2)
        ez2 = safe_unit(ez2)

        c = np.array([cx, cz], dtype=np.float64)
        p1 = c + hx*ex2 + hz*ez2
        p2 = c - hx*ex2 + hz*ez2
        p3 = c - hx*ex2 - hz*ez2
        p4 = c + hx*ex2 - hz*ez2
        poly = np.vstack([p1, p2, p3, p4])
        return poly
    
    def compute_bounds(self, obstacles: List['PathEfficiencyVisualizer.Obstacle'], 
                      start: Tuple[float, float], goal: Tuple[float, float],
                      padding: float, extra_margin: float) -> Tuple[float, float, float, float]:
        """Compute world bounds that cover obstacles and start/goal."""
        xs, zs = [], []
        for obs in obstacles:
            poly = self.obstacle_footprint_poly(obs, extra_margin)
            xs.extend(poly[:,0].tolist())
            zs.extend(poly[:,1].tolist())
        xs.extend([start[0], goal[0]])
        zs.extend([start[1], goal[1]])
        min_x, max_x = min(xs)-padding, max(xs)+padding
        min_z, max_z = min(zs)-padding, max(zs)+padding
        return min_x, min_z, max_x, max_z
    
    def world_to_grid(self, x: float, z: float, spec: 'PathEfficiencyVisualizer.GridSpec') -> Tuple[int, int]:
        """Convert world coordinates to grid indices."""
        cx = (x - spec.origin[0]) / spec.resolution
        cz = (z - spec.origin[1]) / spec.resolution
        j = int(round(cz))
        i = int(round(cx))
        return i, j
    
    def point_in_poly(self, x: float, y: float, poly: np.ndarray) -> bool:
        """Point-in-polygon test."""
        inside = False
        n = poly.shape[0]
        for i in range(n):
            x1, y1 = poly[i]
            x2, y2 = poly[(i+1) % n]
            if ((y1 > y) != (y2 > y)):
                xin = (x2 - x1) * (y - y1) / (y2 - y1 + 1e-12) + x1
                if xin >= x:
                    inside = not inside
        return inside
    
    def rasterize_polygons(self, polys_world: List[np.ndarray], spec: 'PathEfficiencyVisualizer.GridSpec') -> np.ndarray:
        """Rasterize polygons into an occupancy grid."""
        occ = np.zeros((spec.height, spec.width), dtype=np.uint8)
        for poly in polys_world:
            minx, minz = poly[:,0].min(), poly[:,1].min()
            maxx, maxz = poly[:,0].max(), poly[:,1].max()
            min_i, min_j = self.world_to_grid(minx, minz, spec)
            max_i, max_j = self.world_to_grid(maxx, maxz, spec)
            min_i = max(min_i-1, 0); min_j = max(min_j-1, 0)
            max_i = min(max_i+1, spec.width-1); max_j = min(max_j+1, spec.height-1)
            
            for j in range(min_j, max_j+1):
                cz = spec.origin[1] + j * spec.resolution
                for i in range(min_i, max_i+1):
                    cx = spec.origin[0] + i * spec.resolution
                    if self.point_in_poly(cx, cz, poly):
                        occ[j, i] = 1
        return occ
    
    def astar_8conn(self, occ: np.ndarray, start_ij: Tuple[int,int], goal_ij: Tuple[int,int]) -> Optional[List[Tuple[int,int]]]:
        """8-connected A* search."""
        H, W = occ.shape
        si, sj = start_ij
        gi, gj = goal_ij
        if not (0 <= si < W and 0 <= sj < H and 0 <= gi < W and 0 <= gj < H):
            return None
        if occ[sj, si] == 1 or occ[gj, gi] == 1:
            return None

        nbrs = [(-1, -1, math.sqrt(2)), (0, -1, 1.0), (1, -1, math.sqrt(2)),
                (-1,  0, 1.0),                        (1,  0, 1.0),
                (-1,  1, math.sqrt(2)), (0,  1, 1.0), (1,  1, math.sqrt(2))]

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
    
    def compute_ideal_path(self, obstacles_file: Path, start: Tuple[float, float], goal: Tuple[float, float]) -> Tuple[Optional[List[Tuple[float, float]]], float]:
        """Compute ideal path (A*) and return world path and length."""
        try:
            obstacles = self.load_obstacles(obstacles_file)
            if not obstacles:
                # 无障碍物时返回直线路径
                return [start, goal], math.sqrt((goal[0] - start[0])**2 + (goal[1] - start[1])**2)
            
            extra = self.wheel_radius + self.safety_margin
            min_x, min_z, max_x, max_z = self.compute_bounds(obstacles, start, goal, self.padding, extra)
            width = int(math.ceil((max_x - min_x) / self.resolution)) + 1
            height = int(math.ceil((max_z - min_z) / self.resolution)) + 1
            spec = self.GridSpec(origin=(min_x, min_z), resolution=self.resolution, width=width, height=height)

            polys = [self.obstacle_footprint_poly(obs, extra) for obs in obstacles]
            occ = self.rasterize_polygons(polys, spec)

            si, sj = self.world_to_grid(start[0], start[1], spec)
            gi, gj = self.world_to_grid(goal[0], goal[1], spec)

            path_pixels = self.astar_8conn(occ, (si, sj), (gi, gj))
            if path_pixels is None or len(path_pixels) < 2:
                return [start, goal], math.sqrt((goal[0] - start[0])**2 + (goal[1] - start[1])**2)

            # 转换为世界坐标
            world_path = []
            for i, j in path_pixels:
                world_x = spec.origin[0] + i * spec.resolution
                world_z = spec.origin[1] + j * spec.resolution
                world_path.append((world_x, world_z))

            # 计算路径长度
            length = 0.0
            for k in range(len(world_path) - 1):
                dx = world_path[k+1][0] - world_path[k][0]
                dz = world_path[k+1][1] - world_path[k][1]
                length += math.sqrt(dx*dx + dz*dz)
            
            return world_path, length
            
        except Exception as e:
            print(f"Error computing ideal path: {e}")
            return [start, goal], math.sqrt((goal[0] - start[0])**2 + (goal[1] - start[1])**2)
    
    # ==================== Trajectory loading ====================
    
    def load_actual_trajectory_from_csv(self, csv_file: Path) -> Tuple[List[Tuple[float, float]], float]:
        """Load the actual trajectory from CSV."""
        try:
            df = pd.read_csv(csv_file)
            
            pos_x_col = None
            pos_z_col = None
            
            for col in df.columns:
                if 'pos_x' in str(col) and pos_x_col is None:
                    pos_x_col = col
                elif 'pos_z' in str(col) and pos_z_col is None:
                    pos_z_col = col
            
            if pos_x_col is None or pos_z_col is None:
                return [], 0.0
            
            if isinstance(df[pos_x_col], pd.DataFrame):
                pos_x = df[pos_x_col].iloc[:, 0].values
            else:
                pos_x = df[pos_x_col].values
                
            if isinstance(df[pos_z_col], pd.DataFrame):
                pos_z = df[pos_z_col].iloc[:, 0].values
            else:
                pos_z = df[pos_z_col].values
            
            valid_mask = ~(np.isnan(pos_x) | np.isnan(pos_z))
            pos_x = pos_x[valid_mask]
            pos_z = pos_z[valid_mask]
            
            if len(pos_x) < 2:
                return [], 0.0
            
            trajectory = list(zip(pos_x, pos_z))
            
            # Compute trajectory length
            length = 0.0
            for i in range(len(trajectory) - 1):
                dx = trajectory[i+1][0] - trajectory[i][0]
                dz = trajectory[i+1][1] - trajectory[i][1]
                length += math.sqrt(dx*dx + dz*dz)
            
            return trajectory, length
            
        except Exception as e:
            print(f"Error loading trajectory from {csv_file}: {e}")
            return [], 0.0
    
    def load_collision_data(self, csv_file: Path) -> List[Tuple[float, float]]:
        """Load collision points from CSV."""
        collision_positions = []
        
        try:
            df = pd.read_csv(csv_file)
            
            collision_col = None
            pos_x_col = None
            pos_z_col = None
            
            for col in df.columns:
                if 'collision_flag' in str(col) and collision_col is None:
                    collision_col = col
                elif 'pos_x' in str(col) and pos_x_col is None:
                    pos_x_col = col
                elif 'pos_z' in str(col) and pos_z_col is None:
                    pos_z_col = col
            
            if collision_col is None or pos_x_col is None or pos_z_col is None:
                return collision_positions
            
            if isinstance(df[collision_col], pd.DataFrame):
                collision_flags = df[collision_col].iloc[:, 0]
            else:
                collision_flags = df[collision_col]
                
            if isinstance(df[pos_x_col], pd.DataFrame):
                pos_x = df[pos_x_col].iloc[:, 0]
            else:
                pos_x = df[pos_x_col]
                
            if isinstance(df[pos_z_col], pd.DataFrame):
                pos_z = df[pos_z_col].iloc[:, 0]
            else:
                pos_z = df[pos_z_col]
            
            collision_mask = collision_flags == 1
            if collision_mask.any():
                collision_x = pos_x[collision_mask]
                collision_z = pos_z[collision_mask]
                collision_positions = list(zip(collision_x, collision_z))
                
        except Exception as e:
            print(f"Error loading collision data from {csv_file}: {e}")
        
        return collision_positions
    
    # ==================== Obstacle drawing ====================
    
    def draw_obstacles(self, ax, obstacles):
        """Draw obstacles on the plot."""
        for ob in obstacles:
            pos = ob["position"]
            size = ob["size"]
            rot = ob["rotation"]
            name = ob["name"]

            cx = pos["x"]
            cz = pos["z"]
            w = size["x"]
            h = size["z"]
            angle = self.quaternion_to_yaw(rot)

            edge_color = 'black'
            face_color = 'gray'
            
            if "Wall" in name:
                start_x = cx
                start_y = cz
                edge_color = 'blue'
            else:
                x0 = cx - w / 2
                z0 = cz - h / 2
                start_x = x0
                start_y = z0
                edge_color = 'black'

            rect = Rectangle((start_x, start_y), w, h, edgecolor=edge_color, 
                           facecolor=face_color, alpha=0.3, linewidth=1)

            is_identity_rotation = ("Wall" in name and abs(rot["x"]) < 0.01 and 
                                  abs(rot["y"]) < 0.01 and abs(rot["z"]) < 0.01 and 
                                  abs(rot["w"] - 1.0) < 0.01)

            if is_identity_rotation:
                adjusted_angle = angle + 180.0
                t = transforms.Affine2D().rotate_deg_around(cx, cz, adjusted_angle) + ax.transData
            else:
                t = transforms.Affine2D().rotate_deg_around(cx, cz, angle) + ax.transData

            rect.set_transform(t)
            ax.add_patch(rect)
    
    # ==================== Visualization ====================
    
    def create_trial_visualization(self, participant_id: str, trial_id: str, authority: str):
        """Create a path-efficiency plot for a single trial."""
        print(f"Creating visualization for {participant_id} - Trial {trial_id} - Authority {authority}...")
        
        trial_path = self.log_base_path / participant_id / trial_id / authority
        
        # Load actual trajectory
        csv_files = list(trial_path.glob('log_*.csv'))
        if not csv_files:
            print(f"No CSV file found for {participant_id}/{trial_id}/{authority}")
            return
        
        csv_file = csv_files[0]
        actual_trajectory, L_actual = self.load_actual_trajectory_from_csv(csv_file)
        
        if not actual_trajectory:
            print(f"No valid trajectory data for {participant_id}/{trial_id}/{authority}")
            return
        
        # Start/goal
        start_pos = actual_trajectory[0]
        end_pos = actual_trajectory[-1]
        
        # Collision points
        collision_positions = self.load_collision_data(csv_file)
        
        # Find obstacles
        obstacles_files = list(self.log_base_path.glob('**/obstacles.json'))
        if not obstacles_files:
            print("No obstacles.json file found")
            return
        
        obstacles_file = obstacles_files[0]
        
        # Compute ideal path
        ideal_path, L_ideal = self.compute_ideal_path(obstacles_file, start_pos, end_pos)
        
        # Path efficiency
        path_efficiency = L_ideal / L_actual if L_actual > 0 else 0.0
        
        # Load obstacles for drawing
        with open(obstacles_file, 'r') as f:
            obstacles_data = json.load(f)["obstacles"]
        
        # Create plot
        fig, ax = plt.subplots(figsize=(12, 10))
        ax.set_aspect('equal')
        
        # Obstacles
        self.draw_obstacles(ax, obstacles_data)
        
        # Actual path
        actual_config = self.path_colors['actual']
        actual_x = [pos[0] for pos in actual_trajectory]
        actual_z = [pos[1] for pos in actual_trajectory]
        ax.plot(actual_x, actual_z, 
               color=actual_config['color'], 
               linewidth=actual_config['linewidth'],
               alpha=actual_config['alpha'],
               label=f"{actual_config['label']} ({L_actual:.2f}m)")
        
        # Ideal path
        if ideal_path:
            ideal_config = self.path_colors['ideal']
            ideal_x = [pos[0] for pos in ideal_path]
            ideal_z = [pos[1] for pos in ideal_path]
            ax.plot(ideal_x, ideal_z, 
                   color=ideal_config['color'], 
                   linewidth=ideal_config['linewidth'],
                   alpha=ideal_config['alpha'],
                   linestyle=ideal_config['linestyle'],
                   label=f"{ideal_config['label']} ({L_ideal:.2f}m)")
        
        # Start and goal markers
        ax.plot([start_pos[0]], [start_pos[1]], 'go', markersize=10, 
               label='Start Position', zorder=10)
        ax.plot([end_pos[0]], [end_pos[1]], 'ro', markersize=10, 
               label='Goal Position', zorder=10)
        
        # Direction arrows (actual path)
        arrow_step = max(1, len(actual_trajectory) // 10)
        for i in range(0, len(actual_trajectory)-1, arrow_step):
            x, z = actual_trajectory[i]
            dx = actual_trajectory[i+1][0] - actual_trajectory[i][0]
            dz = actual_trajectory[i+1][1] - actual_trajectory[i][1]
            
            length = np.sqrt(dx**2 + dz**2)
            if length > 0.1:
                arrow_length = min(0.3, length * 0.5)
                dx_norm = (dx / length) * arrow_length
                dz_norm = (dz / length) * arrow_length
                
                ax.arrow(x, z, dx_norm, dz_norm, 
                       head_width=0.1, head_length=0.1, 
                       fc=actual_config['color'], ec=actual_config['color'], 
                       alpha=0.6, zorder=5)
        
        # Collision points
        if collision_positions:
            collision_points = np.array(collision_positions)
            ax.scatter(collision_points[:, 0], collision_points[:, 1], 
                     c='red', marker='x', s=100, linewidth=3, 
                     label=f'Collisions ({len(collision_positions)})', zorder=15)
        
        # Axes and legend
        ax.set_xlabel("X Position (m)", fontsize=12)
        ax.set_ylabel("Z Position (m)", fontsize=12)
        ax.grid(True, alpha=0.3)
        
        # Legend
        ax.legend(loc='upper right', bbox_to_anchor=(1, 1), fontsize=15)
        
        # Save
        output_file = self.output_path / f"path_efficiency_{participant_id}_{trial_id}_{authority}.png"
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Visualization saved to: {output_file}")
        plt.show()
    
    def create_all_trial_visualizations(self):
        """Create path efficiency visualizations for all trials."""
        print("=" * 60)
        print("PATH EFFICIENCY VISUALIZATION FOR METRIC F")
        print("=" * 60)
        
        # Find all participants
        participants = []
        for participant_dir in sorted(self.log_base_path.glob('T_*')):
            if participant_dir.is_dir():
                participants.append(participant_dir.name)
        
        if not participants:
            print("No participants found!")
            return
        
        print(f"Found participants: {participants}")
        
        # Create visualizations for each trial
        total_visualizations = 0
        for participant_id in participants:
            participant_dir = self.log_base_path / participant_id
            
            for trial_dir in sorted(participant_dir.glob('[0-9]*')):
                if not trial_dir.is_dir():
                    continue
                
                trial_id = trial_dir.name
                
                for authority_dir in sorted(trial_dir.glob('0.*')):
                    if not authority_dir.is_dir():
                        continue
                    
                    authority = authority_dir.name
                    self.create_trial_visualization(participant_id, trial_id, authority)
                    total_visualizations += 1
        
        print(f"\nAll visualizations completed!")
        print(f"Total visualizations created: {total_visualizations}")
        print(f"Results saved in: {self.output_path}")

def main():
    """Entry point."""
    log_path = LOG_PATH
    output_path = OUTPUT_PATH
    
    # Create visualizer and run
    visualizer = PathEfficiencyVisualizer(log_path, output_path)
    visualizer.create_all_trial_visualizations()

if __name__ == "__main__":
    main()
