import pandas as pd
import re
import os
from datetime import datetime

def analyze_user_level(file_path):
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
    
    stock_counts = pd.Series(all_stocks).value_counts().head(5)

    # 5. 输出结果报告
    print("\n" + "="*50)
    print(f"📊 雪球用户投资水平分析报告")
    print(f"分析文件: {os.path.basename(file_path)}")
    print(f"总发言数: {len(df)} 篇")
    print("="*50)

    print(f"\n[1. 内容深度]")
    print(f" - 平均字数: {avg_len:.1f}")
    print(f" - 字数中位数: {median_len:.1f}")
    print(f" - 千字长文数: {long_article_count} (占比 {long_article_ratio:.1f}%)")
    print(f"   💡 {'深度型选手' if long_article_ratio > 10 else '短评/碎片化选手'}")

    print(f"\n[2. 社区影响力]")
    print(f" - 平均点赞: {avg_likes:.1f}")
    print(f" - 点赞中位数: {median_likes:.1f}")
    print(f" - 互动效率: {engagement_efficiency:.2f} 次点赞/每千字")
    print(f"   💡 {'高质量博主' if avg_likes > 20 else '普通用户'}")

    print(f"\n[3. 关注领域 (Top 5 提及次数)]")
    if not stock_counts.empty:
        for stock, count in stock_counts.items():
            print(f" - {stock}: {count} 次")
    else:
        print(" - 未提取到明确的股票提及")

    print(f"\n[4. 最火爆的 3 篇发言]")
    top_3 = df.nlargest(3, '点赞数')[['发布时间', '点赞数', '摘要']]
    for i, row in top_3.iterrows():
        time_str = row['发布时间'].strftime('%Y-%m-%d') if pd.notnull(row['发布时间']) else "未知时间"
        print(f" - [{time_str}] 点赞:{int(row['点赞数'])} | {str(row['摘要'])[:60]}...")

    print("\n" + "="*50)

if __name__ == "__main__":
    # 默认分析最后一次爬取的用户（可以手动修改路径）
    USER_ID = "2287364713"
    target_file = f"xueqiu_full_{USER_ID}.csv"
    
    # 如果全量文件没生成，尝试找基础文件
    if not os.path.exists(target_file):
        target_file = f"xueqiu_drission_{USER_ID}.csv"
        
    analyze_user_level(target_file)
