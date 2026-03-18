# 雪球用户发帖爬虫 (Xueqiu User Posts Crawler)

这是一个基于 Python 的雪球（xueqiu.com）用户发帖爬虫。

## 功能
- 爬取指定用户的发帖列表（时间、标题、正文、互动数、链接等）。
- 自动处理基础 Cookie 获取。
- 内置随机延迟防反爬。
- 结果保存为 CSV 文件（UTF-8 带 BOM，方便 Excel 直接打开）。

## 安装依赖

### 基础依赖
```bash
pip install -r requirements.txt
```

### 关于 DrissionPage 的详细说明

DrissionPage 是核心爬虫依赖，需要额外的配置。以下是完整的安装步骤：

#### 1. 安装 DrissionPage 包
```bash
pip install DrissionPage
```

#### 2. 自动下载 Chromium 浏览器

DrissionPage 需要 Chromium 浏览器来运行爬虫。首次运行项目时，会自动下载：

```bash
# 运行以下命令自动下载 Chromium
python -c "from DrissionPage import ChromiumPage; ChromiumPage()"
```

或者直接运行项目的 main.py，它会在首次执行时自动下载：

```bash
python main.py <用户名> <用户ID> 页面开始位置
```

#### 3. 手动指定 Chrome 路径（可选）

如果自动下载失败或你希望使用本地已安装的 Chrome，可以在 xueqiu_drission.py 中修改：

```python
# 修改第 16 行
# 原始（自动下载 Chromium）：
self.page = ChromiumPage()

# 如果使用本地 Chrome（Windows 路径示例）：
self.page = ChromiumPage(addr=r'C:\Program Files\Google\Chrome\Application\chrome.exe')

# Linux/Mac 示例：
# self.page = ChromiumPage(addr='/usr/bin/google-chrome')
```

#### 4. 常见问题

**问题：提示 "找不到 Chromium"**
- 解决：确保已运行上述自动下载命令，或手动安装 Chrome/Chromium

**问题：下载速度慢**
- 原因：默认从国外服务器下载，国内网络可能较慢
- 解决：可使用梯子加速，或在 requirements.txt 中配置镜像源

**问题：权限不足 (Permission Denied)**
- 解决：确保有 Python 依赖安装权限，可能需要使用 `pip install --user` 或虚拟环境

> ✅ **快速检测与登录**
> 如果想验证 DrissionPage 是否安装并能正常启动浏览器，可运行仓库根目录下的 `run.py`：
> ```bash
> python run.py
> ```
> 该脚本会以非无头模式启动一个 Chromium 窗口并打开雪球首页（https://xueqiu.com），方便你手动登录。登录成功后关闭浏览器，然后再运行爬虫主程序。
> 
> **使用流程**：先运行 `run.py` 进行浏览器登录，确认 Cookie 记录在会话中；之后再执行 `main.py` 抓取数据。
> 
> 如果窗口成功弹出并能上网，说明配置和登录都正常。

---

## 使用方法

### 1. 全自动爬取 + 分析 (推荐)
输入用户名和用户 ID，脚本将自动抓取所有帖子（或指定页数）并输出分析报告。

```bash
# 爬取全部页码并分析
python main.py 我無形 4925086612

# 爬取指定页码并分析 (例如爬取前 2 页)
python main.py KeepSlowly 2287364713 2
```

### 2. 仅执行数据分析 (无需爬取)
如果你已经有了 `data` 目录下的 CSV 文件，可以通过以下两种方式直接生成报告。

**方法 A：使用 main.py 入口 (参数传入 -1)**
```bash
python main.py 用户名 用户ID -1
```

**方法 B：直接运行分析脚本 (指定文件路径)**
```bash
python analyze_user.py data/KeepSlowly.csv
```

---

## 认证说明

**无需手动配置认证信息！**

项目采用浏览器会话认证方式：
1. 先运行 `run.py` 打开浏览器并手动登录雪球账号
2. 登录成功后关闭浏览器窗口
3. 再运行 `main.py` 进行数据抓取

这种方式比手动配置 token 更安全可靠，无需担心 token 过期问题。

## 关于反爬 (Anti-Anti-Debugging)
... (existing content) ...



项目目前核心文件：
main.py: 主程序入口（推荐从这里运行）。
xueqiu_short_post_spider.py: 核心爬虫引擎。
analyze_user.py: 数据统计与水平分析引擎。
Usage.md: 使用说明。
log.md: 开发变更日志。

