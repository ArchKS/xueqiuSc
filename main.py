import warnings
warnings.simplefilter("ignore")

import sys
import os
import io
from xueqiu_short_post_spider import XueqiuShortPostSpider
from xueqiu_long_post_spider import XueqiuLongPostSpider
from config import TYPE_PARAM, FILTER_REGEX

# 颜色常量
GREEN = '\033[32m'
YELLOW = '\033[33m'
RED = '\033[31m'
BLUE = '\033[34m'
RESET = '\033[0m'


class TeeStream:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for stream in self.streams:
            stream.write(data)
        return len(data)

    def flush(self):
        for stream in self.streams:
            stream.flush()

    def isatty(self):
        return any(getattr(stream, 'isatty', lambda: False)() for stream in self.streams)


def setup_logging():
    if getattr(setup_logging, "_initialized", False):
        return getattr(setup_logging, "_log_file", None)

    if sys.platform.startswith('win'):
        console_stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
        console_stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', line_buffering=True)
    else:
        console_stdout = sys.stdout
        console_stderr = sys.stderr

    setup_logging._console_stdout = console_stdout
    setup_logging._console_stderr = console_stderr

    log_path = os.path.join(os.getcwd(), "log.txt")
    if os.path.exists(log_path):
        os.remove(log_path)
    log_file = open(log_path, "w", encoding="utf-8", buffering=1)

    sys.stdout = TeeStream(console_stdout, log_file)
    sys.stderr = TeeStream(console_stderr, log_file)

    setup_logging._initialized = True
    setup_logging._log_file = log_file
    return log_file


def teardown_logging():
    if not getattr(setup_logging, "_initialized", False):
        return

    log_file = getattr(setup_logging, "_log_file", None)
    current_stdout = sys.stdout
    current_stderr = sys.stderr

    try:
        if current_stdout:
            current_stdout.flush()
    except Exception:
        pass

    try:
        if current_stderr:
            current_stderr.flush()
    except Exception:
        pass

    sys.stdout = getattr(setup_logging, "_console_stdout", sys.__stdout__)
    sys.stderr = getattr(setup_logging, "_console_stderr", sys.__stderr__)

    if log_file:
        try:
            log_file.flush()
        except Exception:
            pass
        try:
            log_file.close()
        except Exception:
            pass

    setup_logging._initialized = False
    setup_logging._log_file = None

def main():
    setup_logging()

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
    setup_logging()
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{YELLOW}[!] 已收到 Ctrl+C，任务已中断。{RESET}")
    finally:
        teardown_logging()
