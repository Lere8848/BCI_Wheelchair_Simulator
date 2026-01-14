#!/usr/bin/env python3
"""
Metric C: Trajectory Smoothness Analysis
轨迹平滑度分析 - 被试内主分析

重点分析：
1. 同一个受试者在两种Authority下的轨迹平滑度变化
2. 受试者内部比较（within-subject analysis）
3. 分别分析两位受试者的表现

轨迹平滑度计算公式：
S_angle = Σ|wrap[-π,π](θ_{i+1} - θ_i)|

轨迹越平滑，转向角度变化越小，S_angle值越小
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

class MetricCAnalyzer:
    def __init__(self, log_base_path: str, output_path: str = None):
        """
        初始化Metric C分析器
        
        Args:
            log_base_path: 日志文件根目录路径
            output_path: 输出文件夹路径，默认为当前脚本目录
        """
        self.log_base_path = Path(log_base_path)
        self.output_path = Path(output_path) if output_path else Path(__file__).parent
        self.output_path.mkdir(exist_ok=True)
        
    def wrap_angle(self, angle):
        """
        将角度包裹到[-π, π]范围内
        
        Args:
            angle: 输入角度（弧度）
            
        Returns:
            包裹后的角度
        """
        return np.arctan2(np.sin(angle), np.cos(angle))
    
    def compute_heading_from_positions(self, positions):
        """
        从位置序列计算航向角
        
        Args:
            positions: 位置序列 [(x1, z1), (x2, z2), ...]
            
        Returns:
            航向角序列（弧度）
        """
        headings = []
        
        for i in range(len(positions) - 1):
            x1, z1 = positions[i]
            x2, z2 = positions[i + 1]
            
            # 计算两点间的方向向量
            dx = x2 - x1
            dz = z2 - z1
            
            # 计算航向角（使用atan2保证正确的象限）
            heading = np.arctan2(dz, dx)
            headings.append(heading)
        
        return np.array(headings)
    
    def compute_smoothness_from_csv(self, csv_file: Path) -> dict:
        """
        从CSV文件中计算轨迹平滑度
        
        Args:
            csv_file: CSV日志文件路径
            
        Returns:
            Dict包含平滑度统计信息
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
                return self._empty_smoothness_data()
            
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
            
            if len(pos_x) < 3:
                print(f"Warning: Insufficient valid position data in {csv_file}")
                return self._empty_smoothness_data()
            
            # 创建位置序列
            positions = list(zip(pos_x, pos_z))
            
            # 计算航向角序列
            headings = self.compute_heading_from_positions(positions)
            
            if len(headings) < 2:
                return self._empty_smoothness_data()
            
            # 计算平滑度：相邻航向角的变化总和
            angle_changes = []
            for i in range(len(headings) - 1):
                angle_diff = headings[i + 1] - headings[i]
                wrapped_diff = self.wrap_angle(angle_diff)
                angle_changes.append(abs(wrapped_diff))
            
            # 计算总的平滑度指标
            s_angle = np.sum(angle_changes)
            
            # 计算其他统计指标
            mean_angle_change = np.mean(angle_changes)
            max_angle_change = np.max(angle_changes)
            std_angle_change = np.std(angle_changes)
            
            # 计算轨迹长度
            path_length = 0
            for i in range(len(positions) - 1):
                x1, z1 = positions[i]
                x2, z2 = positions[i + 1]
                segment_length = np.sqrt((x2 - x1)**2 + (z2 - z1)**2)
                path_length += segment_length
            
            # 计算标准化平滑度（每单位路径长度的角度变化）
            normalized_smoothness = s_angle / path_length if path_length > 0 else 0
            
            return {
                'total_angle_change': float(s_angle),
                'mean_angle_change': float(mean_angle_change),
                'max_angle_change': float(max_angle_change),
                'std_angle_change': float(std_angle_change),
                'path_length': float(path_length),
                'normalized_smoothness': float(normalized_smoothness),
                'num_segments': len(angle_changes),
                'num_positions': len(positions),
                'csv_file': str(csv_file)
            }
            
        except Exception as e:
            print(f"Error processing {csv_file}: {e}")
            return self._empty_smoothness_data()
    
    def compute_smoothness_from_trajectory(self, traj_file: Path) -> dict:
        """
        从轨迹JSON文件中计算轨迹平滑度
        
        Args:
            traj_file: 轨迹JSON文件路径
            
        Returns:
            Dict包含平滑度统计信息
        """
        try:
            with open(traj_file, 'r') as f:
                traj_data = json.load(f)
            
            if 'points' not in traj_data:
                print(f"Warning: No 'points' found in {traj_file}")
                return self._empty_smoothness_data()
            
            points = traj_data['points']
            if len(points) < 3:
                print(f"Warning: Insufficient trajectory points in {traj_file}")
                return self._empty_smoothness_data()
            
            # 提取位置信息（使用x和z坐标，y是高度）
            positions = []
            for point in points:
                pos = point['position']
                positions.append((pos['x'], pos['z']))
            
            # 计算航向角序列
            headings = self.compute_heading_from_positions(positions)
            
            if len(headings) < 2:
                return self._empty_smoothness_data()
            
            # 计算平滑度：相邻航向角的变化总和
            angle_changes = []
            for i in range(len(headings) - 1):
                angle_diff = headings[i + 1] - headings[i]
                wrapped_diff = self.wrap_angle(angle_diff)
                angle_changes.append(abs(wrapped_diff))
            
            # 计算总的平滑度指标
            s_angle = np.sum(angle_changes)
            
            # 计算其他统计指标
            mean_angle_change = np.mean(angle_changes)
            max_angle_change = np.max(angle_changes)
            std_angle_change = np.std(angle_changes)
            
            # 计算轨迹长度
            path_length = 0
            for i in range(len(positions) - 1):
                x1, z1 = positions[i]
                x2, z2 = positions[i + 1]
                segment_length = np.sqrt((x2 - x1)**2 + (z2 - z1)**2)
                path_length += segment_length
            
            # 计算标准化平滑度（每单位路径长度的角度变化）
            normalized_smoothness = s_angle / path_length if path_length > 0 else 0
            
            return {
                'total_angle_change': float(s_angle),
                'mean_angle_change': float(mean_angle_change),
                'max_angle_change': float(max_angle_change),
                'std_angle_change': float(std_angle_change),
                'path_length': float(path_length),
                'normalized_smoothness': float(normalized_smoothness),
                'num_segments': len(angle_changes),
                'num_positions': len(positions),
                'trajectory_file': str(traj_file)
            }
            
        except Exception as e:
            print(f"Error processing {traj_file}: {e}")
            return self._empty_smoothness_data()
    
    def _empty_smoothness_data(self) -> dict:
        """返回空的平滑度数据"""
        return {
            'total_angle_change': 0.0,
            'mean_angle_change': 0.0,
            'max_angle_change': 0.0,
            'std_angle_change': 0.0,
            'path_length': 0.0,
            'normalized_smoothness': 0.0,
            'num_segments': 0,
            'num_positions': 0,
            'csv_file': '',
            'trajectory_file': ''
        }
    
    def analyze_single_trial(self, participant_id: str, trial_id: str, authority: str) -> dict:
        """
        分析单个试验的轨迹平滑度
        
        Args:
            participant_id: 参与者ID (e.g., 'T_001')
            trial_id: 试验ID (e.g., '01')
            authority: 权限级别 (e.g., '0.3')
            
        Returns:
            Dict包含试验信息和平滑度数据
        """
        trial_path = self.log_base_path / participant_id / trial_id / authority
        
        # 优先使用CSV文件，因为它包含更详细的时间序列数据
        csv_files = list(trial_path.glob('log_*.csv'))
        trajectory_files = list(trial_path.glob('trajectory_*.json'))
        
        smoothness_data = self._empty_smoothness_data()
        
        if csv_files:
            # 使用CSV文件计算平滑度
            smoothness_data = self.compute_smoothness_from_csv(csv_files[0])
        elif trajectory_files:
            # 回退到使用轨迹文件
            smoothness_data = self.compute_smoothness_from_trajectory(trajectory_files[0])
        else:
            print(f"Warning: No trajectory data found in {trial_path}")
        
        # 组合试验信息
        result = {
            'participant': participant_id,
            'trial': trial_id,
            'authority': float(authority),
            **smoothness_data
        }
        
        return result
    
    def collect_all_data(self) -> pd.DataFrame:
        """
        收集所有试验的轨迹平滑度数据
        
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
                    'total_angle_change_mean': authority_03['total_angle_change'].mean(),
                    'normalized_smoothness_mean': authority_03['normalized_smoothness'].mean(),
                    'mean_angle_change_mean': authority_03['mean_angle_change'].mean(),
                    'path_length_mean': authority_03['path_length'].mean(),
                    'trial_count': len(authority_03)
                },
                'authority_0.7': {
                    'total_angle_change_mean': authority_07['total_angle_change'].mean(),
                    'normalized_smoothness_mean': authority_07['normalized_smoothness'].mean(),
                    'mean_angle_change_mean': authority_07['mean_angle_change'].mean(),
                    'path_length_mean': authority_07['path_length'].mean(),
                    'trial_count': len(authority_07)
                }
            }
            
            # 计算差异（注意：平滑度越小越好）
            total_angle_diff = (authority_03['total_angle_change'].mean() - 
                              authority_07['total_angle_change'].mean())
            normalized_diff = (authority_03['normalized_smoothness'].mean() - 
                             authority_07['normalized_smoothness'].mean())
            
            results[participant]['differences'] = {
                'total_angle_change_diff': total_angle_diff,
                'normalized_smoothness_diff': normalized_diff,
                'smoothness_improvement': -normalized_diff  # 负值表示改善
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
                'Total_Angle_Change': data['authority_0.3']['total_angle_change_mean'],
                'Normalized_Smoothness': data['authority_0.3']['normalized_smoothness_mean'],
                'Mean_Angle_Change': data['authority_0.3']['mean_angle_change_mean'],
                'Path_Length': data['authority_0.3']['path_length_mean'],
                'Trial_Count': data['authority_0.3']['trial_count']
            })
            
            # Authority 0.7
            table_data.append({
                'Participant': participant,
                'Authority': 0.7,
                'Total_Angle_Change': data['authority_0.7']['total_angle_change_mean'],
                'Normalized_Smoothness': data['authority_0.7']['normalized_smoothness_mean'],
                'Mean_Angle_Change': data['authority_0.7']['mean_angle_change_mean'],
                'Path_Length': data['authority_0.7']['path_length_mean'],
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
        
        # 创建图形布局
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('Metric C: Trajectory Smoothness Analysis - Within-Subject Comparison', 
                    fontsize=16, fontweight='bold')
        
        # 1. 总角度变化箱线图 - 按参与者分开
        sns.boxplot(data=df_vis, x='participant', y='total_angle_change', 
                   hue='authority_label', ax=axes[0,0])
        axes[0,0].set_title('Total Angle Change by Participant and Authority')
        axes[0,0].set_xlabel('Participant')
        axes[0,0].set_ylabel('Total Angle Change (radians)')
        axes[0,0].legend(title='Authority Level')
        
        # 2. 标准化平滑度箱线图 - 按参与者分开
        sns.boxplot(data=df_vis, x='participant', y='normalized_smoothness', 
                   hue='authority_label', ax=axes[0,1])
        axes[0,1].set_title('Normalized Smoothness by Participant and Authority')
        axes[0,1].set_xlabel('Participant')
        axes[0,1].set_ylabel('Normalized Smoothness (rad/m)')
        axes[0,1].legend(title='Authority Level')
        
        # 3. 平均角度变化箱线图 - 按参与者分开
        sns.boxplot(data=df_vis, x='participant', y='mean_angle_change', 
                   hue='authority_label', ax=axes[1,0])
        axes[1,0].set_title('Mean Angle Change by Participant and Authority')
        axes[1,0].set_xlabel('Participant')
        axes[1,0].set_ylabel('Mean Angle Change (radians)')
        axes[1,0].legend(title='Authority Level')
        
        # 4. 个体差异图 - 标准化平滑度比较
        # 计算每个参与者在两种authority下的平均标准化平滑度
        participant_means = df.groupby(['participant', 'authority'])['normalized_smoothness'].mean().unstack()
        
        x_pos = np.arange(len(participant_means.index))
        width = 0.35
        
        bars1 = axes[1,1].bar(x_pos - width/2, participant_means[0.3], width, 
                             label='Low User Authority', alpha=0.8)
        bars2 = axes[1,1].bar(x_pos + width/2, participant_means[0.7], width,
                             label='High User Authority', alpha=0.8)
        
        axes[1,1].set_xlabel('Participant')
        axes[1,1].set_ylabel('Mean Normalized Smoothness (rad/m)')
        axes[1,1].set_title('Normalized Smoothness Comparison\n(Lower is smoother)')
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
                                 ha='center', va='bottom', fontsize=9)
        
        plt.tight_layout()
        
        # 保存图表
        output_file = self.output_path / "metric_C_trajectory_smoothness_analysis.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Visualization saved to: {output_file}")
        plt.show()
    
    def generate_latex_table(self, summary_df: pd.DataFrame) -> str:
        """
        生成LaTeX表格
        
        Args:
            summary_df: 汇总数据DataFrame
            
        Returns:
            LaTeX表格字符串
        """
        latex_table = """
