#!/usr/bin/env python3
"""
Metric C: Trajectory Visualization on Obstacle Map
在障碍物地图上可视化轨迹，按Authority用颜色区分

功能：
1. 为每个受试者创建单独的轨迹图
2. 在同一障碍物地图上显示所有trial的轨迹
3. 用不同颜色区分不同Authority级别
4. 显示轨迹方向箭头和碰撞点
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

class TrajectoryVisualizer:
    def __init__(self, log_base_path: str, output_path: str = None):
        """
        初始化轨迹可视化器
        
        Args:
            log_base_path: 日志文件根目录路径
            output_path: 输出文件夹路径，默认为当前脚本目录
        """
        self.log_base_path = Path(log_base_path)
        self.output_path = Path(output_path) if output_path else Path(__file__).parent
        self.output_path.mkdir(exist_ok=True)
        
        # 颜色配置
        self.authority_colors = {
            0.3: {'color': '#1f77b4', 'label': 'Low User Authority', 'alpha': 0.8},
            0.7: {'color': '#ff7f0e', 'label': 'High User Authority', 'alpha': 0.8}
        }
        
    def quaternion_to_yaw(self, q):
        """将Unity导出的四元数(x, y, z, w)转换为Y轴的欧拉角"""
        r = R.from_quat([q["x"], q["y"], q["z"], q["w"]])
        yaw = r.as_euler('xyz', degrees=True)[1]  # Y轴旋转
        return yaw
    
    def load_trajectory_from_csv(self, csv_file: Path) -> dict:
        """
        从CSV文件加载轨迹数据
        
        Args:
            csv_file: CSV文件路径
            
        Returns:
            包含轨迹数据的字典
        """
        try:
            df = pd.read_csv(csv_file)
            
            # 查找位置列（处理重复列名）
            pos_x_col = None
            pos_z_col = None
            
            for col in df.columns:
                if 'pos_x' in str(col) and pos_x_col is None:
                    pos_x_col = col
                elif 'pos_z' in str(col) and pos_z_col is None:
                    pos_z_col = col
            
            if pos_x_col is None or pos_z_col is None:
                print(f"Warning: Position columns not found in {csv_file}")
                return None
            
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
                print(f"Warning: Insufficient valid position data in {csv_file}")
                return None
            
            # 构造轨迹点
            positions = np.column_stack([pos_x, pos_z])
            
            return {
                'positions': positions,
                'source_file': str(csv_file)
            }
            
        except Exception as e:
            print(f"Error loading trajectory from {csv_file}: {e}")
            return None
    
    def load_trajectory_from_json(self, json_file: Path) -> dict:
        """
        从JSON文件加载轨迹数据
        
        Args:
            json_file: JSON文件路径
            
        Returns:
            包含轨迹数据的字典
        """
        try:
            with open(json_file, 'r') as f:
                traj_data = json.load(f)["points"]
            
            positions = np.array([[p["position"]["x"], p["position"]["z"]] for p in traj_data])
            
            return {
                'positions': positions,
                'points_data': traj_data,
                'source_file': str(json_file)
            }
            
        except Exception as e:
            print(f"Error loading trajectory from {json_file}: {e}")
            return None
    
    def load_collision_data(self, csv_file: Path) -> list:
        """
        从CSV文件加载碰撞数据
        
        Args:
            csv_file: CSV文件路径
            
        Returns:
            碰撞位置列表
        """
        collision_positions = []
        
        try:
            df = pd.read_csv(csv_file)
            
            # 查找碰撞和位置列
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
            
            # 提取数据
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
            
            # 找到碰撞位置
            collision_mask = collision_flags == 1
            if collision_mask.any():
                collision_x = pos_x[collision_mask]
                collision_z = pos_z[collision_mask]
                collision_positions = list(zip(collision_x, collision_z))
                
        except Exception as e:
            print(f"Error loading collision data from {csv_file}: {e}")
        
        return collision_positions
    
    def load_obstacles(self) -> list:
        """
        加载障碍物数据
        
        Returns:
            障碍物列表
        """
        # 查找obstacles.json文件
        obstacle_files = list(self.log_base_path.glob('**/obstacles.json'))
        
        if not obstacle_files:
            print("Warning: No obstacles.json file found")
            return []
        
        obstacle_file = obstacle_files[0]  # 使用第一个找到的文件
        
        try:
            with open(obstacle_file, 'r') as f:
                obs_data = json.load(f)["obstacles"]
            return obs_data
        except Exception as e:
            print(f"Error loading obstacles from {obstacle_file}: {e}")
            return []
    
    def draw_obstacles(self, ax, obstacles):
        """
        在图上绘制障碍物
        
        Args:
            ax: matplotlib轴对象
            obstacles: 障碍物列表
        """
        for ob in obstacles:
            pos = ob["position"]
            size = ob["size"]
            rot = ob["rotation"]
            name = ob["name"]

            # 中心点和尺寸
            cx = pos["x"]
            cz = pos["z"]
            w = size["x"]
            h = size["z"]
            angle = self.quaternion_to_yaw(rot)  # 角度

            # 默认边缘和填充颜色
            edge_color = 'black'
            face_color = 'gray'
            
            # 根据对象类型确定起始位置和颜色
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

            # 创建障碍物矩形
            rect = Rectangle((start_x, start_y), w, h, edgecolor=edge_color, 
                           facecolor=face_color, alpha=0.3, linewidth=1)

            # 围绕中心点旋转障碍物
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
    
    def collect_participant_trajectories(self, participant_id: str) -> dict:
        """
        收集单个参与者的单个trial轨迹数据（用于Authority对比）
        
        Args:
            participant_id: 参与者ID
            
        Returns:
            按authority分组的轨迹数据字典（每个authority只有一个trial）
        """
        participant_dir = self.log_base_path / participant_id
        if not participant_dir.exists():
            print(f"Participant directory not found: {participant_dir}")
            return {}
        
        trajectories = {}
        
        # 只选择第一个trial进行对比
        trial_dirs = sorted(participant_dir.glob('[0-9]*'))
        if not trial_dirs:
            print(f"No trial directories found for {participant_id}")
            return {}
        
        # 使用第一个trial
        trial_dir = trial_dirs[0]
        trial_id = trial_dir.name
        print(f"Using trial {trial_id} for {participant_id}")
        
        # 遍历该trial下的所有权限级别
        for authority_dir in sorted(trial_dir.glob('0.*')):
            if not authority_dir.is_dir():
                continue
            
            authority = float(authority_dir.name)
            
            # 优先使用CSV文件
            csv_files = list(authority_dir.glob('log_*.csv'))
            json_files = list(authority_dir.glob('trajectory_*.json'))
            
            trajectory_data = None
            collision_data = []
            
            if csv_files:
                trajectory_data = self.load_trajectory_from_csv(csv_files[0])
                collision_data = self.load_collision_data(csv_files[0])
            elif json_files:
                trajectory_data = self.load_trajectory_from_json(json_files[0])
            
            if trajectory_data:
                trajectory_data['trial_id'] = trial_id
                trajectory_data['authority'] = authority
                trajectory_data['collisions'] = collision_data
                trajectories[authority] = trajectory_data  # 直接赋值，不是列表
        
        return trajectories
    
    def create_participant_visualization(self, participant_id: str):
        """
        为单个参与者创建轨迹可视化（单个trial的Authority对比）
        
        Args:
            participant_id: 参与者ID
        """
        print(f"Creating visualization for {participant_id}...")
        
        # 收集轨迹数据
        trajectories = self.collect_participant_trajectories(participant_id)
        
        if not trajectories:
            print(f"No trajectory data found for {participant_id}")
            return
        
        # 检查是否有完整的authority对比数据
        if 0.3 not in trajectories or 0.7 not in trajectories:
            print(f"Incomplete authority data for {participant_id}")
            return
        
        # 加载障碍物
        obstacles = self.load_obstacles()
        
        # 创建图形
        fig, ax = plt.subplots(figsize=(12, 10))
        ax.set_aspect('equal')
        
        # 绘制障碍物
        self.draw_obstacles(ax, obstacles)
        
        # 绘制轨迹
        legend_elements = []
        total_collisions = 0
        trial_id = None
        
        for authority in sorted(trajectories.keys()):
            color_config = self.authority_colors[authority]
            color = color_config['color']
            label = color_config['label']
            alpha = color_config['alpha']
            
            traj_data = trajectories[authority]
            positions = traj_data['positions']
            trial_id = traj_data['trial_id']  # 所有authority使用相同的trial_id
            collisions = traj_data['collisions']
            
            # 绘制轨迹线
            line_alpha = alpha * 0.8
            ax.plot(positions[:, 0], positions[:, 1], 
                   color=color, linewidth=3, alpha=line_alpha,
                   label=label)
            
            # 绘制方向箭头（稀疏采样）
            arrow_step = max(1, len(positions) // 10)  # 最多10个箭头
            for j in range(0, len(positions)-1, arrow_step):
                x, z = positions[j]
                dx = positions[j+1, 0] - positions[j, 0]
                dz = positions[j+1, 1] - positions[j, 1]
                
                # 计算箭头长度和方向
                length = np.sqrt(dx**2 + dz**2)
                if length > 0.1:  # 只绘制有意义的箭头
                    arrow_length = min(0.3, length * 0.5)
                    dx_norm = (dx / length) * arrow_length
                    dz_norm = (dz / length) * arrow_length
                    
                    ax.arrow(x, z, dx_norm, dz_norm, 
                           head_width=0.12, head_length=0.12, 
                           fc=color, ec=color, alpha=alpha*0.7)
            
            # 绘制碰撞点
            authority_collisions = 0
            if collisions:
                collision_points = np.array(collisions)
                ax.scatter(collision_points[:, 0], collision_points[:, 1], 
                         c='red', marker='x', s=100, linewidth=3, 
                         alpha=0.9, zorder=10)
                authority_collisions = len(collisions)
            
            total_collisions += authority_collisions
            
            # 添加到图例
            if authority_collisions > 0:
                legend_label = f"{label} ({authority_collisions} collisions)"
            else:
                legend_label = label
                
            legend_elements.append(plt.Line2D([0], [0], color=color, lw=3, 
                                            label=legend_label))
        
        # 添加碰撞点图例
        if total_collisions > 0:
            legend_elements.append(plt.Line2D([0], [0], marker='x', color='red', 
                                            markersize=10, linestyle='', 
                                            label=f'Collision Points'))
        
        # 设置图例和标题
        ax.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(1, 1), fontsize=11)
        ax.set_title(f"Trajectory Comparison for {participant_id} - Trial {trial_id}\n"
                    f"Low vs High Authority Smoothness Comparison", 
                    fontsize=14, fontweight='bold')
        ax.set_xlabel("X Position (m)", fontsize=12)
        ax.set_ylabel("Z Position (m)", fontsize=12)
        ax.grid(True, alpha=0.3)
        
        # 保存图像
        output_file = self.output_path / f"trajectory_comparison_{participant_id}_trial_{trial_id}.png"
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Visualization saved to: {output_file}")
        plt.show()
    
    def create_all_visualizations(self):
        """
        为所有参与者创建轨迹可视化
        """
        print("=" * 60)
        print("TRAJECTORY VISUALIZATION FOR METRIC C")
        print("=" * 60)
        
        # 查找所有参与者
        participants = []
        for participant_dir in sorted(self.log_base_path.glob('T_*')):
            if participant_dir.is_dir():
                participants.append(participant_dir.name)
        
        if not participants:
            print("No participants found!")
            return
        
        print(f"Found participants: {participants}")
        
        # 为每个参与者创建可视化
        for participant_id in participants:
            self.create_participant_visualization(participant_id)
        
        print(f"\nAll visualizations completed!")
        print(f"Results saved in: {self.output_path}")

def main():
    """主函数"""
    # 设置路径
    log_path = r"d:\UnityProject\wheelchair_sim\Assets\Logs\0820_use_this"
    output_path = Path(__file__).parent
    
    # 创建可视化器并运行
    visualizer = TrajectoryVisualizer(log_path, output_path)
    visualizer.create_all_visualizations()

if __name__ == "__main__":
    main()
