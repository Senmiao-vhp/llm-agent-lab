#!/usr/bin/env bash
# Gitee Go / Jenkins：请在「编译」阶段把「执行命令」设为脚本路径或以下内容。
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT}/app3"
python -m pip install --upgrade pip
pip install -e .
python -m unittest discover -s tests -p "test_*.py" -v