# 雪球用户发言全量爬虫使用指南

本工具基于 Python 开发，使用 `DrissionPage` 驱动浏览器技术，能够自动绕过雪球的 `debugger` 反调试、阿里云 WAF 防火墙，并全自动抓取指定用户的所有历史发言及帖子正文。

## 核心特性
- **自动过验证**：通过真实浏览器环境，自动处理滑块和 JS 挑战。
- **正文全抓取**：自动进入每篇帖子的详情页抓取完整内容。
- **智能防封**：根据文章长度动态计算停留时间，并计入页面加载耗时，模拟真人阅读。
- **时间预估**：实时显示已运行时间、总体进度及预计剩余时间。
- **数据清洗**：自动剔除 HTML 标签（如超链接），仅保留纯文本。
- **自动分页**：自动检测用户总页数，实现一键全量爬取。

---

## 快速开始

### 1. 环境准备
确保你已安装 Python 3.8+。在项目根目录下运行以下命令安装必要依赖：

```bash
pip install requests pandas DrissionPage
```

### 2. 获取关键参数 `xq_a_token`
为了确保爬虫能稳定访问，建议提供你浏览器中的登录 Token：
1. 在浏览器（Chrome/Edge）中打开 [雪球网](https://xueqiu.com/) 并登录。
2. 按 `F12` 打开开发者工具，点击 **Application (应用)** -> **Cookies** -> `https://xueqiu.com`。
3. 找到名为 `xq_a_token` 的值并复制。

### 3. 配置爬虫
打开 `xueqiu_short_post_spider.py`，在文件末尾修改以下配置：

```python
if __name__ == "__main__":
    USER_ID = "2287364713"  # 替换为你想要爬取的用户 ID
    XQ_A_TOKEN = "你的_xq_a_token" # 替换为你刚才复制的 Token
    
    spider = XueqiuDrissionSpider(USER_ID, xq_a_token=XQ_A_TOKEN)
    spider.run() # 默认爬取全部，若只想爬前2页可改为 spider.run(max_pages=2)
```

### 4. 运行爬虫
在终端执行：

```bash
.venv/Scripts/python.exe xueqiu_short_post_spider.py
.venv/Scripts/python.exe analyze_user.py
```

---

## 输出结果
任务完成后，系统会在当前文件夹生成一个 CSV 文件：
`用户名.csv`

**包含字段：**
- `ID`: 帖子唯一标识
- `发布时间`: 格式化的时间字符串
- `点赞数 / 评论数 / 转发数`: 互动数据
- `链接`: 帖子原地址
- `摘要`: 列表页看到的简短内容
- `正文`: 详情页抓取的清洗后的纯文本全文

---

## 注意事项
1. **浏览器驱动**：本工具默认使用系统安装的 Chrome。运行前请关闭已打开的调试模式浏览器窗口。
2. **人机验证**：如果爬取过程中弹出滑块验证码，请在弹出的浏览器窗口中**手动滑动**，脚本检测到通过后会自动继续。
3. **法律声明**：本工具仅供学习和研究使用，请勿用于商业用途或大规模恶意抓取，遵守雪球网的相关服务协议。




之前用接口的形式访问雪球的文章，总有反爬打断，现在我要你模拟用户点击下一页的方式爬取信息；
对当前列表，如果有展开的，则点击展开获取这篇帖子全部内容；没有展开的，则显示的内容即为全部内容；
如果是长文的，则用原逻辑获取长文；
如果当前是专栏，则点击这篇文章，打开浏览器新标签，获取其全文。专栏一般是timeline__item__content类下面为a标签的项；

当Type=2的时候，是请求长文
https://xueqiu.com/v4/statuses/user_timeline.json?page=1&user_id=2287364713&type=2&md5__1038=222029ad07-IW2%2F%3DPhgrCGcGXgIxXTI_k5tgNWGkg7P%3DfRAvPgXgFsPjXtOd7vt42xQ%2F3blxFy%2FQEIVGVWgGPTug5PGlgCPGEgXPtSKgTvPXghPtDRgIv_QqP%3DsBgPPIBgEyrZ_MOvItgyzgGHAsgTabVq%2FgFZvg282gsiBgzT%2Fv3r4GE67uVAgEu_xZAr%2FN_sV0_IgP%2Fr7v_tg
