#!/usr/bin/env python3
"""
Metric A: Number of Collisions Analysis
Collision count analysis (within-subject).

Focus:
1. Compare collision counts and rates for the same participant under two authority levels.
2. Within-subject comparison.
3. Compare performance across participants.
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# =============================
# User-configurable settings
# =============================
# Root directory containing participant logs.
LOG_PATH = r"d:\UnityProject\wheelchair_sim\Assets\Logs\0820_use_this"
# Output directory for figures/CSVs.
OUTPUT_PATH = Path(__file__).parent
# LaTeX table output is disabled by default.
ENABLE_LATEX_OUTPUT = False

class MetricAAnalyzer:
    def __init__(self, log_base_path: str, output_path: str = None):
        """
        Initialize the Metric A analyzer.
        
        Args:
            log_base_path: Root directory containing log files.
            output_path: Output directory (defaults to this script directory).
        """
        self.log_base_path = Path(log_base_path)
        self.output_path = Path(output_path) if output_path else Path(__file__).parent
        self.output_path.mkdir(exist_ok=True)
        
    def extract_collision_data_from_csv(self, csv_file: Path) -> dict:
        """
        Extract collision statistics from a CSV log.
        
        Args:
            csv_file: Path to the CSV log.
            
        Returns:
            Dict containing collision statistics.
        """
        try:
            df = pd.read_csv(csv_file)
            
            # Validate required columns
            if 'collision_flag' not in df.columns or 'collision_count' not in df.columns:
                print(f"Warning: No collision columns found in {csv_file}")
                return self._empty_collision_data()
            
            # Handle duplicated column names (pandas may return a DataFrame)
            if isinstance(df['collision_flag'], pd.DataFrame):
                collision_flags = df['collision_flag'].iloc[:, 0]
            else:
                collision_flags = df['collision_flag']
            
            if isinstance(df['collision_count'], pd.DataFrame):
                collision_counts = df['collision_count'].iloc[:, 0]
            else:
                collision_counts = df['collision_count']
            
            # Compute collision metrics
            total_collisions = int(collision_counts.max()) if len(collision_counts) > 0 else 0
            collision_frames = int((collision_flags > 0).sum())
            
            # Compute trial duration
            if 'timestamp' in df.columns:
                duration = float(df['timestamp'].max() - df['timestamp'].min())
            else:
                duration = float(len(df) * 0.1)  # Assumes 100 ms sampling
            
            # Collision rate (collisions per second)
            collision_rate = float(total_collisions / duration) if duration > 0 else 0.0
            
            # Collision frame rate (collision frames per total frames)
            collision_frame_rate = float(collision_frames / len(df)) if len(df) > 0 else 0.0
            
            return {
                'total_collisions': total_collisions,
                'collision_frames': collision_frames,
                'duration_seconds': duration,
                'total_frames': len(df),
                'collision_rate_per_second': collision_rate,
                'collision_frame_rate': collision_frame_rate,
                'csv_file': str(csv_file)
            }
            
        except Exception as e:
            print(f"Error processing {csv_file}: {e}")
            return self._empty_collision_data()
    
    def _empty_collision_data(self) -> dict:
        """Return an empty collision-statistics dict."""
        return {
            'total_collisions': 0,
            'collision_frames': 0,
            'duration_seconds': 0.0,
            'total_frames': 0,
            'collision_rate_per_second': 0.0,
            'collision_frame_rate': 0.0,
            'csv_file': ''
        }
    
    def analyze_single_trial(self, participant_id: str, trial_id: str, authority: str) -> dict:
        """
        Analyze collision data for a single trial.
        
        Args:
            participant_id: Participant ID (e.g., 'T_001')
            trial_id: Trial ID (e.g., '01')
            authority: Authority level (e.g., '0.3')
            
        Returns:
            Dict containing trial metadata and collision metrics.
        """
        trial_path = self.log_base_path / participant_id / trial_id / authority
        
        # Find CSV log
        csv_files = list(trial_path.glob('log_*.csv'))
        if not csv_files:
            print(f"Warning: No CSV file found in {trial_path}")
            collision_data = self._empty_collision_data()
        else:
            collision_data = self.extract_collision_data_from_csv(csv_files[0])
        
        # 组合试验信息
        result = {
            'participant': participant_id,
            'trial': trial_id,
            'authority': float(authority),
            **collision_data
        }
        
        return result
    
    def collect_all_data(self) -> pd.DataFrame:
        """
        收集所有试验的碰撞数据
        
        Returns:
            包含所有数据的DataFrame
        """
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
        """
        执行被试内分析
        
        Args:
            df: 包含所有数据的DataFrame
            
        Returns:
            分析结果字典
        """
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
                    'total_collisions_mean': authority_03['total_collisions'].mean(),
                    'total_collisions_sum': authority_03['total_collisions'].sum(),
                    'collision_rate_mean': authority_03['collision_rate_per_second'].mean(),
                    'collision_frame_rate_mean': authority_03['collision_frame_rate'].mean(),
                    'trial_count': len(authority_03)
                },
                'authority_0.7': {
                    'total_collisions_mean': authority_07['total_collisions'].mean(),
                    'total_collisions_sum': authority_07['total_collisions'].sum(),
                    'collision_rate_mean': authority_07['collision_rate_per_second'].mean(),
                    'collision_frame_rate_mean': authority_07['collision_frame_rate'].mean(),
                    'trial_count': len(authority_07)
                }
            }
            
            # 计算差异
            collision_diff = (authority_03['total_collisions'].mean() - 
                            authority_07['total_collisions'].mean())
            rate_diff = (authority_03['collision_rate_per_second'].mean() - 
                        authority_07['collision_rate_per_second'].mean())
            
            results[participant]['differences'] = {
                'collision_count_diff': collision_diff,
                'collision_rate_diff': rate_diff
            }
        
        return results
    
    def create_summary_table(self, within_subject_results: dict) -> pd.DataFrame:
        """
        创建汇总表格
        
        Args:
            within_subject_results: 被试内分析结果
            
        Returns:
            汇总表格DataFrame
        """
        table_data = []
        
        for participant, data in within_subject_results.items():
            # Authority 0.3
            table_data.append({
                'Participant': participant,
                'Authority': 0.3,
                'Total_Collisions': data['authority_0.3']['total_collisions_sum'],
                'Mean_Collisions_per_Trial': data['authority_0.3']['total_collisions_mean'],
                'Mean_Collision_Rate_per_Second': data['authority_0.3']['collision_rate_mean'],
                'Mean_Collision_Frame_Rate': data['authority_0.3']['collision_frame_rate_mean'],
                'Trial_Count': data['authority_0.3']['trial_count']
            })
            
            # Authority 0.7
            table_data.append({
                'Participant': participant,
                'Authority': 0.7,
                'Total_Collisions': data['authority_0.7']['total_collisions_sum'],
                'Mean_Collisions_per_Trial': data['authority_0.7']['total_collisions_mean'],
                'Mean_Collision_Rate_per_Second': data['authority_0.7']['collision_rate_mean'],
                'Mean_Collision_Frame_Rate': data['authority_0.7']['collision_frame_rate_mean'],
                'Trial_Count': data['authority_0.7']['trial_count']
            })
        
        return pd.DataFrame(table_data)
    
    def create_visualizations(self, df: pd.DataFrame):
        """
        创建可视化图表
        
        Args:
            df: 包含所有数据的DataFrame
        """
        # 设置图形样式
        plt.style.use('default')
        sns.set_palette("Set2")
        
        # 为authority值创建用户友好的标签
        df_vis = df.copy()
        df_vis['authority_label'] = df_vis['authority'].map({0.3: 'Low User Authority', 0.7: 'High User Authority'})
        
        # 创建图形布局 - 1行3列
        fig, axes = plt.subplots(1, 3, figsize=(18, 6))
        fig.suptitle('Metric A: Collision Analysis - Within-Subject Comparison', 
                    fontsize=16, fontweight='bold')
        
        # 1. 总碰撞次数箱线图 - 按参与者分开
        sns.boxplot(data=df_vis, x='participant', y='total_collisions', 
                   hue='authority_label', ax=axes[0])
        axes[0].set_title('Total Collisions by Participant and Authority')
        axes[0].set_xlabel('Participant')
        axes[0].set_ylabel('Total Collisions')
        axes[0].legend(title='Authority Level')
        
        # 2. 碰撞率箱线图 - 按参与者分开
        sns.boxplot(data=df_vis, x='participant', y='collision_rate_per_second', 
                   hue='authority_label', ax=axes[1])
        axes[1].set_title('Collision Rate by Participant and Authority')
        axes[1].set_xlabel('Participant')
        axes[1].set_ylabel('Collisions per Second')
        axes[1].legend(title='Authority Level')
        
        # 3. 碰撞帧率箱线图 - 按参与者分开
        sns.boxplot(data=df_vis, x='participant', y='collision_frame_rate', 
                   hue='authority_label', ax=axes[2])
        axes[2].set_title('Collision Frame Rate by Participant and Authority')
        axes[2].set_xlabel('Participant')
        axes[2].set_ylabel('Collision Frames / Total Frames')
        axes[2].legend(title='Authority Level')
        
        plt.tight_layout()
        
        # Save figure
        output_file = self.output_path / "metric_A_collision_analysis.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Visualization saved to: {output_file}")
        plt.show()
    
    def generate_latex_table(self, summary_df: pd.DataFrame) -> str:
        """
        Generate a LaTeX table.
        
        Args:
            summary_df: Summary dataframe.
            
        Returns:
            LaTeX table as a string.
        """
        latex_table = """
