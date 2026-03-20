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
try:
    from plyer import notification
except ImportError:
    notification = None

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
        # co.set_argument('--dns-prefetch-disable', 'false')        
        
        self.page = ChromiumPage(co)
        self.save_lock = threading.Lock()
        self.stop_event = threading.Event()
        
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
        from config import MAX_WORKERS, PAGINATION_WORKER_MODE
        num_workers = MAX_WORKERS if MAX_WORKERS else 3
        job_start = time.time()
        self.stop_event.clear()
        
        if existing_ids is None: existing_ids = set()

        def is_page_disconnected_error(exc):
            error_text = str(exc).lower()
            disconnected_markers = (
                '页面链接已断开',
                '与页面的连接已断开',
                '链接已断开',
                '与页面的连接',
                'disconnected',
                'connection lost',
                'connection closed',
                'websocket',
                'target closed',
                'target crashed',
                'frame was detached',
                'tab has been closed',
                'session closed',
                'browser has disconnected',
            )
            return any(marker in error_text for marker in disconnected_markers)

        def raise_if_page_disconnected(exc, worker_id=None):
            if not is_page_disconnected_error(exc):
                return
            self.stop_event.set()
            if worker_id is None:
                tqdm.write(f"{RED}[!] 页面链接已断开，正在取消所有 worker...{RESET}")
            else:
                tqdm.write(f"{RED}[Tab-{worker_id}] 页面链接已断开，正在取消所有 worker...{RESET}")
            raise RuntimeError("PAGE_DISCONNECTED") from exc

        def detect_slider_challenge(tab, scene):
            slider_selectors = (
                'css:.geetest_slider_button',
                'css:.geetest_btn',
                'css:.nc_iconfont.btn_slide',
                'css:.nc_wrapper',
                'css:.captcha_verify_container',
                'css:[class*="slider"]',
                'css:[class*="captcha"]',
            )
            challenge_texts = (
                '滑动',
                '滑块',
                '拖动',
                '请完成验证',
                '请先验证',
                '安全验证',
                '验证码',
            )

            found = False
            try:
                for selector in slider_selectors:
                    if tab.ele(selector, timeout=0.3):
                        found = True
                        break
                if not found:
                    page_text = (tab.html or '')[:20000]
                    found = any(text in page_text for text in challenge_texts)
            except Exception:
                return False

            if not found:
                return False

            message = f"{scene} 时检测到滑块/验证码，请处理浏览器验证。"
            tqdm.write(f"{RED}[!] {message}{RESET}")
            if notification:
                try:
                    notification.notify(
                        title="雪球爬虫检测到滑块",
                        message=message,
                        app_name="xueqiuSc",
                        timeout=10
                    )
                except Exception as notify_error:
                    tqdm.write(f"{YELLOW}[!] 弹窗通知失败: {notify_error}{RESET}")
            return True
             
        user_url = f"https://xueqiu.com/u/{self.user_id}"
        print(f"{BLUE}[+] 探测任务范围...{RESET}")
        self.page.get(user_url)
        time.sleep(2)
        detect_slider_challenge(self.page, "打开用户主页")
        actual_max_page = 0
        try:
            pagination = self.page.ele('.pagination')
            if pagination:
                p_nums = [int(l.text) for l in pagination.eles('tag:a') if l.text.isdigit()]
                if p_nums: actual_max_page = max(p_nums)
        except Exception as e:
            raise_if_page_disconnected(e)

        max_p_limit = end_page if end_page else (actual_max_page if actual_max_page else 100)
        all_pages = list(range(start_page, max_p_limit + 1))
        if not all_pages: return []

        print(f"{BLUE}[!] 并发配置: {num_workers} 个标签页 | 范围: {start_page} - {max_p_limit} 页{RESET}")
        
        total_pages_count = len(all_pages)
        actual_workers = min(num_workers, total_pages_count)

        if PAGINATION_WORKER_MODE == "shifted_total":
            # 按总页数平移起点，例如总页数100、3个worker、从10页开始 => 10 / 44 / 77
            base_starts = [1 + (max_p_limit * i) // actual_workers for i in range(actual_workers)]
            if start_page > 1:
                chunk_starts = [start_page]
                chunk_starts.extend(min(max_p_limit, base_starts[i] + start_page) for i in range(1, actual_workers))
            else:
                chunk_starts = base_starts
            chunk_starts = sorted(set(p for p in chunk_starts if start_page <= p <= max_p_limit))
        else:
            # 按当前抓取区间等分，例如 39-53、3个worker => 39-44 / 45-49 / 50-53
            base_size = total_pages_count // actual_workers
            remainder = total_pages_count % actual_workers
            chunk_starts = []
            current_start = start_page
            for i in range(actual_workers):
                chunk_starts.append(current_start)
                current_start += base_size + (1 if i < remainder else 0)

        chunks = []
        for i, chunk_start in enumerate(chunk_starts):
            chunk_end = chunk_starts[i + 1] - 1 if i + 1 < len(chunk_starts) else max_p_limit
            if chunk_start <= chunk_end:
                chunks.append(list(range(chunk_start, chunk_end + 1)))
        
        print(f"{BLUE}[!] 并发分段模式: {PAGINATION_WORKER_MODE}{RESET}")
        print(f"{BLUE}[!] 分段起始页: {', '.join(str(chunk[0]) for chunk in chunks)}{RESET}")

        # 创建全局进度条
        progress_bar = tqdm(total=total_pages_count, desc="总页数进度", unit="页", dynamic_ncols=True, position=0, leave=True)

        def detect_slider_challenge(tab, scene):
            slider_selectors = (
                'css:.geetest_slider_button',
                'css:.geetest_btn',
                'css:.nc_iconfont.btn_slide',
                'css:.nc_wrapper',
                'css:.captcha_verify_container',
                'css:[class*="slider"]',
                'css:[class*="captcha"]',
            )
            challenge_texts = (
                '滑动',
                '滑块',
                '拖动',
                '请完成验证',
                '请先验证',
                '安全验证',
                '验证码',
            )

            found = False
            try:
                for selector in slider_selectors:
                    if tab.ele(selector, timeout=0.3):
                        found = True
                        break
                if not found:
                    page_text = (tab.html or '')[:20000]
                    found = any(text in page_text for text in challenge_texts)
            except Exception:
                return False

            if not found:
                return False

            message = f"{scene} 时检测到滑块/验证码，请处理浏览器验证。"
            tqdm.write(f"{RED}[!] {message}{RESET}")
            if notification:
                try:
                    notification.notify(
                        title="雪球爬虫检测到滑块",
                        message=message,
                        app_name="xueqiuSc",
                        timeout=10
                    )
                except Exception as notify_error:
                    tqdm.write(f"{YELLOW}[!] 弹窗通知失败: {notify_error}{RESET}")
            return True
        
        def get_active_page(tab):
            active = tab.ele('css:.pagination .active', timeout=1) or tab.ele('css:.pagination li.active', timeout=1)
            if not active:
                return None
            active_text = (active.text or '').strip()
            return active_text if active_text.isdigit() else None

        def jump_with_input(tab, target_page, timeout=3):
            inp = tab.ele('tag:input@@placeholder=页码', timeout=timeout) or tab.ele('css:.pagination input', timeout=2)
            if not inp:
                return False
            try:
                inp.clear()
            except:
                pass
            inp.input(f"{target_page}")
            time.sleep(0.5)
            tab.actions.type('\n')
            time.sleep(4)
            detect_slider_challenge(tab, f"跳转到第 {target_page} 页")
            return get_active_page(tab) == str(target_page)

        def reset_to_first_page(tab):
            for selector in ('text=1', 'text=首页', 'text=第一页'):
                btn = tab.ele(selector, timeout=1.5)
                if not btn:
                    continue
                try:
                    btn.click(by_js=True)
                except:
                    try:
                        btn.click()
                    except:
                        continue
                time.sleep(4)
                detect_slider_challenge(tab, "回到第一页")
                if get_active_page(tab) == '1':
                    return True
            return False

        def notify_page_turn_failed(worker_id, expected_page, preview_text):
            message = f"Tab-{worker_id} 翻到第 {expected_page} 页失败，首帖前30字未变化：{preview_text}"
            tqdm.write(f"{RED}[Tab-{worker_id}] {message}{RESET}")
            if notification:
                try:
                    notification.notify(
                        title="雪球爬虫翻页失败",
                        message=message[:256],
                        app_name="xueqiuSc",
                        timeout=10
                    )
                except Exception as notify_error:
                    tqdm.write(f"{YELLOW}[Tab-{worker_id}] 弹窗通知失败: {notify_error}{RESET}")

        def get_first_post_preview(tab):
            try:
                first_item = tab.ele('.timeline__item', timeout=2)
                if not first_item:
                    return ""
                content_ele = first_item.ele('css:.timeline__item__content', timeout=0.5)
                preview_source = content_ele.text if content_ele and content_ele.text else ""
                if not preview_source:
                    title_ele = first_item.ele('.timeline__item__title', timeout=0.5)
                    preview_source = title_ele.text if title_ele and title_ele.text else ""
                preview_source = re.sub(r'[\r\n\s]+', ' ', preview_source).strip()
                return preview_source[:30]
            except Exception:
                return ""

        def sleep_before_page_turn(worker_id, target_page):
            delay = random.uniform(1, 2)
            # tqdm.write(f"{CYAN}[Tab-{worker_id}] 翻到第 {target_page} 页前暂停 {delay:.1f} 秒...{RESET}")
            # time.sleep(delay)

        def click_next_page(tab, expected_page, previous_preview):
            next_selectors = (
                'text=下一页',
                'text=下页',
                'css:.pagination .next:not(.disabled)',
                'css:.pagination li.next:not(.disabled)',
                'css:.pagination li:last-child',
            )
            for selector in next_selectors:
                btn = tab.ele(selector, timeout=1.5)
                if not btn:
                    continue
                try:
                    btn.click(by_js=True)
                except:
                    try:
                        btn.click()
                    except:
                        continue
                time.sleep(4)
                detect_slider_challenge(tab, f"翻到第 {expected_page} 页")
                current_preview = get_first_post_preview(tab)
                if get_active_page(tab) == str(expected_page):
                    if previous_preview and current_preview == previous_preview:
                        notify_page_turn_failed(worker_id, expected_page, current_preview)
                        return False
                    return True
            return False

        def page_worker(worker_id, target_pages):
            if not target_pages: return
            
            tab = self.page if worker_id == 0 else self.page.new_tab(user_url)
            time.sleep(2)
            detect_slider_challenge(tab, f"打开 Tab-{worker_id}")
            
            for page_index, current_p in enumerate(target_pages):
                if self.stop_event.is_set():
                    break
                try:
                    tqdm.write(f"{CYAN}[Tab-{worker_id}] 正在处理第 {current_p} 页...{RESET}")
                    
                    # 每个 worker 仅在分段起始页做一次定位，后续页面只点“下一页”
                    jump_success = False
                    if page_index == 0:
                        for attempt in range(3):
                            if get_active_page(tab) == str(current_p):
                                jump_success = True
                                break
                            sleep_before_page_turn(worker_id, current_p)
                            tab.scroll.to_bottom()
                            time.sleep(1)
                            if jump_with_input(tab, current_p):
                                jump_success = True
                                break
                            btn = tab.ele(f'text={current_p}', timeout=2)
                            if btn:
                                try:
                                    btn.click(by_js=True)
                                except:
                                    btn.click()
                                time.sleep(4)
                                if get_active_page(tab) == str(current_p):
                                    jump_success = True
                                    break
                            if attempt == 0:
                                tqdm.write(f"{YELLOW}[Tab-{worker_id}] 第 {current_p} 页未找到页码输入框，尝试先回到第一页再跳转。{RESET}")
                                if reset_to_first_page(tab):
                                    tab.scroll.to_bottom()
                                    time.sleep(1)
                                    if jump_with_input(tab, current_p):
                                        jump_success = True
                                        break
                    else:
                        previous_preview = get_first_post_preview(tab)
                        sleep_before_page_turn(worker_id, current_p)
                        tab.scroll.to_bottom()
                        time.sleep(1)
                        jump_success = click_next_page(tab, current_p, previous_preview)
                    
                    if not jump_success:
                        tqdm.write(f"{RED}[Tab-{worker_id}] 第 {current_p} 页跳转校验失败，跳过。{RESET}")
                        with self.save_lock: progress_bar.update(1)
                        continue

                    old_first_id = None
                    try:
                        fi = tab.ele('.timeline__item', timeout=2)
                        if fi: old_first_id = str(fi.ele('.date-and-source').attr('data-id'))
                    except Exception as e:
                        raise_if_page_disconnected(e, worker_id)

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
                                    except Exception as e:
                                        raise_if_page_disconnected(e, worker_id)
                                
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
                            except Exception as e:
                                raise_if_page_disconnected(e, worker_id)
                                continue

                        if page_data:
                            with self.save_lock:
                                final = []
                                for d in page_data:
                                    if d['ID'] in existing_ids:
                                        duplicate_text = (d.get('正文') or '').replace('\r', ' ').replace('\n', ' ').strip()
                                        tqdm.write(
                                            f"{YELLOW}[Tab-{worker_id}] 重复跳过 | ID: {d['ID']} | 页码: {d.get('页码', '未知')} | 正文: {duplicate_text[:120]}{RESET}"
                                        )
                                        continue
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

                except KeyboardInterrupt:
                    self.stop_event.set()
                    raise
                except Exception as e:
                    raise_if_page_disconnected(e, worker_id)
                    tqdm.write(f"{RED}[Tab-{worker_id}] 异常: {e}{RESET}")
                    with self.save_lock: progress_bar.update(1)
            
            if worker_id > 0:
                try:
                    tab.close()
                except Exception:
                    pass

        actual_workers = len(chunks)
        executor = ThreadPoolExecutor(max_workers=actual_workers)
        futures = [executor.submit(page_worker, i, chunks[i]) for i in range(actual_workers)]
        try:
            for future in futures:
                future.result()
        except KeyboardInterrupt:
            self.stop_event.set()
            tqdm.write(f"{YELLOW}[!] 收到 Ctrl+C，正在停止所有并发任务...{RESET}")
            executor.shutdown(wait=False, cancel_futures=True)
            raise
        except RuntimeError as e:
            if str(e) == "PAGE_DISCONNECTED":
                self.stop_event.set()
                tqdm.write(f"{RED}[!] 检测到页面链接断开，已取消所有 worker 和后续任务。{RESET}")
                executor.shutdown(wait=False, cancel_futures=True)
                raise
            raise
        finally:
            progress_bar.close()
            executor.shutdown(wait=False, cancel_futures=True)

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
        except KeyboardInterrupt:
            self.stop_event.set()
            print(f"{YELLOW}[!] 已收到 Ctrl+C，爬虫正在停止。{RESET}")
            raise
        except RuntimeError as e:
            if str(e) == "PAGE_DISCONNECTED":
                self.stop_event.set()
                print(f"{RED}[!] 页面链接已断开，已停止所有并发任务。{RESET}")
                raise
            raise
        finally:
            self.page.quit()

if __name__ == "__main__":
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from config import DEFAULT_USERNAME, DEFAULT_USER_ID, FILTER_REGEX, TYPE_PARAM
    spider = XueqiuShortPostSpider(DEFAULT_USERNAME, DEFAULT_USER_ID, type_param=TYPE_PARAM, filter_regex=FILTER_REGEX)
    spider.run(start_page=1, end_page=2)
