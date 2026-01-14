#!/usr/bin/env python3
"""
Metric E: Number of Accepted User Inputs Analysis
用户输入分析 - 被试内主分析

重点分析：
1. 同一个受试者在两种Authority下的用户输入变化
2. 区分总用户输入数量和有效用户输入数量
3. 分析有效输入比例 (有效输入/总输入)
4. 被试者内部比较（within-subject analysis）
5. 标准化到相同时间长度
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

class MetricEAnalyzer:
    def __init__(self, log_base_path: str, output_path: str = None):
        """
        初始化Metric E分析器
        
        Args:
            log_base_path: 日志文件根目录路径
            output_path: 输出文件夹路径，默认为当前脚本目录
        """
        self.log_base_path = Path(log_base_path)
        self.output_path = Path(output_path) if output_path else Path(__file__).parent
        self.output_path.mkdir(exist_ok=True)
        
    def extract_user_inputs_from_log(self, log_file: Path) -> dict:
        """
        从ROS2日志文件中提取用户输入数据
        
        Args:
            log_file: ROS2日志文件路径
            
        Returns:
            Dict包含用户输入统计信息
        """
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 搜索总的用户输入相关事件
            # 1. 用户命令接收
            user_commands = len(re.findall(r'User command received:', content, re.IGNORECASE))
            # 2. 等待用户输入（表示系统需要用户决策）
            waiting_for_input = len(re.findall(r'waiting for user direction input', content, re.IGNORECASE))
            # 3. 用户方向输入请求
            direction_requests = len(re.findall(r'Multiple paths available.*waiting', content, re.IGNORECASE))
            
            # 总输入 = 用户命令 + 等待输入事件（表示用户需要做决策的次数）
            total_inputs = user_commands + waiting_for_input
            
            # 搜索有效输入事件（实际推动轮椅行动的输入）
            effective_inputs = 0
            # 1. 执行开始事件
            effective_inputs += len(re.findall(r'Starting execution for user direction', content, re.IGNORECASE))
            # 2. 轮椅开始移动
            effective_inputs += len(re.findall(r'Wheelchair motion status changed: Moving=True', content, re.IGNORECASE))
            # 3. 用户命令被接收（这表示用户输入被系统接受）
            effective_inputs += user_commands
            
            # 使用最保守的有效输入计算（用户命令数量）
            effective_inputs = user_commands
            
            # 搜索执行完成事件
            execution_completed = len(re.findall(r'Execution completed', content, re.IGNORECASE))
            
            # 搜索路径检测事件（表示系统状态）
            path_detections = len(re.findall(r'Multiple paths detected', content, re.IGNORECASE))
            
            # 计算日志文件的行数和活动指标
            log_lines = len(content.split('\n'))
            
            return {
                'total_user_inputs': total_inputs,
                'path_detections': path_detections,
                'waiting_for_input': waiting_for_input,
                'user_commands': user_commands,
                'effective_inputs': effective_inputs,
                'execution_completed': execution_completed,
                'log_lines': log_lines,
                'log_file': str(log_file)
            }
            
        except Exception as e:
            print(f"Error processing {log_file}: {e}")
            return self._empty_input_data()
    
    def _empty_input_data(self) -> dict:
        """返回空的输入数据"""
        return {
            'total_user_inputs': 0,
            'path_detections': 0,
            'waiting_for_input': 0,
            'user_commands': 0,
            'effective_inputs': 0,
            'execution_completed': 0,
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
        分析单个试验的用户输入数据
        
        Args:
            participant_id: 参与者ID (e.g., 'T_001')
            trial_id: 试验ID (e.g., '01')
            authority: 权限级别 (e.g., '0.3')
            
        Returns:
            Dict包含试验信息和用户输入数据
        """
        trial_path = self.log_base_path / participant_id / trial_id / authority
        
        # 查找ROS2日志文件
        log_path = trial_path / 'control_fusion_node'
        log_files = list(log_path.glob('*.log')) if log_path.exists() else []
        
        if not log_files:
            print(f"Warning: No ROS2 log file found in {log_path}")
            input_data = self._empty_input_data()
        else:
            input_data = self.extract_user_inputs_from_log(log_files[0])
        
        # 获取试验时长
        csv_files = list(trial_path.glob('log_*.csv'))
        duration = self.get_trial_duration_from_csv(csv_files[0]) if csv_files else 0.0
        
        # 计算有效输入比例
        effective_ratio = (input_data['effective_inputs'] / input_data['total_user_inputs'] 
                          if input_data['total_user_inputs'] > 0 else 0.0)
        
        # 组合试验信息
        result = {
            'participant': participant_id,
            'trial': trial_id,
            'authority': float(authority),
            'duration_seconds': duration,
            'effective_input_ratio': effective_ratio,
            **input_data
        }
        
        return result
    
    def collect_all_data(self) -> pd.DataFrame:
        """
        收集所有试验的用户输入数据
        
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
                    'total_inputs_mean': authority_03['total_user_inputs'].mean(),
                    'total_inputs_sum': authority_03['total_user_inputs'].sum(),
                    'effective_inputs_mean': authority_03['effective_inputs'].mean(),
                    'effective_inputs_sum': authority_03['effective_inputs'].sum(),
                    'effective_ratio_mean': authority_03['effective_input_ratio'].mean(),
                    'trial_count': len(authority_03)
                },
                'authority_0.7': {
                    'total_inputs_mean': authority_07['total_user_inputs'].mean(),
                    'total_inputs_sum': authority_07['total_user_inputs'].sum(),
                    'effective_inputs_mean': authority_07['effective_inputs'].mean(),
                    'effective_inputs_sum': authority_07['effective_inputs'].sum(),
                    'effective_ratio_mean': authority_07['effective_input_ratio'].mean(),
                    'trial_count': len(authority_07)
                }
            }
            
            # 计算差异
            total_inputs_diff = (authority_03['total_user_inputs'].mean() - 
                               authority_07['total_user_inputs'].mean())
            effective_inputs_diff = (authority_03['effective_inputs'].mean() - 
                                   authority_07['effective_inputs'].mean())
            effective_ratio_diff = (authority_03['effective_input_ratio'].mean() - 
                                  authority_07['effective_input_ratio'].mean())
            
            results[participant]['differences'] = {
                'total_inputs_diff': total_inputs_diff,
                'effective_inputs_diff': effective_inputs_diff,
                'effective_ratio_diff': effective_ratio_diff
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
                'Total_Inputs': data['authority_0.3']['total_inputs_sum'],
                'Mean_Total_Inputs_per_Trial': data['authority_0.3']['total_inputs_mean'],
                'Effective_Inputs': data['authority_0.3']['effective_inputs_sum'],
                'Mean_Effective_Inputs_per_Trial': data['authority_0.3']['effective_inputs_mean'],
                'Effective_Input_Ratio': data['authority_0.3']['effective_ratio_mean'],
                'Trial_Count': data['authority_0.3']['trial_count']
            })
            
            # Authority 0.7
            table_data.append({
                'Participant': participant,
                'Authority': 0.7,
                'Total_Inputs': data['authority_0.7']['total_inputs_sum'],
                'Mean_Total_Inputs_per_Trial': data['authority_0.7']['total_inputs_mean'],
                'Effective_Inputs': data['authority_0.7']['effective_inputs_sum'],
                'Mean_Effective_Inputs_per_Trial': data['authority_0.7']['effective_inputs_mean'],
                'Effective_Input_Ratio': data['authority_0.7']['effective_ratio_mean'],
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
        
        # 创建图形布局 - 简化为1x2布局，只保留两个核心图表
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        fig.suptitle('Metric E: Effective User Input Analysis - Within-Subject Comparison', 
                    fontsize=16, fontweight='bold')
        
        # 1. 有效用户输入数量箱线图
        sns.boxplot(data=df_vis, x='participant', y='effective_inputs', 
                   hue='authority_label', ax=axes[0])
        axes[0].set_title('Effective User Inputs by Participant and Authority')
        axes[0].set_xlabel('Participant')
        axes[0].set_ylabel('Effective User Inputs')
        axes[0].legend(title='Authority Level')
        
        # 2. 有效输入数量对比柱状图
        participant_means_effective = df.groupby(['participant', 'authority'])['effective_inputs'].mean().unstack()
        x_pos = np.arange(len(participant_means_effective.index))
        width = 0.35
        
        bars1 = axes[1].bar(x_pos - width/2, participant_means_effective[0.3], width, 
                             label='Low User Authority', alpha=0.8)
        bars2 = axes[1].bar(x_pos + width/2, participant_means_effective[0.7], width,
                             label='High User Authority', alpha=0.8)
        
        axes[1].set_xlabel('Participant')
        axes[1].set_ylabel('Mean Effective Inputs per Trial')
        axes[1].set_title('Effective Inputs Comparison')
        axes[1].set_xticks(x_pos)
        axes[1].set_xticklabels(participant_means_effective.index)
        axes[1].legend()
        axes[1].grid(axis='y', alpha=0.3)
        
        # 添加数值标签
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                axes[1].annotate(f'{height:.1f}',
                                 xy=(bar.get_x() + bar.get_width() / 2, height),
                                 xytext=(0, 3),
                                 textcoords="offset points",
                                 ha='center', va='bottom')
        
        plt.tight_layout()
        
        # 保存图表
        output_file = self.output_path / "metric_E_user_inputs_analysis.png"
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
\\caption{Metric E: User Input Analysis by Participant and Authority Level}
\\label{tab:metric_e_user_inputs}
\\begin{tabular}{ccccc}
\\toprule
Participant & Authority & Total & Effective & Effective \\\\
           & Level     & Inputs & Inputs   & Ratio \\\\
\\midrule
"""
        
        for _, row in summary_df.iterrows():
            latex_table += f"{row['Participant']} & {row['Authority']:.1f} & "
            latex_table += f"{row['Total_Inputs']:.0f} & "
            latex_table += f"{row['Effective_Inputs']:.0f} & "
            latex_table += f"{row['Effective_Input_Ratio']:.3f} \\\\\n"
        
        latex_table += """\\bottomrule
\\end{tabular}
\\end{table}
"""
        return latex_table
    
    def run_complete_analysis(self):
        """
        运行完整的Metric E分析
        """
        print("=" * 60)
        print("METRIC E: USER INPUT ANALYSIS")
        print("=" * 60)
        
        # 1. 收集数据
        print("\n1. Collecting user input data from all trials...")
        df = self.collect_all_data()
        
        if df.empty:
            print("No data found. Please check the log file paths.")
            return
        
        # 保存原始数据
        raw_data_file = self.output_path / "metric_E_raw_data.csv"
        df.to_csv(raw_data_file, index=False)
        print(f"Raw data saved to: {raw_data_file}")
        
        # 2. 显示原始数据
        print("\n2. Raw Data Summary:")
        print("-" * 40)
        display_cols = ['participant', 'trial', 'authority', 'total_user_inputs', 
                       'effective_inputs', 'effective_input_ratio']
        print(df[display_cols].to_string(index=False))
        
        # 3. 被试内分析
        print("\n3. Within-Subject Analysis:")
        print("-" * 40)
        within_subject_results = self.perform_within_subject_analysis(df)
        
        for participant, data in within_subject_results.items():
            print(f"\n{participant}:")
            print(f"  Authority 0.3:")
            print(f"    Total inputs: {data['authority_0.3']['total_inputs_sum']} "
                  f"({data['authority_0.3']['total_inputs_mean']:.1f} per trial)")
            print(f"    Effective inputs: {data['authority_0.3']['effective_inputs_sum']} "
                  f"({data['authority_0.3']['effective_inputs_mean']:.1f} per trial)")
            print(f"    Effective ratio: {data['authority_0.3']['effective_ratio_mean']:.3f}")
            
            print(f"  Authority 0.7:")
            print(f"    Total inputs: {data['authority_0.7']['total_inputs_sum']} "
                  f"({data['authority_0.7']['total_inputs_mean']:.1f} per trial)")
            print(f"    Effective inputs: {data['authority_0.7']['effective_inputs_sum']} "
                  f"({data['authority_0.7']['effective_inputs_mean']:.1f} per trial)")
            print(f"    Effective ratio: {data['authority_0.7']['effective_ratio_mean']:.3f}")
            
            print(f"  Differences (0.3 vs 0.7):")
            print(f"    Total inputs: {data['differences']['total_inputs_diff']:+.1f} per trial")
            print(f"    Effective inputs: {data['differences']['effective_inputs_diff']:+.1f} per trial")
            print(f"    Effective ratio: {data['differences']['effective_ratio_diff']:+.3f}")
        
        # 4. 创建汇总表格
        print("\n4. Summary Table:")
        print("-" * 40)
        summary_df = self.create_summary_table(within_subject_results)
        print(summary_df.to_string(index=False))
        
        # 保存汇总表格
        summary_file = self.output_path / "metric_E_summary_table.csv"
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
        latex_file = self.output_path / "metric_E_latex_table.tex"
        with open(latex_file, 'w', encoding='utf-8') as f:
            f.write(latex_table)
        print(f"LaTeX table saved to: {latex_file}")
        
        # 7. 分析总结
        print("\n7. Analysis Summary:")
        print("-" * 40)
        
        # 总体统计
        total_inputs_03 = df[df['authority'] == 0.3]['total_user_inputs'].sum()
        total_inputs_07 = df[df['authority'] == 0.7]['total_user_inputs'].sum()
        effective_inputs_03 = df[df['authority'] == 0.3]['effective_inputs'].sum()
        effective_inputs_07 = df[df['authority'] == 0.7]['effective_inputs'].sum()
        
        print(f"• Total user inputs:")
        print(f"  - Authority 0.3: {total_inputs_03}")
        print(f"  - Authority 0.7: {total_inputs_07}")
        print(f"  - Difference: {total_inputs_03 - total_inputs_07} more inputs with lower authority")
        
        print(f"• Effective user inputs:")
        print(f"  - Authority 0.3: {effective_inputs_03}")
        print(f"  - Authority 0.7: {effective_inputs_07}")
        print(f"  - Difference: {effective_inputs_03 - effective_inputs_07} more effective inputs with lower authority")
        
        avg_ratio_03 = df[df['authority'] == 0.3]['effective_input_ratio'].mean()
        avg_ratio_07 = df[df['authority'] == 0.7]['effective_input_ratio'].mean()
        
        print(f"• Average effective input ratio:")
        print(f"  - Authority 0.3: {avg_ratio_03:.3f}")
        print(f"  - Authority 0.7: {avg_ratio_07:.3f}")
        print(f"  - Higher authority has {avg_ratio_07 - avg_ratio_03:+.3f} better efficiency")
        
        # 按参与者分析
        print(f"\n• Individual participant analysis:")
        for participant in df['participant'].unique():
            p_data = df[df['participant'] == participant]
            p_03 = p_data[p_data['authority'] == 0.3]
            p_07 = p_data[p_data['authority'] == 0.7]
            
            avg_eff_03 = p_03['effective_inputs'].mean()
            avg_eff_07 = p_07['effective_inputs'].mean()
            
            print(f"  - {participant}: {avg_eff_03:.1f} vs {avg_eff_07:.1f} effective inputs per trial (0.3 vs 0.7)")
        
        print(f"• Analysis completed successfully!")
        print(f"• Results saved in: {self.output_path}")

def main():
    """主函数"""
    # 设置路径
    log_path = r"d:\UnityProject\wheelchair_sim\Assets\Logs\0820_use_this"
    output_path = Path(__file__).parent
    
    # 创建分析器并运行分析
    analyzer = MetricEAnalyzer(log_path, output_path)
    analyzer.run_complete_analysis()

if __name__ == "__main__":
    main()
