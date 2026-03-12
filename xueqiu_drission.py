from DrissionPage import ChromiumPage
import time
import os
import pandas as pd
import json
import re
import random
from datetime import datetime

class XueqiuDrissionSpider:
    def __init__(self, username, user_id, xq_a_token=None):
        self.username = username
        self.user_id = user_id
        self.xq_a_token = xq_a_token  # 保留参数以防需要，但不再使用
        
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
        print("[+] 正在启动浏览器并访问雪球...")
        self.page.get("https://xueqiu.com/")
        self.page.get("https://xueqiu.com/")
        
        if self.xq_a_token:
            print("[+] 正在设置 xq_a_token...")
            self.page.set.cookies({'name': 'xq_a_token', 'value': self.xq_a_token, 'domain': '.xueqiu.com'})
        
        user_url = f"https://xueqiu.com/u/{self.user_id}"
        self.page.get(user_url)
        print("[+] 等待 WAF 验证完成...")
        time.sleep(5)

    def fetch_posts(self, start_page=1, end_page=None, existing_ids=None):
        """抓取用户帖子列表并深入抓取正文"""
        all_data = []
        job_start = time.time()
        
        if existing_ids is None:
            existing_ids = set()
            
        current_page = start_page
        max_page_limit = end_page if end_page else 9999
        total_expected = 0

        while current_page <= max_page_limit:
            print(f"[*] 正在获取第 {current_page} 页列表...")
            api_url = f"https://xueqiu.com/v4/statuses/user_timeline.json?page={current_page}&user_id={self.user_id}&count=20"
            self.page.get(api_url)
            
            try:
                res_data = self.page.json
                if not res_data or 'statuses' not in res_data:
                    print(f"[-] 第 {current_page} 页未获取到列表。")
                    break
                
                # 自动检测最大页码
                if current_page == start_page:
                    actual_max_page = res_data.get('maxPage', 1)
                    total_expected_count = res_data.get('total', 0)
                    if end_page is None:
                        max_page_limit = actual_max_page
                    print(f"[!] 检测到该用户总共有 {actual_max_page} 页，共 {total_expected_count} 条发言")
                    total_expected = (max_page_limit - start_page + 1) * 20 # 预估总数
                
                statuses = res_data['statuses']
                if not statuses:
                    break
                
                total_in_page = len(statuses)
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
                    
                    progress_info = f"[*] [{idx}/{total_in_page}] (总:{items_done}) [{time_str}] {post_date}"

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
                        '摘要': self.clean_html(raw_description),
                        '点赞数': status.get('like_count'),
                        '评论数': status.get('reply_count'),
                        '转发数': status.get('retweet_count'),
                        '链接': f"https://xueqiu.com{status.get('target')}"
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
                    
                    all_data.append(item)
                
                print(f"\n[+] 第 {current_page} 页处理完成，当前累计 {len(all_data)} 条")
                current_page += 1
                
            except Exception as e:
                print(f"[-] 处理第 {current_page} 页时出错: {e}")
                break
                
            time.sleep(2)
            
        return all_data

    def run(self, start_page=1, end_page=None):
        try:
            # 确保 data 目录存在
            if not os.path.exists("data"):
                os.makedirs("data")
            filename = os.path.join("data", f"xueqiu_full_{self.username}.csv")
            
            # 加载现有数据用于去重
            existing_ids = set()
            existing_df = pd.DataFrame()
            if os.path.exists(filename):
                try:
                    existing_df = pd.read_csv(filename, encoding='utf-8-sig')
                    existing_ids = set(existing_df['ID'].astype(str).tolist())
                    print(f"[*] 已加载本地数据，包含 {len(existing_ids)} 条记录。")
                except Exception as e:
                    print(f"[!] 读取旧文件失败，将作为新任务开始: {e}")

            self.setup_cookies()
            # 传入已有的 IDs 避免重复爬取详情页
            data = self.fetch_posts(start_page, end_page, existing_ids)
            
            if data:
                new_df = pd.DataFrame(data)
                # 合并新旧数据
                if not existing_df.empty:
                    df = pd.concat([existing_df, new_df], ignore_index=True)
                else:
                    df = new_df
                
                # 根据 ID 去重，保留最新的记录（通常新爬取的在前或后，这里统一去重）
                df['ID'] = df['ID'].astype(str)
                df.drop_duplicates(subset=['ID'], keep='last', inplace=True)
                
                # 重新排序字段
                cols = ['ID', '发布时间', '点赞数', '评论数', '转发数', '链接', '摘要', '正文']
                df = df[cols]
                # 按时间排序（可选，方便查看）
                df.sort_values(by='发布时间', ascending=False, inplace=True)
                
                df.to_csv(filename, index=False, encoding='utf-8-sig')
                print(f"[!] 任务完成！共保存 {len(df)} 条唯一记录至 {filename}")
            else:
                print("[-] 未获取到新数据。")
        finally:
            print("[+] 任务结束，正在关闭浏览器...")
            self.page.quit()

if __name__ == "__main__":
    USERNAME = "KeepSlowly"
    USER_ID = "2287364713"
    # XQ_A_TOKEN 不再需要，依赖 run.py 中的浏览器登录会话
    
    spider = XueqiuDrissionSpider(USERNAME, USER_ID)
    # 不传参数默认爬取全部页码
    spider.run() 

