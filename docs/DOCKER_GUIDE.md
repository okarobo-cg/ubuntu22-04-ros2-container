# Docker ガイド (diffbot_sim 環境)

Docker に慣れていない人向けに、この環境を動かすのに必要なことだけをまとめます。

---

## 1. まず押さえる 3 つの言葉

| 言葉 | たとえ | この環境では |
|---|---|---|
| **イメージ (image)** | OS + ソフトをまとめた「設計図 / 型」 | `diffbot_sim:humble` (Ubuntu 22.04 + ROS 2 Humble + Gazebo Fortress) |
| **コンテナ (container)** | イメージから作った「実物」。中で作業する | `diffbot_sim` |
| **ボリューム (マウント)** | ホストのフォルダをコンテナに「共有」する | `src/ config/ models/ worlds/` |

### ⚠️ 一番大事なこと: コンテナの中の変更は消える

コンテナを削除 (`docker compose down` / `docker rm`) すると、**マウントしていない場所への変更はすべて消えます**。

| 場所 | 消える? |
|---|---|
| `/ros2_ws/src`, `/ros2_ws/config`, `/ros2_ws/models`, `/ros2_ws/worlds` | **残る** (ホストのフォルダと共有) |
| `/ros2_ws/build`, `/ros2_ws/install`, `/ros2_ws/log` | 消える → `colcon build` し直せば OK |
| `apt install` で入れたソフト、`~/.bashrc` の変更 | 消える → **`docker/Dockerfile` に書く** |

つまり、

- **自分で書くコード・設定は必ず `src/` などマウントされたフォルダに置く**
- **`apt install` したものは `docker/Dockerfile` にも追記する** (追記しないと他の人の環境で動かない)

---

## 2. 初回セットアップ (ホスト PC 側)

### 2-1. Docker のインストール (Ubuntu ホストの場合)

```bash
# 公式の手順: https://docs.docker.com/engine/install/ubuntu/
curl -fsSL https://get.docker.com | sh
# sudo なしで docker を使えるようにする (実行後、一度ログアウト→ログイン)
sudo usermod -aG docker $USER
```

### 2-2. ディレクトリ構成

配布物を次の構成で置きます。

```
<プロジェクト>/
├── src/              ← このリポジトリ (README.md, diffbot_sim/, docker/, docs/)
├── config/
├── models/           ← 自作の Gazebo モデル置き場 (空で OK)
└── worlds/           ← 自作ワールド置き場 (空で OK)
```

```bash
mkdir -p <プロジェクト>/{config,models,worlds}
```

> 空のフォルダが無いと Docker が root 所有で勝手に作ってしまうので、先に作っておきます。

### 2-3. イメージのビルドと起動

```bash
cd <プロジェクト>/src/docker

xhost +local:            # コンテナからホストの画面に GUI を出す許可 (PC を再起動するたびに 1 回)
docker compose build     # イメージを作る (初回は 10 分ほど。Dockerfile を変えたときも実行)
docker compose up -d     # コンテナをバックグラウンドで起動
docker compose exec ros2 bash   # コンテナの中に入る
```

コンテナの中で:

```bash
cd /ros2_ws
colcon build --symlink-install
source install/setup.bash
ros2 launch diffbot_sim sim.launch.py
```

### 2-4. 端末を増やす

ROS 2 では端末を何枚も使います。ホストで新しい端末を開き、同じコマンドでコンテナに入ります。

```bash
cd <プロジェクト>/src/docker
docker compose exec ros2 bash
# 中に入ったら (install/setup.bash は .bashrc で自動読み込み済み)
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

---

## 3. よく使うコマンド早見表

ホスト側で `src/docker/` にいる前提です。

| やりたいこと | コマンド |
|---|---|
| イメージを作る / 作り直す | `docker compose build` |
| コンテナ起動 | `docker compose up -d` |
| コンテナに入る (何枚でも) | `docker compose exec ros2 bash` |
| コンテナ停止 (中身は残る) | `docker compose stop` |
| 停止したコンテナを再開 | `docker compose start` |
| コンテナ削除 (マウント外の変更は消える) | `docker compose down` |
| 動いているコンテナ一覧 | `docker ps` |
| すべてのコンテナ一覧 | `docker ps -a` |
| イメージ一覧 | `docker images` |
| 使っていないデータを掃除 | `docker system prune` |

`docker compose` を使わない場合の同等コマンド (参考):

```bash
docker build -t diffbot_sim:humble <プロジェクト>/src/docker
docker run -it --name diffbot_sim --net=host --ipc=host \
  -e DISPLAY=$DISPLAY -e QT_X11_NO_MITSHM=1 \
  -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
  -v <プロジェクト>/src:/ros2_ws/src \
  -v <プロジェクト>/config:/ros2_ws/config \
  -v <プロジェクト>/models:/ros2_ws/models \
  -v <プロジェクト>/worlds:/ros2_ws/worlds \
  --device /dev/dri \
  diffbot_sim:humble bash
# 2 枚目以降の端末: docker exec -it diffbot_sim bash
```

---

## 4. 各設定の意味 (`docker-compose.yml`)

| 設定 | 意味 |
|---|---|
| `network_mode: host` | ホストと同じネットワークを使う。ROS 2 (DDS) の通信がそのまま通る |
| `ipc: host` | 共有メモリをホストと共有。ROS 2 や GUI が安定する |
| `DISPLAY`, `/tmp/.X11-unix` | コンテナの GUI (Gazebo, RViz) をホストの画面に表示する |
| `devices: /dev/dri` | GPU (Intel / AMD) を使う。無いと CPU 描画になり重い |
| `volumes` | ホストのフォルダを共有 (ここに置いたファイルは消えない) |

### GPU について

- **Intel / AMD の GPU**: `/dev/dri` を渡すだけで OK (compose ファイルに設定済み)。
- **NVIDIA の GPU**: ホストに NVIDIA Container Toolkit を入れ、compose ファイルの `devices` の代わりに以下を追加します。
  ```yaml
      deploy:
        resources:
          reservations:
            devices:
              - driver: nvidia
                count: all
                capabilities: [gpu, graphics, utility]
      environment:
        - NVIDIA_DRIVER_CAPABILITIES=all
  ```
- GPU を渡さなくても動作はします (実測: LiDAR 約 9 Hz、カメラ 約 13 Hz)。

確認方法 (コンテナ内): `ls /dev/dri` で `card0` や `renderD128` が見えれば GPU が渡っています。

---

## 5. 注意点

### ファイルの所有者 (パーミッション)

コンテナ内は `root` ユーザなので、コンテナ内で作ったファイルはホストから見ると **root 所有** になり、ホストのエディタで保存できないことがあります。そのときはコンテナ内で所有者を直します。

```bash
# コンテナ内で (1000 は多くの Ubuntu で最初のユーザの UID。ホストで `id -u` で確認)
chown -R 1000:1000 /ros2_ws/src
```

### 同じネットワークで複数人が使う場合

`network_mode: host` なので、同じ LAN にいる他の人の ROS 2 ノードと通信が混ざることがあります。人ごとに別の番号を設定してください。

```bash
export ROS_DOMAIN_ID=10   # 0〜101 の範囲で人ごとに変える (~/.bashrc に書くなら Dockerfile へ)
```

### Git で配布するとき

`build/ install/ log/` はビルドで生成されるので Git に含めません (`.gitignore` に書く)。
