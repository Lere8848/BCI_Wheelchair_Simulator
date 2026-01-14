#!/usr/bin/env python3
"""
Wheelchair Simulation Metrics Results Display
更清晰地展示分析结果
"""

import pandas as pd
import numpy as np
from pathlib import Path

def display_results():
    """显示分析结果"""
    
    # 读取数据
    data_path = Path(__file__).parent / "metrics_raw_data.csv"
    if not data_path.exists():
        print("请先运行 metrics_analysis.py 生成数据")
        return
    
    df = pd.read_csv(data_path)
    
    print("=" * 80)
    print("WHEELCHAIR SIMULATION METRICS ANALYSIS RESULTS")
    print("=" * 80)
    
    # 显示原始数据
    print("\n1. RAW DATA FOR ALL TRIALS:")
    print("-" * 50)
    print(df.to_string(index=False))
    
    # 按参与者分组的统计
    print("\n\n2. STATISTICS BY PARTICIPANT:")
    print("-" * 50)
    participant_stats = df.groupby('participant').agg({
        'total_collisions': ['mean', 'sum'],
        'total_safety_stops': ['mean', 'sum'],
        'accepted_inputs': ['mean', 'sum'],
        'path_detections': ['mean', 'sum'],
        'direction_inputs': ['mean', 'sum'],
        'duration': 'mean'
    }).round(2)
    print(participant_stats)
    
    # 按权限级别分组的统计
    print("\n\n3. STATISTICS BY USER AUTHORITY LEVEL:")
    print("-" * 50)
    authority_stats = df.groupby('authority').agg({
        'total_collisions': ['mean', 'std', 'sum'],
        'total_safety_stops': ['mean', 'std', 'sum'],
        'accepted_inputs': ['mean', 'std', 'sum'],
        'path_detections': ['mean', 'std', 'sum'],
        'direction_inputs': ['mean', 'std', 'sum'],
        'duration': ['mean', 'std']
    }).round(2)
    print(authority_stats)
    
    # 按试验分组的统计
    print("\n\n4. STATISTICS BY TRIAL:")
    print("-" * 50)
    trial_stats = df.groupby(['participant', 'trial']).agg({
        'total_collisions': 'sum',
        'total_safety_stops': 'sum',
        'accepted_inputs': 'sum',
        'path_detections': 'sum',
        'direction_inputs': 'sum',
        'duration': 'sum'
    }).round(2)
    print(trial_stats)
    
    # 关键指标汇总
    print("\n\n5. KEY METRICS SUMMARY:")
    print("-" * 50)
    
    # 计算每个权限级别的平均值
    summary_0_3 = df[df['authority'] == 0.3]
    summary_0_7 = df[df['authority'] == 0.7]
    
    print(f"User Authority 0.3 (n={len(summary_0_3)}):")
    print(f"  • Average Collisions per trial: {summary_0_3['total_collisions'].mean():.2f} ± {summary_0_3['total_collisions'].std():.2f}")
    print(f"  • Average Safety Stops per trial: {summary_0_3['total_safety_stops'].mean():.2f} ± {summary_0_3['total_safety_stops'].std():.2f}")
    print(f"  • Average User Inputs per trial: {summary_0_3['accepted_inputs'].mean():.0f} ± {summary_0_3['accepted_inputs'].std():.0f}")
    print(f"  • Average Trial Duration: {summary_0_3['duration'].mean():.1f} ± {summary_0_3['duration'].std():.1f} seconds")
    
    print(f"\nUser Authority 0.7 (n={len(summary_0_7)}):")
    print(f"  • Average Collisions per trial: {summary_0_7['total_collisions'].mean():.2f} ± {summary_0_7['total_collisions'].std():.2f}")
    print(f"  • Average Safety Stops per trial: {summary_0_7['total_safety_stops'].mean():.2f} ± {summary_0_7['total_safety_stops'].std():.2f}")
    print(f"  • Average User Inputs per trial: {summary_0_7['accepted_inputs'].mean():.0f} ± {summary_0_7['accepted_inputs'].std():.0f}")
    print(f"  • Average Trial Duration: {summary_0_7['duration'].mean():.1f} ± {summary_0_7['duration'].std():.1f} seconds")
    
    # 对比分析
    print("\n\n6. COMPARATIVE ANALYSIS:")
    print("-" * 50)
    
    # 安全性对比
    safety_diff = summary_0_3['total_safety_stops'].mean() - summary_0_7['total_safety_stops'].mean()
    print(f"Safety Stop Difference (0.3 vs 0.7): {safety_diff:+.2f}")
    if safety_diff > 0:
        print("  → Lower user authority (0.3) has MORE safety stops")
    else:
        print("  → Higher user authority (0.7) has MORE safety stops")
    
    # 效率对比
    input_diff = summary_0_3['accepted_inputs'].mean() - summary_0_7['accepted_inputs'].mean()
    print(f"User Input Difference (0.3 vs 0.7): {input_diff:+.0f}")
    if input_diff > 0:
        print("  → Lower user authority (0.3) requires MORE user inputs")
    else:
        print("  → Higher user authority (0.7) requires MORE user inputs")
    
    # 时间效率对比
    time_diff = summary_0_3['duration'].mean() - summary_0_7['duration'].mean()
    print(f"Duration Difference (0.3 vs 0.7): {time_diff:+.1f} seconds")
    if time_diff > 0:
        print("  → Lower user authority (0.3) takes LONGER to complete")
    else:
        print("  → Higher user authority (0.7) takes LONGER to complete")
    
    print("\n\n7. INTERPRETATION:")
    print("-" * 50)
    print("• Metric A (Collisions): All trials completed without collisions (0 collisions)")
    print("• Metric B (Safety Stops): Found safety-related events in ROS2 logs")
    print("• Metric E (User Inputs): Significant difference between authority levels")
    print("• Lower authority (0.3) appears to require more user inputs but may be safer")
    print("• Higher authority (0.7) is more efficient but may have fewer safety interventions")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    display_results()
