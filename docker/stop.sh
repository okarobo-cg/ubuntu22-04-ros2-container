#!/bin/bash
# コンテナを停止する。--remove を付けると削除する (docker compose down)。
# src / config / models / worlds はホストにあるので消えないが、
# コンテナ内の build / install や apt install したものは削除で消える。
set -e

cd "$(dirname "$0")"

if [ "$1" = "--remove" ]; then
  docker compose down
else
  docker compose stop
fi
