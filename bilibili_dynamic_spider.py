import warnings
warnings.simplefilter("ignore")

from DrissionPage import ChromiumPage, ChromiumOptions
import time
import os
import pandas as pd
import re
import random
from datetime import datetime, timedelta
import colorama
from config import TIME_CONFIG, FILTER_REGEX, LOAD_IMAGES

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

class BilibiliDynamicSpider:
    def __init__(self, username, user_id, start_limit, end_limit=None):
        self.username = username
        self.user_id = user_id
        self.start_limit = start_limit
        self.end_limit = end_limit
        
        co = ChromiumOptions()
        co.no_imgs(not LOAD_IMAGES)
        co.set_load_mode('normal')
        co.set_argument('--no-sandbox')
        co.set_argument('--disable-gpu')
        self.page = ChromiumPage(co)
        
    def format_date(self, date_str):
        if not date_str: return ""
        clean_str = re.sub(r'^发布于\s*', '', date_str.strip())
        now = datetime.now()
        try:
            if '刚刚' in clean_str: return now.strftime('%Y-%m-%d %H:%M')
            if '分钟前' in clean_str:
                m = int(re.search(r'\d+', clean_str).group())
                return (now - timedelta(minutes=m)).strftime('%Y-%m-%d %H:%M')
            if '小时前' in clean_str:
                h = int(re.search(r'\d+', clean_str).group())
                return (now - timedelta(hours=h)).strftime('%Y-%m-%d %H:%M')
            if '昨天' in clean_str:
                time_match = re.search(r'\d{2}:\d{2}', clean_str)
                time_part = time_match.group() if time_match else now.strftime('%H:%M')
                return f"{(now - timedelta(days=1)).strftime('%Y-%m-%d')} {time_part}"
            m_short = re.match(r'^(\d{1,2})-(\d{1,2})(?:\s+(\d{2}:\d{2}))?$', clean_str)
            if m_short:
                month, day = int(m_short.group(1)), int(m_short.group(2))
                time_part = m_short.group(3) or "00:00"
                year = now.year if month <= now.month else now.year - 1
                return f"{year}-{month:02d}-{day:02d} {time_part}"
            m_full = re.match(r'^(\d{4})-(\d{1,2})-(\d{1,2})(?:\s+(\d{2}:\d{2}))?$', clean_str)
            if m_full:
                year, month, day = int(m_full.group(1)), int(m_full.group(2)), int(m_full.group(3))
                time_part = m_full.group(4) or "00:00"
                return f"{year}-{month:02d}-{day:02d} {time_part}"
            return clean_str
        except: return clean_str

    def parse_time_to_dt(self, formatted_time):
        try: return datetime.strptime(formatted_time, '%Y-%m-%d %H:%M')
        except: return None

    def run(self):
        # 启动监听器，捕获动态列表的 API 响应
        self.page.listen.start('polymer/web-dynamic/v1/feed/space')
        
        base_url = f"https://space.bilibili.com/{self.user_id}"
        print(f"\n{GREEN}[Step 1] 正在打开 B站用户主页: {base_url}{RESET}")
        self.page.get(base_url)
        time.sleep(5)
        
        dynamic_url = f"https://space.bilibili.com/{self.user_id}/dynamic"
        print(f"{GREEN}[Step 2] 正在进入博主动态页: {dynamic_url}{RESET}")
        self.page.get(dynamic_url)
        
        all_data, seen_ids, scroll_count, max_scrolls = [], set(), 0, 50
        filename = os.path.join("data", f"bili_{self.username}.csv")
        if not os.path.exists("data"): os.makedirs("data")

        print(f"{MAGENTA}[Step 3] 正在通过 API 监听抓取动态内容...{RESET}")
        
        stop_fetching = False
        while scroll_count < max_scrolls and not stop_fetching:
            # 等待数据包
            res = self.page.listen.wait(timeout=10)
            if res:
                data = res.response.body
                if isinstance(data, dict) and data.get('code') == 0:
                    items = data.get('data', {}).get('items', [])
                    print(f"{BLUE}[i] API 返回了 {len(items)} 条动态{RESET}")
                    
                    new_in_this_scroll = 0
                    for item in items:
                        try:
                            modules = item.get('modules', {})
                            # 1. 提取时间
                            pub_module = modules.get('module_author', {})
                            raw_time = pub_module.get('pub_time', '')
                            fmt_time = self.format_date(raw_time)
                            post_dt = self.parse_time_to_dt(fmt_time)
                            
                            # 2. 提取 ID 和链接
                            post_id = item.get('id_str', '')
                            link = f"https://www.bilibili.com/opus/{post_id}"
                            
                            if post_id in seen_ids: continue
                            seen_ids.add(post_id)

                            # 3. 时间判定
                            if post_dt:
                                if post_dt < self.start_limit:
                                    print(f"{YELLOW}[!] 到达时间下限: {fmt_time}。{RESET}")
                                    stop_fetching = True
                                    break
                                if self.end_limit and post_dt > self.end_limit: continue

                            # 4. 提取内容
                            content = ""
                            desc_module = modules.get('module_dynamic', {})
                            
                            # A. 尝试从主要内容区提取
                            if desc_module.get('major'):
                                major = desc_module['major']
                                m_type = major.get('type')
                                
                                if m_type == 'MAJOR_TYPE_OPUS':
                                    opus = major.get('opus', {})
                                    content = opus.get('title', '') or ''
                                    if opus.get('content', {}).get('text'):
                                        content += " " + opus['content']['text']
                                elif m_type == 'MAJOR_TYPE_ARCHIVE':
                                    content = "[视频] " + major.get('archive', {}).get('title', '')
                                elif m_type == 'MAJOR_TYPE_ARTICLE':
                                    content = "[专栏] " + major.get('article', {}).get('title', '') + " " + major.get('article', {}).get('desc', '')
                                elif m_type == 'MAJOR_TYPE_COMMON':
                                    content = major.get('common', {}).get('title', '') + " " + major.get('common', {}).get('desc', '')
                            
                            # B. 如果 A 没拿到，从描述文字区拿
                            if not content.strip():
                                content = desc_module.get('desc', {}).get('text', '')

                            # C. 如果还是空的，尝试从其他模块拿
                            if not content.strip():
                                # 有些动态可能只有图片，文字在特殊的附加模块
                                additional = modules.get('module_stat', {}) # 虽然这是统计，但有时有辅助信息
                                # 或者找找有没有 title
                                content = pub_module.get('name', '') + " 的动态"

                            # D. 转发内容处理
                            if item.get('type') == 'DYNAMIC_TYPE_FORWARD':
                                orig = item.get('orig', {})
                                orig_modules = orig.get('modules', {})
                                orig_desc = orig_modules.get('module_dynamic', {}).get('desc', {}).get('text', '')
                                if not orig_desc:
                                    # 转发的可能是视频
                                    orig_major = orig_modules.get('module_dynamic', {}).get('major', {})
                                    if orig_major.get('type') == 'MAJOR_TYPE_ARCHIVE':
                                        orig_desc = "[视频] " + orig_major.get('archive', {}).get('title', '')
                                
                                if orig_desc:
                                    content += f" // 转发原文: {orig_desc.strip()}"

                            content = content.strip()
                            if not content and not link: continue

                            all_data.append({
                                '博主': self.username,
                                '发布时间': fmt_time,
                                '链接': link,
                                '正文': content
                            })
                            new_in_this_scroll += 1
                            preview = content[:60].replace('\n', ' ')
                            print(f"  [+] {fmt_time} | {preview}")
                        except Exception as e:
                            print(f"{RED}[!] 解析 API 项出错: {e}{RESET}")
                            continue
                
                # 滚动加载更多
                self.page.scroll.to_bottom()
                time.sleep(3)
                scroll_count += 1
                
                if all_data:
                    pd.DataFrame(all_data).to_csv(filename, index=False, encoding='utf-8-sig')
            else:
                # 没监听到包，尝试滚动一下触发
                print(f"{YELLOW}[!] 未监听到 API 数据，尝试向下滚动...{RESET}")
                self.page.scroll.to_bottom()
                time.sleep(5)
                scroll_count += 1
                if scroll_count > 10 and not all_data:
                    print(f"{RED}[-] 无法获取动态数据，请检查网络或博主设置。{RESET}")
                    break

        self.save_and_quit(all_data, filename)

        self.save_and_quit(all_data, filename)

    def save_and_quit(self, data, filename):
        if data:
            pd.DataFrame(data).to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"\n{GREEN}[V] 抓取完成！共抓取 {len(data)} 条，数据保存在: {filename}{RESET}")
        else:
            print(f"\n{RED}[-] 未在设定的时间范围内找到任何动态。{RESET}")
        self.page.quit()

