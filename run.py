"""简单脚本：只打开一个 Chromium 窗口，然后等待用户关闭"""
from DrissionPage import ChromiumPage
from DrissionPage._base.chromium import ChromiumOptions

if __name__ == "__main__":
    # 创建可见的浏览器需要通过 ChromiumOptions 设置 headless=False
    opts = ChromiumOptions()
    opts.headless(False)
    page = ChromiumPage(opts)
    # 打开空白页以确保窗口弹出
    page.get('about:blank')
    print("浏览器已打开，按回车关闭程序")
    try:
        input()
    except KeyboardInterrupt:
        pass
    finally:
        page.close()
        print("浏览器已关闭")
