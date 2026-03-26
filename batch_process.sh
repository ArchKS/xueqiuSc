#!/bin/bash

# 创建输出目录
mkdir -p filter
mkdir -p result

# 清理现有的 filter 目录
rm -f filter/*

# 遍历 data 目录下的所有 CSV 文件
for file in data/*.csv; do
    # 获取文件名（不含路径和扩展名）
    filename=$(basename "$file")
    name="${filename%.*}"

    echo "-----------------------------------"
    echo "正在处理博主: $name ..."

    # 1. 使用 filter_csv.py 进行过滤
    # 使用与 process.sh 一致的参数: -len 10 -c 1
    python3 filter_csv.py "$file" -len 10 -c 1

    # 2. 找到生成的过滤后文件并使用 keep_time_and_content.py 处理
    # 过滤后的文件通常在 filter/ 目录下，且含有 _filter_ 标识
    filtered_file=$(find filter/ -name "${name}_filter_*.csv" | head -n 1)

    if [ -n "$filtered_file" ]; then
        python3 keep_time_and_content.py "$filtered_file"

        # 3. 将最终的 _time_content.csv 移动到 result 目录
        engagement_file=$(find filter/ -name "${name}_filter_*_time_content.csv" | head -n 1)
        
        if [ -n "$engagement_file" ]; then
            # 移动并重命名为更简洁的名字
            mv "$engagement_file" "result/${name}_time_content.csv"
            echo "[+] 成功生成: result/${name}_time_content.csv"
        else
            echo "[-] 警告: 未找到 ${name} 的 time_content 文件"
        fi
    else
        echo "[-] 警告: 未找到 ${name} 的过滤后文件 (可能是没有符合条件的帖子)"
    fi

    # 4. 删除中间生成的临时文件（清理 filter 目录下关于该博主的所有文件）
    rm -f filter/"${name}"_*
done

# 可选：如果 filter 目录为空，则删除它
# rmdir filter 2>/dev/null

echo "-----------------------------------"
echo "批量处理完成！结果保存在 result 目录下。"
