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


## 使用方法

```bash
# 1. 先登录
python3 xueqiu_auth_login.py

#2. 爬取短贴和转发
sh batch_run_ranges.sh 价投6688 7462417628 1 215 TYPE_PARAM=None

#3. 爬取长贴
sh batch_run_ranges.sh 价投6688 7462417628 1 215 TYPE_PARAM=2

```

```bash
# 爬取全部页码并分析
python main.py 我無形 4925086612

# 爬取指定页码并分析 (例如爬取前 2 页)
python main.py KeepSlowly 2287364713 2


# 过滤本地 CSV 数据
# 语法: python filter_csv.py <文件路径> [-l 最小点赞数] [-c 最小评论数] [-len 最小字数]
python filter_csv.py data/KeepSlowly.csv -l 10 -len 100


# 目前：从多页跳转并发爬会有BUG
# 目前爬虫在并发时，采用的是1、4、7；2、5、8；3、6、9的并发格式，但由于当页码超过10页后，底部跳转导航栏没有输入框了，导致爬虫无法跳转到指定页，帮我设置成，如果没找到输入框，则跳转到第一页然后再跳转到指定页


python3 main.py 柯中 5243796549
```

