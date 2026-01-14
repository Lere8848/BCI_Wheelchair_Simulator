#!/usr/bin/env python3
"""
Metric B: Number of Danger-Stop Triggers Analysis
危险停止触发次数分析 - 被试内主分析

重点分析：
1. 同一个受试者在两种Authority下的danger-stop触发次数变化
2. 受试者内部比较（within-subject analysis）
3. 分别分析两位受试者的表现
4. 从ROS2日志中提取early stop和danger stop事件
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import re
import warnings
warnings.filterwarnings('ignore')

class MetricBAnalyzer:
    def __init__(self, log_base_path: str, output_path: str = None):
        """
        初始化Metric B分析器
        
        Args:
            log_base_path: 日志文件根目录路径
            output_path: 输出文件夹路径，默认为当前脚本目录
        """
        self.log_base_path = Path(log_base_path)
        self.output_path = Path(output_path) if output_path else Path(__file__).parent
        self.output_path.mkdir(exist_ok=True)
        
    def extract_danger_stops_from_log(self, log_file: Path) -> dict:
        """
        从ROS2日志文件中提取危险停止数据
        
        Args:
            log_file: ROS2日志文件路径
            
        Returns:
            Dict包含危险停止统计信息
        """
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 搜索关键词
            early_stops = len(re.findall(r'early\s*stop', content, re.IGNORECASE))
            danger_stops = len(re.findall(r'danger\s*stop', content, re.IGNORECASE))
            
            # 搜索其他可能的安全相关事件
            safety_warnings = len(re.findall(r'safety.*warning', content, re.IGNORECASE))
            emergency_stops = len(re.findall(r'emergency.*stop', content, re.IGNORECASE))
            collision_warnings = len(re.findall(r'collision.*warning', content, re.IGNORECASE))
            
            # 总的安全停止事件
            total_safety_stops = early_stops + danger_stops + emergency_stops
            total_safety_events = total_safety_stops + safety_warnings + collision_warnings
            
            # 计算日志文件的行数作为活动指标
            log_lines = len(content.split('\n'))
            
            return {
                'early_stops': early_stops,
                'danger_stops': danger_stops,
                'safety_warnings': safety_warnings,
                'emergency_stops': emergency_stops,
                'collision_warnings': collision_warnings,
                'total_safety_stops': total_safety_stops,
                'total_safety_events': total_safety_events,
                'log_lines': log_lines,
                'log_file': str(log_file)
            }
            
        except Exception as e:
            print(f"Error processing {log_file}: {e}")
            return self._empty_safety_data()
    
    def _empty_safety_data(self) -> dict:
        """返回空的安全数据"""
        return {
            'early_stops': 0,
            'danger_stops': 0,
            'safety_warnings': 0,
            'emergency_stops': 0,
            'collision_warnings': 0,
            'total_safety_stops': 0,
            'total_safety_events': 0,
            'log_lines': 0,
            'log_file': ''
        }
    
    def get_trial_duration_from_csv(self, csv_file: Path) -> float:
        """
        从CSV文件获取试验时长
        
        Args:
            csv_file: CSV文件路径
            
        Returns:
            试验时长（秒）
        """
        try:
            df = pd.read_csv(csv_file)
            if 'timestamp' in df.columns:
                return float(df['timestamp'].max() - df['timestamp'].min())
            else:
                return float(len(df) * 0.1)  # 假设100ms采样率
        except:
            return 0.0
    
    def analyze_single_trial(self, participant_id: str, trial_id: str, authority: str) -> dict:
        """
        分析单个试验的危险停止数据
        
        Args:
            participant_id: 参与者ID (e.g., 'T_001')
            trial_id: 试验ID (e.g., '01')
            authority: 权限级别 (e.g., '0.3')
            
        Returns:
            Dict包含试验信息和危险停止数据
        """
        trial_path = self.log_base_path / participant_id / trial_id / authority
        
        # 查找ROS2日志文件
        log_path = trial_path / 'control_fusion_node'
        log_files = list(log_path.glob('*.log')) if log_path.exists() else []
        
        if not log_files:
            print(f"Warning: No ROS2 log file found in {log_path}")
            safety_data = self._empty_safety_data()
        else:
            safety_data = self.extract_danger_stops_from_log(log_files[0])
        
        # 获取试验时长
        csv_files = list(trial_path.glob('log_*.csv'))
        duration = self.get_trial_duration_from_csv(csv_files[0]) if csv_files else 0.0
        
        # 计算安全事件率
        safety_stops_rate = safety_data['total_safety_stops'] / duration if duration > 0 else 0.0
        safety_events_rate = safety_data['total_safety_events'] / duration if duration > 0 else 0.0
        
        # 组合试验信息
        result = {
            'participant': participant_id,
            'trial': trial_id,
            'authority': float(authority),
            'duration_seconds': duration,
            'safety_stops_rate_per_second': safety_stops_rate,
            'safety_events_rate_per_second': safety_events_rate,
            **safety_data
        }
        
        return result
    
    def collect_all_data(self) -> pd.DataFrame:
        """
        收集所有试验的危险停止数据
        
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
                    'early_stops_mean': authority_03['early_stops'].mean(),
                    'danger_stops_mean': authority_03['danger_stops'].mean(),
                    'total_safety_stops_mean': authority_03['total_safety_stops'].mean(),
                    'total_safety_stops_sum': authority_03['total_safety_stops'].sum(),
                    'total_safety_events_mean': authority_03['total_safety_events'].mean(),
                    'safety_stops_rate_mean': authority_03['safety_stops_rate_per_second'].mean(),
                    'trial_count': len(authority_03)
                },
                'authority_0.7': {
                    'early_stops_mean': authority_07['early_stops'].mean(),
                    'danger_stops_mean': authority_07['danger_stops'].mean(),
                    'total_safety_stops_mean': authority_07['total_safety_stops'].mean(),
                    'total_safety_stops_sum': authority_07['total_safety_stops'].sum(),
                    'total_safety_events_mean': authority_07['total_safety_events'].mean(),
                    'safety_stops_rate_mean': authority_07['safety_stops_rate_per_second'].mean(),
                    'trial_count': len(authority_07)
                }
            }
            
            # 计算差异
            safety_stops_diff = (authority_03['total_safety_stops'].mean() - 
                               authority_07['total_safety_stops'].mean())
            safety_rate_diff = (authority_03['safety_stops_rate_per_second'].mean() - 
                              authority_07['safety_stops_rate_per_second'].mean())
            
            results[participant]['differences'] = {
                'safety_stops_diff': safety_stops_diff,
                'safety_rate_diff': safety_rate_diff
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
                'Early_Stops': data['authority_0.3']['early_stops_mean'],
                'Danger_Stops': data['authority_0.3']['danger_stops_mean'],
                'Total_Safety_Stops': data['authority_0.3']['total_safety_stops_sum'],
                'Mean_Safety_Stops_per_Trial': data['authority_0.3']['total_safety_stops_mean'],
                'Mean_Safety_Events_per_Trial': data['authority_0.3']['total_safety_events_mean'],
                'Safety_Stops_Rate_per_Second': data['authority_0.3']['safety_stops_rate_mean'],
                'Trial_Count': data['authority_0.3']['trial_count']
            })
            
            # Authority 0.7
            table_data.append({
                'Participant': participant,
                'Authority': 0.7,
                'Early_Stops': data['authority_0.7']['early_stops_mean'],
                'Danger_Stops': data['authority_0.7']['danger_stops_mean'],
                'Total_Safety_Stops': data['authority_0.7']['total_safety_stops_sum'],
                'Mean_Safety_Stops_per_Trial': data['authority_0.7']['total_safety_stops_mean'],
                'Mean_Safety_Events_per_Trial': data['authority_0.7']['total_safety_events_mean'],
                'Safety_Stops_Rate_per_Second': data['authority_0.7']['safety_stops_rate_mean'],
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
        fig.suptitle('Metric B: Danger-Stop Triggers Analysis - Within-Subject Comparison', 
                    fontsize=16, fontweight='bold')
        
        # 1. 总安全停止次数箱线图 - 按参与者分开
        sns.boxplot(data=df_vis, x='participant', y='total_safety_stops', 
                   hue='authority_label', ax=axes[0,0])
        axes[0,0].set_title('Total Safety Stops by Participant and Authority')
        axes[0,0].set_xlabel('Participant')
        axes[0,0].set_ylabel('Total Safety Stops')
        axes[0,0].legend(title='Authority Level')
        
        # 2. 早期停止次数箱线图 - 按参与者分开
        sns.boxplot(data=df_vis, x='participant', y='early_stops', 
                   hue='authority_label', ax=axes[0,1])
        axes[0,1].set_title('Early Stops by Participant and Authority')
        axes[0,1].set_xlabel('Participant')
        axes[0,1].set_ylabel('Early Stops')
        axes[0,1].legend(title='Authority Level')
        
        # 3. 危险停止次数箱线图 - 按参与者分开
        sns.boxplot(data=df_vis, x='participant', y='danger_stops', 
                   hue='authority_label', ax=axes[1,0])
        axes[1,0].set_title('Danger Stops by Participant and Authority')
        axes[1,0].set_xlabel('Participant')
        axes[1,0].set_ylabel('Danger Stops')
        axes[1,0].legend(title='Authority Level')
        
        # 4. 个体差异图 - 安全停止率
        # 计算每个参与者在两种authority下的平均安全停止率
        participant_means = df.groupby(['participant', 'authority'])['safety_stops_rate_per_second'].mean().unstack()
        
        x_pos = np.arange(len(participant_means.index))
        width = 0.35
        
        bars1 = axes[1,1].bar(x_pos - width/2, participant_means[0.3], width, 
                             label='Low User Authority', alpha=0.8)
        bars2 = axes[1,1].bar(x_pos + width/2, participant_means[0.7], width,
                             label='High User Authority', alpha=0.8)
        
        axes[1,1].set_xlabel('Participant')
        axes[1,1].set_ylabel('Safety Stops Rate (per second)')
        axes[1,1].set_title('Safety Stops Rate Comparison')
        axes[1,1].set_xticks(x_pos)
        axes[1,1].set_xticklabels(participant_means.index)
        axes[1,1].legend()
        axes[1,1].grid(axis='y', alpha=0.3)
        
        # 添加数值标签
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                axes[1,1].annotate(f'{height:.4f}',
                                 xy=(bar.get_x() + bar.get_width() / 2, height),
                                 xytext=(0, 3),
                                 textcoords="offset points",
                                 ha='center', va='bottom')
        
        plt.tight_layout()
        
        # 保存图表
        output_file = self.output_path / "metric_B_danger_stops_analysis.png"
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
\\caption{Metric B: Danger-Stop Triggers Analysis by Participant and Authority Level}
\\label{tab:metric_b_danger_stops}
\\begin{tabular}{ccccccc}
\\toprule
Participant & Authority & Early & Danger & Total Safety & Mean per & Rate per \\\\
           & Level     & Stops & Stops  & Stops       & Trial   & Second \\\\
\\midrule
"""
        
        for _, row in summary_df.iterrows():
            latex_table += f"{row['Participant']} & {row['Authority']:.1f} & "
            latex_table += f"{row['Early_Stops']:.1f} & "
            latex_table += f"{row['Danger_Stops']:.1f} & "
            latex_table += f"{row['Total_Safety_Stops']:.0f} & "
            latex_table += f"{row['Mean_Safety_Stops_per_Trial']:.2f} & "
            latex_table += f"{row['Safety_Stops_Rate_per_Second']:.4f} \\\\\n"
        
        latex_table += """\\bottomrule
\\end{tabular}
\\end{table}
"""
        return latex_table
    
    def run_complete_analysis(self):
        """
        运行完整的Metric B分析
        """
        print("=" * 60)
        print("METRIC B: DANGER-STOP TRIGGERS ANALYSIS")
        print("=" * 60)
        
        # 1. 收集数据
        print("\n1. Collecting danger-stop data from all trials...")
        df = self.collect_all_data()
        
        if df.empty:
            print("No data found. Please check the log file paths.")
            return
        
        # 保存原始数据
        raw_data_file = self.output_path / "metric_B_raw_data.csv"
        df.to_csv(raw_data_file, index=False)
        print(f"Raw data saved to: {raw_data_file}")
        
        # 2. 显示原始数据
        print("\n2. Raw Data:")
        print("-" * 40)
        print(df[['participant', 'trial', 'authority', 'early_stops', 'danger_stops', 
                 'total_safety_stops', 'total_safety_events', 'safety_stops_rate_per_second']].to_string(index=False))
        
        # 3. 被试内分析
        print("\n3. Within-Subject Analysis:")
        print("-" * 40)
        within_subject_results = self.perform_within_subject_analysis(df)
        
        for participant, data in within_subject_results.items():
            print(f"\n{participant}:")
            print(f"  Authority 0.3: {data['authority_0.3']['total_safety_stops_sum']} total safety stops "
                  f"({data['authority_0.3']['total_safety_stops_mean']:.2f} per trial)")
            print(f"  Authority 0.7: {data['authority_0.7']['total_safety_stops_sum']} total safety stops "
                  f"({data['authority_0.7']['total_safety_stops_mean']:.2f} per trial)")
            print(f"  Difference: {data['differences']['safety_stops_diff']:+.2f} safety stops per trial")
            print(f"  Rate difference: {data['differences']['safety_rate_diff']:+.4f} stops per second")
        
        # 4. 创建汇总表格
        print("\n4. Summary Table:")
        print("-" * 40)
        summary_df = self.create_summary_table(within_subject_results)
        print(summary_df.to_string(index=False))
        
        # 保存汇总表格
        summary_file = self.output_path / "metric_B_summary_table.csv"
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
        latex_file = self.output_path / "metric_B_latex_table.tex"
        with open(latex_file, 'w', encoding='utf-8') as f:
            f.write(latex_table)
        print(f"LaTeX table saved to: {latex_file}")
        
        # 7. 分析总结
        print("\n7. Analysis Summary:")
        print("-" * 40)
        total_safety_stops = df['total_safety_stops'].sum()
        print(f"• Total safety stops across all trials: {total_safety_stops}")
        
        auth_03_stops = df[df['authority'] == 0.3]['total_safety_stops'].sum()
        auth_07_stops = df[df['authority'] == 0.7]['total_safety_stops'].sum()
        print(f"• Authority 0.3: {auth_03_stops} total safety stops")
        print(f"• Authority 0.7: {auth_07_stops} total safety stops")
        
        if auth_03_stops > auth_07_stops:
            print(f"• Lower authority (0.3) triggered {auth_03_stops - auth_07_stops} more safety stops")
        elif auth_07_stops > auth_03_stops:
            print(f"• Higher authority (0.7) triggered {auth_07_stops - auth_03_stops} more safety stops")
        else:
            print(f"• Both authority levels triggered equal numbers of safety stops")
        
        print(f"• Analysis completed successfully!")
        print(f"• Results saved in: {self.output_path}")

def main():
    """主函数"""
    # 设置路径
    log_path = r"d:\UnityProject\wheelchair_sim\Assets\Logs\0820_use_this"
    output_path = Path(__file__).parent
    
    # 创建分析器并运行分析
    analyzer = MetricBAnalyzer(log_path, output_path)
    analyzer.run_complete_analysis()

if __name__ == "__main__":
    main()
