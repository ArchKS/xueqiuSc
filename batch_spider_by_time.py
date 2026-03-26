import sys
import os
import time
import re
import json
import random
from datetime import datetime, timedelta
import pandas as pd
import colorama
from xueqiu_short_post_spider import XueqiuShortPostSpider
from xueqiu_long_post_spider import XueqiuLongPostSpider
import config
from config import (
    TYPE_PARAM, FILTER_REGEX, USER_LIST, TIME_CONFIG,
    DEFAULT_MIN_LIKES, DEFAULT_MIN_COMMENTS, DEFAULT_MIN_LENGTH,
    DEFAULT_SUPER_LIKES, DEFAULT_SUPER_COMMENTS, DEFAULT_SUPER_LENGTH
)

# 强制在此脚本中只使用一个 Worker (单 Tab 模式)，避免批量爬取时开启过多页面
config.MAX_WORKERS = 1

# 初始化 colorama
colorama.init(autoreset=True)
GREEN = colorama.Fore.GREEN
YELLOW = colorama.Fore.YELLOW
RED = colorama.Fore.RED
BLUE = colorama.Fore.BLUE
CYAN = colorama.Fore.CYAN
MAGENTA = colorama.Fore.MAGENTA
BOLD = colorama.Style.BRIGHT
RESET = colorama.Style.RESET_ALL

# 获取当前时间用于日志文件名
current_time_str = datetime.now().strftime('%Y%m%d_%H%M%S')
error_log_file = f"error_{current_time_str}.log"

