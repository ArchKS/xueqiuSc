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
import colorama
import config
from config import DEFAULT_USERNAME, DEFAULT_USER_ID, FILTER_REGEX

# 初始化 colorama 以支持 Windows 颜色输出
colorama.init(autoreset=True)

# 颜色常量
GREEN = colorama.Fore.GREEN
YELLOW = colorama.Fore.YELLOW
RED = colorama.Fore.RED
BLUE = colorama.Fore.BLUE
RESET = colorama.Style.RESET_ALL

class XueqiuLongPostSpider:
    def __init__(self, username, user_id, xq_a_token=None, type_param=0, filter_regex=None):
        self.username = username
        self.user_id = user_id
        self.xq_a_token = xq_a_token  # 保留参数以防需要，但不再使用
        self.type_param = type_param  # 0: 原发, None: 包含转发
        # 过滤规则（正则），匹配则不保存该条发言
        if filter_regex:
            self.filter_patterns = [re.compile(p, re.I) for p in filter_regex]
        else:
            self.filter_patterns = []
        
        # 性能优化配置
        from DrissionPage import ChromiumOptions
        co = ChromiumOptions()
        co.no_imgs(config.NO_IMG)           # 禁用图片加载
        co.set_load_mode('eager')  # DOM 加载完即返回，不等待图片和广告        # 预连接雪球，减少 DNS 解析和握手时间
        co.set_argument('--dns-prefetch-disable', 'false')        
        # 初始化浏览器页面对象
        self.page = ChromiumPage(co)
        
    def clean_html(self, html_text):
        """去除 HTML 标签，如 <a>AAA</a> 简化为 AAA"""
        if not html_text:
            return ""
        # 移除所有 HTML 标签
        clean_text = re.sub(r'<[^>]+>', '', html_text)
        # 替换常见的 HTML 实体
        clean_text = clean_text.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
        return clean_text.strip()

    def format_date(self, date_str):
        """统一日期格式为 YYYY-MM-DD HH:mm，并补齐缺失的年份"""
        if not date_str:
            return datetime.now().strftime('%Y-%m-%d %H:%M')
        
        # 彻底清理：移除“修改于”、“· 来自...”等干扰词
        clean_str = re.sub(r'修改于', '', str(date_str))
        clean_str = re.sub(r'·.*$', '', clean_str).strip()
        
        from datetime import datetime, timedelta
        now = datetime.now()
        current_year = now.year

        try:
            # 1. 处理“n分钟前” / “n小时前”
            if '分钟前' in clean_str:
                m = int(re.search(r'\d+', clean_str).group())
                return (now - timedelta(minutes=m)).strftime('%Y-%m-%d %H:%M')
            if '小时前' in clean_str:
                h = int(re.search(r'\d+', clean_str).group())
                return (now - timedelta(hours=h)).strftime('%Y-%m-%d %H:%M')
            
            # 2. 处理“今天 HH:mm” / “昨天 HH:mm”
            if '今天' in clean_str:
                time_match = re.search(r'\d{2}:\d{2}', clean_str)
                time_part = time_match.group() if time_match else now.strftime('%H:%M')
                return f"{now.strftime('%Y-%m-%d')} {time_part}"
            if '昨天' in clean_str:
                time_match = re.search(r'\d{2}:\d{2}', clean_str)
                time_part = time_match.group() if time_match else now.strftime('%H:%M')
                yesterday = (now - timedelta(days=1)).strftime('%Y-%m-%d')
                return f"{yesterday} {time_part}"

            # 3. 提取标准的日期时间部分
            # 优先匹配全量格式 YYYY-MM-DD HH:mm
            m_full = re.search(r'(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})', clean_str)
            if m_full:
                return f"{m_full.group(1)} {m_full.group(2)}"
            
            # 匹配短格式 MM-DD HH:mm
            m_short = re.search(r'(\d{2}-\d{2})\s+(\d{2}:\d{2})', clean_str)
            if m_short:
                date_part = m_short.group(1) # MM-DD
                time_part = m_short.group(2) # HH:mm
                month = int(date_part.split('-')[0])
                # 如果月份大于当前月份，推定为去年
                year = current_year if month <= now.month else current_year - 1
                return f"{year}-{date_part} {time_part}"
            
            # 匹配纯日期 YYYY-MM-DD
            m_date = re.search(r'(\d{4}-\d{2}-\d{2})', clean_str)
            if m_date:
                return f"{m_date.group(1)} 00:00"

            # 兜底：如果只是 MM-DD
            m_only_date = re.search(r'(\d{2}-\d{2})', clean_str)
            if m_only_date:
                date_part = m_only_date.group(1)
                month = int(date_part.split('-')[0])
                year = current_year if month <= now.month else current_year - 1
                return f"{year}-{date_part} 00:00"

            return clean_str
        except Exception:
            return clean_str

    def get_page_json(self):
        """兼容不同平台/不同 Chromium 渲染模式下的 JSON 页面读取。"""
        # 方案 1：优先使用 DrissionPage 自带 json 属性（Windows 上通常可直接拿到 dict）
        try:
            data = self.page.json
            if isinstance(data, dict):
                return data
        except Exception:
            pass

        # 方案 2：某些环境（当前这台 Mac）会把 JSON 渲染在 <pre> 里
        try:
            pre = self.page.ele('tag:pre', timeout=0.5)
            if pre and pre.text:
                return json.loads(pre.text)
        except Exception:
            pass

        # 方案 3：兜底从页面 HTML 中提取 <pre>...</pre>
        try:
            html = self.page.html or ''
            m = re.search(r'<pre[^>]*>(.*?)</pre>', html, re.S | re.I)
            if m:
                return json.loads(unescape(m.group(1)))
        except Exception:
            pass

        return None

    def fetch_detail(self, url, post_date):
        """访问帖子详情页获取完整正文"""
        fetch_start = time.time()
        try:
            # 访问详情页
            self.page.get(url)
            
            # 极致优化：缩短每个选择器的超时时间，一旦发现正文立即跳出
            selectors = [
                '.status-detail', 
                '.article__content', 
                '.post__description',
                '.article-item__content',
                'div.content'
            ]
            
            content = ""
            for selector in selectors:
                # 尝试快速寻找元素，超时设为 0.5s
                ele = self.page.ele(selector, timeout=0.5)
                if ele and ele.text:
                    content = ele.text
                    break
            
            # 如果还是没找到，尝试极速扫描 article 标签
            if not content:
                main_article = self.page.ele('tag:article', timeout=0.3)
                if main_article:
                    content = main_article.text
            
            return content.strip(), fetch_start
        except Exception as e:
            print(f"  [!] 详情页抓取失败: {url}, 错误: {e}")
            return "", fetch_start

    def setup_cookies(self):
        """设置初始 Cookie 并访问主页过验证"""
        print(f"{GREEN}[+] 正在启动浏览器并访问雪球...{RESET}")
        self.page.get("https://xueqiu.com/")
        
        if self.xq_a_token:
            print(f"{GREEN}[+] 正在设置 xq_a_token...{RESET}")
            self.page.set.cookies({'name': 'xq_a_token', 'value': self.xq_a_token, 'domain': '.xueqiu.com'})
        
        user_url = f"https://xueqiu.com/u/{self.user_id}"
        self.page.get(user_url)
        print(f"{GREEN}[+] 等待 WAF 验证完成...{RESET}")
        time.sleep(5)

    def fetch_posts(self, start_page=1, end_page=None, existing_ids=None, filename=None):
        """抓取用户帖子列表并深入抓取正文，每页结束后追加到文件"""
        all_data = []
        job_start = time.time()
        
        if existing_ids is None:
            existing_ids = set()
            
        current_page = start_page
        max_page_limit = end_page if end_page else 9999
        actual_max_page = 0
        total_expected = 0
        last_id = None # 用于 max_id 分页
        last_page_first_id = None # 用于验证页面是否更新

        while current_page <= max_page_limit:
            # 构造 URL，如果不是第一页则带上 max_id (雪球更推荐的分页方式，更稳定)
            api_url = f"https://xueqiu.com/v4/statuses/user_timeline.json?page={current_page}&user_id={self.user_id}&count=20"
            if self.type_param is not None:
                api_url += f"&type={self.type_param}"
            if last_id and current_page > 1:
                api_url += f"&max_id={last_id}"
            
            # 关键修复：先回到个人主页建立 Referer 上下文，防止直接跳转 API 触发 WAF 令牌挑战
            if self.page.url != f"https://xueqiu.com/u/{self.user_id}":
                self.page.get(f"https://xueqiu.com/u/{self.user_id}")
                time.sleep(1)

            print(f"{BLUE}正在获取第 {current_page} 页列表...{RESET}")
            
            # 添加重试机制，处理反爬
            max_retries = 3
            res_data = None
            for attempt in range(max_retries):
                if attempt > 0:
                    print(f"{YELLOW}[-] 重试前使用基本 URL 重新获取...{RESET}")
                    try:
                        self.setup_cookies()
                        # 使用不带可选参数的基本 URL 重试，避免触发 md5__1038 等参数
                        retry_url = f"https://xueqiu.com/v4/statuses/user_timeline.json?page={current_page}&user_id={self.user_id}&count=20"
                        if self.type_param is not None:
                            retry_url += f"&type={self.type_param}"
                        print(f"{GREEN}[+] 重试请求 URL: {retry_url}{RESET}")
                        self.page.get(retry_url)
                    except Exception as init_e:
                        print(f"{RED}[-] 重新初始化失败: {init_e}{RESET}")
                        continue  # 跳过这次重试
                
                else:
                    print(f"{GREEN}[+] 请求 URL: {api_url}{RESET}")
                    self.page.get(api_url)
                
                # 等待潜在的 WAF 跳转完成（处理 md5__1038 等令牌挑战）
                for _ in range(5):
                    try:
                        res_data = self.get_page_json()
                        if res_data and 'statuses' in res_data:
                            break
                    except Exception as e:
                        print(f"{RED}[-] JSON 解析失败: {e}{RESET}")
                        res_data = None
                    time.sleep(1)
                
                if res_data and 'statuses' in res_data:
                    statuses = res_data['statuses']
                    if statuses:
                        current_first_id = str(statuses[0].get('id'))
                        if current_page > 1 and current_first_id == last_page_first_id:
                            print(f"{YELLOW}[!] 警告：第 {current_page} 页获取到的数据与上一页完全一致，可能是翻页失效或缓存，正在重试...{RESET}")
                            time.sleep(5)
                            continue
                        last_page_first_id = current_first_id
                    
                    break
                else:
                    print(f"{RED}[-] 第 {current_page} 页获取失败 (尝试 {attempt+1}/{max_retries})，等待重试...{RESET}")
                    time.sleep(5 + attempt * 2)  # 递增等待时间
            
            try:
                if not res_data or 'statuses' not in res_data:
                    print(f"{RED}[-] 第 {current_page} 页跳过，继续下一页。{RESET}")
                    current_page += 1
                    continue
                
                # 自动检测最大页码
                if current_page == start_page:
                    actual_max_page = res_data.get('maxPage', 1)
                    total_expected_count = res_data.get('total', 0)
                    if end_page is None:
                        max_page_limit = actual_max_page
                    
                    # 确定本次任务的精确/预估总数
                    effective_end_page = min(max_page_limit, actual_max_page)
                    
                    if start_page == 1 and (end_page is None or end_page >= actual_max_page):
                        # 1. 全量爬取：直接使用 API 提供的精确总数
                        total_expected = total_expected_count
                    else:
                        # 2. 范围爬取：使用估算值 (每页20条)
                        total_expected = (effective_end_page - start_page + 1) * 20
                        
                    print(f"{BLUE}[!] 检测到该用户总共有 {actual_max_page} 页，共 {total_expected_count} 条发言{RESET}")
                
                statuses = res_data['statuses']
                if not statuses:
                    break
                
                # 更新 last_id 用于下一页
                if statuses:
                    last_id = statuses[-1].get('id')
                
                total_in_page = len(statuses)
                page_data = []  # 该页数据
                for idx, status in enumerate(statuses, 1):
                    post_id = str(status.get('id'))
                    post_date = datetime.fromtimestamp(status.get('created_at') / 1000).strftime('%Y-%m-%d %H:%M') if status.get('created_at') else '未知时间'
                    
                    # 进度字符串
                    items_done = len(all_data) + 1 # 包含当前这一个
                    elapsed = time.time() - job_start
                    if items_done > 1:
                        avg_time = elapsed / items_done
                        # 修正剩余任务估算：基于当前页到结束页的剩余项
                        remaining_pages = max(0, max_page_limit - current_page)
                        remaining_items_in_current_page = total_in_page - idx
                        remaining_tasks = (remaining_pages * 20) + remaining_items_in_current_page
                        
                        eta_seconds = remaining_tasks * avg_time
                        m, s = divmod(int(elapsed), 60)
                        rem_m, rem_s = divmod(int(eta_seconds), 60)
                        time_str = f"{m:02d}m{s:02d}s 剩{rem_m:02d}m{rem_s:02d}s"
                    else:
                        time_str = "计算中..."
                    
                    # 在输出中明确显示当前页码
                    progress_info = f"[P{current_page}/{actual_max_page} {idx:2d}/{total_in_page:2d}] (总:{items_done:3d})"

                    # 长文不去重
                    # if post_id in existing_ids:
                    #     print(f"{progress_info} | \033[33m[跳过] {post_date} {post_id} | 已存在于本地\033[0m")
                    #     continue
                        
                    # 获取 API 里的原始正文
                    raw_text = status.get('text', '')
                    raw_description = status.get('description', '')
                    can_expand = status.get('expend', False)
                    
                    item = {
                        'ID': str(status.get('id')),
                        '发布时间': self.format_date(post_date),
                        '点赞数': status.get('like_count') or 0,
                        '评论数': status.get('reply_count') or 0,
                        '转发数': status.get('retweet_count') or 0,
                        '页码': f"{current_page}/{actual_max_page}",
                        '链接': f"https://xueqiu.com{status.get('target')}",
                        '摘要': self.clean_html(raw_description),
                    }
                    
                    # 记录单篇帖子开始处理的时间
                    post_process_start = time.time()
                    
                    # 抓取详情或直接使用
                    post_url = item['链接']
                    if can_expand and post_url and 'xueqiu.com' in post_url:
                        full_content, fetch_start = self.fetch_detail(post_url, post_date)
                        item['正文'] = full_content if full_content else self.clean_html(raw_text)
                        
                        # 检查字数并暂停程序
                        if not item['正文'] or len(item['正文'].strip()) == 0:
                            print(f"{RED}[!] 当前已经获取不到内容 (字数为0) | 链接: {post_url}{RESET}")
                            input(f"{YELLOW}请检查浏览器是否遇到反爬挑战，处理完毕后按回车继续...{RESET}")
                        
                        # 动态停留逻辑
                        content_len = len(item['正文'])
                        target_wait = 1 + min(4, content_len / 1000)
                        time_already_spent = time.time() - fetch_start
                        actual_sleep = max(0.1, target_wait - time_already_spent)
                        
                        time.sleep(actual_sleep)
                        # 计算单篇总耗时
                        post_duration = time.time() - post_process_start
                        print(f"{progress_info} | \033[34m[抓取] {content_len:5d}字 | {post_date} | ID:{post_id}\033[0m")
                    else:
                        item['正文'] = self.clean_html(raw_text)
                        status_msg = "\033[32m[完整] 直接获取\033[0m" if not can_expand else "\033[32m[限制] 无链接跳过\033[0m"
                        print(f"{progress_info} | {status_msg} | {post_date} | ID:{post_id}")
                    
                    # 标题/内容打印与正则过滤
                    title_str = item['摘要'].strip() if item['摘要'] else item['正文'][:10].strip()
                    if any(p.search(title_str) for p in self.filter_patterns):
                        print(f"{progress_info} | \033[33m[过滤] {title_str}\033[0m")
                        continue
                    print(f"    标题/内容: {title_str[:10]}")

                    all_data.append(item)
                    page_data.append(item)
                    existing_ids.add(post_id) # 立即加入已采集 ID 集合，防止本会话翻页回弹导致重复抓取
                
                print(f"\n{GREEN}[+] 第 {current_page} 页处理完成，当前累计 {len(all_data)} 条{RESET}")
                
                # 每页结束后追加到文件
                if page_data and filename:
                    page_df = pd.DataFrame(page_data)
                    # 确保列顺序一致
                    cols_to_save = ['ID', '发布时间', '点赞数', '评论数', '转发数', '页码', '链接', '摘要', '正文']
                    page_df = page_df[[c for c in cols_to_save if c in page_df.columns]]
                    page_df.to_csv(filename, mode='a', header=not os.path.exists(filename), index=False, encoding='utf-8-sig')
                    
                    # 计算耗时与 ETA
                    elapsed = time.time() - job_start
                    pages_done = current_page - start_page + 1
                    avg_time_per_page = elapsed / pages_done
                    remaining_pages = max(0, max_page_limit - current_page)
                    
                    eta_seconds = remaining_pages * avg_time_per_page
                    total_seconds = elapsed + eta_seconds
                    
                    def format_hms(s):
                        h, m = divmod(int(s), 3600)
                        m, s = divmod(m, 60)
                        return f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"

                    progress_time = f"{format_hms(eta_seconds)} / {format_hms(total_seconds)}"
                    print(f"{GREEN}[+] 已追加 {len(page_data)} 条记录到文件 | 预估剩余/总计: {progress_time}{RESET}")
                
                current_page += 1
                
            except Exception as e:
                print(f"{RED}[-] 处理第 {current_page} 页时出错: {e}，重新初始化浏览器并跳过该页{RESET}")
                try:
                    self.setup_cookies()
                except Exception as init_e:
                    print(f"{RED}[-] 重新初始化失败: {init_e}{RESET}")
                current_page += 1
                continue
            time.sleep(2)
        return all_data

    def run(self, start_page=1, end_page=None):
        try:
            # 确保 data 目录存在
            if not os.path.exists("data"):
                os.makedirs("data")
            filename = os.path.join("data", f"{self.username}.csv")

            # 加载现有数据用于去重
            existing_ids = set()
            if os.path.exists(filename):
                try:
                    # 先读取现有列名
                    temp_df = pd.read_csv(filename, encoding='utf-8-sig', nrows=0)
                    # 如果缺少页码列，则需要全量读取并补充，否则后续追加会错位
                    if '页码' not in temp_df.columns:
                        existing_df = pd.read_csv(filename, encoding='utf-8-sig')
                        idx = existing_df.columns.get_loc('转发数') + 1 if '转发数' in existing_df.columns else len(existing_df.columns)
                        existing_df.insert(idx, '页码', '旧数据/未知')
                        existing_df.to_csv(filename, index=False, encoding='utf-8-sig')
                        print(f"{YELLOW}[!] 已为旧数据补充 '页码' 列。{RESET}")
                        existing_ids = set(existing_df['ID'].astype(str).tolist())
                    else:
                        # 仅读取 ID 列用于去重，节省内存
                        id_df = pd.read_csv(filename, encoding='utf-8-sig', usecols=['ID'])
                        existing_ids = set(id_df['ID'].astype(str).tolist())
                    
                    print(f"{BLUE}已加载本地数据，包含 {len(existing_ids)} 条记录。{RESET}")
                except Exception as e:
                    print(f"{RED}[!] 读取旧文件失败: {e}{RESET}")

            self.setup_cookies()
            # 传入已有的 IDs 避免重复爬取详情页，每页追加到文件
            self.fetch_posts(start_page, end_page, existing_ids, filename)
            
            if os.path.exists(filename):
                # 最终去重与排序：fetch_posts 已经把新旧数据都存进去了
                df = pd.read_csv(filename, encoding='utf-8-sig')
                
                # 根据 ID 去重，保留最新的记录
                df['ID'] = df['ID'].astype(str)
                df.drop_duplicates(subset=['ID'], keep='last', inplace=True)
                
                # 统一日期格式
                if '发布时间' in df.columns:
                    print(f"{BLUE}[+] 正在统一日期格式...{RESET}")
                    df['发布时间'] = df['发布时间'].apply(self.format_date)
                
                # 重新排序字段
                cols = ['ID', '发布时间', '点赞数', '评论数', '转发数', '页码', '链接', '摘要', '正文']
                df = df[[c for c in cols if c in df.columns]]
                # 按时间排序
                df.sort_values(by='发布时间', ascending=False, inplace=True)
                
                df.to_csv(filename, index=False, encoding='utf-8-sig')
                print(f"{BLUE}[!] 任务完成！当前共 {len(df)} 条唯一记录至 {filename}{RESET}")
            else:
                print(f"{RED}[-] 未获取到新数据。{RESET}")
        finally:
            print(f"{GREEN}[+] 任务结束，正在关闭浏览器...{RESET}")
            self.page.quit()

if __name__ == "__main__":
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
   
    
    # 支持命令行 --type=X
    for arg in sys.argv:
        if arg.startswith("--type="):
            try:
                val = arg.split("=")[1]
                if val.lower() == "none":
                    config.TYPE_PARAM = None
                else:
                    config.TYPE_PARAM = int(val)
            except:
                pass

    # XQ_A_TOKEN 不再需要，依赖 run.py 中的浏览器登录会话
    spider = XueqiuLongPostSpider(DEFAULT_USERNAME, DEFAULT_USER_ID, type_param=config.TYPE_PARAM, filter_regex=FILTER_REGEX)
    # 限制抓取页数以供测试
    spider.run(start_page=1, end_page=2) 

