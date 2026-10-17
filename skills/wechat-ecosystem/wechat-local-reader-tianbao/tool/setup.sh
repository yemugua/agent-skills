#!/usr/bin/env bash
# wechat-local-reader 安装脚本（macOS / Linux）
# 用法： bash tool/setup.sh
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

# 找 Python：优先 python3，其次 python
PY=""
for c in python3 python; do
    if command -v "$c" >/dev/null 2>&1; then PY="$c"; break; fi
done
if [ -z "$PY" ]; then
    echo "错误：未找到 Python。请先安装 Python >= 3.10。"
    exit 1
fi
echo "使用解释器: $($PY --version 2>&1)"

echo "[1/3] 创建隔离虚拟环境 .venv ..."
"$PY" -m venv .venv
VPY="$ROOT/.venv/bin/python"

echo "[2/3] 安装依赖（优先阿里云镜像，失败回退 PyPI）..."
if ! "$VPY" -m pip install -r requirements.txt \
        -i https://mirrors.aliyun.com/pypi/simple/ \
        --trusted-host mirrors.aliyun.com --timeout 60 --retries 3; then
    echo "镜像安装失败，回退到 PyPI ..."
    "$VPY" -m pip install -r requirements.txt --timeout 60 --retries 3
fi

echo "[3/3] 生成启动器 wechat-cli ..."
# 说明：不走 `pip install -e .`（国内网络下常因构建隔离拉不到 setuptools 而失败），
# 改为设置 PYTHONPATH + 直接调用 click 入口，效果等价且更稳。
cat > wechat-cli <<EOF
#!/bin/sh
export PYTHONPATH="$ROOT"
exec "$VPY" -c 'import sys; from wechat_cli.main import cli; sys.exit(cli())' "\$@"
EOF
chmod +x wechat-cli

echo
echo "安装完成。把 $ROOT 加入 PATH 后，即可直接运行："
echo "    wechat-cli --help"
echo "或在该目录内使用： ./wechat-cli --help"