\\begin{table}[h]
\\centering
\\caption{Metric C: Trajectory Smoothness Analysis by Participant and Authority Level}
\\label{tab:metric_c_smoothness}
\\begin{tabular}{cccccc}
\\toprule
Participant & Authority & Total Angle & Normalized & Mean Angle & Path Length \\\\
           & Level     & Change (rad) & Smoothness & Change (rad) & (m) \\\\
\\midrule
"""
        
        for _, row in summary_df.iterrows():
            latex_table += f"{row['Participant']} & {row['Authority']:.1f} & "
            latex_table += f"{row['Total_Angle_Change']:.3f} & "
            latex_table += f"{row['Normalized_Smoothness']:.4f} & "
            latex_table += f"{row['Mean_Angle_Change']:.4f} & "
            latex_table += f"{row['Path_Length']:.2f} \\\\\n"
        
        latex_table += """\\bottomrule
\\end{tabular}
\\end{table}

\\textbf{Note:} Lower values indicate smoother trajectories. Normalized smoothness is angle change per unit path length.
"""
        return latex_table
    
    def run_complete_analysis(self):
        """
        运行完整的Metric C分析
        """
        print("=" * 60)
        print("METRIC C: TRAJECTORY SMOOTHNESS ANALYSIS")
        print("=" * 60)
        
        # 1. 收集数据
        print("\n1. Collecting trajectory data from all trials...")
        df = self.collect_all_data()
        
        if df.empty:
            print("No data found. Please check the log file paths.")
            return
        
        # 保存原始数据
        raw_data_file = self.output_path / "metric_C_raw_data.csv"
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
            print(f"  Authority 0.3: {data['authority_0.3']['normalized_smoothness_mean']:.4f} rad/m "
                  f"(total: {data['authority_0.3']['total_angle_change_mean']:.3f} rad)")
            print(f"  Authority 0.7: {data['authority_0.7']['normalized_smoothness_mean']:.4f} rad/m "
                  f"(total: {data['authority_0.7']['total_angle_change_mean']:.3f} rad)")
            improvement = data['differences']['smoothness_improvement']
            direction = "smoother" if improvement > 0 else "less smooth"
            print(f"  High authority trajectory is {abs(improvement):.4f} rad/m {direction}")
        
        # 4. 创建汇总表格
        print("\n4. Summary Table:")
        print("-" * 40)
        summary_df = self.create_summary_table(within_subject_results)
        print(summary_df.to_string(index=False))
        
        # 保存汇总表格
        summary_file = self.output_path / "metric_C_summary_table.csv"
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
        latex_file = self.output_path / "metric_C_latex_table.tex"
        with open(latex_file, 'w', encoding='utf-8') as f:
            f.write(latex_table)
        print(f"LaTeX table saved to: {latex_file}")
        
        # 7. 分析总结
        print("\n7. Analysis Summary:")
        print("-" * 40)
        print(f"• Total trials analyzed: {len(df)}")
        
        # 计算整体平滑度统计
        auth_03_smoothness = df[df['authority'] == 0.3]['normalized_smoothness'].mean()
        auth_07_smoothness = df[df['authority'] == 0.7]['normalized_smoothness'].mean()
        
        print(f"• Overall normalized smoothness:")
        print(f"  - Low authority (0.3): {auth_03_smoothness:.4f} rad/m")
        print(f"  - High authority (0.7): {auth_07_smoothness:.4f} rad/m")
        
        if auth_03_smoothness > auth_07_smoothness:
            improvement = ((auth_03_smoothness - auth_07_smoothness) / auth_03_smoothness) * 100
            print(f"  - High authority shows {improvement:.1f}% smoother trajectories")
        else:
            worsening = ((auth_07_smoothness - auth_03_smoothness) / auth_03_smoothness) * 100
            print(f"  - High authority shows {worsening:.1f}% less smooth trajectories")
        
        print(f"• Analysis completed successfully!")
        print(f"• Results saved in: {self.output_path}")

def main():
    """主函数"""
    # 设置路径
    log_path = r"d:\UnityProject\wheelchair_sim\Assets\Logs\0820_use_this"
    output_path = Path(__file__).parent
    
    # 创建分析器并运行分析
    analyzer = MetricCAnalyzer(log_path, output_path)
    analyzer.run_complete_analysis()

if __name__ == "__main__":
    main()