def get_time_limits_local(config):
    mode = config.get("mode", "days")
    value = config.get("value", 30)
    now = datetime.now()
    start_limit = None
    if mode == "days": start_limit = now - timedelta(days=value)
    elif mode == "months": start_limit = now - timedelta(days=value * 30)
    elif mode == "years": start_limit = now - timedelta(days=value * 365)
    elif mode == "range":
        s_str = config.get("start_date")
        if s_str: start_limit = datetime.strptime(s_str, '%Y-%m-%d')
    if start_limit is None: start_limit = now - timedelta(days=30)
    e_str = config.get("end_date")
    end_limit = (datetime.strptime(e_str, '%Y-%m-%d') + timedelta(days=1)) if e_str else None
    return start_limit, end_limit

if __name__ == "__main__":
    import sys
    # 默认值
    target_username, target_uid = "史诗级韭菜", "322005137"
    if len(sys.argv) >= 3:
        target_username, target_uid = sys.argv[1], sys.argv[2]
    
    start_limit, end_limit = get_time_limits_local(TIME_CONFIG)
    # 调试模式默认拉长到 7 天
    if TIME_CONFIG.get("mode") == "days" and TIME_CONFIG.get("value") <= 1:
        start_limit = datetime.now() - timedelta(days=7)

    print(f"{BOLD}{CYAN}B站动态爬虫启动: {target_username} ({target_uid})")
    print(f"{CYAN}时间范围: {start_limit.strftime('%Y-%m-%d')} 至 {end_limit.strftime('%Y-%m-%d') if end_limit else '现在'}")
    
    spider = BilibiliDynamicSpider(target_username, target_uid, start_limit, end_limit)
    spider.run()