\\begin{table}[h]
\\centering
\\caption{Metric A: Collision Analysis by Participant and Authority Level}
\\label{tab:metric_a_collisions}
\\begin{tabular}{cccccc}
\\toprule
Participant & Authority & Total & Mean per & Collision Rate & Frame Rate \\\\
           & Level     & Collisions & Trial & (per second) & (\\%) \\\\
\\midrule
"""
        
        for _, row in summary_df.iterrows():
            latex_table += f"{row['Participant']} & {row['Authority']:.1f} & "
            latex_table += f"{row['Total_Collisions']:.0f} & "
            latex_table += f"{row['Mean_Collisions_per_Trial']:.2f} & "
            latex_table += f"{row['Mean_Collision_Rate_per_Second']:.4f} & "
            latex_table += f"{row['Mean_Collision_Frame_Rate']*100:.2f} \\\\\n"
        
        latex_table += """\\bottomrule
\\end{tabular}
\\end{table}
"""
        return latex_table
    
    def run_complete_analysis(self):
        """
        Run the complete Metric A analysis.
        """
        print("=" * 60)
        print("METRIC A: COLLISION ANALYSIS")
        print("=" * 60)
        
        # 1) Collect data
        print("\n1. Collecting collision data from all trials...")
        df = self.collect_all_data()
        
        if df.empty:
            print("No data found. Please check the log file paths.")
            return
        
        # Save raw data
        raw_data_file = self.output_path / "metric_A_raw_data.csv"
        df.to_csv(raw_data_file, index=False)
        print(f"Raw data saved to: {raw_data_file}")
        
        # 2) Show raw data
        print("\n2. Raw Data:")
        print("-" * 40)
        print(df.to_string(index=False))
        
        # 3) Within-subject analysis
        print("\n3. Within-Subject Analysis:")
        print("-" * 40)
        within_subject_results = self.perform_within_subject_analysis(df)
        
        for participant, data in within_subject_results.items():
            print(f"\n{participant}:")
            print(f"  Authority 0.3: {data['authority_0.3']['total_collisions_sum']} total collisions "
                  f"({data['authority_0.3']['total_collisions_mean']:.2f} per trial)")
            print(f"  Authority 0.7: {data['authority_0.7']['total_collisions_sum']} total collisions "
                  f"({data['authority_0.7']['total_collisions_mean']:.2f} per trial)")
            print(f"  Difference: {data['differences']['collision_count_diff']:+.2f} collisions per trial")
        
        # 4) Summary table
        print("\n4. Summary Table:")
        print("-" * 40)
        summary_df = self.create_summary_table(within_subject_results)
        print(summary_df.to_string(index=False))
        
        # Save summary table
        summary_file = self.output_path / "metric_A_summary_table.csv"
        summary_df.to_csv(summary_file, index=False)
        print(f"Summary table saved to: {summary_file}")
        
        # 5) Visualizations
        print("\n5. Generating visualizations...")
        self.create_visualizations(df)

        # 6) LaTeX table output (disabled)
        # If you want to re-enable it, set ENABLE_LATEX_OUTPUT=True and uncomment below.
        # if ENABLE_LATEX_OUTPUT:
        #     print("\n6. LaTeX Table:")
        #     print("-" * 40)
        #     latex_table = self.generate_latex_table(summary_df)
        #     print(latex_table)
        #
        #     latex_file = self.output_path / "metric_A_latex_table.tex"
        #     with open(latex_file, 'w', encoding='utf-8') as f:
        #         f.write(latex_table)
        #     print(f"LaTeX table saved to: {latex_file}")
        
        # 7) Summary
        print("\n7. Analysis Summary:")
        print("-" * 40)
        total_collisions = df['total_collisions'].sum()
        print(f"• Total collisions across all trials: {total_collisions}")
        
        if total_collisions == 0:
            print("• No collisions occurred in any trial")
            print("• Both authority levels achieved perfect collision avoidance")
        else:
            auth_03_collisions = df[df['authority'] == 0.3]['total_collisions'].sum()
            auth_07_collisions = df[df['authority'] == 0.7]['total_collisions'].sum()
            print(f"• Authority 0.3: {auth_03_collisions} total collisions")
            print(f"• Authority 0.7: {auth_07_collisions} total collisions")
        
        print(f"• Analysis completed successfully!")
        print(f"• Results saved in: {self.output_path}")

def main():
    """Entry point."""
    analyzer = MetricAAnalyzer(LOG_PATH, OUTPUT_PATH)
    analyzer.run_complete_analysis()

if __name__ == "__main__":
    main()
