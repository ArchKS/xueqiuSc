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

# 初始化 colorama 以支持 Windows 颜色输出
colorama.init(autoreset=True)

# 颜色常量
GREEN = colorama.Fore.GREEN
YELLOW = colorama.Fore.YELLOW
RED = colorama.Fore.RED
BLUE = colorama.Fore.BLUE
RESET = colorama.Style.RESET_ALL

class XueqiuShortPostSpider:
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

    def setup_cookies(self):
        """仅在需要时设置 Cookie，不再进行多余的首页跳转和 WAF 等待"""
        if self.xq_a_token:
            print(f"{GREEN}[+] 正在设置 xq_a_token...{RESET}")
            # 先访问主域以便设置 cookie
            if "xueqiu.com" not in self.page.url:
                self.page.get("https://xueqiu.com", timeout=5)
            self.page.set.cookies({'name': 'xq_a_token', 'value': self.xq_a_token, 'domain': '.xueqiu.com'})
        
        # 不再在这里进行跳转和 5秒等待，交给 fetch_posts 处理

    def fetch_posts(self, start_page=1, end_page=None, existing_ids=None, filename=None):
        """模拟用户点击 UI 方式抓取帖子列表"""
        all_data = []
        job_start = time.time()
        
        if existing_ids is None:
            existing_ids = set()
            
        current_page = start_page
        max_page_limit = end_page if end_page else 9999
        actual_max_page = 0

        # 直接进入用户主页
        user_url = f"https://xueqiu.com/u/{self.user_id}"
        print(f"{BLUE}[+] 直接访问用户主页: {user_url}{RESET}")
        self.page.get(user_url)
        # 仅留必要的短时间等待页面渲染，不再搞 WAF 专项等待
        time.sleep(2)

        # 如果设定了只看原发 (type_param=0)
        if self.type_param == 0:
            print(f"{BLUE}[+] 正在筛选“原发”帖子...{RESET}")
            original_btn = self.page.ele('text=原发', timeout=2)
            if original_btn:
                original_btn.click()
                time.sleep(2)
            else:
                print(f"{YELLOW}[!] 找不到“原发”筛选按钮，将显示全部{RESET}")

        # 尝试获取总页数
        try:
            pagination = self.page.ele('.pagination')
            if pagination:
                page_links = pagination.eles('tag:a')
                page_nums = []
                for link in page_links:
                    if link.text.isdigit():
                        page_nums.append(int(link.text))
                if page_nums:
                    actual_max_page = max(page_nums)
                    # 如果最后一页是省略号后的，可能需要更复杂的逻辑，但通常最大数字就在那
                    print(f"{BLUE}[!] 检测到总页数约为: {actual_max_page}{RESET}")
        except:
            pass

        # 如果开始页不是第1页，利用输入框直接跳转
        if current_page > 1:
            print(f"{BLUE}[+] 正在跳转到第 {current_page} 页...{RESET}")
            try:
                pagination = self.page.ele('.pagination', timeout=5)
                jump_input = pagination.ele('tag:input', timeout=2)
                if jump_input:
                    jump_input.input(f"{current_page}\n") # 输入页码并回车
                    print(f"{GREEN}[+] 已发送跳转指令到第 {current_page} 页{RESET}")
                    time.sleep(3) # 等待跳转完成
                else:
                    print(f"{YELLOW}[!] 找不到跳转输入框，尝试点击数字按钮...{RESET}")
                    page_btn = pagination.ele(f'text={current_page}', timeout=2)
                    if page_btn: page_btn.click()
            except Exception as e:
                print(f"{RED}[!] 跳转分页时出错: {e}，将从当前位置开始抓取{RESET}")

        while current_page <= max_page_limit:
            print(f"{GREEN}[+] 正在处理第 {current_page} 页...{RESET}")
            time.sleep(2) # 等待页面加载
            
            # 获取当前页所有帖子
            items = self.page.eles('.timeline__item')
            if not items:
                print(f"{RED}[-] 第 {current_page} 页未找到帖子，可能已到底或加载失败{RESET}")
                break
            
            total_in_page = len(items)
            page_data = []
            
            for idx, item in enumerate(items, 1):
                try:
                    # 获取 ID
                    date_link = item.ele('.date-and-source', timeout=1)
                    if not date_link:
                        continue
                    post_id = str(date_link.attr('data-id'))
                    post_date = date_link.text.strip()
                    
                    # 进度信息
                    items_done = len(all_data) + 1
                    # 优化对齐：P当前页/总页 序号(2位), 本页总数(2位), 总计抓取数(3位)
                    total_p_str = str(actual_max_page) if actual_max_page else "?"
                    progress_info = f"[P{current_page}/{total_p_str} {idx:2d}/{total_in_page:2d}] "
                    
                    if post_id in existing_ids:
                        formatted_dt = self.format_date(post_date)
                        print(f"{progress_info} | \033[33m[跳过] {formatted_dt} | 已存在于本地\033[0m")
                        continue

                    # 识别并处理内容（普通帖子 vs 专栏文章）
                    # 识别并处理内容（普通帖子 vs 专栏文章）
                    content_ele = item.ele('.timeline__item__content', timeout=1)
                    full_text = ""
                    
                    # 检查是否为专栏 (通常带有 timeline__item__content--longtext 类，或内部有指向详情的 a 标签)
                    is_column = False
                    article_link = None
                    if content_ele:
                        classes = content_ele.attr('class') or ""
                        # 优先寻找专栏特有的 fake-anchor 或者包含文章 ID 的 a 标签
                        article_link = content_ele.ele('.fake-anchor', timeout=0.2) or \
                                       content_ele.ele(f'a[href*="{post_id}"]', timeout=0.2)
                        
                        if article_link or "longtext" in classes or item.ele('.timeline__item__title', timeout=0.1):
                            is_column = True

                    if is_column and content_ele:
                        # 专栏文章：通过新标签页抓取全文
                        href = article_link.attr('href') if article_link else None
                        if not href:
                            link_ele = content_ele.ele('tag:a', timeout=0.5)
                            href = link_ele.attr('href') if link_ele else None
                            
                        if href:
                            if not href.startswith('http'):
                                href = f"https://xueqiu.com{href}"
                            
                            print(f"{progress_info} | \033[34m[专栏] 抓取全文: {href}\033[0m")
                            try:
                                new_tab = self.page.new_tab(href)
                                # 增加更多备用选择器并等待加载
                                content_selectors = [
                                    '.article__content', 
                                    '.status-detail', 
                                    '.article-item__content',
                                    '.post__description',
                                    'tag:article'
                                ]
                                content_found = ""
                                for _ in range(3): # 循环尝试加载
                                    for sel in content_selectors:
                                        ele = new_tab.ele(sel, timeout=1.5)
                                        if ele and ele.text and len(ele.text) > 10:
                                            content_found = ele.text
                                            break
                                    if content_found: break
                                    time.sleep(1)
                                
                                full_text = content_found if content_found else content_ele.text
                                new_tab.close()
                                
                                # 检查字数并暂停程序
                                if not full_text or len(full_text.strip()) == 0:
                                    print(f"{RED}[!] 当前已经获取不到内容 (字数为0) | 链接: {href}{RESET}")
                                    input(f"{YELLOW}请检查浏览器是否遇到反爬挑战，处理完毕后按回车继续...{RESET}")
                            except Exception as e:
                                print(f"  [!] 专栏详情抓取失败: {e}")
                                full_text = content_ele.text
                        else:
                            full_text = content_ele.text
                    else:
                        # 普通帖子：处理“展开”按钮
                        expand_btn = item.ele('text=展开', timeout=0.5)
                        if expand_btn:
                            try:
                                expand_btn.click()
                                time.sleep(0.8) # 确保 DOM 更新
                            except:
                                pass
                        full_text = content_ele.text if content_ele else ""
                    
                    # 1. 提取博主本人的回复/评论部分（处理转发链）
                    # 雪球的转发链格式通常为：本人评论内容 // @原作者: 原内容
                    if full_text and "//" in full_text:
                        # 使用正则匹配 // @用户 这种典型的引用起始点
                        parts = re.split(r'\s*//\s*@', full_text, 1)
                        if len(parts) > 1:
                            full_text = parts[0].strip()

                    # 2. 清理正文中的 UI 残留文本和单字符图标
                    if full_text:
                        # 移除常见的 UI 操作词
                        cleanup_tags = [r'展开\s*', r'收起\s*', r'查看对话', r'查看图片']
                        for tag in cleanup_tags:
                            full_text = re.sub(tag, '', full_text)
                        
                        # 移除末尾可能残留的单字符图标 (雪球常用的 iconfont 编码)
                        full_text = re.sub(r'[\ue63b\ue63c\ue623]\s*$', '', full_text)
                        full_text = full_text.strip()
                    
                    # 提取互动数据
                    footer = item.ele('.timeline__item__ft', timeout=1)
                    likes = 0
                    replies = 0
                    retweets = 0
                    if footer:
                        # 转发、讨论、赞 的顺序通常固定，或者根据 iconfont
                        # 简单通过文本提取数字
                        ft_links = footer.eles('tag:a')
                        for ft_link in ft_links:
                            txt = ft_link.text
                            num = 0
                            if any(c.isdigit() for c in txt):
                                num = int(''.join(filter(str.isdigit, txt)))
                            
                            if '转发' in txt or (ft_link.ele('.iconfont') and ft_link.ele('.iconfont').text == ''):
                                retweets = num
                            elif ft_link.ele('.iconfont') and ft_link.ele('.iconfont').text == '':
                                replies = num
                            elif ft_link.ele('.iconfont') and ft_link.ele('.iconfont').text == '':
                                likes = num
                    
                    data_item = {
                        'ID': post_id,
                        '发布时间': self.format_date(post_date),
                        '点赞数': likes,
                        '评论数': replies,
                        '转发数': retweets,
                        '页码': f"{current_page}/{actual_max_page or '?'}",
                        '链接': f"https://xueqiu.com/{self.user_id}/{post_id}",
                        '摘要': full_text[:50].replace('\n', ' ') + '...',
                        '正文': full_text
                    }
                    
                    # 过滤
                    title_str = data_item['摘要']
                    if any(p.search(full_text) for p in self.filter_patterns):
                        print(f"{progress_info} | \033[33m[过滤] {data_item['发布时间']} | {title_str[:15]}\033[0m")
                        continue
                        
                    # 优化采集输出：对齐字数，显示 ID
                    print(f"{progress_info} | \033[32m[采集] {len(full_text):5d}字 | {data_item['发布时间']} | ID:{post_id}\033[0m")
                    
                    all_data.append(data_item)
                    page_data.append(data_item)
                    
                except Exception as e:
                    print(f"  [!] 处理条目出错: {e}")
                    continue

            # 每页结束后追加到文件
            if page_data and filename:
                page_df = pd.DataFrame(page_data)
                cols_to_save = ['ID', '发布时间', '点赞数', '评论数', '转发数', '页码', '链接', '摘要', '正文']
                page_df = page_df[[c for c in cols_to_save if c in page_df.columns]]
                page_df.to_csv(filename, mode='a', header=not os.path.exists(filename), index=False, encoding='utf-8-sig')
                print(f"{GREEN}[+] 第 {current_page} 页已保存 {len(page_data)} 条记录{RESET}")

            # 翻页
            if current_page >= max_page_limit:
                break
                
            next_btn = self.page.ele('text=下一页', timeout=2)
            if next_btn:
                next_btn.click()
                current_page += 1
                time.sleep(3)
            else:
                print(f"{YELLOW}[!] 找不到“下一页”按钮，可能已结束{RESET}")
                break
                
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
    from config import DEFAULT_USERNAME, DEFAULT_USER_ID, FILTER_REGEX, TYPE_PARAM
    
    # XQ_A_TOKEN 不再需要，依赖 run.py 中的浏览器登录会话
    spider = XueqiuShortPostSpider(DEFAULT_USERNAME, DEFAULT_USER_ID, type_param=TYPE_PARAM, filter_regex=FILTER_REGEX)
    # 不传参数默认爬取全部页码
    spider.run(start_page=1, end_page=2) 

