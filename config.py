

# 正则过滤列表：匹配到则不保存该条记录（用于过滤系统通知类型内容）
# 注意：每条正则会应用于帖子标题/正文前缀，不区分大小写
FILTER_REGEX = [
    r"^我刚刚关注了股票",
    r"^我刚刚调整了雪球组合",
]

# ================= 数据分析配置 =================
TOP_STOCKS_COUNT = 20  # 关注领域显示的股票数量
TOP_POSTS_COUNT = 3    # 最火爆发言显示的条数

# ================= 默认测试账号配置 =================
# 当直接运行 spider 文件进行测试时，使用的默认用户名和 ID
DEFAULT_USERNAME = "KeepSlowly"
DEFAULT_USER_ID = "2287364713"


# ================= 爬取行为配置 =================
# TYPE_PARAM 控制抓取类型与使用的引擎：
# None : 抓取所有短贴（包含转发），使用 UI 模式引擎 (XueqiuShortPostSpider)
# 0    : 只抓取原发短贴，使用 UI 模式引擎 (XueqiuShortPostSpider)
# 2    : 只抓取长贴 (专栏文章)，使用 API 模式引擎 (XueqiuLongPostSpider)
TYPE_PARAM = None