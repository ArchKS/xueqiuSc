python3 main.py 黑色面包 9507152383
python3 main.py 罗宾逊投资 1115064374
python3 main.py 梦游坤哥 8414489464
python3 main.py 我無形 4925086612
python3 main.py 钟晓渡 8565549431
python3 main.py KeepSlowly 2287364713
python3 main.py PaulWu 1965894836
python3 main.py Zendu 3629171097

python3 main.py 凝视三千弱水的深渊 9236758887

python3 main.py 狸哥很懒 1835829265
python3 main.py Conan的投资笔记 1830611415
python3 main.py Elon翻开每一页 5739488179
python3 main.py 石stone 5509299851
python3 main.py 火蚁投资 2063132956
python3 main.py 超级鹿鼎公 8790885129
python3 main.py 胜和 2612090930
python3 main.py 陸陸陸三率投资 3579186337
python3 main.py 菜头日记 5266360866
python3 main.py Metasmile 3755925868
python3 main.py 雪月霜 1505944393



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