#!/usr/bin/env bash
# Gitee Go / Jenkins：流水线必须先完成「检出代码」。
# 若 Shell 启动时 cwd 已失效（getcwd 报错），先跳到脚本所在目录再解析仓库根。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="${SCRIPT_DIR}/.."
cd "${ROOT}"
ROOT="$(pwd)"
if git rev-parse --show-toplevel >/dev/null 2>&1; then
  ROOT="$(git rev-parse --show-toplevel)"
fi

APPDIR="${ROOT}/app3"
if [[ ! -d "${APPDIR}" ]]; then
  echo "ERROR: ${APPDIR} not found." >&2
  exit 1
fi
cd "${APPDIR}"
python -m pip install --upgrade pip
pip install -e .
python -m unittest discover -s tests -p "test_*.py" -v
