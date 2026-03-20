#!/usr/bin/env bash
rm -f slog.txt

set -euo pipefail

exec > >(tee slog.txt) 2>&1




python3 main.py 超级鹿鼎公 8790885129 689 690

python3 main.py 超级鹿鼎公 8790885129 855 867



