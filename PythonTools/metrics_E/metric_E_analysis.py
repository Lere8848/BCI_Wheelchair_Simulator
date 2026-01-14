#!/usr/bin/env python3
"""
Metric F: Path Efficiency Analysis
路径效率分析 - 被试内主分析

重点分析：
1. 同一个受试者在两种Authority下的路径效率变化
2. 受试者内部比较（within-subject analysis）
3. 分别分析两位受试者的表现

路径效率计算公式：
PE = L_ideal / L_actual ∈ (0,1]

其中：
- L_ideal: 使用A*算法计算的最短安全路径长度
- L_actual: 实际轮椅行驶的累积路径长度
- PE越接近1表示路径效率越高
"""

import os
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import warnings
import math
from dataclasses import dataclass
from typing import List, Tuple, Optional
from heapq import heappush, heappop

warnings.filterwarnings('ignore')

class MetricFAnalyzer:
    def __init__(self, log_base_path: str, output_path: str = None):
        """
        初始化Metric F分析器
        
        Args:
            log_base_path: 日志文件根目录路径
            output_path: 输出文件夹路径，默认为当前脚本目录
        """
        self.log_base_path = Path(log_base_path)
        self.output_path = Path(output_path) if output_path else Path(__file__).parent
        self.output_path.mkdir(exist_ok=True)
        
        # A*算法参数
        self.resolution = 0.05  # 网格分辨率 (m/pixel)
        self.wheel_radius = 0.35  # 轮椅外半径 (m)
        self.safety_margin = 0.15  # 安全边距 (m)
        self.padding = 1.0  # 世界边界填充 (m)
        
    # ==================== A*算法相关函数 ====================
    
    @dataclass
    class Obstacle:
        name: str
        center: Tuple[float, float]  # (x, z)
        size_x: float               # Unity local x size (米)
        size_z: float               # Unity local z size (米)
        rotmat: np.ndarray          # 3x3 旋转矩阵（世界系）

    @dataclass
    class GridSpec:
        origin: Tuple[float, float]   # (min_x, min_z) 世界坐标
        resolution: float             # 米/像素
        width: int
        height: int
    
    def quat_to_rotmat(self, qx, qy, qz, qw):
        """将四元数转换为 3x3 旋转矩阵"""
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
    
    def load_obstacles(self, obstacles_file: Path) -> List['MetricFAnalyzer.Obstacle']:
        """加载障碍物数据"""
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
                R = self.quat_to_rotmat(qx, qy, qz, qw)
                obs_list.append(self.Obstacle(name=name, center=(px, pz), size_x=sx, size_z=sz, rotmat=R))
            return obs_list
        except Exception as e:
            print(f"Error loading obstacles from {obstacles_file}: {e}")
            return []
    
    def obstacle_footprint_poly(self, obs: 'MetricFAnalyzer.Obstacle', extra_margin: float) -> np.ndarray:
        """将障碍物转换为膨胀后的多边形"""
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
    
    def compute_bounds(self, obstacles: List['MetricFAnalyzer.Obstacle'], 
                      start: Tuple[float, float], goal: Tuple[float, float],
                      padding: float, extra_margin: float) -> Tuple[float, float, float, float]:
        """计算世界范围边界"""
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
    
    def world_to_grid(self, x: float, z: float, spec: 'MetricFAnalyzer.GridSpec') -> Tuple[int, int]:
        """世界坐标转网格索引"""
        cx = (x - spec.origin[0]) / spec.resolution
        cz = (z - spec.origin[1]) / spec.resolution
        j = int(round(cz))  # row
        i = int(round(cx))  # col
        return i, j
    
    def point_in_poly(self, x: float, y: float, poly: np.ndarray) -> bool:
        """点在多边形内测试"""
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
    
    def rasterize_polygons(self, polys_world: List[np.ndarray], spec: 'MetricFAnalyzer.GridSpec') -> np.ndarray:
        """将多边形栅格化为占据网格"""
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
        """8邻接A*算法"""
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
    
    def compute_L_ideal(self, obstacles_file: Path, start: Tuple[float, float], goal: Tuple[float, float]) -> float:
        """计算理想路径长度"""
        try:
            # 加载障碍物
            obstacles = self.load_obstacles(obstacles_file)
            if not obstacles:
                print(f"Warning: No obstacles loaded from {obstacles_file}")
                # 如果没有障碍物，返回直线距离
                return math.sqrt((goal[0] - start[0])**2 + (goal[1] - start[1])**2)
            
            # 计算边界并建立网格
            extra = self.wheel_radius + self.safety_margin
            min_x, min_z, max_x, max_z = self.compute_bounds(obstacles, start, goal, self.padding, extra)
            width = int(math.ceil((max_x - min_x) / self.resolution)) + 1
            height = int(math.ceil((max_z - min_z) / self.resolution)) + 1
            spec = self.GridSpec(origin=(min_x, min_z), resolution=self.resolution, width=width, height=height)

            # 将障碍物转换为膨胀多边形
            polys = [self.obstacle_footprint_poly(obs, extra) for obs in obstacles]

            # 栅格化占据网格
            occ = self.rasterize_polygons(polys, spec)

            # 起终点映射到像素
            si, sj = self.world_to_grid(start[0], start[1], spec)
            gi, gj = self.world_to_grid(goal[0], goal[1], spec)

            # A*最短路径
            path = self.astar_8conn(occ, (si, sj), (gi, gj))
            if path is None or len(path) < 2:
                print(f"Warning: A* failed for start={start}, goal={goal}")
                # A*失败时返回直线距离作为下界
                return math.sqrt((goal[0] - start[0])**2 + (goal[1] - start[1])**2)

            # 计算路径长度
            length_px = 0.0
            for k in range(len(path) - 1):
                (i1, j1), (i2, j2) = path[k], path[k+1]
                di, dj = i2 - i1, j2 - j1
                step = math.sqrt(di*di + dj*dj)
                length_px += step
            
            L_ideal = length_px * self.resolution
            return L_ideal
            
        except Exception as e:
            print(f"Error computing L_ideal: {e}")
            # 出错时返回直线距离
            return math.sqrt((goal[0] - start[0])**2 + (goal[1] - start[1])**2)
    
    # ==================== 路径效率分析函数 ====================
    
    def compute_actual_path_length_from_csv(self, csv_file: Path) -> Tuple[float, Tuple[float, float], Tuple[float, float]]:
        """从CSV文件计算实际路径长度并返回起终点"""
        try:
            df = pd.read_csv(csv_file)
            
            # 查找位置列
            pos_x_col = None
            pos_z_col = None
            
            for col in df.columns:
                if 'pos_x' in str(col) and pos_x_col is None:
                    pos_x_col = col
                elif 'pos_z' in str(col) and pos_z_col is None:
                    pos_z_col = col
            
            if pos_x_col is None or pos_z_col is None:
                print(f"Warning: Position columns not found in {csv_file}")
                return 0.0, (0.0, 0.0), (0.0, 0.0)
            
            # 提取位置数据
            if isinstance(df[pos_x_col], pd.DataFrame):
                pos_x = df[pos_x_col].iloc[:, 0].values
            else:
                pos_x = df[pos_x_col].values
                
            if isinstance(df[pos_z_col], pd.DataFrame):
                pos_z = df[pos_z_col].iloc[:, 0].values
            else:
                pos_z = df[pos_z_col].values
            
            # 去除无效值
            valid_mask = ~(np.isnan(pos_x) | np.isnan(pos_z))
            pos_x = pos_x[valid_mask]
            pos_z = pos_z[valid_mask]
            
            if len(pos_x) < 2:
                return 0.0, (0.0, 0.0), (0.0, 0.0)
            
            # 计算累积路径长度
            cumulative_distance = 0.0
            for i in range(len(pos_x) - 1):
                dx = pos_x[i + 1] - pos_x[i]
                dz = pos_z[i + 1] - pos_z[i]
                segment_distance = np.sqrt(dx**2 + dz**2)
                cumulative_distance += segment_distance
            
            start_pos = (float(pos_x[0]), float(pos_z[0]))
            end_pos = (float(pos_x[-1]), float(pos_z[-1]))
            
            return cumulative_distance, start_pos, end_pos
            
        except Exception as e:
            print(f"Error processing {csv_file}: {e}")
            return 0.0, (0.0, 0.0), (0.0, 0.0)
    
    def compute_actual_path_length_from_trajectory(self, traj_file: Path) -> Tuple[float, Tuple[float, float], Tuple[float, float]]:
        """从轨迹JSON文件计算实际路径长度"""
        try:
            with open(traj_file, 'r') as f:
                traj_data = json.load(f)
            
            if 'points' not in traj_data:
                return 0.0, (0.0, 0.0), (0.0, 0.0)
            
            points = traj_data['points']
            if len(points) < 2:
                return 0.0, (0.0, 0.0), (0.0, 0.0)
            
            # 提取位置信息
            positions = []
            for point in points:
                pos = point['position']
                positions.append((pos['x'], pos['z']))
            
            # 计算路径长度
            cumulative_distance = 0.0
            for i in range(len(positions) - 1):
                x1, z1 = positions[i]
                x2, z2 = positions[i + 1]
                segment_distance = np.sqrt((x2 - x1)**2 + (z2 - z1)**2)
                cumulative_distance += segment_distance
            
            start_pos = positions[0]
            end_pos = positions[-1]
            
            return cumulative_distance, start_pos, end_pos
            
        except Exception as e:
            print(f"Error processing {traj_file}: {e}")
            return 0.0, (0.0, 0.0), (0.0, 0.0)
    
    def analyze_single_trial(self, participant_id: str, trial_id: str, authority: str) -> dict:
        """分析单个试验的路径效率"""
        trial_path = self.log_base_path / participant_id / trial_id / authority
        
        # 查找轨迹文件
        csv_files = list(trial_path.glob('log_*.csv'))
        trajectory_files = list(trial_path.glob('trajectory_*.json'))
        
        # 计算实际路径长度
        L_actual = 0.0
        start_pos = (0.0, 0.0)
        end_pos = (0.0, 0.0)
        
        if csv_files:
            L_actual, start_pos, end_pos = self.compute_actual_path_length_from_csv(csv_files[0])
        elif trajectory_files:
            L_actual, start_pos, end_pos = self.compute_actual_path_length_from_trajectory(trajectory_files[0])
        else:
            print(f"Warning: No trajectory data found in {trial_path}")
            return self._empty_path_efficiency_data(participant_id, trial_id, authority)
        
        # 查找障碍物文件
        obstacles_files = list(self.log_base_path.glob('**/obstacles.json'))
        if not obstacles_files:
            print("Warning: No obstacles.json file found")
            return self._empty_path_efficiency_data(participant_id, trial_id, authority)
        
        obstacles_file = obstacles_files[0]
        
        # 计算理想路径长度
        L_ideal = self.compute_L_ideal(obstacles_file, start_pos, end_pos)
        
        # 计算路径效率
        path_efficiency = L_ideal / L_actual if L_actual > 0 else 0.0
        
        # 计算直线距离
        straight_distance = math.sqrt((end_pos[0] - start_pos[0])**2 + (end_pos[1] - start_pos[1])**2)
        
        return {
            'participant': participant_id,
            'trial': trial_id,
            'authority': float(authority),
            'L_actual': float(L_actual),
            'L_ideal': float(L_ideal),
            'path_efficiency': float(path_efficiency),
            'straight_distance': float(straight_distance),
            'start_position': start_pos,
            'end_position': end_pos,
            'source_file': str(csv_files[0] if csv_files else trajectory_files[0] if trajectory_files else '')
        }
    
    def _empty_path_efficiency_data(self, participant_id: str, trial_id: str, authority: str) -> dict:
        """返回空的路径效率数据"""
        return {
            'participant': participant_id,
            'trial': trial_id,
            'authority': float(authority),
            'L_actual': 0.0,
            'L_ideal': 0.0,
            'path_efficiency': 0.0,
            'straight_distance': 0.0,
            'start_position': (0.0, 0.0),
            'end_position': (0.0, 0.0),
            'source_file': ''
        }
    
    def collect_all_data(self) -> pd.DataFrame:
        """收集所有试验的路径效率数据"""
        all_results = []
        
        # 遍历所有参与者
        for participant_dir in sorted(self.log_base_path.glob('T_*')):
            if not participant_dir.is_dir():
                continue
                
            participant_id = participant_dir.name
            print(f"Processing participant: {participant_id}")
            
            # 遍历所有试验
            for trial_dir in sorted(participant_dir.glob('[0-9]*')):
                if not trial_dir.is_dir():
                    continue
                    
                trial_id = trial_dir.name
                print(f"  Processing trial: {trial_id}")
                
                # 遍历所有权限级别
                for authority_dir in sorted(trial_dir.glob('0.*')):
                    if not authority_dir.is_dir():
                        continue
                    
                    authority = authority_dir.name
                    print(f"    Processing authority: {authority}")
                    
                    # 分析单个试验
                    result = self.analyze_single_trial(participant_id, trial_id, authority)
                    all_results.append(result)
        
        return pd.DataFrame(all_results)
    
    def perform_within_subject_analysis(self, df: pd.DataFrame) -> dict:
        """执行被试内分析"""
        results = {}
        
        # 为每位受试者分别分析
        for participant in df['participant'].unique():
            participant_data = df[df['participant'] == participant]
            
            # 按Authority分组
            authority_03 = participant_data[participant_data['authority'] == 0.3]
            authority_07 = participant_data[participant_data['authority'] == 0.7]
            
            # 计算各指标的平均值
            results[participant] = {
                'authority_0.3': {
                    'path_efficiency_mean': authority_03['path_efficiency'].mean(),
                    'L_actual_mean': authority_03['L_actual'].mean(),
                    'L_ideal_mean': authority_03['L_ideal'].mean(),
                    'straight_distance_mean': authority_03['straight_distance'].mean(),
                    'trial_count': len(authority_03)
                },
                'authority_0.7': {
                    'path_efficiency_mean': authority_07['path_efficiency'].mean(),
                    'L_actual_mean': authority_07['L_actual'].mean(),
                    'L_ideal_mean': authority_07['L_ideal'].mean(),
                    'straight_distance_mean': authority_07['straight_distance'].mean(),
                    'trial_count': len(authority_07)
                }
            }
            
            # 计算差异
            efficiency_diff = (authority_07['path_efficiency'].mean() - 
                             authority_03['path_efficiency'].mean())
            
            results[participant]['differences'] = {
                'efficiency_diff': efficiency_diff
            }
        
        return results
    
    def create_summary_table(self, within_subject_results: dict) -> pd.DataFrame:
        """创建汇总表格"""
        table_data = []
        
        for participant, data in within_subject_results.items():
            # Authority 0.3
            table_data.append({
                'Participant': participant,
                'Authority': 0.3,
                'Path_Efficiency': data['authority_0.3']['path_efficiency_mean'],
                'L_Actual': data['authority_0.3']['L_actual_mean'],
                'L_Ideal': data['authority_0.3']['L_ideal_mean'],
                'Straight_Distance': data['authority_0.3']['straight_distance_mean'],
                'Trial_Count': data['authority_0.3']['trial_count']
            })
            
            # Authority 0.7
            table_data.append({
                'Participant': participant,
                'Authority': 0.7,
                'Path_Efficiency': data['authority_0.7']['path_efficiency_mean'],
                'L_Actual': data['authority_0.7']['L_actual_mean'],
                'L_Ideal': data['authority_0.7']['L_ideal_mean'],
                'Straight_Distance': data['authority_0.7']['straight_distance_mean'],
                'Trial_Count': data['authority_0.7']['trial_count']
            })
        
        return pd.DataFrame(table_data)
    
    def create_visualizations(self, df: pd.DataFrame):
        """创建可视化图表"""
        plt.style.use('default')
        sns.set_palette("Set2")
        
        df_vis = df.copy()
        df_vis['authority_label'] = df_vis['authority'].map({0.3: 'Low User Authority', 0.7: 'High User Authority'})
        
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('Metric F: Path Efficiency Analysis - Within-Subject Comparison', 
                    fontsize=16, fontweight='bold')
        
        # 1. 路径效率箱线图
        sns.boxplot(data=df_vis, x='participant', y='path_efficiency', 
                   hue='authority_label', ax=axes[0,0])
        axes[0,0].set_title('Path Efficiency by Participant and Authority')
        axes[0,0].set_xlabel('Participant')
        axes[0,0].set_ylabel('Path Efficiency (L_ideal/L_actual)')
        axes[0,0].legend(title='Authority Level')
        
        # 2. 实际路径长度箱线图
        sns.boxplot(data=df_vis, x='participant', y='L_actual', 
                   hue='authority_label', ax=axes[0,1])
        axes[0,1].set_title('Actual Path Length by Participant and Authority')
        axes[0,1].set_xlabel('Participant')
        axes[0,1].set_ylabel('L_actual (m)')
        axes[0,1].legend(title='Authority Level')
        
        # 3. 理想路径长度箱线图
        sns.boxplot(data=df_vis, x='participant', y='L_ideal', 
                   hue='authority_label', ax=axes[1,0])
        axes[1,0].set_title('Ideal Path Length by Participant and Authority')
        axes[1,0].set_xlabel('Participant')
        axes[1,0].set_ylabel('L_ideal (m)')
        axes[1,0].legend(title='Authority Level')
        
        # 4. 路径效率对比柱状图
        participant_means = df.groupby(['participant', 'authority'])['path_efficiency'].mean().unstack()
        
        x_pos = np.arange(len(participant_means.index))
        width = 0.35
        
        bars1 = axes[1,1].bar(x_pos - width/2, participant_means[0.3], width, 
                             label='Low User Authority', alpha=0.8)
        bars2 = axes[1,1].bar(x_pos + width/2, participant_means[0.7], width,
                             label='High User Authority', alpha=0.8)
        
        axes[1,1].set_xlabel('Participant')
        axes[1,1].set_ylabel('Mean Path Efficiency')
        axes[1,1].set_title('Path Efficiency Comparison\n(Higher is better)')
        axes[1,1].set_xticks(x_pos)
        axes[1,1].set_xticklabels(participant_means.index)
        axes[1,1].legend()
        axes[1,1].grid(axis='y', alpha=0.3)
        
        # 添加数值标签
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                axes[1,1].annotate(f'{height:.3f}',
                                 xy=(bar.get_x() + bar.get_width() / 2, height),
                                 xytext=(0, 3),
                                 textcoords="offset points",
                                 ha='center', va='bottom')
        
        plt.tight_layout()
        
        # 保存图表
        output_file = self.output_path / "metric_F_path_efficiency_analysis.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Visualization saved to: {output_file}")
        plt.show()
    
    def generate_latex_table(self, summary_df: pd.DataFrame) -> str:
        """生成LaTeX表格"""
        latex_table = """
\\begin{table}[h]
\\centering
\\caption{Metric F: Path Efficiency Analysis by Participant and Authority Level}
\\label{tab:metric_f_efficiency}
\\begin{tabular}{cccccc}
\\toprule
Participant & Authority & Path & L\\textsubscript{actual} & L\\textsubscript{ideal} & Straight \\\\
           & Level     & Efficiency & (m) & (m) & Distance (m) \\\\
\\midrule
"""
        
        for _, row in summary_df.iterrows():
            latex_table += f"{row['Participant']} & {row['Authority']:.1f} & "
            latex_table += f"{row['Path_Efficiency']:.3f} & "
            latex_table += f"{row['L_Actual']:.2f} & "
            latex_table += f"{row['L_Ideal']:.2f} & "
            latex_table += f"{row['Straight_Distance']:.2f} \\\\\n"
        
        latex_table += """\\bottomrule
\\end{tabular}
\\end{table}

\\textbf{Note:} Path efficiency = L\\textsubscript{ideal}/L\\textsubscript{actual} ∈ (0,1]. Higher values indicate better efficiency. L\\textsubscript{ideal} is computed using A* algorithm with obstacle inflation.
"""
        return latex_table
    
    def run_complete_analysis(self):
        """运行完整的Metric F分析"""
        print("=" * 60)
        print("METRIC F: PATH EFFICIENCY ANALYSIS")
        print("=" * 60)
        
        # 1. 收集数据
        print("\n1. Collecting path efficiency data from all trials...")
        df = self.collect_all_data()
        
        if df.empty:
            print("No data found. Please check the log file paths.")
            return
        
        # 保存原始数据
        raw_data_file = self.output_path / "metric_F_raw_data.csv"
        df.to_csv(raw_data_file, index=False)
        print(f"Raw data saved to: {raw_data_file}")
        
        # 2. 显示原始数据
        print("\n2. Raw Data:")
        print("-" * 40)
        print(df.to_string(index=False))
        
        # 3. 被试内分析
        print("\n3. Within-Subject Analysis:")
        print("-" * 40)
        within_subject_results = self.perform_within_subject_analysis(df)
        
        for participant, data in within_subject_results.items():
            print(f"\n{participant}:")
            print(f"  Authority 0.3: {data['authority_0.3']['path_efficiency_mean']:.3f} efficiency")
            print(f"  Authority 0.7: {data['authority_0.7']['path_efficiency_mean']:.3f} efficiency")
            efficiency_diff = data['differences']['efficiency_diff']
            direction = "more efficient" if efficiency_diff > 0 else "less efficient"
            print(f"  High authority is {abs(efficiency_diff):.3f} {direction}")
        
        # 4. 创建汇总表格
        print("\n4. Summary Table:")
        print("-" * 40)
        summary_df = self.create_summary_table(within_subject_results)
        print(summary_df.to_string(index=False))
        
        # 保存汇总表格
        summary_file = self.output_path / "metric_F_summary_table.csv"
        summary_df.to_csv(summary_file, index=False)
        print(f"Summary table saved to: {summary_file}")
        
        # 5. 生成可视化
        print("\n5. Generating visualizations...")
        self.create_visualizations(df)
        
        # 6. 生成LaTeX表格
        print("\n6. LaTeX Table:")
        print("-" * 40)
        latex_table = self.generate_latex_table(summary_df)
        print(latex_table)
        
        # 保存LaTeX表格
        latex_file = self.output_path / "metric_F_latex_table.tex"
        with open(latex_file, 'w', encoding='utf-8') as f:
            f.write(latex_table)
        print(f"LaTeX table saved to: {latex_file}")
        
        # 7. 分析总结
        print("\n7. Analysis Summary:")
        print("-" * 40)
        print(f"• Total trials analyzed: {len(df)}")
        
        # 计算整体效率统计
        auth_03_efficiency = df[df['authority'] == 0.3]['path_efficiency'].mean()
        auth_07_efficiency = df[df['authority'] == 0.7]['path_efficiency'].mean()
        
        print(f"• Overall path efficiency:")
        print(f"  - Low authority (0.3): {auth_03_efficiency:.3f}")
        print(f"  - High authority (0.7): {auth_07_efficiency:.3f}")
        
        if auth_07_efficiency > auth_03_efficiency:
            improvement = ((auth_07_efficiency - auth_03_efficiency) / auth_03_efficiency) * 100
            print(f"  - High authority shows {improvement:.1f}% better efficiency")
        else:
            decrease = ((auth_03_efficiency - auth_07_efficiency) / auth_03_efficiency) * 100
            print(f"  - High authority shows {decrease:.1f}% worse efficiency")
        
        print(f"• Analysis completed successfully!")
        print(f"• Results saved in: {self.output_path}")

def main():
    """主函数"""
    # 设置路径
    log_path = r"d:\UnityProject\wheelchair_sim\Assets\Logs\0820_use_this"
    output_path = Path(__file__).parent
    
    # 创建分析器并运行分析
    analyzer = MetricFAnalyzer(log_path, output_path)
    analyzer.run_complete_analysis()

if __name__ == "__main__":
    main()
