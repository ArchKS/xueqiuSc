import argparse
import os
import re
import pandas as pd


def load_csv(file_path):
    try:
        return pd.read_csv(file_path, encoding="utf-8-sig")
    except UnicodeDecodeError:
        return pd.read_csv(file_path, encoding="gb18030")


def parse_page_value(value):
    if pd.isna(value):
        return None, None

    text = str(value).strip()
    match = re.match(r"^\s*(\d+)\s*/\s*(\d+)\s*$", text)
    if not match:
        return None, None

    current_page = int(match.group(1))
    total_pages = int(match.group(2))
    return current_page, total_pages


def build_missing_ranges(missing_pages):
    if not missing_pages:
        return []

    ranges = []
    start = missing_pages[0]
    end = missing_pages[0]

    for page in missing_pages[1:]:
        if page == end + 1:
            end = page
            continue
        ranges.append((start, end))
        start = end = page

    ranges.append((start, end))
    return ranges


def find_missing_pages(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")

    df = load_csv(file_path)
    if "页码" not in df.columns:
        raise ValueError("CSV 中未找到 '页码' 列。")

    parsed = df["页码"].apply(parse_page_value)
    current_pages = sorted({page for page, _ in parsed if page is not None})
    total_pages_set = {total for _, total in parsed if total is not None}

    if not current_pages:
        raise ValueError("未能从 '页码' 列中解析出有效页码，预期格式为 '当前页/总页'。")

    total_pages = max(total_pages_set) if total_pages_set else max(current_pages)
    all_pages = set(range(1, total_pages + 1))
    missing_pages = sorted(all_pages - set(current_pages))
    missing_ranges = build_missing_ranges(missing_pages)

    print(f"文件: {file_path}")
    print(f"已记录页码数: {len(current_pages)}")
    print(f"总页数: {total_pages}")

    if not missing_ranges:
        print("未发现缺失页码。")
        return

    print("缺失页码:")
    for start, end in missing_ranges:
        if start == end:
            print(f"{start}页缺失")
        else:
            print(f"{start}~{end}页缺失")


def main():
    parser = argparse.ArgumentParser(description="查找 CSV 中缺失的页码")
    parser.add_argument("file", help="CSV 文件路径")
    args = parser.parse_args()
    find_missing_pages(args.file)


if __name__ == "__main__":
    main()
