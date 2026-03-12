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
python main.py <用户名> <用户ID>
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

> ✅ **快速检测**
> 如果想验证 DrissionPage 是否安装并能正常启动浏览器，可运行仓库根目录下的 `run.py`：
> ```bash
> python run.py
> ```
> 该脚本会以非无头模式启动一个 Chromium 窗口并打开空白页，等待按回车关闭；窗口弹出即表示配置成功。

---

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