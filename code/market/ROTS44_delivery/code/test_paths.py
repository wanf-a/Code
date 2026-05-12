#!/usr/bin/env python3
"""
test_paths.py — 测试路径配置是否正确
运行: cd ROTS44_delivery/code && python test_paths.py
"""
import os
import sys

def test_paths():
    """测试所有关键路径是否存在"""
    print("=" * 70)
    print("  路径配置测试")
    print("=" * 70)
    
    # 计算基础路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    delivery_dir = os.path.dirname(script_dir)
    project_root = os.path.dirname(delivery_dir)
    case_dir = os.path.join(project_root, 'Case', 'ROTS 44')
    output_dir = os.path.join(delivery_dir, 'ROTS 44')
    
    print(f"\n当前脚本: {__file__}")
    print(f"脚本目录: {script_dir}")
    print(f"交付目录: {delivery_dir}")
    print(f"项目根目录: {project_root}")
    print(f"数据源目录: {case_dir}")
    print(f"输出目录: {output_dir}")
    
    # 检查关键路径
    paths_to_check = {
        "数据源目录 (Case)": case_dir,
        "标准算例文件": os.path.join(case_dir, "标准算例-JPES-ROTS-44.xlsm"),
        "Input 目录": os.path.join(case_dir, "Input"),
        "Output 目录": os.path.join(case_dir, "Output"),
        "交付代码目录": script_dir,
        "策略配置文件": os.path.join(script_dir, "strategy_config.ini"),
        "输出根目录": output_dir,
    }
    
    print("\n" + "=" * 70)
    print("  关键路径检查")
    print("=" * 70)
    
    all_ok = True
    for name, path in paths_to_check.items():
        exists = os.path.exists(path)
        status = "✓" if exists else "✗"
        print(f"{status} {name:20s}: {path}")
        if not exists:
            all_ok = False
    
    # 检查数据文件
    data_files = [
        "summary_timeseries.csv",
        "summary_daily.csv",
        "summary_revenue.csv",
    ]
    
    print("\n" + "=" * 70)
    print("  数据文件检查")
    print("=" * 70)
    
    for filename in data_files:
        # 优先检查输出目录（summary_data.py 生成）
        output_path = os.path.join(output_dir, filename)
        case_path = os.path.join(case_dir, filename)
        
        if os.path.exists(output_path):
            status = "✓"
            location = "输出目录"
            path = output_path
        elif os.path.exists(case_path):
            status = "○"
            location = "Case目录"
            path = case_path
        else:
            status = "✗"
            location = "不存在"
            path = f"{output_path} 或 {case_path}"
        
        print(f"{status} {filename:30s} ({location})")
        if status != "✗":
            print(f"   → {path}")
    
    # 检查 Input 子目录
    input_dir = os.path.join(case_dir, "Input")
    if os.path.exists(input_dir):
        input_days = sorted([d for d in os.listdir(input_dir) if d.startswith('2026')])
        print(f"\n  Input 目录包含 {len(input_days)} 天数据")
        if input_days:
            print(f"  范围: {input_days[0]} ~ {input_days[-1]}")
    
    # 检查 Output 子目录
    output_dir_case = os.path.join(case_dir, "Output")
    if os.path.exists(output_dir_case):
        output_days = sorted([d for d in os.listdir(output_dir_case) if d.startswith('2026')])
        print(f"\n  Output 目录包含 {len(output_days)} 天数据")
        if output_days:
            print(f"  范围: {output_days[0]} ~ {output_days[-1]}")
    
    # 检查输出目录
    print(f"\n  输出目录: {output_dir}")
    if os.path.exists(output_dir):
        print(f"  ✓ 输出目录已存在")
        subdirs = [d for d in os.listdir(output_dir) if os.path.isdir(os.path.join(output_dir, d))]
        if subdirs:
            print(f"  子目录: {', '.join(subdirs)}")
    else:
        print(f"  ○ 输出目录不存在（运行脚本后会自动创建）")
    
    # 总结
    print("\n" + "=" * 70)
    if all_ok:
        print("  ✓ 所有关键路径配置正确！")
        print("\n  数据文件说明:")
        print("  - summary_*.csv 文件由 summary_data.py 生成")
        print("  - 运行: python summary_data.py")
        print("  - 输出到: ROTS44_delivery/ROTS 44/")
        print("\n  可以开始运行脚本")
    else:
        print("  ✗ 部分路径不存在，请检查项目结构")
        print("  确保 ROTS44_delivery 和 Case 在同一父目录下")
    print("=" * 70)
    
    return all_ok

if __name__ == '__main__':
    success = test_paths()
    sys.exit(0 if success else 1)
