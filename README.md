# 雪球用户发帖爬虫 (Xueqiu User Posts Crawler)

这是一个基于 Python 的雪球（xueqiu.com）用户发帖爬虫。

## 安装依赖

1. 基础依赖

```bash
pip install -r requirements.txt
```


2. 自动下载 Chromium 浏览器

DrissionPage 需要 Chromium 浏览器来运行爬虫。首次运行项目时，会自动下载：

```bash
# 运行以下命令自动下载 Chromium
python -c "from DrissionPage import ChromiumPage; ChromiumPage()"
```

或者直接运行项目的 main.py，它会在首次执行时自动下载：

```bash
python main.py <用户名> <用户ID> 页面开始位置
```

3. 手动指定 Chrome 路径（可选）

如果自动下载失败或你希望使用本地已安装的 Chrome，可以在 xueqiu_short_post_spider.py 或 xueqiu_long_post_spider.py 中修改：

```python
self.page = ChromiumPage()

# 如果使用本地 Chrome（Windows 路径示例）：
self.page = ChromiumPage(addr=r'C:\Program Files\Google\Chrome\Application\chrome.exe')

# Linux/Mac 示例：
# self.page = ChromiumPage(addr='/usr/bin/google-chrome')
```

## 使用方法


```bash
# 爬取全部页码并分析
python main.py 我無形 4925086612

# 爬取指定页码并分析 (例如爬取前 2 页)
python main.py KeepSlowly 2287364713 2

#仅执行数据分析 (无需爬取)
python main.py 用户名 用户ID -1

# 直接运行分析脚本
python analyze_user.py data/KeepSlowly.csv

# 过滤本地 CSV 数据
# 语法: python filter_csv.py <文件路径> [-l 最小点赞数] [-c 最小评论数] [-len 最小字数]
python filter_csv.py data/KeepSlowly.csv -l 10 -len 100
```


