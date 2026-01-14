#!/usr/bin/env python3
"""
Metric C: Trajectory Visualization on Obstacle Map
Visualize trajectories on the obstacle map and use colors to distinguish user authority.

Features:
1. Create a trajectory plot per participant
2. Plot trajectories on the same obstacle map
3. Use different colors for different authority levels
4. Show direction arrows and collision points
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

# =========================
# User-configurable settings
# =========================
LOG_PATH = r"d:\UnityProject\wheelchair_sim\Assets\Logs\0820_use_this"
OUTPUT_PATH = Path(__file__).parent

class TrajectoryVisualizer:
    def __init__(self, log_base_path: str, output_path: str = None):
        """
        Initialize the trajectory visualizer.
        
        Args:
            log_base_path: Root directory that contains the log folders
            output_path: Output directory; defaults to this script directory
        """
        self.log_base_path = Path(log_base_path)
        self.output_path = Path(output_path) if output_path else Path(__file__).parent
        self.output_path.mkdir(exist_ok=True)
        
        # Color config by authority level
        self.authority_colors = {
            0.3: {'color': '#1f77b4', 'label': 'Low User Authority', 'alpha': 0.8},
            0.7: {'color': '#ff7f0e', 'label': 'High User Authority', 'alpha': 0.8}
        }
        
    def quaternion_to_yaw(self, q):
        """Convert Unity quaternion (x, y, z, w) to yaw (rotation around Y axis)."""
        r = R.from_quat([q["x"], q["y"], q["z"], q["w"]])
        yaw = r.as_euler('xyz', degrees=True)[1]  # rotation about Y axis
        return yaw
    
    def load_trajectory_from_csv(self, csv_file: Path) -> dict:
        """
        Load trajectory data from a CSV file.
        
        Args:
            csv_file: CSV log file path
            
        Returns:
            Dict containing trajectory data
        """
        try:
            df = pd.read_csv(csv_file)
            
            # Find position columns (handle potential duplicate column names)
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
            
            # Extract position data
            if isinstance(df[pos_x_col], pd.DataFrame):
                pos_x = df[pos_x_col].iloc[:, 0].values
            else:
                pos_x = df[pos_x_col].values
                
            if isinstance(df[pos_z_col], pd.DataFrame):
                pos_z = df[pos_z_col].iloc[:, 0].values
            else:
                pos_z = df[pos_z_col].values
            
            # Filter invalid values
            valid_mask = ~(np.isnan(pos_x) | np.isnan(pos_z))
            pos_x = pos_x[valid_mask]
            pos_z = pos_z[valid_mask]
            
            if len(pos_x) < 2:
                print(f"Warning: Insufficient valid position data in {csv_file}")
                return None
            
            # Build trajectory points
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
        Load trajectory data from a JSON file.
        
        Args:
            json_file: JSON file path
            
        Returns:
            Dict containing trajectory data
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
        Load collision point positions from a CSV file.
        
        Args:
            csv_file: CSV file path
            
        Returns:
            List of (x, z) collision positions
        """
        collision_positions = []
        
        try:
            df = pd.read_csv(csv_file)
            
            # Find collision and position columns
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
            
            # Extract data
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
            
            # Collect collision positions
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
        Load obstacle data.
        
        Returns:
            List of obstacles
        """
        # Find obstacles.json
        obstacle_files = list(self.log_base_path.glob('**/obstacles.json'))
        
        if not obstacle_files:
            print("Warning: No obstacles.json file found")
            return []
        
        obstacle_file = obstacle_files[0]  # Use the first match
        
        try:
            with open(obstacle_file, 'r') as f:
                obs_data = json.load(f)["obstacles"]
            return obs_data
        except Exception as e:
            print(f"Error loading obstacles from {obstacle_file}: {e}")
            return []
    
    def draw_obstacles(self, ax, obstacles):
        """
        Draw obstacles on the plot.
        
        Args:
            ax: Matplotlib Axes
            obstacles: Obstacle list
        """
        for ob in obstacles:
            pos = ob["position"]
            size = ob["size"]
            rot = ob["rotation"]
            name = ob["name"]

            # Center and size
            cx = pos["x"]
            cz = pos["z"]
            w = size["x"]
            h = size["z"]
            angle = self.quaternion_to_yaw(rot)  # degrees

            # Default edge and face colors
            edge_color = 'black'
            face_color = 'gray'
            
            # Determine start position and styling based on object type
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

            # Create obstacle rectangle
            rect = Rectangle((start_x, start_y), w, h, edgecolor=edge_color, 
                           facecolor=face_color, alpha=0.3, linewidth=1)

            # Rotate around the obstacle center
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
        Collect trajectories for a single participant for one trial (for authority comparison).
        
        Args:
            participant_id: Participant ID
            
        Returns:
            Trajectory dict grouped by authority (one trial per authority)
        """
        participant_dir = self.log_base_path / participant_id
        if not participant_dir.exists():
            print(f"Participant directory not found: {participant_dir}")
            return {}
        
        trajectories = {}
        
        # Use the first trial for comparison
        trial_dirs = sorted(participant_dir.glob('[0-9]*'))
        if not trial_dirs:
            print(f"No trial directories found for {participant_id}")
            return {}
        
        # Use the first trial
        trial_dir = trial_dirs[0]
        trial_id = trial_dir.name
        print(f"Using trial {trial_id} for {participant_id}")
        
        # Iterate all authority levels under this trial
        for authority_dir in sorted(trial_dir.glob('0.*')):
            if not authority_dir.is_dir():
                continue
            
            authority = float(authority_dir.name)
            
            # Prefer CSV if present
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
                trajectories[authority] = trajectory_data  # One entry per authority
        
        return trajectories
    
    def create_participant_visualization(self, participant_id: str):
        """
        Create trajectory visualization for a single participant (authority comparison within one trial).
        
        Args:
            participant_id: Participant ID
        """
        print(f"Creating visualization for {participant_id}...")
        
        # Collect trajectory data
        trajectories = self.collect_participant_trajectories(participant_id)
        
        if not trajectories:
            print(f"No trajectory data found for {participant_id}")
            return
        
        # Ensure we have both authority levels
        if 0.3 not in trajectories or 0.7 not in trajectories:
            print(f"Incomplete authority data for {participant_id}")
            return
        
        # Load obstacles
        obstacles = self.load_obstacles()
        
        # Create figure
        fig, ax = plt.subplots(figsize=(12, 10))
        ax.set_aspect('equal')
        
        # Draw obstacles
        self.draw_obstacles(ax, obstacles)
        
        # Draw trajectories
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
            trial_id = traj_data['trial_id']  # Same trial_id for all authorities
            collisions = traj_data['collisions']
            
            # Trajectory line
            line_alpha = alpha * 0.8
            ax.plot(positions[:, 0], positions[:, 1], 
                   color=color, linewidth=3, alpha=line_alpha,
                   label=label)
            
            # Direction arrows (sparse sampling)
            arrow_step = max(1, len(positions) // 10)  # 最多10个箭头
            for j in range(0, len(positions)-1, arrow_step):
                x, z = positions[j]
                dx = positions[j+1, 0] - positions[j, 0]
                dz = positions[j+1, 1] - positions[j, 1]
                
                # Compute arrow length and direction
                length = np.sqrt(dx**2 + dz**2)
                if length > 0.1:  # Only draw meaningful arrows
                    arrow_length = min(0.3, length * 0.5)
                    dx_norm = (dx / length) * arrow_length
                    dz_norm = (dz / length) * arrow_length
                    
                    ax.arrow(x, z, dx_norm, dz_norm, 
                           head_width=0.12, head_length=0.12, 
                           fc=color, ec=color, alpha=alpha*0.7)
            
            # Collision points
            authority_collisions = 0
            if collisions:
                collision_points = np.array(collisions)
                ax.scatter(collision_points[:, 0], collision_points[:, 1], 
                         c='red', marker='x', s=100, linewidth=3, 
                         alpha=0.9, zorder=10)
                authority_collisions = len(collisions)
            
            total_collisions += authority_collisions
            
            # Legend entry
            if authority_collisions > 0:
                legend_label = f"{label} ({authority_collisions} collisions)"
            else:
                legend_label = label
                
            legend_elements.append(plt.Line2D([0], [0], color=color, lw=3, 
                                            label=legend_label))
        
        # Collision legend
        if total_collisions > 0:
            legend_elements.append(plt.Line2D([0], [0], marker='x', color='red', 
                                            markersize=10, linestyle='', 
                                            label=f'Collision Points'))
        
        # Legend and titles
        ax.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(1, 1), fontsize=11)
        ax.set_title(f"Trajectory Comparison for {participant_id} - Trial {trial_id}\n"
                    f"Low vs High Authority Smoothness Comparison", 
                    fontsize=14, fontweight='bold')
        ax.set_xlabel("X Position (m)", fontsize=12)
        ax.set_ylabel("Z Position (m)", fontsize=12)
        ax.grid(True, alpha=0.3)
        
        # Save figure
        output_file = self.output_path / f"trajectory_comparison_{participant_id}_trial_{trial_id}.png"
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Visualization saved to: {output_file}")
        plt.show()
    
    def create_all_visualizations(self):
        """
        Create trajectory visualizations for all participants.
        """
        print("=" * 60)
        print("TRAJECTORY VISUALIZATION FOR METRIC C")
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
        
        # Create visualizations per participant
        for participant_id in participants:
            self.create_participant_visualization(participant_id)
        
        print(f"\nAll visualizations completed!")
        print(f"Results saved in: {self.output_path}")

def main():
    """Entry point."""
    log_path = LOG_PATH
    output_path = OUTPUT_PATH
    
    # Create visualizer and run
    visualizer = TrajectoryVisualizer(log_path, output_path)
    visualizer.create_all_visualizations()

if __name__ == "__main__":
    main()
