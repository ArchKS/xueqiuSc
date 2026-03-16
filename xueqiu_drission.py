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

# 颜色常量
GREEN = '\033[32m'
YELLOW = '\033[33m'
RED = '\033[31m'
BLUE = '\033[34m'
RESET = '\033[0m'

class XueqiuDrissionSpider:
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
        co.no_imgs(True)           # 禁用图片加载
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

    def append_raw_json(self, data, page_no):
        """将每页原始 JSON 追加保存到 json 目录。"""
        if not data:
            return
        json_dir = 'json'
        if not os.path.exists(json_dir):
            os.makedirs(json_dir)

        file_path = os.path.join(json_dir, f'xueqiu_raw_{self.username}.jsonl')
        record = {
            'page': page_no,
            'user_id': self.user_id,
            'username': self.username,
            'saved_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'data': data,
        }
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False))
            f.write('\n')

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
        
        # 确保 json 目录存在
        if not os.path.exists("json"):
            os.makedirs("json")
        
        if existing_ids is None:
            existing_ids = set()
            
        current_page = start_page
        max_page_limit = end_page if end_page else 9999
        actual_max_page = 0
        total_expected = 0
        last_id = None # 用于 max_id 分页

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
                    # 保存 JSON 到分页文件
                    json_file = os.path.join("json", f"page_{current_page}.json")
                    with open(json_file, 'w', encoding='utf-8') as f:
                        json.dump(res_data, f, ensure_ascii=False, indent=4)
                    print(f"{GREEN}[+] 已保存第 {current_page} 页 JSON 到 {json_file}{RESET}")
                    break
                else:
                    print(f"{RED}[-] 第 {current_page} 页获取失败 (尝试 {attempt+1}/{max_retries})，等待重试...{RESET}")
                    time.sleep(5 + attempt * 2)  # 递增等待时间
            
            try:
                if not res_data or 'statuses' not in res_data:
                    print(f"{RED}[-] 第 {current_page} 页跳过，继续下一页。{RESET}")
                    current_page += 1
                    continue

                # 追加保存原始 JSON，便于排查接口返回差异
                try:
                    self.append_raw_json(res_data, current_page)
                    print(f"{GREEN}[+] 已追加保存第 {current_page} 页原始 JSON 到 json 目录{RESET}")
                except Exception as save_e:
                    print(f"{RED}[!] 保存第 {current_page} 页原始 JSON 失败: {save_e}{RESET}")
                
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
                    post_date = datetime.fromtimestamp(status.get('created_at') / 1000).strftime('%Y-%m-%d %H:%M:%S') if status.get('created_at') else '未知时间'
                    
                    # 进度字符串
                    items_done = len(all_data) + 1 # 包含当前这一个
                    elapsed = time.time() - job_start
                    if items_done > 1:
                        avg_time = elapsed / items_done
                        remaining_tasks = max(0, ((max_page_limit - start_page + 1) * 20) - items_done)
                        eta_seconds = remaining_tasks * avg_time
                        m, s = divmod(int(elapsed), 60)
                        rem_m, rem_s = divmod(int(eta_seconds), 60)
                        time_str = f"{m:02d}m{s:02d}s 剩{rem_m:02d}m{rem_s:02d}s"
                    else:
                        time_str = "计算中..."
                    
                    progress_info = f"[{idx}/{total_in_page}] (总:{items_done}/{total_expected}) [{time_str}] {post_date}"

                    if post_id in existing_ids:
                        print(f"{progress_info} | \033[33m[跳过] 已存在于本地\033[0m")
                        continue
                        
                    # 获取 API 里的原始正文
                    raw_text = status.get('text', '')
                    raw_description = status.get('description', '')
                    can_expand = status.get('expend', False)
                    
                    item = {
                        'ID': status.get('id'),
                        '发布时间': post_date,
                        '点赞数': status.get('like_count'),
                        '评论数': status.get('reply_count'),
                        '转发数': status.get('retweet_count'),
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
                        
                        # 动态停留逻辑
                        content_len = len(item['正文'])
                        target_wait = 1 + min(4, content_len / 1000)
                        time_already_spent = time.time() - fetch_start
                        actual_sleep = max(0.1, target_wait - time_already_spent)
                        
                        time.sleep(actual_sleep)
                        # 计算单篇总耗时
                        post_duration = time.time() - post_process_start
                        print(f"{progress_info} | \033[34m[抓取] {content_len}字 | 耗时:{post_duration:.1f}s\033[0m")
                    else:
                        item['正文'] = self.clean_html(raw_text)
                        status_msg = "\033[32m[完整] 直接获取\033[0m" if not can_expand else "\033[32m[限制] 无链接跳过\033[0m"
                        # 计算单篇总耗时
                        post_duration = time.time() - post_process_start
                        print(f"{progress_info} | {status_msg} | 耗时:{post_duration:.2f}s")
                    
                    # 标题/内容打印与正则过滤
                    title_str = item['摘要'].strip() if item['摘要'] else item['正文'][:10].strip()
                    if any(p.search(title_str) for p in self.filter_patterns):
                        print(f"{progress_info} | \033[33m[过滤] {title_str}\033[0m")
                        continue
                    print(f"    标题/内容: {title_str[:10]}")

                    all_data.append(item)
                    page_data.append(item)
                
                print(f"\n{GREEN}[+] 第 {current_page} 页处理完成，当前累计 {len(all_data)} 条{RESET}")
                
                # 每页结束后追加到文件
                if page_data and filename:
                    page_df = pd.DataFrame(page_data)
                    # 确保列顺序一致
                    cols_to_save = ['ID', '发布时间', '点赞数', '评论数', '转发数', '页码', '链接', '摘要', '正文']
                    page_df = page_df[[c for c in cols_to_save if c in page_df.columns]]
                    page_df.to_csv(filename, mode='a', header=not os.path.exists(filename), index=False, encoding='utf-8-sig')
                    print(f"{GREEN}[+] 已追加 {len(page_data)} 条记录到文件{RESET}")
                
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

            # 每次运行前清空该用户旧的原始 jsonl，避免多次运行结果混在一起
            json_dir = 'json'
            if not os.path.exists(json_dir):
                os.makedirs(json_dir)
            raw_json_file = os.path.join(json_dir, f'xueqiu_raw_{self.username}.jsonl')
            if os.path.exists(raw_json_file):
                os.remove(raw_json_file)
                print(f"{GREEN}[+] 已清空旧的原始 JSON 文件: {raw_json_file}{RESET}")
            
            # 加载现有数据用于去重
            existing_ids = set()
            existing_df = pd.DataFrame()
            if os.path.exists(filename):
                try:
                    existing_df = pd.read_csv(filename, encoding='utf-8-sig')
                    # 如果缺少页码列，则补充（兼容旧版本数据）
                    if '页码' not in existing_df.columns:
                        # 在转发数后面插入页码列
                        idx = existing_df.columns.get_loc('转发数') + 1 if '转发数' in existing_df.columns else len(existing_df.columns)
                        existing_df.insert(idx, '页码', '1/1')
                        existing_df.to_csv(filename, index=False, encoding='utf-8-sig')
                        print(f"{YELLOW}[!] 检测到旧版本数据，已自动补充 '页码' 列。{RESET}")
                    
                    existing_ids = set(existing_df['ID'].astype(str).tolist())
                    print(f"{BLUE}已加载本地数据，包含 {len(existing_ids)} 条记录。{RESET}")
                except Exception as e:
                    print(f"{RED}[!] 读取旧文件失败，将作为新任务开始: {e}{RESET}")

            self.setup_cookies()
            # 传入已有的 IDs 避免重复爬取详情页，每页追加到文件
            self.fetch_posts(start_page, end_page, existing_ids, filename)
            
            if os.path.exists(filename):
                new_df = pd.read_csv(filename, encoding='utf-8-sig')
                # 合并新旧数据
                if not existing_df.empty:
                    df = pd.concat([existing_df, new_df], ignore_index=True)
                else:
                    df = new_df
                
                # 根据 ID 去重，保留最新的记录（通常新爬取的在前或后，这里统一去重）
                df['ID'] = df['ID'].astype(str)
                df.drop_duplicates(subset=['ID'], keep='last', inplace=True)
                
                # 重新排序字段
                cols = ['ID', '发布时间', '点赞数', '评论数', '转发数', '页码', '链接', '摘要', '正文']
                df = df[cols]
                # 按时间排序（可选，方便查看）
                df.sort_values(by='发布时间', ascending=False, inplace=True)
                
                df.to_csv(filename, index=False, encoding='utf-8-sig')
                print(f"{BLUE}[!] 任务完成！共保存 {len(df)} 条唯一记录至 {filename}{RESET}")
            else:
                print(f"{RED}[-] 未获取到新数据。{RESET}")
        finally:
            print(f"{GREEN}[+] 任务结束，正在关闭浏览器...{RESET}")
            self.page.quit()

if __name__ == "__main__":
    USERNAME = "KeepSlowly"
    USER_ID = "2287364713"
    # XQ_A_TOKEN 不再需要，依赖 run.py 中的浏览器登录会话
    
    spider = XueqiuDrissionSpider(USERNAME, USER_ID)
    # 不传参数默认爬取全部页码
    spider.run() 

