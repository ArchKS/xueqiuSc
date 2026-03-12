import requests
import time
import json
import pandas as pd
from datetime import datetime
import random

class XueqiuSpider:
    def __init__(self, user_id, xq_a_token=None):
        self.user_id = user_id
        self.xq_a_token = xq_a_token
        self.base_url = "https://xueqiu.com/v4/statuses/user_timeline.json"
        self.session = requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Referer": f"https://xueqiu.com/u/{user_id}",
            "Accept": "application/json, text/plain, */*",
        }
        # 如果提供了 token，直接注入到 Cookie 中
        if self.xq_a_token:
            self.session.cookies.set("xq_a_token", self.xq_a_token, domain="xueqiu.com")
        
        # 初始访问主页以获取其他必要的 Cookie (如 acw_tc)
        self._get_initial_cookies()

    def _get_initial_cookies(self):
        """访问雪球主页获取基础 Cookie (xq_a_token 等)"""
        try:
            # 首页可以拿到基础 cookie
            home_url = "https://xueqiu.com/"
            self.session.get(home_url, headers=self.headers, timeout=10)
            print("[+] 已初始化获取 Cookie")
        except Exception as e:
            print(f"[-] 初始化 Cookie 失败: {e}")

    def fetch_posts(self, page=1):
        """爬取指定页码的发言"""
        params = {
            "page": page,
            "user_id": self.user_id,
            "count": 20,
            # 使用用户最初提供的 md5 参数（注意：这个可能会过期）
            "md5__1038": "222029ad07-GWAPJgfPUIgc_Xt_IuGk_IGEB_E_kMigpgs%2FTXXt%2F%2FO%3DMab62MW%3DuxWE6MbbhgrGSeD0EQV_%2F_hgI2g%3DQggEgkqgg4EgtB_JgIBgCgIKgyg%2FAueOwgtXEg2x%3DMZgsvTug5Sughgr%3DM5_XZZmVQ_0gglvgAR8YPt73aPol7%2FBt7go2PoqsrKgvfW2Srtq%3DTg02g"
        }
        
        try:
            response = self.session.get(self.base_url, params=params, headers=self.headers, timeout=10)
            if response.status_code == 200:
                try:
                    return response.json()
                except Exception:
                    print(f"[-] 解析 JSON 失败。返回内容摘要: {response.text[:200]}")
                    return None
            elif response.status_code == 403:
                print(f"[-] 遭遇 403 拒绝访问 (Page {page})。")
                print(f"[-] 返回内容摘要: {response.text[:200]}")
            else:
                print(f"[-] 请求失败，状态码: {response.status_code}")
        except Exception as e:
            print(f"[-] 网络请求异常: {e}")
        return None

    def parse_data(self, data):
        """解析 JSON 返回值"""
        results = []
        if not data or 'statuses' not in data:
            return results
        
        for status in data['statuses']:
            item = {
                'ID': status.get('id'),
                '发布时间': datetime.fromtimestamp(status.get('created_at') / 1000).strftime('%Y-%m-%d %H:%M:%S') if status.get('created_at') else '',
                '标题': status.get('title'),
                '正文内容': status.get('text'), # 原始 HTML 文本
                '点赞数': status.get('like_count'),
                '转发数': status.get('retweet_count'),
                '评论数': status.get('reply_count'),
                '来源': status.get('source'),
                '链接': f"https://xueqiu.com{status.get('target')}"
            }
            results.append(item)
        return results

    def run(self, max_pages=3):
        """执行爬取任务"""
        all_data = []
        for page in range(1, max_pages + 1):
            print(f"[*] 正在爬取第 {page} 页...")
            data = self.fetch_posts(page)
            posts = self.parse_data(data)
            
            if not posts:
                print("[-] 未获取到数据或被拦截，停止爬取")
                break
                
            all_data.extend(posts)
            print(f"[+] 成功爬取 {len(posts)} 条数据")
            
            # 防反爬：随机延迟 3-6 秒
            wait_time = random.uniform(3, 6)
            time.sleep(wait_time) 
            
        # 保存为 CSV
        if all_data:
            df = pd.DataFrame(all_data)
            filename = f"xueqiu_user_{self.user_id}.csv"
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"[!] 爬取完成，共 {len(all_data)} 条，结果已保存至 {filename}")
        else:
            print("[-] 任务结束，未抓取到任何数据。")

if __name__ == "__main__":
    # 示例用户 ID: 2287364713 (KeepSlowly)
    USER_ID = "2287364713" 
    XQ_A_TOKEN = "504a44e00386c3f66bbe3f3d99efa234850e2e30"
    spider = XueqiuSpider(USER_ID, xq_a_token=XQ_A_TOKEN)
    spider.run(max_pages=3)