def log_error(message):
    with open(error_log_file, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - ERROR - {message}\n")

def clean_content(text):
    """按照 filter_csv.py 中的方式清洗正文内容"""
    if not text:
        return ""
    
    # 1. 清理元数据 (雪球专栏作者信息等)
    pattern = r'(来自.*?的雪球专栏)?\s*(来源\s*[：:]\s*.*?)?作者\s*[：:]\s*.*?（https://xueqiu\.com/.*?）\s*'
    text = re.sub(pattern, '', text, flags=re.DOTALL)
    
    # 2. 处理转发链：保留第一个 //@ 之前的内容
    text = re.split(r'\s*//\s*@', text, 1)[0].strip()
    
    # 3. 处理回复前缀：移除开头的 "回复@xxx: "
    text = re.sub(r'^回复\s*@.*?[：:]\s*', '', text)
    
    # 4. 移除正文中的所有换行符 (\n 和 \r)，替换为空格
    text = re.sub(r'[\r\n]+', ' ', text).strip()
    
    # 5. 彻底清理可能残留的空格
    text = text.strip()
    
    return text

def get_time_limits(config):
    mode = config.get("mode", "days")
    value = config.get("value", 30)
    now = datetime.now()
    
    start_limit = None
    end_limit = None
    
    if mode == "days":
        start_limit = now - timedelta(days=value)
    elif mode == "months":
        start_limit = now - timedelta(days=value * 30)
    elif mode == "years":
        start_limit = now - timedelta(days=value * 365)
    elif mode == "range":
        s_str = config.get("start_date")
        e_str = config.get("end_date")
        if s_str:
            try: start_limit = datetime.strptime(s_str, '%Y-%m-%d')
            except: pass
        if e_str:
            try: end_limit = datetime.strptime(e_str, '%Y-%m-%d') + timedelta(days=1)
            except: pass
            
    if start_limit is None:
        start_limit = now - timedelta(days=30)
    
    return start_limit, end_limit

def get_unified_filename(config):
    now_str = datetime.now().strftime('%Y%m%d')
    mode = config.get("mode", "days")
    value = config.get("value", 30)
    
    if mode == "days":
        suffix = f"{value}days"
    elif mode == "months":
        suffix = f"{value}months"
    elif mode == "years":
        suffix = f"{value}years"
    elif mode == "range":
        s = config.get("start_date", "start").replace("-", "")
        e = config.get("end_date", "end").replace("-", "")
        suffix = f"range_{s}_{e}"
    else:
        suffix = "custom"
        
    return os.path.join("recent", f"investors_{now_str}_{suffix}.csv")

class TimeLimitedShortSpider(XueqiuShortPostSpider):
    def __init__(self, username, user_id, start_limit, end_limit=None, type_param=0, filter_regex=None, unified_filename=None):
        super().__init__(username, user_id, type_param=type_param, filter_regex=filter_regex)
        self.start_limit = start_limit
        self.end_limit = end_limit
        self.unified_filename = unified_filename
        self.first_page_items_seen = 0
        print(f"{CYAN}[!] 时间范围: {self.start_limit.strftime('%Y-%m-%d')} 至 {self.end_limit.strftime('%Y-%m-%d') if self.end_limit else '现在'}")

    def format_date(self, date_str):
        formatted = super().format_date(date_str)
        try:
            post_dt = datetime.strptime(formatted, '%Y-%m-%d %H:%M')
            if post_dt < self.start_limit:
                if self.first_page_items_seen < 2:
                    self.first_page_items_seen += 1
                    return formatted

                if not self.stop_event.is_set():
                    print(f"\n{YELLOW}[!] 到达时间下限 ({formatted})，停止爬取任务...{RESET}")
                    self.stop_event.set()
            else:
                self.first_page_items_seen += 1
        except:
            pass
        return formatted

    def run(self, start_page=1, end_page=None):
        """覆盖原 run，确保在爬取前就加载统一文件中的 ID，避免重复爬取"""
        temp_file = os.path.join("data", f"{self.username}.csv")
        if os.path.exists(temp_file): os.remove(temp_file)
        
        existing_ids = set()
        if self.unified_filename and os.path.exists(self.unified_filename):
            try:
                df_existing = pd.read_csv(self.unified_filename, usecols=['ID', '博主'], encoding='utf-8-sig')
                existing_ids = set(df_existing[df_existing['博主'] == self.username]['ID'].astype(str).tolist())
                print(f"{BLUE}[i] 已加载统一文件历史记录 {len(existing_ids)} 条，爬取时将自动跳过。{RESET}")
            except Exception as e:
                print(f"{YELLOW}[!] 加载统一文件历史记录失败: {e}{RESET}")

        try:
            self.setup_cookies()
            if not os.path.exists("data"): os.makedirs("data")
            self.fetch_posts(start_page, end_page, existing_ids, temp_file)
            
            if os.path.exists(temp_file):
                df = pd.read_csv(temp_file, encoding='utf-8-sig')
                if '发布时间' in df.columns:
                    df['dt_temp'] = pd.to_datetime(df['发布时间'], errors='coerce')
                    # 1. 严格过滤时间上限 (如果是 range 模式)
                    if self.end_limit:
                        df = df[df['dt_temp'] <= self.end_limit]
                    # 2. 严格过滤时间下限 (所有模式都需要)
                    df = df[df['dt_temp'] >= self.start_limit]
                    df = df.drop(columns=['dt_temp'])
                
                # 3. 数据过滤逻辑 (同步 filter_csv.py)
                # a. 先清洗正文以便准确计算字数
                if '正文' in df.columns:
                    df['正文'] = df['正文'].fillna('').apply(clean_content)
                    df['字数'] = df['正文'].apply(len)
                else:
                    df['字数'] = 0

                # b. 转换互动数值
                for col in ['点赞数', '评论数']:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                    else:
                        df[col] = 0

                # c. 应用门槛
                pass_normal = (df['点赞数'] >= DEFAULT_MIN_LIKES) & \
                              (df['评论数'] >= DEFAULT_MIN_COMMENTS) & \
                              (df['字数'] >= DEFAULT_MIN_LENGTH)
                
                pass_super_likes = (df['点赞数'] >= DEFAULT_SUPER_LIKES) if DEFAULT_SUPER_LIKES is not None else False
                pass_super_comments = (df['评论数'] >= DEFAULT_SUPER_COMMENTS) if DEFAULT_SUPER_COMMENTS is not None else False
                pass_super_length = (df['字数'] >= DEFAULT_SUPER_LENGTH) if DEFAULT_SUPER_LENGTH is not None else False
                
                df = df[pass_normal | pass_super_likes | pass_super_comments | pass_super_length]

                # 4. 精简列：去掉转赞评和摘要
                exclude_cols = ['点赞数', '评论数', '转发数', '摘要', '字数']
                df = df[[c for c in df.columns if c not in exclude_cols]]
                
                if '博主' not in df.columns:
                    df.insert(0, '博主', self.username)
                
                if self.unified_filename:
                    if os.path.exists(self.unified_filename):
                        try:
                            check_df = pd.read_csv(self.unified_filename, usecols=['ID'], encoding='utf-8-sig')
                            final_ids = set(check_df['ID'].astype(str).tolist())
                            df['ID'] = df['ID'].astype(str)
                            df = df[~df['ID'].isin(final_ids)]
                        except: pass

                    if not df.empty:
                        header = not os.path.exists(self.unified_filename)
                        df.to_csv(self.unified_filename, mode='a', header=header, index=False, encoding='utf-8-sig')
                        print(f"{GREEN}[+] 已将 {len(df)} 条新记录合并至: {self.unified_filename}{RESET}")
                    else:
                        print(f"{YELLOW}[i] 没有新记录需要合并。{RESET}")
                    
                    if os.path.exists(temp_file): os.remove(temp_file)
        finally:
            self.page.quit()

class TimeLimitedLongSpider(XueqiuLongPostSpider):
    def __init__(self, username, user_id, start_limit, end_limit=None, type_param=2, filter_regex=None, unified_filename=None):
        super().__init__(username, user_id, type_param=type_param, filter_regex=filter_regex)
        self.start_limit = start_limit
        self.end_limit = end_limit
        self.unified_filename = unified_filename
        self._stop_fetching = False
        print(f"{CYAN}[!] 时间范围: {self.start_limit.strftime('%Y-%m-%d')} 至 {self.end_limit.strftime('%Y-%m-%d') if self.end_limit else '现在'}")

    def run(self, start_page=1, end_page=None):
        existing_ids = set()
        if self.unified_filename and os.path.exists(self.unified_filename):
            try:
                df_existing = pd.read_csv(self.unified_filename, usecols=['ID', '博主'], encoding='utf-8-sig')
                existing_ids = set(df_existing[df_existing['博主'] == self.username]['ID'].astype(str).tolist())
                print(f"{BLUE}[i] 已加载统一文件历史记录 {len(existing_ids)} 条用于去重。{RESET}")
            except Exception as e:
                print(f"{YELLOW}[!] 读取统一文件历史记录失败: {e}{RESET}")

        try:
            self.setup_cookies()
            self.fetch_posts(start_page, end_page, existing_ids, None)
        finally:
            print(f"{GREEN}[+] 任务结束，正在关闭浏览器...{RESET}")
            self.page.quit()

    def fetch_posts(self, start_page=1, end_page=None, existing_ids=None, filename=None):
        all_data = []
        job_start = time.time()
        if existing_ids is None: existing_ids = set()
        current_page = start_page
        max_page_limit = end_page if end_page else 9999
        last_id = None
        actual_filename = self.unified_filename if self.unified_filename else filename

        while current_page <= max_page_limit and not self._stop_fetching:
            api_url = f"https://xueqiu.com/v4/statuses/user_timeline.json?page={current_page}&user_id={self.user_id}&count=20"
            if self.type_param is not None: api_url += f"&type={self.type_param}"
            if last_id and current_page > 1: api_url += f"&max_id={last_id}"
            
            if self.page.url != f"https://xueqiu.com/u/{self.user_id}":
                self.page.get(f"https://xueqiu.com/u/{self.user_id}")
                time.sleep(1)

            print(f"{BLUE}正在获取第 {current_page} 页列表...{RESET}")
            res_data = None
            for attempt in range(3):
                self.page.get(api_url)
                for _ in range(5):
                    try:
                        res_data = self.get_page_json()
                        if res_data and 'statuses' in res_data: break
                    except: pass
                    time.sleep(1)
                if res_data and 'statuses' in res_data: break
                time.sleep(2)

            if not res_data or 'statuses' not in res_data:
                print(f"{RED}[-] 第 {current_page} 页获取失败，继续下一页。{RESET}")
                current_page += 1
                continue

            statuses = res_data['statuses']
            if not statuses: break
            last_id = statuses[-1].get('id')
            
            page_data = []
            for idx, status in enumerate(statuses):
                post_id = str(status.get('id'))
                raw_ts = status.get('created_at')
                if not raw_ts: continue
                post_dt = datetime.fromtimestamp(raw_ts / 1000)
                formatted_date = post_dt.strftime('%Y-%m-%d %H:%M')
                
                is_pinned = (current_page == 1 and idx == 0)
                if post_dt < self.start_limit:
                    if is_pinned:
                        print(f"{YELLOW}[!] 识别到置顶贴 ({formatted_date})，跳过时间限制检查。{RESET}")
                    else:
                        print(f"{YELLOW}[!] 到达时间下限 ({formatted_date})，停止处理。{RESET}")
                        self._stop_fetching = True
                        break
                
                if self.end_limit and post_dt > self.end_limit: continue
                if post_id in existing_ids: continue
                
                # 获取互动数据
                likes = status.get('like_count') or 0
                comments = status.get('reply_count') or 0
                
                raw_text = status.get('text', '')
                can_expand = status.get('expend', False)
                link = f"https://xueqiu.com{status.get('target')}"
                
                # 获取并清洗正文
                if can_expand and link and 'xueqiu.com' in link:
                    full_content, _ = self.fetch_detail(link, formatted_date)
                    content = clean_content(full_content if full_content else self.clean_html(raw_text))
                else:
                    content = clean_content(self.clean_html(raw_text))

                # 数据过滤 (同步 filter_csv.py)
                content_len = len(content)
                pass_normal = (likes >= DEFAULT_MIN_LIKES) and \
                              (comments >= DEFAULT_MIN_COMMENTS) and \
                              (content_len >= DEFAULT_MIN_LENGTH)
                
                pass_super_likes = (likes >= DEFAULT_SUPER_LIKES) if DEFAULT_SUPER_LIKES is not None else False
                pass_super_comments = (comments >= DEFAULT_SUPER_COMMENTS) if DEFAULT_SUPER_COMMENTS is not None else False
                pass_super_length = (content_len >= DEFAULT_SUPER_LENGTH) if DEFAULT_SUPER_LENGTH is not None else False
                
                if not (pass_normal or pass_super_likes or pass_super_comments or pass_super_length):
                    print(f"  [!] 过滤跳过: {formatted_date} | 赞:{likes} 评:{comments} 字:{content_len}")
                    continue

                item = {
                    '博主': self.username,
                    'ID': post_id,
                    '发布时间': formatted_date,
                    '页码': f"{current_page}",
                    '链接': link,
                    '正文': content
                }

                page_data.append(item)
                all_data.append(item)
                existing_ids.add(post_id)
                print(f"  [+] 已通过: {formatted_date} | {item['正文'][:20]}...")

            if page_data and actual_filename:
                cols_to_save = ['博主', 'ID', '发布时间', '页码', '链接', '正文']
                pd.DataFrame(page_data)[cols_to_save].to_csv(actual_filename, mode='a', header=not os.path.exists(actual_filename), index=False, encoding='utf-8-sig')
            
            if self._stop_fetching: break
            current_page += 1
            time.sleep(random.uniform(1, 3))

def main():
    start_limit, end_limit = get_time_limits(TIME_CONFIG)
    unified_file = get_unified_filename(TIME_CONFIG)
    
    if not os.path.exists("data"): os.makedirs("data")
    if not os.path.exists("recent"): os.makedirs("recent")
    
    print(f"\n{BOLD}{CYAN}{'='*60}")
    print(f"{BOLD}{CYAN} 批量时间范围爬取启动 (统一存储模式)")
    print(f"{CYAN} 设定范围: {GREEN}{start_limit.strftime('%Y-%m-%d')} {CYAN}至 {GREEN}{end_limit.strftime('%Y-%m-%d') if end_limit else '现在'}")
    print(f"{CYAN} 存储文件: {YELLOW}{unified_file}")
    print(f"{BOLD}{CYAN}{'='*60}\n")

    if not USER_LIST:
        print(f"{RED}[!] 错误: USER_LIST 为空，请在 config.py 中配置博主列表。{RESET}")
        return

    for user in USER_LIST:
        name = user.get("username")
        uid = user.get("userid")
        if not name or not uid:
            log_error(f"跳过无效配置: {user}")
            continue

        print(f"\n{BOLD}{MAGENTA}>>> 正在处理博主: {name} ({uid}){RESET}")
        try:
            if TYPE_PARAM == 2:
                spider = TimeLimitedLongSpider(name, uid, start_limit, end_limit, type_param=TYPE_PARAM, filter_regex=FILTER_REGEX, unified_filename=unified_file)
                spider.run(start_page=1, end_page=None)
            else:
                spider = TimeLimitedShortSpider(name, uid, start_limit, end_limit, type_param=TYPE_PARAM, filter_regex=FILTER_REGEX, unified_filename=unified_file)
                spider.run(start_page=1, end_page=None)
            
            print(f"{GREEN}[V] 博主 {name} 处理完成。{RESET}")
        except Exception as e:
            msg = f"处理博主 {name}({uid}) 失败: {str(e)}"
            print(f"{RED}{msg}{RESET}")
            log_error(msg)
        
        time.sleep(5)

    print(f"\n{BOLD}{GREEN}{'='*60}")
    print(f"{BOLD}{GREEN} 所有博主任务执行完毕！")
    print(f"{GREEN} 最终数据已汇总至: {unified_file}")
    print(f"{GREEN} 错误详情（如有）请查看: {error_log_file}")
    print(f"{BOLD}{GREEN}{'='*60}\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{YELLOW}[!] 用户手动中断任务。{RESET}")
    except Exception as e:
        log_error(f"全局运行异常: {e}")
        print(f"{RED}[!] 全局运行异常: {e}{RESET}")


