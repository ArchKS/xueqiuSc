import pandas as pd
import argparse
import os
import colorama
import re
from prettytable import PrettyTable
from datetime import datetime
from config import (
    TOP_STOCKS_COUNT, TOP_POSTS_COUNT, KEYWORDS_FILTER, FILTER_REGEX,
    DEFAULT_MIN_LIKES, DEFAULT_MIN_COMMENTS, DEFAULT_MIN_LENGTH,
    DEFAULT_SUPER_LIKES, DEFAULT_SUPER_COMMENTS, SHOW_ANALYSIS_REPORT
)

# 初始化 colorama 支持彩色输出
colorama.init(autoreset=True)
GREEN = colorama.Fore.GREEN
YELLOW = colorama.Fore.YELLOW
RED = colorama.Fore.RED
CYAN = colorama.Fore.CYAN
MAGENTA = colorama.Fore.MAGENTA
BLUE = colorama.Fore.BLUE
WHITE = colorama.Fore.WHITE
BOLD = colorama.Style.BRIGHT

def filter_csv(file_path, min_likes, min_comments, min_length, super_likes=None, super_comments=None):
    if not os.path.exists(file_path):
        print(f"{RED}[-] 错误: 文件 '{file_path}' 不存在。")
        return

    try:
        df = pd.read_csv(file_path, encoding='utf-8-sig')
    except UnicodeDecodeError:
        df = pd.read_csv(file_path, encoding='gb18030')

    original_count = len(df)
    if SHOW_ANALYSIS_REPORT:
        print(f"{CYAN}[*] 成功加载 {file_path}，共 {original_count} 条记录。{WHITE}")

    # 1. 数据基础清洗
    df['点赞数'] = pd.to_numeric(df['点赞数'], errors='coerce').fillna(0)
    df['评论数'] = pd.to_numeric(df['评论数'], errors='coerce').fillna(0)
    df['转发数'] = pd.to_numeric(df['转发数'], errors='coerce').fillna(0)
    df['正文'] = df['正文'].fillna('').astype(str)
    df['发布时间'] = pd.to_datetime(df['发布时间'], errors='coerce')
    
    # 0. 时间范围统计
    valid_dates = df['发布时间'].dropna()
    if not valid_dates.empty:
        start_date = valid_dates.min().strftime('%Y-%m-%d')
        end_date = valid_dates.max().strftime('%Y-%m-%d')
        time_range_str = f"{start_date} 至 {end_date}"
        days_diff = (valid_dates.max() - valid_dates.min()).days
        post_frequency = original_count / max(days_diff, 1)
    else:
        time_range_str = "未知"
        days_diff = 0
        post_frequency = 0

    # 2. 清理元数据与换行符
    pattern = r'(来自.*?的雪球专栏)?\s*(来源\s*[：:]\s*.*?)?作者\s*[：:]\s*.*?（https://xueqiu\.com/.*?）\s*'
    df['正文'] = df['正文'].str.replace(pattern, '', regex=True, flags=re.DOTALL)
    
    # 提取博主本人发文逻辑：
    # a. 处理转发链：保留第一个 //@ 之前的内容
    df['正文'] = df['正文'].apply(lambda x: re.split(r'\s*//\s*@', x, 1)[0].strip())
    
    # b. 处理回复前缀：移除开头的 "回复@xxx: "
    df['正文'] = df['正文'].str.replace(r'^回复\s*@.*?[：:]\s*', '', regex=True)
    
    # 移除正文中的所有换行符 (\n 和 \r)
    df['正文'] = df['正文'].str.replace(r'[\r\n]+', ' ', regex=True).str.strip()
    
    # 彻底清理可能残留的空格
    df['正文'] = df['正文'].str.strip()
    
    # 重新计算字数辅助列，因为上面的清洗可能会缩短正文长度
    df['字数'] = df['正文'].apply(len)
    
    if SHOW_ANALYSIS_REPORT:
        # 3. 计算深度与影响力指标
        avg_len = df['字数'].mean()
        median_len = df['字数'].median()
        long_article_count = len(df[df['字数'] > 1000])
        long_article_ratio = (long_article_count / original_count) * 100

        avg_likes = df['点赞数'].mean()
        median_likes = df['点赞数'].median()
        engagement_efficiency = (df['点赞数'].sum() / df['字数'].sum()) * 1000 if df['字数'].sum() > 0 else 0

        # 4. 风格统计：提取提及的股票
        stock_pattern = r'\$([^$()]+)(?:\(([^$]+)\))?\$'
        all_stocks = []
        for text in df['正文']:
            matches = re.findall(stock_pattern, text)
            for m in matches:
                all_stocks.append(m[0].strip())
        stock_counts = pd.Series(all_stocks).value_counts().head(TOP_STOCKS_COUNT)

        # 5. 输出综合分析报告
        header = f" {BOLD}{CYAN}[ 雪球数据综合分析报告: {os.path.basename(file_path)} ]{WHITE} "
        print("\n" + f"{CYAN}═{WHITE}" * 70)
        print(f" {header.center(75)} ")
        print(f"{CYAN}═{WHITE}" * 70)
        print(f"  {YELLOW}[*]{WHITE} 分析范围: {GREEN}{time_range_str}{WHITE} ({days_diff}天)")
        print(f"  {YELLOW}[*]{WHITE} 总发言数: {GREEN}{original_count}{WHITE} 篇 (约 {GREEN}{post_frequency:.2f}{WHITE} 篇/天)")
        print(f"{CYAN}-{WHITE}" * 70)

        print(f"\n{MAGENTA}[ 1. 内容深度与影响力 ]{WHITE}")
        print(f"  + 平均字数: {avg_len:.1f} | 字数中位数: {median_len:.1f}")
        print(f"  + 千字长文: {long_article_count} 篇 (占比 {long_article_ratio:.1f}%)")
        print(f"  + 平均点赞: {avg_likes:.1f} | 点赞中位数: {median_likes:.1f}")
        print(f"  + 互动效率: {engagement_efficiency:.2f} 次点赞/每千字")
        
        status_label = f'{CYAN}深度型选手{WHITE}' if long_article_ratio > 10 else f'{YELLOW}短评/碎片化选手{WHITE}'
        influence_label = f'{CYAN}高质量博主{WHITE}' if avg_likes > 20 else f'{YELLOW}普通用户{WHITE}'
        print(f"  {RED}[!] 用户画像: >>> {status_label} | {influence_label} {RED}<<<{WHITE}")

        print(f"\n{MAGENTA}[ 2. 数据分布情况 ]{WHITE}")
        def print_dist(series, label):
            print(f"\n{YELLOW}>> {label} 分布:{WHITE}")
            if label == "正文字数":
                custom_bins = [-1, 20, 100, 300, 1000, float('inf')]
                custom_labels = ["0 - 20", "21 - 100", "101 - 300", "301 - 1000", "1000+"]
            else:
                custom_bins = [-1, 20, 100, 300, float('inf')]
                custom_labels = ["0 - 20", "21 - 100", "101 - 300", "300+"]
            
            bins = pd.cut(series, bins=custom_bins, labels=custom_labels)
            dist = bins.value_counts().sort_index()
            for interval_label, count in dist.items():
                pct = (count / len(series)) * 100
                bar = "■" * int(pct / 2)
                print(f"   {str(interval_label).ljust(12)} | {count:4d} 篇 ({pct:4.1f}%) {bar}")

        print_dist(df['点赞数'], "点赞数")
        print_dist(df['评论数'], "评论数")
        print_dist(df['字数'], "正文字数")

        if not stock_counts.empty:
            print(f"\n{MAGENTA}[ 3. 关注领域 (TOP {TOP_STOCKS_COUNT}) ]{WHITE}")
            table = PrettyTable()
            table.field_names = ["序号", "标的名称", "提及次数"]
            for i, (stock, count) in enumerate(stock_counts.items(), 1):
                table.add_row([f"{YELLOW}{i}{WHITE}", f"{GREEN}{stock}{WHITE}", f"{CYAN}{count}{WHITE}"])
            print(table)

        long_posts = df[df['字数'] > 1000].copy()
        if not long_posts.empty:
            print(f"\n{MAGENTA}[ 4. 千字长文清单 ]{WHITE}")
            table = PrettyTable()
            table.field_names = ["序号", "点赞", "评论", "转发", "预览 (前25字)", "链接"]
            table.align["预览 (前25字)"] = "l"
            for i, (idx, row) in enumerate(long_posts.iterrows(), 1):
                preview = row['正文'][:25]
                table.add_row([
                    f"{YELLOW}{i}{WHITE}", f"{int(row['点赞数'])}", f"{int(row['评论数'])}", 
                    f"{int(row['转发数'])}", f"{GREEN}{preview}...{WHITE}", f"{BLUE}{row['链接']}{WHITE}"
                ])
            print(table)

        print(f"\n" + f"{CYAN}═{WHITE}" * 70 + "\n")

    # 6. ID 去重逻辑 (优先保留正文最长的版本)

    # 先按照 ID 和字数降序排序
    df = df.sort_values(by=['ID', '字数'], ascending=[True, False])
    # 标记重复项 (除了第一项/最长项以外的所有重复项)
    same_mask = df.duplicated(subset=['ID'], keep='first')
    
    same_df = df[same_mask].copy() # 被去重的项
    df_unique = df[~same_mask].copy() # 唯一项 (用于后续过滤)

    # 7. 应用过滤逻辑 (在去重后的数据上进行)
    pass_normal = (df_unique['点赞数'] >= min_likes) & (df_unique['评论数'] >= min_comments) & (df_unique['字数'] >= min_length)
    pass_super_likes = (df_unique['点赞数'] >= super_likes) if super_likes is not None else False
    pass_super_comments = (df_unique['评论数'] >= super_comments) if super_comments is not None else False
    pass_filter_regex = pd.Series(False, index=df_unique.index)
    
    # 关键词过滤逻辑：支持多组匹配，英文忽略大小写
    pass_keywords = pd.Series(False, index=df_unique.index)
    keyword_group_results = [] # 存储 (df, group_name)

    if FILTER_REGEX:
        body_regex = '|'.join(f"(?:{pattern})" for pattern in FILTER_REGEX if pattern)
        if body_regex:
            # 命中 FILTER_REGEX 的正文会被排除，不进入保留结果
            pass_filter_regex = df_unique['正文'].str.contains(body_regex, case=False, na=False, regex=True)

    if KEYWORDS_FILTER:
        for group_name, keywords in KEYWORDS_FILTER.items():
            if not keywords: continue
            # 拼接组内关键词正则表达式
            pattern = '|'.join([re.escape(str(k)) for k in keywords])
            # case=False 实现忽略大小写
            mask = df_unique['正文'].str.contains(pattern, case=False, na=False)
            pass_keywords = pass_keywords | mask
            
            if mask.any():
                kw_df = df_unique[mask].copy()
                # 预先清理辅助列
                for col in ['字数', '摘要']:
                    if col in kw_df.columns:
                        kw_df.drop(columns=[col], inplace=True, errors='ignore')
                keyword_group_results.append((kw_df, group_name))
    
    condition = (pass_normal | pass_super_likes | pass_super_comments | pass_keywords) & (~pass_filter_regex)
    
    filtered_df = df_unique[condition].copy()
    rejected_df = df_unique[~condition].copy() 
    
    # 移除辅助列并准备保存
    for temp_df in [filtered_df, rejected_df, same_df]:
        if temp_df.empty: continue
        if '字数' in temp_df.columns:
            temp_df.drop(columns=['字数'], inplace=True, errors='ignore')
        if '摘要' in temp_df.columns:
            temp_df.drop(columns=['摘要'], inplace=True, errors='ignore')
    
    output_dir = "filter"
    if not os.path.exists(output_dir): os.makedirs(output_dir)

    base_name = os.path.basename(file_path)
    name, ext = os.path.splitext(base_name)
    
    suffix_parts = []
    if min_likes > 0: suffix_parts.append(f"L{min_likes}")
    if min_comments > 0: suffix_parts.append(f"C{min_comments}")
    if min_length > 0: suffix_parts.append(f"Len{min_length}")
    if super_likes: suffix_parts.append(f"SL{super_likes}")
    if super_comments: suffix_parts.append(f"SC{super_comments}")
    suffix = "_" + "_".join(suffix_parts) if suffix_parts else "_all"

    # 保存 1: 满足条件的唯一记录
    if not filtered_df.empty:
        p = os.path.join(output_dir, f"{name}_filter{suffix}{ext}")
        filtered_df.to_csv(p, index=False, encoding='utf-8-sig')
        print(f"{GREEN}[+] 保留 {len(filtered_df)} 条唯一记录。保存至: {p}")

    # 保存 2: 被过滤条件剔除的唯一记录
    if not rejected_df.empty:
        p = os.path.join(output_dir, f"{name}_rejected{suffix}{ext}")
        rejected_df.to_csv(p, index=False, encoding='utf-8-sig')
        print(f"{RED}[-] 剔除 {len(rejected_df)} 条不合规记录。保存至: {p}")

    # 保存 3: 被去重逻辑剔除的项 (Same ID, 但正文较短)
    if not same_df.empty:
        p = os.path.join(output_dir, f"{name}_same{suffix}{ext}")
        same_df.to_csv(p, index=False, encoding='utf-8-sig')
        if SHOW_ANALYSIS_REPORT:
            print(f"{YELLOW}[!] 发现 {len(same_df)} 条重复 ID 项 (已保留最长正文版本)。重复项保存至: {p}{WHITE}")

    # 保存 4: 为每一组关键词单独保存文件
    for kw_df, kw_str in keyword_group_results:
        p = os.path.join(output_dir, f"{name}_KW_{kw_str}{ext}")
        kw_df.to_csv(p, index=False, encoding='utf-8-sig')
        print(f"{CYAN}[+] 关键词组 [{kw_str}] 匹配成功：{len(kw_df)} 条命中。保存至: {p}{WHITE}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="雪球帖子数据综合过滤与分析工具")
    parser.add_argument("file", help="CSV 文件路径")
    parser.add_argument("-l", "--likes", type=int, default=DEFAULT_MIN_LIKES)
    parser.add_argument("-c", "--comments", type=int, default=DEFAULT_MIN_COMMENTS)
    parser.add_argument("-len", "--length", type=int, default=DEFAULT_MIN_LENGTH)
    parser.add_argument("-sl", "--super-likes", type=int, default=DEFAULT_SUPER_LIKES)
    parser.add_argument("-sc", "--super-comments", type=int, default=DEFAULT_SUPER_COMMENTS)
    args = parser.parse_args()
    filter_csv(args.file, args.likes, args.comments, args.length, args.super_likes, args.super_comments)
