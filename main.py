import warnings
warnings.simplefilter("ignore")

import sys
import os
from xueqiu_short_post_spider import XueqiuShortPostSpider
from xueqiu_long_post_spider import XueqiuLongPostSpider
from config import TYPE_PARAM, FILTER_REGEX

# 颜色常量
GREEN = '\033[32m'
YELLOW = '\033[33m'
RED = '\033[31m'
BLUE = '\033[34m'
RESET = '\033[0m'

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
                print(f"{BLUE}设定抓取前 {end_page} 页数据{RESET}")
        except ValueError:
            print(f"{RED}[-] 错误: 参数必须是数字{RESET}")
    elif len(sys.argv) >= 5:
        try:
            start_page = int(sys.argv[3])
            end_page = int(sys.argv[4])
            print(f"{BLUE}设定抓取范围: 第 {start_page} 页 到 第 {end_page} 页{RESET}")
        except ValueError:
            print(f"{RED}[-] 错误: 参数必须是数字{RESET}")

    # 构造生成的文件路径
    target_file = os.path.join("data", f"{username}.csv")

    # 如果不是仅分析模式 (-1)，则执行爬取
    if start_page != -1:
        if TYPE_PARAM == 2:
            print(f"\n{GREEN}[Step 1] 开始爬取雪球长贴(专栏): {username}({uid}) [API模式] ...{RESET}")
            spider = XueqiuLongPostSpider(username, uid, type_param=TYPE_PARAM, filter_regex=FILTER_REGEX)
        else:
            mode_desc = "原发" if TYPE_PARAM == 0 else "全部"
            print(f"\n{GREEN}[Step 1] 开始爬取雪球短贴({mode_desc}): {username}({uid}) [UI模式] ...{RESET}")
            spider = XueqiuShortPostSpider(username, uid, type_param=TYPE_PARAM, filter_regex=FILTER_REGEX)
            
        spider.run(start_page=start_page, end_page=end_page)
    
    if os.path.exists(target_file):
        print(f"\n{GREEN}[Step 2] 爬取完成！{RESET}")
    else:
        print(f"\n{RED}[-] 错误: 未能找到生成的数据文件 {target_file}。{RESET}")

if __name__ == "__main__":
    main()
