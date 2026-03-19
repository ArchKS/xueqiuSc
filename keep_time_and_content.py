import pandas as pd
import os
import glob
import argparse

def process_file(file_path):
    """
    读取CSV文件，仅保留'发布时间'和'正文'列，并在同级目录保存结果。
    """
    if not os.path.exists(file_path):
        print(f"错误: 文件 '{file_path}' 不存在。")
        return

    file_dir = os.path.dirname(file_path)
    file_name = os.path.basename(file_path)
    output_name = file_name.replace('.csv', '_time_content.csv')
    output_path = os.path.join(file_dir, output_name)
    
    print(f"正在处理: {file_name}...")
    
    try:
        # 尝试不同的编码读取
        try:
            df = pd.read_csv(file_path, encoding='utf-8-sig')
        except UnicodeDecodeError:
            df = pd.read_csv(file_path, encoding='gb18030')

        # 检查列是否存在
        columns_to_keep = []
        if '发布时间' in df.columns:
            columns_to_keep.append('发布时间')
        elif '时间' in df.columns:
            columns_to_keep.append('时间')
        
        if '正文' in df.columns:
            columns_to_keep.append('正文')

        if len(columns_to_keep) < 2:
            print(f"警告: 文件 {file_name} 缺少必要的列 (发布时间/正文)。跳过。")
            return

        # 仅保留需要的列
        df_filtered = df[columns_to_keep]

        # 保存结果
        df_filtered.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"成功保存到: {output_path}")

    except Exception as e:
        print(f"处理 {file_name} 时出错: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="只保留CSV文件的'发布时间'和'正文'列。")
    parser.add_argument("files", nargs="*", help="要处理的CSV文件路径（支持多个）")
    
    args = parser.parse_args()

    if not args.files:
        # 如果没有指定文件，则默认处理 data/ 目录下的所有 csv
        print("未指定文件，默认处理 data/*.csv ...")
        csv_files = glob.glob(os.path.join('data', '*.csv'))
        for f in csv_files:
            process_file(f)
    else:
        for f in args.files:
            process_file(f)
