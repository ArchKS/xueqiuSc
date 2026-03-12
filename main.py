import sys
import os
from xueqiu_drission import XueqiuDrissionSpider
from analyze_user import analyze_user_level

def main():
    if len(sys.argv) < 2:
        print("用法: python main.py <用户ID> [最大页数]")
        print("示例 (爬取全部): python main.py 2287364713")
        print("示例 (爬取2页): python main.py 2287364713 2")
        return

    uid = sys.argv[1]
    max_pages = None
    
    if len(sys.argv) >= 3:
        try:
            max_pages = int(sys.argv[2])
            print(f"[*] 设定最大爬取页数为: {max_pages}")
        except ValueError:
            print("[-] 错误: 最大页数必须是数字。将默认爬取所有页。")

    # 你提供的固定 Token
    XQ_A_TOKEN = "504a44e00386c3f66bbe3f3d99efa234850e2e30"

    print(f"\n[Step 1] 开始爬取用户 {uid} 的数据...")
    spider = XueqiuDrissionSpider(uid, xq_a_token=XQ_A_TOKEN)
    
    # 执行爬取
    spider.run(max_pages=max_pages)
    
    # 构造生成的文件路径
    target_file = f"xueqiu_full_{uid}.csv"
    
    if os.path.exists(target_file):
        print(f"\n[Step 2] 爬取完成，开始分析数据...")
        analyze_user_level(target_file)
    else:
        print(f"\n[-] 错误: 未能找到生成的数据文件 {target_file}，分析取消。")

if __name__ == "__main__":
    main()
