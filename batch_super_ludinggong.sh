#!/usr/bin/env bash
rm -f slog.txt

type_param="${1:-}"

sh batch_run_ranges.sh 管我财 9650668145 571 585 "$type_param"
sh batch_run_ranges.sh 管我财 9650668145 1021 1035 "$type_param"
sh batch_run_ranges.sh 管我财 9650668145 1396 1410 "$type_param"