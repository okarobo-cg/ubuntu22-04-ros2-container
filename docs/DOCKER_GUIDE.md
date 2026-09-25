# Docker ガイド (diffbot_sim 環境)

Docker に慣れていない人向けに、この環境を動かすのに必要なことだけをまとめます。

---

## 1. まず押さえる 3 つの言葉

| 言葉 | たとえ | この環境では |
|---|---|---|
| **イメージ (image)** | OS + ソフトをまとめた「設計図 / 型」 | `diffbot_sim:humble` (Ubuntu 22.04 + ROS 2 Humble + Gazebo Fortress) |
| **コンテナ (container)** | イメージから作った「実物」。中で作業する | `ubuntu_22_04_ros2` |
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
docker run -it --name ubuntu_22_04_ros2 --net=host --ipc=host \
  -e DISPLAY=$DISPLAY -e QT_X11_NO_MITSHM=1 \
  -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
  -v <プロジェクト>/src:/ros2_ws/src \
  -v <プロジェクト>/config:/ros2_ws/config \
  -v <プロジェクト>/models:/ros2_ws/models \
  -v <プロジェクト>/worlds:/ros2_ws/worlds \
  --device /dev/dri \
  diffbot_sim:humble bash
# 2 枚目以降の端末: docker exec -it ubuntu_22_04_ros2 bash
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

---

## 6. Windows で動かす

