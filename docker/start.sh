#!/bin/bash
# イメージをビルドし、コンテナをバックグラウンドで起動する。
# 実行後は shell.sh でコンテナに入る。
set -e

cd "$(dirname "$0")"

echo "[1/3] GUI 表示の許可 (xhost +local:)"
xhost +local: >/dev/null 2>&1 || true

echo "[2/3] フォルダの準備"
mkdir -p ../../config ../../models ../../worlds

echo "[3/3] イメージのビルドとコンテナ起動"
docker compose build
docker compose up -d

echo ""
echo "コンテナ ubuntu_22_04_ros2 が起動しました。"
echo "  入る: ./shell.sh"
echo "  止める: ./stop.sh"
