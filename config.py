

# 正则过滤列表：匹配到则不保存该条记录（用于过滤系统通知类型内容）
# 注意：每条正则会应用于帖子标题/正文前缀，不区分大小写

FILTER_REGEX = [
    r"^我刚刚关注了股票",
    r"^我刚刚调整了雪球组合",
    r"^我刚创建了一个组合",
    # 2013-05-20以￥6.51买入$上峰水泥(SZ000672)$。
    r"^(\d{4}-\d{2}-\d{2})以￥.*?\$.*?\$",
    r"在￥([\d.]+)时关注股票\$.*?\$",
    # 关注股票$高鸿股份(SZ000851)$
    r"关注股票\$.*?\$",
    #将$超声电子(SZ000823)$卖出目标价调整为￥15。
    r"将\$.*?\$.*?目标价调整为￥",

]

# ================= 数据分析配置 =================
TOP_STOCKS_COUNT = 20  # 关注领域显示的股票数量
TOP_POSTS_COUNT = 3    # 最火爆发言显示的条数
SHOW_ANALYSIS_REPORT = False  # 是否显示雪球数据综合分析报告

# ================= 关键词过滤配置 =================
# 匹配到每一组中的任一关键词，则保留该记录 (组内 OR 逻辑)
# 每组关键词会单独生成一个 CSV 文件，文件名使用字典的 Key
KEYWORDS_FILTER = {
    # "煤炭": ["煤", "神华", "陕煤","淮北"],
    # "电力": ["火电", "发电", "电力","华能","川投","黔源","恒源","中石化冠德"],
    # "水泥": ["塔牌", "海螺", "电力","华能"],
}

# ================= 默认过滤阈值配置 =================
DEFAULT_MIN_LIKES = 0        # 默认最小点赞
DEFAULT_MIN_COMMENTS = 0     # 1 默认最小评论
DEFAULT_MIN_LENGTH = 10       # 默认最小字数
DEFAULT_SUPER_LIKES = None   # 默认超级点赞阈值
DEFAULT_SUPER_COMMENTS = None # 默认超级评论阈值
DEFAULT_SUPER_LENGTH = None   # 默认超级字数阈值 (大于此字数则无视点赞/评论直接通过)

# ================= 默认测试账号配置 =================
# 当直接运行 spider 文件进行测试时，使用的默认用户名和 ID
DEFAULT_USERNAME = "柯中"
DEFAULT_USER_ID = "5243796549"


# ================= 批量爬取配置 (batch_spider_by_time.py) =================
# 待爬取的博主列表
USER_LIST = [
    # {"username": "超级鹿鼎公", "userid": "8790885129"},
    # {"username": "黑色面包", "userid": "9507152383"},
    # {"username": "KeepSlowly", "userid": "2287364713"},
    # {"username": "柯中", "userid": "5243796549"},
    # {"username": "PaulWu", "userid": "1965894836"},
    # {"username": "凝视三千弱水的深渊", "userid": "9236758887"},
    {"username": "雪月霜", "userid": "1505944393"},
    # {"username": "史诗级韭菜", "userid": "2214010836"},
]

# 时间范围配置
# mode 支持: 'days', 'months', 'years', 'range'
# 如果是 'range'，需提供 start_date 和 end_date (格式: 'YYYY-MM-DD')
# 如果是 'days'/'months'/'years'，需提供 value
TIME_CONFIG = {
    "mode": "days",    # 默认近 30 天
    "value": 1, 
    "start_date": None, 
    "end_date": None
}

# ================= 爬取行为配置 =================
# TYPE_PARAM 控制抓取类型与使用的引擎：
# None : 抓取所有短贴（包含转发），使用 UI 模式引擎 (XueqiuShortPostSpider)
# 0    : 只抓取原发短贴，使用 UI 模式引擎 (XueqiuShortPostSpider)
# 2    : 只抓取长贴 (专栏文章)，使用 API 模式引擎 (XueqiuLongPostSpider)
import os
# 从环境变量读取 TYPE_PARAM，支持 "0", "2", "none" (不区分大小写)
env_type = os.environ.get("TYPE_PARAM")
if env_type is not None:
    if env_type.lower() == "none":
        TYPE_PARAM = None
    else:
        try:
            TYPE_PARAM = int(env_type)
        except:
            TYPE_PARAM = None # 默认回退
else:
    TYPE_PARAM = None

# ================= 并发爬取配置 =================
# 控制同时开启的浏览器标签页（Tab）数量
# 建议：3-5 之间。数字越大速度越快，但对电脑性能和反爬风险要求越高。
MAX_WORKERS = 2

# ================= 并发分段模式配置 =================
# 可选值:
# range_split        : 按当前抓取区间等分
# shifted_total      : 按总页数平移起点
PAGINATION_WORKER_MODE = "range_split"

# ================= 反爬策略配置 =================
# 如果抓取到的正文字数为 0，是否判定为触发了验证码/滑块等反爬机制
# 开启后 (True)，脚本会在此刻暂停，等待您在浏览器手动完成验证后按回车继续。
# 关闭后 (False)，遇到字数为 0 将直接记录为空并跳过，不会中断爬虫流程。
PAUSE_ON_EMPTY_CONTENT = False

#目前爬虫在并发时，采用的是1、4、7；2、5、8；3、6、9的并发格式，但由于当页码超过10页后，底部跳转导航栏没有输入框了，导致爬虫无法跳转到指定页
#如果是1-25,26-50,51-75,76-100的方式，则万一进程停止，无法从下一页开始，但可以从 10~25间断处理



