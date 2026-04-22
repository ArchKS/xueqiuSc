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

# 格式：username userid startpage endpage postType
#2. 爬取短贴和转发
sh batch_run_ranges.sh 价投6688 7462417628 1 215 TYPE_PARAM=None

#3. 爬取长贴
sh batch_run_ranges.sh 价投6688 7462417628 1 215 TYPE_PARAM=2

```

过滤
```bash
# 过滤本地 CSV 数据
# 语法: python filter_csv.py <文件路径> [-l 最小点赞数] [-c 最小评论数] [-len 最小字数]
python filter_csv.py data/KeepSlowly.csv -l 10 -len 100


# 目前：从多页跳转并发爬会有BUG
# 目前爬虫在并发时，采用的是1、4、7；2、5、8；3、6、9的并发格式，但由于当页码超过10页后，底部跳转导航栏没有输入框了，导致爬虫无法跳转到指定页，帮我设置成，如果没找到输入框，则跳转到第一页然后再跳转到指定页
```



```bash
# 爬取博主们近期数据,配置信息在config.py中
# USER_LIST 是博主列表
# TIME_CONFIG 是时间配置
# TYPE_PARAM 是爬取的帖子类型
python3 batch_spider_by_time.py

```

过滤数据

```bash


# 查看帮助文档
python filter_csv.py -h

# 示例 1: 筛选点赞数 >= 10，且字数 >= 100 的帖子
python filter_csv.py data/KeepSlowly.csv -l 10 -len 100

# 示例 2: 筛选评论数 >= 5 的帖子
python filter_csv.py data/KeepSlowly.csv -c 5

# 示例 3: 筛选点赞数 >= 20，评论数 >= 10，字数 >= 500 的超级干货
python filter_csv.py data/KeepSlowly.csv -l 20 -c 10 -len 500

逻辑实现：
基础通过门槛：必须同时满足 点赞数 >= l 且 评论数 >= c 且 正文字数 >= len。
特赦（豁免）机制：
如果 点赞数 >= sl，直接通过，无视其他所有条件。
如果 评论数 >= sc，直接通过，无视其他所有条件。
命令行参数更新：
-l, --likes: 基础点赞门槛 (b)
-c, --comments: 基础评论门槛 (a)
-len, --length: 基础字数门槛 (c)
-sl, --super-likes: 特赦点赞数 (y)
-sc, --super-comments: 特赦评论数 (x)
使用示例：
如果你想要：评论 >= 10 且 点赞 >= 5 且 字数 >= 20 才能通过，但 如果点赞超过 50 或 评论超过 30 则无条件通过：



python3 filter_csv.py data/凝视三千弱水的深渊Z_Full.csv -l 5 -c 10 -len 20
```