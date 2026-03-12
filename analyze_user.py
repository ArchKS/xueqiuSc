import pandas as pd
import re
import os
from datetime import datetime

def analyze_user_level(file_path, top_stocks_count=5, top_posts_count=3):
    if not os.path.exists(file_path):
        print(f"[-] 错误: 文件 {file_path} 不存在。请先运行爬虫。")
        return

    # 读取数据
    try:
        df = pd.read_csv(file_path, encoding='utf-8-sig')
    except UnicodeDecodeError:
        # 如果 utf-8-sig 失败，尝试 gb18030 (比 gbk 支持更多字符)
        df = pd.read_csv(file_path, encoding='gb18030')
    
    # 基础清洗：确保数据类型正确
    df['点赞数'] = pd.to_numeric(df['点赞数'], errors='coerce').fillna(0)
    df['评论数'] = pd.to_numeric(df['评论数'], errors='coerce').fillna(0)
    df['转发数'] = pd.to_numeric(df['转发数'], errors='coerce').fillna(0)
    df['正文'] = df['正文'].astype(str)
    df['发布时间'] = pd.to_datetime(df['发布时间'], errors='coerce')
    
    # 0. 时间范围统计
    valid_dates = df['发布时间'].dropna()
    if not valid_dates.empty:
        start_date = valid_dates.min().strftime('%Y-%m-%d')
        end_date = valid_dates.max().strftime('%Y-%m-%d')
        time_range_str = f"{start_date} 至 {end_date}"
        days_diff = (valid_dates.max() - valid_dates.min()).days
        post_frequency = len(df) / max(days_diff, 1)
    else:
        time_range_str = "未知"
        post_frequency = 0

    # 1. 深度统计 (Content Depth)
    df['字数'] = df['正文'].apply(len)
    avg_len = df['字数'].mean()
    median_len = df['字数'].median()
    long_article_count = len(df[df['字数'] > 1000])
    long_article_ratio = (long_article_count / len(df)) * 100

    # 2. 影响力统计 (Influence)
    total_engagements = df['点赞数'].sum() + df['评论数'].sum() + df['转发数'].sum()
    avg_likes = df['点赞数'].mean()
    median_likes = df['点赞数'].median()
    
    # 3. 互动效率 (每千字获得的点赞)
    engagement_efficiency = (df['点赞数'].sum() / df['字数'].sum()) * 1000 if df['字数'].sum() > 0 else 0

    # 4. 风格统计：提取提及的股票 (雪球特征: $股票名称(代码)$ 或 $代码$)
    stock_pattern = r'\$([^$()]+)(?:\(([^$]+)\))?\$'
    all_stocks = []
    for text in df['正文']:
        matches = re.findall(stock_pattern, text)
        for m in matches:
            all_stocks.append(m[0].strip())
    
    stock_counts = pd.Series(all_stocks).value_counts().head(top_stocks_count)

    # 5. 输出结果报告
    header = f" 📊 USER ANALYSIS REPORT: {os.path.basename(file_path)} "
    print("\n" + "═" * 60)
    print(f" {header.center(58)} ")
    print("═" * 60)
    print(f"  � 分析范围: {time_range_str} ({days_diff}天)")
    print(f"  📝 总发言数: {len(df)} 篇 (约 {post_frequency:.2f} 篇/天)")
    print("-" * 60)

    print(f"\n[ 1. 内容深度 / 📚 CONTENT DEPTH ]")
    print(f"  + 平均字数: {avg_len:.1f}")
    print(f"  + 字数中位数: {median_len:.1f}")
    print(f"  + 千字长文: {long_article_count} 篇 (占比 {long_article_ratio:.1f}%)")
    status_label = '深度型选手 🧠' if long_article_ratio > 10 else '短评/碎片化选手 ⚡'
    print(f"  [!] 用户画像: >>> {status_label} <<<")

    print(f"\n[ 2. 社区影响力 / 🔥 INFLUENCE ]")
    print(f"  + 平均点赞: {avg_likes:.1f}")
    print(f"  + 点赞中位数: {median_likes:.1f}")
    print(f"  + 互动效率: {engagement_efficiency:.2f} 次点赞/每千字")
    influence_label = '高质量博主 🏆' if avg_likes > 20 else '普通用户 👤'
    print(f"  [!] 影响力评级: >>> {influence_label} <<<")

    print(f"\n[ 3. 关注领域 / 🎯 TOP {top_stocks_count} STOCKS ]")
    print("-" * 30)
    if not stock_counts.empty:
        for i, (stock, count) in enumerate(stock_counts.items(), 1):
            bar = "📈" * min(int(count), 10) # 使用趋势图 Emoji 作为条形图
            print(f"  {i}. {str(stock).ljust(12)} | {str(count).rjust(3)} 次 {bar}")
    else:
        print("  (未提取到明确的股票提及)")

    print(f"\n[ 4. 最火爆的 {top_posts_count} 篇发言 / 🌟 TOP POSTS ]")
    print("-" * 30)
    top_n = df.nlargest(top_posts_count, '点赞数')[['发布时间', '点赞数', '摘要']]
    for i, row in top_n.iterrows():
        time_str = row['发布时间'].strftime('%Y-%m-%d') if pd.notnull(row['发布时间']) else "未知时间"
        print(f"  ({i+1}) 📅 [{time_str}] ❤️ {int(row['点赞数'])} Likes")
        print(f"      \"{str(row['摘要'])[:300]}...\"")
        print()

    print("═" * 60 + "\n")

if __name__ == "__main__":
    import sys
    
    # 支持从命令行指定文件名：python analyze_user.py <文件名>
    if len(sys.argv) > 1:
        target_file = sys.argv[1]
    else:
        # 默认分析示例用户
        USERNAME = "KeepSlowly"
        target_file = os.path.join("data", f"xueqiu_full_{USERNAME}.csv")
    
    print(f"[*] 正在分析文件: {target_file}")
    
    # 默认配置
    analyze_user_level(target_file, top_stocks_count=8, top_posts_count=5)
