# 本地 / CI（含 Gitee Go）：必须在 app3 目录安装包（pyproject.toml 在 app3/ 下，不在仓库根目录）
.PHONY: test
test:
	cd app3 && python -m pip install -U pip && pip install -e . && python -m unittest discover -s tests -p "test_*.py" -v
