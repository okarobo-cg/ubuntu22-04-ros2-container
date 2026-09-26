#!/bin/bash
# 起動中のコンテナで bash を開く (端末を増やすときも同じ)。
set -e

cd "$(dirname "$0")"

docker compose exec ros2 bash