Windows では **Docker Desktop** を使い、GUI (Gazebo, RViz) は **WSLg** (Windows 11 の WSL2 に標準で入っている GUI 機能) で表示します。
起動は `src\docker\windows\` にあるスクリプトで行います。

> ⚠️ Windows 用スクリプトは作成者の環境 (Linux) で「構文チェック」と「docker に渡すコマンドの確認」まではしましたが、**Windows 実機ではまだ試していません**。動かなかったら `check_env.bat` の結果と一緒に報告してください。

### 6-1. 準備 (初回のみ)

| 必要なもの | 入れ方 |
|---|---|
| Windows 11 (推奨) または Windows 10 21H2 以降 | Windows 10 の場合は Store 版 WSL が必要 (`wsl --update`) |
| WSL2 | 管理者 PowerShell で `wsl --install` → 再起動。入っていれば `wsl --update` |
| Docker Desktop | https://docs.docker.com/desktop/setup/install/windows-install/ から入れる。設定の「Use the WSL 2 based engine」を ON (既定で ON) |
| Git for Windows (clone する場合) | https://git-scm.com/download/win |
| 空き容量 | 10 GB 以上 (イメージが約 4 GB) |

フォルダ構成は Linux と同じです (`src` の中に `docker\windows\` がある)。

```powershell
# 例: C:\work\diffbot に置く
mkdir C:\work\diffbot
cd C:\work\diffbot
git clone <リポジトリの URL> src
```

> `.gitattributes` で改行コードを指定してあるので、Windows で clone しても Linux 用ファイル (`.sh`, `.py` など) は LF のままになります。

### 6-2. 起動

1. Docker Desktop を起動し、左下が **Engine running** になるまで待つ
2. エクスプローラーで `src\docker\windows\` を開き、**`check_env.bat`** をダブルクリック → `[NG]` が無いことを確認
3. **`start.bat`** をダブルクリック
   - 初回はイメージのビルドで 10 分ほどかかる
   - Gazebo と RViz2 のウィンドウが開き、ABU Robocon 2027 フィールドの赤スタートゾーンにロボットが出る
4. 操縦するときは **`teleop.bat`** をダブルクリックし、そのウィンドウを選んだ状態で `i` (前進) / `,` (後退) / `j` `l` (旋回) / `k` (停止)
5. 終わるときは `start.bat` の画面で `Ctrl+C`、その後 **`stop.bat`**

### 6-3. スクリプト一覧

| スクリプト | 内容 |
|---|---|
| `start.bat` / `start.ps1` | Docker 確認 → (必要なら) ビルド → コンテナ起動 → `colcon build` → シミュレーション起動 |
| `teleop.bat` / `teleop.ps1` | キーボード操縦 |
| `shell.bat` / `shell.ps1` | 起動中のコンテナで bash を開く (ROS 2 コマンドを打つ端末を増やす) |
| `stop.bat` / `stop.ps1` | コンテナ停止。`-Remove` を付けると削除 |
| `check_env.bat` / `check_env.ps1` | Windows / WSL / Docker / WSLg / GPU の状態を確認 |

`.bat` はダブルクリック用の入口で、中で同名の `.ps1` を呼んでいます
(PowerShell の実行ポリシーで `.ps1` が直接実行できない PC でも動くようにするため)。

### 6-4. start のオプション

PowerShell で `src\docker\windows` に移動して実行します (`.bat` にも同じオプションを付けられます)。

```powershell
.\start.bat                        # Robocon 2027 フィールド・赤チーム (既定)
.\start.bat -Team blue             # 青チーム
.\start.bat -Launch diffbot        # 練習用ワールド
.\start.bat -Launch shell          # シミュレーションは起動せず bash だけ開く
.\start.bat -NoRviz                # RViz を出さない (軽くなる)
.\start.bat -Headless              # Gazebo の画面を出さない (GUI が出ないときの切り分け)
.\start.bat -Display vcxsrv        # WSLg ではなく VcXsrv で表示
.\start.bat -Gpu                   # GPU 描画を使う (試験的)
.\start.bat -Build                 # イメージを作り直す (Dockerfile を変えたとき)
Get-Help .\start.ps1 -Detailed     # オプションの説明
```

### 6-5. 仕組み (Linux 版との違い)

| 項目 | Linux (`docker-compose.yml`) | Windows (`docker-compose.windows.yml`) |
|---|---|---|
| GUI | ホストの X11 (`/tmp/.X11-unix`, `xhost +local:`) | WSLg。Docker Desktop の VM 内の `/run/desktop/mnt/host/wslg` をマウント |
| GPU | `/dev/dri` (Intel/AMD) | `docker-compose.windows-gpu.yml` で `/dev/dxg` + `/usr/lib/wsl` (D3D12 経由, 試験的) |
| ネットワーク | `network_mode: host` | 使わない (ROS 2 の通信はコンテナ内で完結) |
| 共有メモリ | `ipc: host` | `shm_size: 2gb` |
| マウント | `src config models worlds` | 同じ |

イメージ (`diffbot_sim:humble`) とコンテナ名 (`ubuntu_22_04_ros2`) は Linux 版と共通です。

### 6-6. うまくいかないとき

| 症状 | 対処 |
|---|---|
| `Docker Desktop が起動していません` | Docker Desktop を起動し、Engine running になってから再実行 |
| ビルドで `no matching manifest` / Windows コンテナの話が出る | タスクトレイの Docker アイコン → **Switch to Linux containers** |
| コンテナがすぐ終了し `exec /entrypoint.sh: no such file or directory` | `entrypoint.sh` が CRLF。Dockerfile で自動変換しているので `start.bat -Build` で作り直す |
| Gazebo / RViz の画面が出ない (`could not connect to display`) | `wsl --update` して PC を再起動 → `check_env.bat` で「WSLg の X11 ソケットが見えます」を確認。ダメなら VcXsrv を入れて XLaunch を「Disable access control」にチェックして起動し、`start.bat -Display vcxsrv` |
| 画面は出るが真っ黒・すぐ落ちる (`-Gpu` 使用時) | `-Gpu` を外す (CPU 描画) |
| 動作がとても重い | `-NoRviz`、または `-Gpu` を試す。ノート PC は電源につなぐ |
| `.ps1` を直接実行すると「スクリプトの実行が無効」 | `.bat` の方を使う。または `powershell -ExecutionPolicy Bypass -File .\start.ps1` |
| 日本語が文字化けする | Windows Terminal か PowerShell 7 を使う (スクリプトは UTF-8 BOM 付きで保存済み) |
| 前回の Gazebo が残って動作がおかしい | `start.bat` は起動前に残った Gazebo を自動で止める。それでもダメなら `stop.bat` → `start.bat` |
