#!/bin/bash
# イメージをビルドし、コンテナをバックグラウンドで起動する。
# 実行後は shell.sh でコンテナに入る。
set -e

cd "$(dirname "$0")"

echo "[1/2] GUI 表示の許可 (xhost +local:)"
xhost +local: >/dev/null 2>&1 || true   # WSL2 (WSLg) では不要だが害はない

echo "[2/2] イメージのビルドとコンテナ起動"
# コンテナの一般ユーザ okarobo をホストのユーザに合わせる
export HOST_UID=$(id -u) HOST_GID=$(id -g)
export VIDEO_GID=$(getent group video | cut -d: -f3 || true)
export RENDER_GID=$(getent group render | cut -d: -f3 || true)

# WSL2 (/dev/dxg がある) なら WSLg + D3D12 GPU 用の設定 (docker-compose.wsl.yml) を重ねる
if [ -e /dev/dxg ]; then
  echo "      WSL2 を検出: docker-compose.wsl.yml を重ねて使います"
  export COMPOSE_FILE=docker-compose.yml:docker-compose.wsl.yml
fi

docker compose build
docker compose up -d

echo ""
echo "コンテナ ubuntu_22_04_ros2 が起動しました。"
echo "  入る: ./shell.sh"
echo "  止める: ./stop.sh"
