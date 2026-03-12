# 雪球用户发帖爬虫 (Xueqiu User Posts Crawler)

这是一个基于 Python 的雪球（xueqiu.com）用户发帖爬虫。

## 功能
- 爬取指定用户的发帖列表（时间、标题、正文、互动数、链接等）。
- 自动处理基础 Cookie 获取。
- 内置随机延迟防反爬。
- 结果保存为 CSV 文件（UTF-8 带 BOM，方便 Excel 直接打开）。

## 安装依赖
```bash
pip install -r requirements.txt
```

## 使用方法

### 1. 全自动爬取 + 分析 (推荐)
输入用户名和用户 ID，脚本将自动抓取所有帖子（或指定页数）并输出分析报告。

```bash
# 爬取全部页码并分析
python main.py KeepSlowly 2287364713

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
python analyze_user.py data/xueqiu_full_KeepSlowly.csv
```

---

## 关于反爬 (Anti-Anti-Debugging)
... (existing content) ...



项目目前核心文件：
main.py: 主程序入口（推荐从这里运行）。
xueqiu_drission.py: 核心爬虫引擎。
analyze_user.py: 数据统计与水平分析引擎。
Usage.md: 使用说明。
log.md: 开发变更日志。