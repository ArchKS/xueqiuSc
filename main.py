import sys
import os
from xueqiu_drission import XueqiuDrissionSpider
from analyze_user import analyze_user_level

# ================= 配置区 =================
# 分析配置
TOP_STOCKS_COUNT = 8  # 关注领域显示的股票数量
TOP_POSTS_COUNT = 5   # 最火爆发言显示的条数
# ==========================================

def main():
    # 强制控制台输出使用 UTF-8，防止中文和特殊符号乱码
    if sys.platform.startswith('win'):
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    if len(sys.argv) < 3:
        print("用法: python main.py <用户名> <用户ID> [最大页数]")
        print("示例 (爬取全部): python main.py KeepSlowly 2287364713")
        print("示例 (爬取2页): python main.py KeepSlowly 2287364713 2")
        return

    username = sys.argv[1]
    uid = sys.argv[2]
    max_pages = None
    
    if len(sys.argv) >= 4:
        try:
            max_pages = int(sys.argv[3])
            if max_pages == -1:
                print("[*] 检测到 -1，跳过爬取阶段，直接分析现有数据。")
            else:
                print(f"[*] 设定最大爬取页数为: {max_pages}")
        except ValueError:
            print("[-] 错误: 最大页数必须是数字。将默认爬取所有页。")

    # 构造生成的文件路径
    target_file = os.path.join("data", f"xueqiu_full_{username}.csv")

    # 如果不是仅分析模式 (-1)，则执行爬取
    if max_pages != -1:
        print(f"\n[Step 1] 开始爬取用户 {username}({uid}) 的数据...")
        spider = XueqiuDrissionSpider(username, uid)
        spider.run(max_pages=max_pages)
    
    if os.path.exists(target_file):
        print(f"\n[Step 2] 爬取完成，开始分析数据...")
        analyze_user_level(
            target_file, 
            top_stocks_count=TOP_STOCKS_COUNT, 
            top_posts_count=TOP_POSTS_COUNT
        )
    else:
        print(f"\n[-] 错误: 未能找到生成的数据文件 {target_file}，分析取消。")

if __name__ == "__main__":
    main()
