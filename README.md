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
1. 修改 `xueqiu_spider.py` 中的 `USER_ID` 为你想爬取的 ID。
2. 运行脚本：
```bash
python xueqiu_spider.py
```

## 关于反爬 (Anti-Anti-Debugging)
雪球有较强的动态参数校验（如 `md5__1038`）。
- 如果遇到 `403` 错误，说明该参数校验生效或 IP 被暂时封锁。
- 你可以从浏览器控制台抓取最新的 `md5__1038` 放入请求参数中。
- 针对控制台 `debugger` 断点，建议在浏览器中使用 "Never pause here" 忽略。
