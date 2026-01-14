#!/usr/bin/env python3
"""
Metric D: Distance Traveled within Fixed Time Window Analysis
Distance traveled analysis within a fixed time window (within-subject).

Focus:
1. Compare distance traveled under two authority levels for the same participant
2. Within-subject comparison
3. Analyze each participant separately

Distance formula:
L_actual = Σ || (x_{t+1} - x_t, z_{t+1} - z_t) ||_2

Under a fixed time budget, making more progress along the path indicates higher productivity and efficiency.
"""

import os
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# =========================
# User-configurable settings
# =========================
LOG_PATH = r"d:\UnityProject\wheelchair_sim\Assets\Logs\0820_use_this"
OUTPUT_PATH = Path(__file__).parent
ENABLE_LATEX_OUTPUT = False

class MetricDAnalyzer:
    def __init__(self, log_base_path: str, output_path: str = None):
        """
        Initialize the Metric D analyzer.
        
        Args:
            log_base_path: Root directory that contains the log folders
            output_path: Output directory; defaults to this script directory
        """
        self.log_base_path = Path(log_base_path)
        self.output_path = Path(output_path) if output_path else Path(__file__).parent
        self.output_path.mkdir(exist_ok=True)
        
    def compute_path_distance_from_csv(self, csv_file: Path) -> dict:
        """
        Compute traveled distance from a CSV log file.
        
        Args:
            csv_file: CSV log file path
            
        Returns:
            Dict with distance statistics
        """
        try:
            df = pd.read_csv(csv_file)
            
            # Find position/time columns (handle potential duplicate column names)
            pos_x_col = None
            pos_z_col = None
            timestamp_col = None
            
            for col in df.columns:
                if 'pos_x' in str(col) and pos_x_col is None:
                    pos_x_col = col
                elif 'pos_z' in str(col) and pos_z_col is None:
                    pos_z_col = col
                elif 'timestamp' in str(col) and timestamp_col is None:
                    timestamp_col = col
            
            if pos_x_col is None or pos_z_col is None:
                print(f"Warning: Position columns not found in {csv_file}")
                return self._empty_distance_data()
            
            # Extract position data
            if isinstance(df[pos_x_col], pd.DataFrame):
                pos_x = df[pos_x_col].iloc[:, 0].values
            else:
                pos_x = df[pos_x_col].values
                
            if isinstance(df[pos_z_col], pd.DataFrame):
                pos_z = df[pos_z_col].iloc[:, 0].values
            else:
                pos_z = df[pos_z_col].values
            
            # Extract timestamps
            if timestamp_col is not None:
                if isinstance(df[timestamp_col], pd.DataFrame):
                    timestamps = df[timestamp_col].iloc[:, 0].values
                else:
                    timestamps = df[timestamp_col].values
            else:
                # If there is no timestamp column, assume a fixed sampling rate
                timestamps = np.arange(len(pos_x)) * 0.1  # assume 100ms
            
            # Filter invalid values
            valid_mask = ~(np.isnan(pos_x) | np.isnan(pos_z))
            pos_x = pos_x[valid_mask]
            pos_z = pos_z[valid_mask]
            timestamps = timestamps[valid_mask]
            
            if len(pos_x) < 2:
                print(f"Warning: Insufficient valid position data in {csv_file}")
                return self._empty_distance_data()
            
            # Cumulative path length
            path_segments = []
            cumulative_distance = 0.0
            cumulative_distances = [0.0]  # distance at start is 0
            
            for i in range(len(pos_x) - 1):
                x1, z1 = pos_x[i], pos_z[i]
                x2, z2 = pos_x[i + 1], pos_z[i + 1]
                
                # Euclidean segment distance
                segment_distance = np.sqrt((x2 - x1)**2 + (z2 - z1)**2)
                path_segments.append(segment_distance)
                cumulative_distance += segment_distance
                cumulative_distances.append(cumulative_distance)
            
            # Time-related metrics
            total_time = float(timestamps[-1] - timestamps[0]) if len(timestamps) > 1 else 0.0
            
            # Average speed
            avg_speed = cumulative_distance / total_time if total_time > 0 else 0.0
            
            # Movement time (exclude near-stationary segments)
            movement_threshold = 0.01  # m/s
            movement_segments = [seg for seg in path_segments if seg > movement_threshold * 0.1]  # assume 0.1s
            movement_time = len(movement_segments) * 0.1  # assume 0.1s
            
            # Effective speed
            effective_speed = cumulative_distance / movement_time if movement_time > 0 else 0.0
            
            # Straight-line distance
            straight_line_distance = np.sqrt((pos_x[-1] - pos_x[0])**2 + (pos_z[-1] - pos_z[0])**2)
            
            # Path efficiency (straight/actual)
            path_efficiency = straight_line_distance / cumulative_distance if cumulative_distance > 0 else 0.0
            
            return {
                'total_distance': float(cumulative_distance),
                'straight_line_distance': float(straight_line_distance),
                'path_efficiency': float(path_efficiency),
                'total_time': float(total_time),
                'movement_time': float(movement_time),
                'avg_speed': float(avg_speed),
                'effective_speed': float(effective_speed),
                'num_segments': len(path_segments),
                'num_points': len(pos_x),
                'start_position': (float(pos_x[0]), float(pos_z[0])),
                'end_position': (float(pos_x[-1]), float(pos_z[-1])),
                'csv_file': str(csv_file)
            }
            
        except Exception as e:
            print(f"Error processing {csv_file}: {e}")
            return self._empty_distance_data()
    
    def compute_path_distance_from_trajectory(self, traj_file: Path) -> dict:
        """
        Compute traveled distance from a trajectory JSON file.
        
        Args:
            traj_file: Trajectory JSON file path
            
        Returns:
            Dict with distance statistics
        """
        try:
            with open(traj_file, 'r') as f:
                traj_data = json.load(f)
            
            if 'points' not in traj_data:
                print(f"Warning: No 'points' found in {traj_file}")
                return self._empty_distance_data()
            
            points = traj_data['points']
            if len(points) < 2:
                print(f"Warning: Insufficient trajectory points in {traj_file}")
                return self._empty_distance_data()
            
            # Extract positions and timestamps
            positions = []
            timestamps = []
            
            for point in points:
                pos = point['position']
                positions.append((pos['x'], pos['z']))
                timestamps.append(point['time'])
            
            # Cumulative path length
            path_segments = []
            cumulative_distance = 0.0
            
            for i in range(len(positions) - 1):
                x1, z1 = positions[i]
                x2, z2 = positions[i + 1]
                
                segment_distance = np.sqrt((x2 - x1)**2 + (z2 - z1)**2)
                path_segments.append(segment_distance)
                cumulative_distance += segment_distance
            
            # Time-related metrics
            total_time = float(timestamps[-1] - timestamps[0]) if len(timestamps) > 1 else 0.0
            avg_speed = cumulative_distance / total_time if total_time > 0 else 0.0
            
            # Straight-line distance
            start_pos = positions[0]
            end_pos = positions[-1]
            straight_line_distance = np.sqrt((end_pos[0] - start_pos[0])**2 + (end_pos[1] - start_pos[1])**2)
            
            # Path efficiency
            path_efficiency = straight_line_distance / cumulative_distance if cumulative_distance > 0 else 0.0
            
            return {
                'total_distance': float(cumulative_distance),
                'straight_line_distance': float(straight_line_distance),
                'path_efficiency': float(path_efficiency),
                'total_time': float(total_time),
                'movement_time': float(total_time),  # assume all points are moving time
                'avg_speed': float(avg_speed),
                'effective_speed': float(avg_speed),
                'num_segments': len(path_segments),
                'num_points': len(positions),
                'start_position': start_pos,
                'end_position': end_pos,
                'trajectory_file': str(traj_file)
            }
            
        except Exception as e:
            print(f"Error processing {traj_file}: {e}")
            return self._empty_distance_data()
    
    def _empty_distance_data(self) -> dict:
        """Return an empty distance-data record."""
        return {
            'total_distance': 0.0,
            'straight_line_distance': 0.0,
            'path_efficiency': 0.0,
            'total_time': 0.0,
            'movement_time': 0.0,
            'avg_speed': 0.0,
            'effective_speed': 0.0,
            'num_segments': 0,
            'num_points': 0,
            'start_position': (0.0, 0.0),
            'end_position': (0.0, 0.0),
            'csv_file': '',
            'trajectory_file': ''
        }
    
    def analyze_single_trial(self, participant_id: str, trial_id: str, authority: str) -> dict:
        """
        Analyze distance traveled for a single trial.
        
        Args:
            participant_id: Participant ID (e.g., 'T_001')
            trial_id: Trial ID (e.g., '01')
            authority: Authority level (e.g., '0.3')
            
        Returns:
            Dict containing trial info and distance data
        """
        trial_path = self.log_base_path / participant_id / trial_id / authority
        
        # Prefer CSV because it typically contains richer time-series data
        csv_files = list(trial_path.glob('log_*.csv'))
        trajectory_files = list(trial_path.glob('trajectory_*.json'))
        
        distance_data = self._empty_distance_data()
        
        if csv_files:
            # Compute distance using the CSV file
            distance_data = self.compute_path_distance_from_csv(csv_files[0])
        elif trajectory_files:
            # Fallback to trajectory file
            distance_data = self.compute_path_distance_from_trajectory(trajectory_files[0])
        else:
            print(f"Warning: No trajectory data found in {trial_path}")
        
        # Combine trial info
        result = {
            'participant': participant_id,
            'trial': trial_id,
            'authority': float(authority),
            **distance_data
        }
        
        return result
    
    def collect_all_data(self) -> pd.DataFrame:
        """
        Collect distance data for all trials.
        
        Returns:
            DataFrame containing all data
        """
        all_results = []
        
        # Iterate all participants
        for participant_dir in sorted(self.log_base_path.glob('T_*')):
            if not participant_dir.is_dir():
                continue
                
            participant_id = participant_dir.name
            print(f"Processing participant: {participant_id}")
            
            # Iterate all trials
            for trial_dir in sorted(participant_dir.glob('[0-9]*')):
                if not trial_dir.is_dir():
                    continue
                    
                trial_id = trial_dir.name
                print(f"  Processing trial: {trial_id}")
                
                # Iterate all authority levels
                for authority_dir in sorted(trial_dir.glob('0.*')):
                    if not authority_dir.is_dir():
                        continue
                    
                    authority = authority_dir.name
                    print(f"    Processing authority: {authority}")
                    
                    # Analyze single trial
                    result = self.analyze_single_trial(participant_id, trial_id, authority)
                    all_results.append(result)
        
        return pd.DataFrame(all_results)
    
    def perform_within_subject_analysis(self, df: pd.DataFrame) -> dict:
        """
        Perform within-subject analysis.
        
        Args:
            df: DataFrame containing all data
            
        Returns:
            Results dict
        """
        results = {}
        
        # Analyze each participant separately
        for participant in df['participant'].unique():
            participant_data = df[df['participant'] == participant]
            
            # Group by authority
            authority_03 = participant_data[participant_data['authority'] == 0.3]
            authority_07 = participant_data[participant_data['authority'] == 0.7]
            
            # Compute means
            results[participant] = {
                'authority_0.3': {
                    'total_distance_mean': authority_03['total_distance'].mean(),
                    'avg_speed_mean': authority_03['avg_speed'].mean(),
                    'effective_speed_mean': authority_03['effective_speed'].mean(),
                    'path_efficiency_mean': authority_03['path_efficiency'].mean(),
                    'total_time_mean': authority_03['total_time'].mean(),
                    'trial_count': len(authority_03)
                },
                'authority_0.7': {
                    'total_distance_mean': authority_07['total_distance'].mean(),
                    'avg_speed_mean': authority_07['avg_speed'].mean(),
                    'effective_speed_mean': authority_07['effective_speed'].mean(),
                    'path_efficiency_mean': authority_07['path_efficiency'].mean(),
                    'total_time_mean': authority_07['total_time'].mean(),
                    'trial_count': len(authority_07)
                }
            }
            
            # Differences
            distance_diff = (authority_07['total_distance'].mean() - 
                           authority_03['total_distance'].mean())
            speed_diff = (authority_07['avg_speed'].mean() - 
                         authority_03['avg_speed'].mean())
            efficiency_diff = (authority_07['path_efficiency'].mean() - 
                             authority_03['path_efficiency'].mean())
            
            results[participant]['differences'] = {
                'distance_diff': distance_diff,
                'speed_diff': speed_diff,
                'efficiency_diff': efficiency_diff
            }
        
        return results
    
    def create_summary_table(self, within_subject_results: dict) -> pd.DataFrame:
        """
        Create a summary table.
        
        Args:
            within_subject_results: Within-subject results
            
        Returns:
            Summary table DataFrame
        """
        table_data = []
        
        for participant, data in within_subject_results.items():
            # Authority 0.3
            table_data.append({
                'Participant': participant,
                'Authority': 0.3,
                'Total_Distance': data['authority_0.3']['total_distance_mean'],
                'Avg_Speed': data['authority_0.3']['avg_speed_mean'],
                'Effective_Speed': data['authority_0.3']['effective_speed_mean'],
                'Path_Efficiency': data['authority_0.3']['path_efficiency_mean'],
                'Total_Time': data['authority_0.3']['total_time_mean'],
                'Trial_Count': data['authority_0.3']['trial_count']
            })
            
            # Authority 0.7
            table_data.append({
                'Participant': participant,
                'Authority': 0.7,
                'Total_Distance': data['authority_0.7']['total_distance_mean'],
                'Avg_Speed': data['authority_0.7']['avg_speed_mean'],
                'Effective_Speed': data['authority_0.7']['effective_speed_mean'],
                'Path_Efficiency': data['authority_0.7']['path_efficiency_mean'],
                'Total_Time': data['authority_0.7']['total_time_mean'],
                'Trial_Count': data['authority_0.7']['trial_count']
            })
        
        return pd.DataFrame(table_data)
    
    def create_visualizations(self, df: pd.DataFrame):
        """
        Create visualization plots.
        
        Args:
            df: DataFrame containing all data
        """
        # Plot style
        plt.style.use('default')
        sns.set_palette("Set2")
        
        # User-friendly labels
        df_vis = df.copy()
        df_vis['authority_label'] = df_vis['authority'].map({0.3: 'Low User Authority', 0.7: 'High User Authority'})
        
        # Figure layout
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('Metric D: Distance Traveled Analysis - Within-Subject Comparison', 
                    fontsize=16, fontweight='bold')
        
        # 1. 总距离箱线图 - 按参与者分开
        sns.boxplot(data=df_vis, x='participant', y='total_distance', 
                   hue='authority_label', ax=axes[0,0])
        axes[0,0].set_title('Total Distance by Participant and Authority')
        axes[0,0].set_xlabel('Participant')
        axes[0,0].set_ylabel('Total Distance (m)')
        axes[0,0].legend(title='Authority Level')
        
        # 2. 平均速度箱线图 - 按参与者分开
        sns.boxplot(data=df_vis, x='participant', y='avg_speed', 
                   hue='authority_label', ax=axes[0,1])
        axes[0,1].set_title('Average Speed by Participant and Authority')
        axes[0,1].set_xlabel('Participant')
        axes[0,1].set_ylabel('Average Speed (m/s)')
        axes[0,1].legend(title='Authority Level')
        
        # 3. 路径效率箱线图 - 按参与者分开
        sns.boxplot(data=df_vis, x='participant', y='path_efficiency', 
                   hue='authority_label', ax=axes[1,0])
        axes[1,0].set_title('Path Efficiency by Participant and Authority')
        axes[1,0].set_xlabel('Participant')
        axes[1,0].set_ylabel('Path Efficiency (straight/actual)')
        axes[1,0].legend(title='Authority Level')
        
        # 4. Participant comparison: mean total distance by authority
        participant_means = df.groupby(['participant', 'authority'])['total_distance'].mean().unstack()
        
        x_pos = np.arange(len(participant_means.index))
        width = 0.35
        
        bars1 = axes[1,1].bar(x_pos - width/2, participant_means[0.3], width, 
                             label='Low User Authority', alpha=0.8)
        bars2 = axes[1,1].bar(x_pos + width/2, participant_means[0.7], width,
                             label='High User Authority', alpha=0.8)
        
        axes[1,1].set_xlabel('Participant')
        axes[1,1].set_ylabel('Mean Total Distance (m)')
        axes[1,1].set_title('Distance Traveled Comparison')
        axes[1,1].set_xticks(x_pos)
        axes[1,1].set_xticklabels(participant_means.index)
        axes[1,1].legend()
        axes[1,1].grid(axis='y', alpha=0.3)
        
        # Value labels
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                axes[1,1].annotate(f'{height:.2f}',
                                 xy=(bar.get_x() + bar.get_width() / 2, height),
                                 xytext=(0, 3),
                                 textcoords="offset points",
                                 ha='center', va='bottom')
        
        plt.tight_layout()
        
        # Save plot
        output_file = self.output_path / "metric_D_distance_analysis.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Visualization saved to: {output_file}")
        plt.show()
    
    def generate_latex_table(self, summary_df: pd.DataFrame) -> str:
        """
        Generate a LaTeX table.
        
        Args:
            summary_df: Summary DataFrame
            
        Returns:
            LaTeX table string
        """
        latex_table = """
\\begin{table}[h]
\\centering
\\caption{Metric D: Distance Traveled Analysis by Participant and Authority Level}
\\label{tab:metric_d_distance}
\\begin{tabular}{ccccccc}
\\toprule
Participant & Authority & Total & Avg Speed & Effective & Path & Total \\\\
           & Level     & Distance (m) & (m/s) & Speed (m/s) & Efficiency & Time (s) \\\\
\\midrule
"""
        
        for _, row in summary_df.iterrows():
            latex_table += f"{row['Participant']} & {row['Authority']:.1f} & "
            latex_table += f"{row['Total_Distance']:.2f} & "
            latex_table += f"{row['Avg_Speed']:.3f} & "
            latex_table += f"{row['Effective_Speed']:.3f} & "
            latex_table += f"{row['Path_Efficiency']:.3f} & "
            latex_table += f"{row['Total_Time']:.1f} \\\\\n"
        
        latex_table += """\\bottomrule
\\end{tabular}
\\end{table}

\\textbf{Note:} Higher values indicate better efficiency. Path efficiency is the ratio of straight-line distance to actual path length.
"""
        return latex_table
    
    def run_complete_analysis(self):
        """
        Run the complete Metric D analysis.
        """
        print("=" * 60)
        print("METRIC D: DISTANCE TRAVELED ANALYSIS")
        print("=" * 60)
        
        # 1. Collect data
        print("\n1. Collecting distance data from all trials...")
        df = self.collect_all_data()
        
        if df.empty:
            print("No data found. Please check the log file paths.")
            return
        
        # Save raw data
        raw_data_file = self.output_path / "metric_D_raw_data.csv"
        df.to_csv(raw_data_file, index=False)
        print(f"Raw data saved to: {raw_data_file}")
        
        # 2. Print raw data
        print("\n2. Raw Data:")
        print("-" * 40)
        print(df.to_string(index=False))
        
        # 3. Within-subject analysis
        print("\n3. Within-Subject Analysis:")
        print("-" * 40)
        within_subject_results = self.perform_within_subject_analysis(df)
        
        for participant, data in within_subject_results.items():
            print(f"\n{participant}:")
            print(f"  Authority 0.3: {data['authority_0.3']['total_distance_mean']:.2f}m "
                  f"(speed: {data['authority_0.3']['avg_speed_mean']:.3f} m/s)")
            print(f"  Authority 0.7: {data['authority_0.7']['total_distance_mean']:.2f}m "
                  f"(speed: {data['authority_0.7']['avg_speed_mean']:.3f} m/s)")
            distance_diff = data['differences']['distance_diff']
            direction = "farther" if distance_diff > 0 else "shorter"
            print(f"  High authority traveled {abs(distance_diff):.2f}m {direction}")
        
        # 4. Summary table
        print("\n4. Summary Table:")
        print("-" * 40)
        summary_df = self.create_summary_table(within_subject_results)
        print(summary_df.to_string(index=False))
        
        # Save summary table
        summary_file = self.output_path / "metric_D_summary_table.csv"
        summary_df.to_csv(summary_file, index=False)
        print(f"Summary table saved to: {summary_file}")
        
        # 5. Visualizations
        print("\n5. Generating visualizations...")
        self.create_visualizations(df)
        
        # 6. LaTeX table
        # print("\n6. LaTeX Table:")
        # print("-" * 40)
        # latex_table = self.generate_latex_table(summary_df)
        # print(latex_table)
        
        # 7. Summary
        print("\n7. Analysis Summary:")
        print("-" * 40)
        print(f"• Total trials analyzed: {len(df)}")
        
        # Overall distance stats
        auth_03_distance = df[df['authority'] == 0.3]['total_distance'].mean()
        auth_07_distance = df[df['authority'] == 0.7]['total_distance'].mean()
        
        print(f"• Overall distance traveled:")
        print(f"  - Low authority (0.3): {auth_03_distance:.2f}m")
        print(f"  - High authority (0.7): {auth_07_distance:.2f}m")
        
        if auth_07_distance > auth_03_distance:
            improvement = ((auth_07_distance - auth_03_distance) / auth_03_distance) * 100
            print(f"  - High authority shows {improvement:.1f}% more distance")
        else:
            decrease = ((auth_03_distance - auth_07_distance) / auth_03_distance) * 100
            print(f"  - High authority shows {decrease:.1f}% less distance")
        
        # Overall speed stats
        auth_03_speed = df[df['authority'] == 0.3]['avg_speed'].mean()
        auth_07_speed = df[df['authority'] == 0.7]['avg_speed'].mean()
        
        print(f"• Overall average speed:")
        print(f"  - Low authority (0.3): {auth_03_speed:.3f} m/s")
        print(f"  - High authority (0.7): {auth_07_speed:.3f} m/s")
        
        print(f"• Analysis completed successfully!")
        print(f"• Results saved in: {self.output_path}")

def main():
    """Entry point."""
    log_path = LOG_PATH
    output_path = OUTPUT_PATH
    
    # Create analyzer and run
    analyzer = MetricDAnalyzer(log_path, output_path)
    analyzer.run_complete_analysis()

if __name__ == "__main__":
    main()
