import pandas as pd
import os
import glob
import argparse

def process_file(file_path):
    """
    读取CSV文件，保留'发布时间'和'正文'列。
    1. 保存原序版 (_time_content.csv)
    2. 保存根据转赞评总数降序排列版 (_top_engagement.csv)
    """
    if not os.path.exists(file_path):
        print(f"错误: 文件 '{file_path}' 不存在。")
        return

    file_dir = os.path.dirname(file_path)
    file_name = os.path.basename(file_path)
    
    print(f"正在处理: {file_name}...")
    
    try:
        # 尝试不同的编码读取
        try:
            df = pd.read_csv(file_path, encoding='utf-8-sig')
        except UnicodeDecodeError:
            df = pd.read_csv(file_path, encoding='gb18030')

        # 检查必要的显示列是否存在
        display_cols = []
        if '发布时间' in df.columns:
            display_cols.append('发布时间')
        elif '时间' in df.columns:
            display_cols.append('时间')
        
        if '正文' in df.columns:
            display_cols.append('正文')

        if len(display_cols) < 2:
            print(f"警告: 文件 {file_name} 缺少必要的显示列 (发布时间/正文)。跳过。")
            return

        # 1. 保存原序版
        output_path_original = os.path.join(file_dir, file_name.replace('.csv', '_time_content.csv'))
        df[display_cols].to_csv(output_path_original, index=False, encoding='utf-8-sig')
        print(f"成功保存原序版到: {output_path_original}")

        # 2. 计算互动量并保存排序版
        engagement_cols = ['点赞数', '评论数', '转发数']
        available_engagement = [c for c in engagement_cols if c in df.columns]
        
        # 定义排序版需要保留的列并调整顺序：时间, 转赞评, 链接, 正文
        sorted_display_cols = []
        if '发布时间' in df.columns:
            sorted_display_cols.append('发布时间')
        elif '时间' in df.columns:
            sorted_display_cols.append('时间')
            
        # 添加互动数据列
        for col in available_engagement:
            sorted_display_cols.append(col)
            
        # 添加链接
        if '链接' in df.columns:
            sorted_display_cols.append('链接')
            
        # 最后添加正文
        if '正文' in df.columns:
            sorted_display_cols.append('正文')

        if available_engagement:
            # 复制一份用于计算，不破坏原 df
            df_calc = df.copy()
            for col in available_engagement:
                df_calc[col] = pd.to_numeric(df_calc[col], errors='coerce').fillna(0)
            
            df_calc['total_engagement'] = df_calc[available_engagement].sum(axis=1)
            
            # 根据总互动量降序排列
            df_sorted = df_calc.sort_values(by='total_engagement', ascending=False)
            
            output_path_sorted = os.path.join(file_dir, file_name.replace('.csv', '_top_engagement.csv'))
            df_sorted[sorted_display_cols].to_csv(output_path_sorted, index=False, encoding='utf-8-sig')
            print(f"成功保存排序版到: {output_path_sorted}")
        else:
            print(f"提示: {file_name} 缺少互动量列，无法生成排序版。")

    except Exception as e:
        print(f"处理 {file_name} 时出错: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="只保留CSV文件的'发布时间'和'正文'列，并生成排序版。")
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
