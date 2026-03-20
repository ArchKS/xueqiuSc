#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 4 ]; then
  echo "用法: bash batch_run_ranges.sh <username> <uid> <start_page> <end_page>"
  exit 1
fi

username="$1"
uid="$2"
start_page="$3"
end_page="$4"

chunk_size=30
sleep_seconds=600

if ! [[ "$start_page" =~ ^[0-9]+$ && "$end_page" =~ ^[0-9]+$ ]]; then
  echo "错误: start_page 和 end_page 必须是整数"
  exit 1
fi

if [ "$start_page" -gt "$end_page" ]; then
  echo "错误: start_page 不能大于 end_page"
  exit 1
fi

current_start="$start_page"

while [ "$current_start" -le "$end_page" ]; do
  current_end=$((current_start + chunk_size - 1))
  if [ "$current_end" -gt "$end_page" ]; then
    current_end="$end_page"
  fi

  echo "执行区间: ${current_start}-${current_end}"
  python3 main.py "$username" "$uid" "$current_start" "$current_end"

  if [ "$current_end" -lt "$end_page" ]; then
    echo "当前区间完成，暂停 10 分钟..."
    sleep "$sleep_seconds"
  fi

  current_start=$((current_end + 1))
done
