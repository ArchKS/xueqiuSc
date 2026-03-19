import warnings
warnings.simplefilter("ignore")

from DrissionPage import ChromiumPage
import time
import os
import pandas as pd
import json
import re
import random
from datetime import datetime
from html import unescape
from concurrent.futures import ThreadPoolExecutor
import threading
import colorama
from tqdm import tqdm

# 初始化 colorama 以支持 Windows 颜色输出
colorama.init(autoreset=True)

# 颜色常量
GREEN = colorama.Fore.GREEN
YELLOW = colorama.Fore.YELLOW
RED = colorama.Fore.RED
BLUE = colorama.Fore.BLUE
CYAN = colorama.Fore.CYAN
RESET = colorama.Style.RESET_ALL

class XueqiuShortPostSpider:
    def __init__(self, username, user_id, xq_a_token=None, type_param=0, filter_regex=None):
        self.username = username
        self.user_id = user_id
        self.xq_a_token = xq_a_token 
        self.type_param = type_param 
        
        if filter_regex:
            self.filter_patterns = [re.compile(p, re.I) for p in filter_regex]
        else:
            self.filter_patterns = []
        
        from DrissionPage import ChromiumOptions
        co = ChromiumOptions()
        co.no_imgs(True)
        co.set_load_mode('eager')
        co.set_argument('--dns-prefetch-disable', 'false')        
        
        self.page = ChromiumPage(co)
        self.save_lock = threading.Lock() 
        
    def clean_html(self, html_text):
        if not html_text: return ""
        clean_text = re.sub(r'<[^>]+>', '', html_text)
        clean_text = clean_text.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
        return clean_text.strip()

    def format_date(self, date_str):
        if not date_str: return datetime.now().strftime('%Y-%m-%d %H:%M')
        clean_str = re.sub(r'修改于', '', str(date_str))
        clean_str = re.sub(r'·.*$', '', clean_str).strip()
        
        from datetime import datetime, timedelta
        now = datetime.now()
        current_year = now.year

        try:
            if '分钟前' in clean_str:
                m = int(re.search(r'\d+', clean_str).group())
                return (now - timedelta(minutes=m)).strftime('%Y-%m-%d %H:%M')
            if '小时前' in clean_str:
                h = int(re.search(r'\d+', clean_str).group())
                return (now - timedelta(hours=h)).strftime('%Y-%m-%d %H:%M')
            if '今天' in clean_str:
                time_match = re.search(r'\d{2}:\d{2}', clean_str)
                time_part = time_match.group() if time_match else now.strftime('%H:%M')
                return f"{now.strftime('%Y-%m-%d')} {time_part}"
            if '昨天' in clean_str:
                time_match = re.search(r'\d{2}:\d{2}', clean_str)
                time_part = time_match.group() if time_match else now.strftime('%H:%M')
                yesterday = (now - timedelta(days=1)).strftime('%Y-%m-%d')
                return f"{yesterday} {time_part}"
            m_full = re.search(r'(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})', clean_str)
            if m_full: return f"{m_full.group(1)} {m_full.group(2)}"
            m_short = re.search(r'(\d{2}-\d{2})\s+(\d{2}:\d{2})', clean_str)
            if m_short:
                date_part, time_part = m_short.group(1), m_short.group(2)
                month = int(date_part.split('-')[0])
                year = current_year if month <= now.month else current_year - 1
                return f"{year}-{date_part} {time_part}"
            m_date = re.search(r'(\d{4}-\d{2}-\d{2})', clean_str)
            if m_date: return f"{m_date.group(1)} 00:00"
            return clean_str
        except: return clean_str

    def setup_cookies(self):
        if self.xq_a_token:
            if "xueqiu.com" not in self.page.url:
                self.page.get("https://xueqiu.com", timeout=5)
            self.page.set.cookies({'name': 'xq_a_token', 'value': self.xq_a_token, 'domain': '.xueqiu.com'})

    def fetch_posts(self, start_page=1, end_page=None, existing_ids=None, filename=None):
        """[并发版] 顺序翻页优化版"""
        from config import MAX_WORKERS
        num_workers = MAX_WORKERS if MAX_WORKERS else 3
        job_start = time.time()
        
        if existing_ids is None: existing_ids = set()
            
        user_url = f"https://xueqiu.com/u/{self.user_id}"
        print(f"{BLUE}[+] 探测任务范围...{RESET}")
        self.page.get(user_url)
        time.sleep(2)
        actual_max_page = 0
        try:
            pagination = self.page.ele('.pagination')
            if pagination:
                p_nums = [int(l.text) for l in pagination.eles('tag:a') if l.text.isdigit()]
                if p_nums: actual_max_page = max(p_nums)
        except: pass

        max_p_limit = end_page if end_page else (actual_max_page if actual_max_page else 100)
        all_pages = list(range(start_page, max_p_limit + 1))
        if not all_pages: return []

        print(f"{BLUE}[!] 并发配置: {num_workers} 个标签页 | 范围: {start_page} - {max_p_limit} 页{RESET}")
        
        total_pages_count = len(all_pages)
        # 改为轮询分配 (例如: Tab1处理1,4,7, Tab2处理2,5,8)
        chunks = [all_pages[i::num_workers] for i in range(num_workers)]
        
        # 创建全局进度条
        progress_bar = tqdm(total=total_pages_count, desc="总页数进度", unit="页", dynamic_ncols=True, position=0, leave=True)
        
        def page_worker(worker_id, target_pages):
            if not target_pages: return
            
            tab = self.page if worker_id == 0 else self.page.new_tab(user_url)
            time.sleep(2)
            
            for current_p in target_pages:
                try:
                    tqdm.write(f"{CYAN}[Tab-{worker_id}] 正在处理第 {current_p} 页...{RESET}")
                    
                    # 因为是不连续页码，必须每页都执行一次跳转
                    jump_success = False
                    for attempt in range(3):
                        tab.scroll.to_bottom(); time.sleep(1)
                        inp = tab.ele('tag:input@@placeholder=页码', timeout=3) or tab.ele('css:.pagination input', timeout=2)
                        if inp:
                            inp.clear(); inp.input(f"{current_p}"); time.sleep(0.5); tab.actions.type('\n')
                            time.sleep(4)
                        else:
                            btn = tab.ele(f'text={current_p}', timeout=2)
                            if btn: btn.click(by_js=True); time.sleep(4)
                            
                        active = tab.ele('css:.pagination .active', timeout=2) or tab.ele('css:.pagination li.active', timeout=2)
                        if active and active.text == str(current_p): jump_success = True; break
                    
                    if not jump_success:
                        tqdm.write(f"{RED}[Tab-{worker_id}] 第 {current_p} 页跳转校验失败，跳过。{RESET}")
                        with self.save_lock: progress_bar.update(1)
                        continue

                    old_first_id = None
                    try:
                        fi = tab.ele('.timeline__item', timeout=2)
                        if fi: old_first_id = str(fi.ele('.date-and-source').attr('data-id'))
                    except: pass

                    items = tab.eles('.timeline__item')
                    if items:
                        page_data = []
                        for item in items:
                            try:
                                d_link = item.ele('css:.date-and-source', timeout=1)
                                if not d_link: continue
                                pid = str(d_link.attr('data-id'))
                                with self.save_lock:
                                    if pid in existing_ids: continue
                                content_ele = item.ele('css:.timeline__item__content', timeout=1)
                                footer = item.ele('css:.timeline__item__ft', timeout=1)
                                l=r=w=0
                                if footer:
                                    for fl in footer.eles('tag:a'):
                                        txt = fl.text or ""
                                        title_attr = fl.attr('title') or ""
                                        num = int(''.join(filter(str.isdigit, txt))) if any(c.isdigit() for c in txt) else 0
                                        
                                        icon = fl.ele('css:.iconfont', timeout=0)
                                        icon_txt = icon.text if icon else ""

                                        if '转发' in txt or '转发' in title_attr or icon_txt == '': w = num
                                        elif '讨论' in txt or '评论' in txt or '评论' in title_attr or icon_txt == '': r = num
                                        elif '赞' in txt or '赞' in title_attr or icon_txt == '': l = num
                                
                                # 点击展开以获取全部内容
                                expand_btn = item.ele('text=展开', timeout=0.1)
                                if expand_btn:
                                    try: 
                                        expand_btn.click()
                                        time.sleep(0.5)  # 等待 DOM 更新展开的内容
                                    except: pass
                                
                                d = {
                                    'ID': pid, '发布时间': self.format_date(d_link.text.strip()),
                                    '点赞数': l, '评论数': r, '转发数': w,
                                    '页码': f"{current_p}/{actual_max_page}",
                                    '链接': f"https://xueqiu.com/{self.user_id}/{pid}",
                                    '正文': content_ele.text if content_ele else ""
                                }
                                
                                # 检查是否获取到内容，处理潜在的反爬限制
                                if not d['正文'] or len(d['正文'].strip()) == 0:
                                    # 如果展开后也没有内容，尝试寻找可能包含文章标题的元素
                                    title_ele = item.ele('.timeline__item__title', timeout=0.1)
                                    if title_ele and title_ele.text:
                                        d['正文'] = title_ele.text
                                    else:
                                        from config import PAUSE_ON_EMPTY_CONTENT
                                        if PAUSE_ON_EMPTY_CONTENT:
                                            # 如果确定是真的没获取到任何内容，暂停让用户处理
                                            tqdm.write(f"{RED}[!] 当前已经获取不到内容 (字数为0) | ID: {pid}{RESET}")
                                            input(f"{YELLOW}请检查浏览器是否遇到反爬挑战，处理完毕后按回车继续...{RESET}")
                                            # 用户处理后再次尝试获取内容
                                            content_ele = item.ele('css:.timeline__item__content', timeout=1)
                                            d['正文'] = content_ele.text if content_ele else ""
                                        else:
                                            tqdm.write(f"{YELLOW}[!] 跳过空内容检查 (PAUSE_ON_EMPTY_CONTENT = False) | ID: {pid}{RESET}")

                                page_data.append(d)
                            except: continue

                        if page_data:
                            with self.save_lock:
                                final = []
                                for d in page_data:
                                    if d['ID'] in existing_ids: continue
                                    txt = d['正文']
                                    if "//" in txt: txt = re.split(r'\s*//\s*@', txt, 1)[0].strip()
                                    for tag in [r'展开\s*', r'收起\s*', r'查看对话', r'查看图片']: txt = re.sub(tag, '', txt)
                                    d['正文'], d['摘要'] = txt.strip(), txt.strip()[:50].replace('\n', ' ') + '...'
                                    if any(p.search(d['正文']) for p in self.filter_patterns): continue
                                    existing_ids.add(d['ID'])
                                    final.append(d)
                                if final and filename:
                                    df_p = pd.DataFrame(final)
                                    cols = ['ID', '发布时间', '点赞数', '评论数', '转发数', '页码', '链接', '摘要', '正文']
                                    df_p[[c for c in cols if c in df_p.columns]].to_csv(filename, mode='a', header=not os.path.exists(filename), index=False, encoding='utf-8-sig')
                                    tqdm.write(f"{GREEN}[Tab-{worker_id}] 第 {current_p} 页已存 | 库内总数: {len(existing_ids)}{RESET}")
                    
                    # 每次完成一页，进度条 + 1
                    with self.save_lock:
                        progress_bar.update(1)

                except Exception as e:
                    tqdm.write(f"{RED}[Tab-{worker_id}] 异常: {e}{RESET}")
                    with self.save_lock: progress_bar.update(1)
            
            if worker_id > 0: tab.close()

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            executor.map(lambda i: page_worker(i, chunks[i]), range(num_workers))
            
        progress_bar.close()
        return []

    def run(self, start_page=1, end_page=None):
        try:
            if not os.path.exists("data"): os.makedirs("data")
            filename = os.path.join("data", f"{self.username}.csv")
            existing_ids = set()
            if os.path.exists(filename):
                try:
                    temp_df = pd.read_csv(filename, encoding='utf-8-sig', nrows=0)
                    if '页码' not in temp_df.columns:
                        existing_df = pd.read_csv(filename, encoding='utf-8-sig')
                        idx = existing_df.columns.get_loc('转发数') + 1 if '转发数' in existing_df.columns else len(existing_df.columns)
                        existing_df.insert(idx, '页码', '旧数据/未知')
                        existing_df.to_csv(filename, index=False, encoding='utf-8-sig')
                    id_df = pd.read_csv(filename, encoding='utf-8-sig', usecols=['ID'])
                    existing_ids = set(id_df['ID'].astype(str).tolist())
                except: pass
            self.setup_cookies()
            self.fetch_posts(start_page, end_page, existing_ids, filename)
            if os.path.exists(filename):
                df = pd.read_csv(filename, encoding='utf-8-sig')
                df['ID'] = df['ID'].astype(str)
                df.drop_duplicates(subset=['ID'], keep='last', inplace=True)
                if '发布时间' in df.columns: df['发布时间'] = df['发布时间'].apply(self.format_date)
                cols = ['ID', '发布时间', '点赞数', '评论数', '转发数', '页码', '链接', '摘要', '正文']
                df = df[[c for c in cols if c in df.columns]]
                df.sort_values(by='发布时间', ascending=False, inplace=True)
                df.to_csv(filename, index=False, encoding='utf-8-sig')
                print(f"{BLUE}[!] 任务完成！总数: {len(df)} 至 {filename}{RESET}")
        finally:
            self.page.quit()

if __name__ == "__main__":
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from config import DEFAULT_USERNAME, DEFAULT_USER_ID, FILTER_REGEX, TYPE_PARAM
    spider = XueqiuShortPostSpider(DEFAULT_USERNAME, DEFAULT_USER_ID, type_param=TYPE_PARAM, filter_regex=FILTER_REGEX)
    spider.run(start_page=1, end_page=2)
