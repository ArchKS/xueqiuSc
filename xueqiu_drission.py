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
        self.xq_a_token = xq_a_token
        # 初始化浏览器页面对象
        self.page = ChromiumPage()
        
    def clean_html(self, html_text):
        """去除 HTML 标签，如 <a>AAA</a> 简化为 AAA"""
        if not html_text:
            return ""
        # 移除所有 HTML 标签
        clean_text = re.sub(r'<[^>]+>', '', html_text)
        # 替换常见的 HTML 实体
        clean_text = clean_text.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
        return clean_text.strip()

    def fetch_detail(self, url):
        """访问帖子详情页获取完整正文"""
        fetch_start = time.time()
        print(f"  [>] 正在爬取详情: {url}")
        try:
            # 访问详情页
            self.page.get(url)
            # 移除固定的 time.sleep，改为更智能的元素等待
            
            # 尝试不同的正文容器选择器
            selectors = [
                '.status-detail', 
                '.article__content', 
                '.post__description',
                '.article-item__content',
                'div.content'
            ]
            
            content = ""
            for selector in selectors:
                try:
                    # 使用较短的等待时间，如果页面已经加载完会很快
                    ele = self.page.ele(selector, timeout=2)
                    if ele and ele.text:
                        content = ele.text
                        break
                except:
                    continue
            
            # 如果还是没找到，尝试通过 HTML 结构获取较大的文本块
            if not content:
                main_article = self.page.ele('tag:article', timeout=1)
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
        
        if self.xq_a_token:
            print("[+] 正在设置 xq_a_token...")
            self.page.set.cookies({'name': 'xq_a_token', 'value': self.xq_a_token, 'domain': '.xueqiu.com'})
        
        user_url = f"https://xueqiu.com/u/{self.user_id}"
        self.page.get(user_url)
        print("[+] 等待 WAF 验证完成...")
        time.sleep(5)

    def fetch_posts(self, max_pages=None):
        """抓取用户帖子列表并深入抓取正文"""
        all_data = []
        job_start = time.time()
        
        current_page = 1
        max_page_limit = max_pages if max_pages else 9999
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
                if current_page == 1:
                    actual_max_page = res_data.get('maxPage', 1)
                    total_expected_count = res_data.get('total', 0)
                    if max_pages is None:
                        max_page_limit = actual_max_page
                    print(f"[!] 检测到该用户总共有 {actual_max_page} 页，共 {total_expected_count} 条发言")
                    total_expected = max_page_limit * 20 # 预估总数
                
                statuses = res_data['statuses']
                if not statuses:
                    break
                
                total_in_page = len(statuses)
                for idx, status in enumerate(statuses, 1):
                    # 获取 API 里的原始正文 (text 字段通常比 description 更完整)
                    raw_text = status.get('text', '')
                    raw_description = status.get('description', '')
                    
                    # 使用官方提供的 truncated 字段判断是否截断
                    is_truncated = status.get('truncated', False)
                    
                    # 基础信息
                    item = {
                        'ID': status.get('id'),
                        '发布时间': datetime.fromtimestamp(status.get('created_at') / 1000).strftime('%Y-%m-%d %H:%M:%S') if status.get('created_at') else '',
                        '摘要': self.clean_html(raw_description),
                        '点赞数': status.get('like_count'),
                        '评论数': status.get('reply_count'),
                        '转发数': status.get('retweet_count'),
                        '链接': f"https://xueqiu.com{status.get('target')}"
                    }
                    
                    # 只有在被截断的情况下才去爬详情页
                    post_url = item['链接']
                    if is_truncated and post_url and 'xueqiu.com' in post_url:
                        # 访问详情页
                        full_content, fetch_start = self.fetch_detail(post_url)
                        item['正文'] = full_content if full_content else self.clean_html(raw_text)
                        
                        # 动态停留
                        content_len = len(item['正文'])
                        target_wait = 1 + min(4, content_len / 1000)
                        time_already_spent = time.time() - fetch_start
                        actual_sleep = max(0.1, target_wait - time_already_spent)
                        
                        print(f"  [#] 检测到 truncated=True，深入抓取。目标总时: {target_wait:.2f}s, 补填休息: {actual_sleep:.2f}s")
                        time.sleep(actual_sleep)
                    else:
                        # 如果没截断，直接使用 API 里的 text 字段并清洗
                        item['正文'] = self.clean_html(raw_text)
                        if is_truncated: # 冗余逻辑：如果 truncated 为 True 但没有链接，也只能用现有内容
                             print(f"  [#] 内容虽截断但无链接，跳过。")
                        else:
                             print(f"  [#] 内容完整 (truncated=False)，跳过详情页。")
                    
                    all_data.append(item)
                    
                    # 总体进度统计
                    items_done = len(all_data)
                    elapsed = time.time() - job_start
                    if items_done > 1:
                        avg_time = elapsed / items_done
                        remaining_tasks = max(0, (max_page_limit * 20) - items_done)
                        eta_seconds = remaining_tasks * avg_time
                        m, s = divmod(int(elapsed), 60)
                        rem_m, rem_s = divmod(int(eta_seconds), 60)
                        time_str = f"已用:{m:02d}m{s:02d}s, 预计剩余:{rem_m:02d}m{rem_s:02d}s"
                    else:
                        time_str = "正在计算..."

                    print(f"  [*] 进度: {idx}/{total_in_page} (总体:{items_done}/约{max_page_limit*20}) | {time_str}")
                    
                    all_data.append(item)
                
                print(f"[+] 第 {current_page} 页处理完成，当前累计 {len(all_data)} 条")
                current_page += 1
                
            except Exception as e:
                print(f"[-] 处理第 {current_page} 页时出错: {e}")
                break
                
            time.sleep(2)
            
        return all_data

    def run(self, max_pages=None):
        try:
            self.setup_cookies()
            data = self.fetch_posts(max_pages)
            
            if data:
                df = pd.DataFrame(data)
                # 确保 data 目录存在
                if not os.path.exists("data"):
                    os.makedirs("data")
                filename = os.path.join("data", f"xueqiu_full_{self.username}.csv")
                # 重新排序字段，让正文排在摘要后面
                cols = ['ID', '发布时间', '点赞数', '评论数', '转发数', '链接', '摘要', '正文']
                df = df[cols]
                df.to_csv(filename, index=False, encoding='utf-8-sig')
                print(f"[!] 任务完成！包含正文的数据已保存至 {filename}")
            else:
                print("[-] 未能抓取到任何数据。")
        finally:
            print("[+] 任务结束，正在关闭浏览器...")
            self.page.quit()

if __name__ == "__main__":
    USERNAME = "KeepSlowly"
    USER_ID = "2287364713"
    XQ_A_TOKEN = "504a44e00386c3f66bbe3f3d99efa234850e2e30"
    
    spider = XueqiuDrissionSpider(USERNAME, USER_ID, xq_a_token=XQ_A_TOKEN)
    # 不传参数默认爬取全部页码
    spider.run() 

