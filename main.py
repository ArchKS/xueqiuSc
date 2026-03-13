import sys
import os
from xueqiu_drission import XueqiuDrissionSpider
from analyze_user import analyze_user_level

# ================= 配置区 =================
# 分析配置
TOP_STOCKS_COUNT = 20  # 关注领域显示的股票数量
TOP_POSTS_COUNT = 10   # 最火爆发言显示的条数
# 爬取配置
IS_ORIGINAL_POST = True  # 是否原发，True 表示只抓取原发 (type=0)，False 表示包含转发 (不添加 type 参数)
# 正则过滤列表：匹配到则不保存该条记录（用于过滤系统通知类型内容）
# 注意：每条正则会应用于帖子标题/正文前缀，不区分大小写
FILTER_REGEX = [
    r"^我刚刚关注了股票",
    r"^我刚刚调整了雪球组合",
]
# ==========================================

def main():
    # 强制控制台输出使用 UTF-8，防止中文和特殊符号乱码
    if sys.platform.startswith('win'):
        import io
        # 增加 line_buffering=True 解决 Windows 下输出缓存导致的延迟显示问题
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)

    if len(sys.argv) < 3:
        print("用法: python main.py <用户名> <用户ID> [最大页数] 或 [开始页] [结束页]")
        print("示例 (爬取全部): python main.py KeepSlowly 2287364713")
        print("示例 (前5页): python main.py KeepSlowly 2287364713 5")
        print("示例 (第3-10页): python main.py KeepSlowly 2287364713 3 10")
        print("示例 (仅分析): python main.py KeepSlowly 2287364713 -1")
        return

    username = sys.argv[1]
    uid = sys.argv[2]
    start_page = 1
    end_page = None
    
    # 解析分页逻辑
    if len(sys.argv) == 4:
        try:
            val = int(sys.argv[3])
            if val == -1:
                start_page = -1 # 仅分析标志
            else:
                end_page = val
                print(f"设定抓取前 {end_page} 页数据")
        except ValueError:
            print("[-] 错误: 参数必须是数字")
    elif len(sys.argv) >= 5:
        try:
            start_page = int(sys.argv[3])
            end_page = int(sys.argv[4])
            print(f"设定抓取范围: 第 {start_page} 页 到 第 {end_page} 页")
        except ValueError:
            print("[-] 错误: 参数必须是数字")

    # 构造生成的文件路径
    target_file = os.path.join("data", f"xueqiu_full_{username}.csv")

    # 如果不是仅分析模式 (-1)，则执行爬取
    if start_page != -1:
        print(f"\n[Step 1] 开始爬取用户 {username}({uid}) 的数据...")
        type_value = 0 if IS_ORIGINAL_POST else None
        spider = XueqiuDrissionSpider(username, uid, type_param=type_value, filter_regex=FILTER_REGEX)
        spider.run(start_page=start_page, end_page=end_page)
    
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
