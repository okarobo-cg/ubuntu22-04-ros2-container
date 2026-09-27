# Docker ガイド (diffbot_sim 環境)

Docker に慣れていない人向けに、この環境を動かすのに必要なことだけをまとめます。

---

## 1. まず押さえる 3 つの言葉

| 言葉 | たとえ | この環境では |
|---|---|---|
| **イメージ (image)** | OS + ソフトをまとめた「設計図 / 型」 | `diffbot_sim:humble` (Ubuntu 22.04 + ROS 2 Humble + Gazebo Fortress) |
| **コンテナ (container)** | イメージから作った「実物」。中で作業する | `ubuntu_22_04_ros2` |
| **ボリューム (マウント)** | ホストのフォルダをコンテナに「共有」する | clone したフォルダ |

### ⚠️ 一番大事なこと: コンテナの中の変更は消える

コンテナを削除 (`docker compose down` / `docker rm`) すると、**マウントしていない場所への変更はすべて消えます**。

| 場所 | 消える? |
|---|---|
| `/ros2_ws/src/ubuntu22-04-ros2-container` | **残る** (ホストのフォルダと共有) |
| `/ros2_ws/build`, `/ros2_ws/install`, `/ros2_ws/log` | 消える → `colcon build` し直せば OK |
| `apt install` で入れたソフト、`~/.bashrc` の変更 | 消える → **`docker/Dockerfile` に書く** |

つまり、

- **自分で書くコード・設定は必ず clone したフォルダ (マウントされたフォルダ) の中に置く**
- **`apt install` したものは `docker/Dockerfile` にも追記する** (追記しないと他の人の環境で動かない)

---

## 2. 初回セットアップ (ホスト PC 側)

### 2-1. Docker のインストール (Ubuntu ホストの場合)

```bash
# 公式の手順: https://docs.docker.com/engine/install/ubuntu/
curl -fsSL https://get.docker.com | sh
# sudo なしで docker を使えるようにする (実行後、一度ログアウト→ログインするか newgrp docker)
sudo usermod -aG docker $USER
```

### 2-2. ディレクトリ構成と取得

```bash
git clone <リポジトリの URL>
cd ubuntu22-04-ros2-container
```

clone したフォルダ全体がコンテナ内の `/ros2_ws/src/ubuntu22-04-ros2-container` にマウントされます。フォルダ名や置き場所は自由です。

### 2-3. 起動して入る

`docker/` のスクリプトが、GUI 表示の許可・イメージのビルド・コンテナ起動をまとめてやってくれます。`docker` コマンドを自分で打つ必要はありません。

```bash
docker/start.sh    # 初回はイメージのビルドで 10 分ほど。以降はコンテナ起動のみ (数秒)
docker/shell.sh    # コンテナに入る
```

コンテナの中で:

```bash
cd /ros2_ws
colcon build --symlink-install
source install/setup.bash
ros2 launch diffbot_sim sim.launch.py
```

止めるときは `docker/stop.sh` (中身も削除するなら `docker/stop.sh --remove`)。

### 2-4. 端末を増やす

ROS 2 では端末を何枚も使います。ホストで新しい端末を開き、`docker/shell.sh` を実行すれば同じコンテナに入れます。

```bash
docker/shell.sh
# 中に入ったら (install/setup.bash は .bashrc で自動読み込み済み)
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

---

## 3. よく使うコマンド早見表

`start.sh` / `shell.sh` / `stop.sh` (Windows は `.bat`) が内部で実行している `docker compose` コマンドの対応表です。普段はスクリプトを使えば十分ですが、仕組みを知りたいときや直接使いたいときに参照してください。ホスト側で `docker/` にいる前提です。

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
docker build -t diffbot_sim:humble \
  --build-arg USER_UID=$(id -u) --build-arg USER_GID=$(id -g) <リポジトリ>/docker
docker run -it --name ubuntu_22_04_ros2 --net=host --ipc=host \
  -e DISPLAY=$DISPLAY -e QT_X11_NO_MITSHM=1 \
  -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
  -v <リポジトリ>:/ros2_ws/src/ubuntu22-04-ros2-container \
  --device /dev/dri \
  --group-add $(getent group video | cut -d: -f3) --group-add $(getent group render | cut -d: -f3) \
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
| `group_add` | 一般ユーザ `okarobo` が `/dev/dri` を使えるよう、ホストの `video` / `render` グループに入れる |
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
- **WSL2**: `/dev/dri` の代わりに `/dev/dxg` を使います (7 章)。
- GPU を渡さなくても動作はします (実測: LiDAR 約 9 Hz、カメラ 約 13 Hz)。

確認方法 (コンテナ内):

- `ls /dev/dri` で `card0` や `renderD128` が見えれば GPU が渡っています (WSL2 は `ls /dev/dxg`)。
- `glxinfo -B` の `OpenGL renderer string` が GPU 名 (WSL2 は `D3D12 (...)`) なら GPU 描画、`llvmpipe` なら CPU 描画です。

---

## 5. 注意点

### ファイルの所有者 (パーミッション)

コンテナ内は一般ユーザ **`okarobo`** で、UID/GID はホストのユーザに合わせてあります (`start.sh` が自動で渡す。Windows は 1000)。そのためコンテナ内で作ったファイルもホスト側で自分の所有になります。`apt install` などが必要なときは `sudo` が (パスワードなしで) 使えます。

`start.sh` を使わずに直接 `docker compose` を実行するなど UID が合わなかった場合は、コンテナ内で所有者を直します。

```bash
# コンテナ内で (1000 は多くの Ubuntu で最初のユーザの UID。ホストで `id -u` で確認)
sudo chown -R 1000:1000 /ros2_ws/src/ubuntu22-04-ros2-container
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
起動は `docker\windows\` にあるスクリプトで行います。

> ⚠️ Windows 用スクリプトは作成者の環境 (Linux) で「構文チェック」と「docker に渡すコマンドの確認」まではしましたが、**Windows 実機ではまだ試していません**。動かなかったら `check_env.bat` の結果と一緒に報告してください。

### 6-1. 準備 (初回のみ)

| 必要なもの | 入れ方 |
|---|---|
| Windows 11 (推奨) または Windows 10 21H2 以降 | Windows 10 の場合は Store 版 WSL が必要 (`wsl --update`) |
| WSL2 | 管理者 PowerShell で `wsl --install` → 再起動。入っていれば `wsl --update` |
| Docker Desktop | https://docs.docker.com/desktop/setup/install/windows-install/ から入れる。設定の「Use the WSL 2 based engine」を ON (既定で ON) |
| Git for Windows (clone する場合) | https://git-scm.com/download/win |
| 空き容量 | 10 GB 以上 (イメージが約 4 GB) |

フォルダ構成は Linux と同じです (リポジトリの中に `docker\windows\` がある)。

```powershell
git clone <リポジトリの URL>
```

置き場所は自由ですが、WSL2 のフォルダ (エクスプローラーで `\\wsl$\<ディストリ名>\home\...`) に clone すると、コンテナとのファイル共有が速くなります。

> `.gitattributes` で改行コードを指定してあるので、Windows で clone しても Linux 用ファイル (`.sh`, `.py` など) は LF のままになります。

### 6-2. 起動

1. Docker Desktop を起動し、左下が **Engine running** になるまで待つ
2. エクスプローラーで `docker\windows\` を開き、**`check_env.bat`** をダブルクリック → `[NG]` が無いことを確認
3. **`start.bat`** をダブルクリック
   - 初回はイメージのビルドで 10 分ほどかかる
   - コンテナがバックグラウンドで起動する (この時点ではシミュレーションはまだ起動していない)
4. **`shell.bat`** をダブルクリックしてコンテナに入り、次を実行する

   ```bash
   cd /ros2_ws
   colcon build --symlink-install
   source install/setup.bash
   ros2 launch robocon2027_field robocon2027.launch.py
   ```

   Gazebo と RViz2 のウィンドウが開き、ABU Robocon 2027 フィールドの赤スタートゾーンにロボットが出る。
5. 操縦するときは **`teleop.bat`** をダブルクリックし、そのウィンドウを選んだ状態で `i` (前進) / `,` (後退) / `j` `l` (旋回) / `k` (停止)
6. 終わるときは `shell.bat` の画面で `Ctrl+C`、その後 **`stop.bat`**

### 6-3. スクリプト一覧

| スクリプト | 内容 |
|---|---|
| `start.bat` / `start.ps1` | Docker 確認 → (必要なら) ビルド → コンテナをバックグラウンド起動 |
| `teleop.bat` / `teleop.ps1` | キーボード操縦 |
| `shell.bat` / `shell.ps1` | 起動中のコンテナで bash を開く (ROS 2 コマンドを打つ端末を増やす) |
| `stop.bat` / `stop.ps1` | コンテナ停止。`-Remove` を付けると削除 |
| `check_env.bat` / `check_env.ps1` | Windows / WSL / Docker / WSLg / GPU の状態を確認 |

`.bat` はダブルクリック用の入口で、中で同名の `.ps1` を呼んでいます
(PowerShell の実行ポリシーで `.ps1` が直接実行できない PC でも動くようにするため)。

### 6-4. start のオプション

PowerShell で `docker\windows` に移動して実行します (`.bat` にも同じオプションを付けられます)。

```powershell
.\start.bat                        # 既定 (WSLg で表示)
.\start.bat -Display vcxsrv        # WSLg ではなく VcXsrv で表示
.\start.bat -Gpu                   # GPU 描画を使う (試験的)
.\start.bat -Build                 # イメージを作り直す (Dockerfile を変えたとき)
Get-Help .\start.ps1 -Detailed     # オプションの説明
```

シミュレーションの起動 (`ros2 launch ...`) やワールド・チームの切り替えは、`shell.bat` でコンテナに入ってから launch コマンドの引数で行います。

### 6-5. 仕組み (Linux 版との違い)

| 項目 | Linux (`docker-compose.yml`) | Windows (`docker-compose.windows.yml`) |
|---|---|---|
| GUI | ホストの X11 (`/tmp/.X11-unix`, `xhost +local:`) | WSLg。Docker Desktop の VM 内の `/run/desktop/mnt/host/wslg` をマウント |
| GPU | `/dev/dri` (Intel/AMD) | `docker-compose.windows-gpu.yml` で `/dev/dxg` + `/usr/lib/wsl` (D3D12 経由, 試験的) |
| ネットワーク | `network_mode: host` | 使わない (ROS 2 の通信はコンテナ内で完結) |
| 共有メモリ | `ipc: host` | `shm_size: 2gb` |
| マウント | リポジトリ全体 | 同じ |

イメージ (`diffbot_sim:humble`) とコンテナ名 (`ubuntu_22_04_ros2`) は Linux 版と共通です。

### 6-6. うまくいかないとき

| 症状 | 対処 |
|---|---|
| `Docker Desktop が起動していません` | Docker Desktop を起動し、Engine running になってから再実行 |
| ビルドで `no matching manifest` / Windows コンテナの話が出る | タスクトレイの Docker アイコン → **Switch to Linux containers** |
| コンテナがすぐ終了し `exec /entrypoint.sh: no such file or directory` | `entrypoint.sh` が CRLF。Dockerfile で自動変換しているので `start.bat -Build` で作り直す |
| Gazebo / RViz の画面が出ない (`could not connect to display`) | `wsl --update` して PC を再起動 → `check_env.bat` で「WSLg の X11 ソケットが見えます」を確認。ダメなら VcXsrv を入れて XLaunch を「Disable access control」にチェックして起動し、`start.bat -Display vcxsrv` |
| 画面は出るが真っ黒・すぐ落ちる (`-Gpu` 使用時) | `-Gpu` を外す (CPU 描画)。`OGRE EXCEPTION ... copyTo` で落ちる問題は `MESA_GL_VERSION_OVERRIDE=4.3` で対策済み (7 章) |
| 動作がとても重い | `ros2 launch ... rviz:=false` (RViz を出さない)、または `-Gpu` を試す。ノート PC は電源につなぐ |
| `.ps1` を直接実行すると「スクリプトの実行が無効」 | `.bat` の方を使う。または `powershell -ExecutionPolicy Bypass -File .\start.ps1` |
| 日本語が文字化けする | Windows Terminal か PowerShell 7 を使う (スクリプトは UTF-8 BOM 付きで保存済み) |
| 前回の Gazebo が残って動作がおかしい | コンテナ内で `pkill -f "ign gazebo"` してから launch し直す。それでもダメなら `stop.bat` → `start.bat` |

---

## 7. WSL2 の Ubuntu で動かす

Windows の Docker Desktop ではなく、WSL2 の Ubuntu に Docker Engine (docker-ce) を入れて使う場合です。
手順は Ubuntu と同じで、`docker/start.sh` → `docker/shell.sh` を使います。

`start.sh` は `/dev/dxg` (WSL2 の GPU デバイス) を見つけると WSL2 と判定し、
[docker-compose.wsl.yml](../docker/docker-compose.wsl.yml) を重ねて起動します。

| 項目 | 設定 |
|---|---|
| GUI | WSLg (`/mnt/wslg` をマウント)。`xhost` は不要 |
| GPU | `/dev/dri` を `/dev/dxg` に差し替え、`/usr/lib/wsl` の D3D12 ドライバを使う |
| `MESA_GL_VERSION_OVERRIDE=4.3` | D3D12 ドライバは OpenGL 4.2 までしか名乗らない。Gazebo (Ogre2) のカメラ・LiDAR は 4.3 の機能を使うため、これが無いと Gazebo が落ちる |
| `MESA_D3D12_DEFAULT_ADAPTER_NAME` | GPU が複数ある PC で使う GPU を選ぶ (既定はコメントアウト) |

`docker compose` を直接使う場合は、2 つのファイルを指定します (`!override` を使うので Docker Compose v2.24.4 以降が必要)。

```bash
docker compose -f docker-compose.yml -f docker-compose.wsl.yml up -d
```

### 7-1. うまくいかないとき

| 症状 | 対処 |
|---|---|
| `permission denied while trying to connect to the docker API` | ユーザが `docker` グループに入っていない。`sudo usermod -aG docker $USER` → `newgrp docker` (または WSL を開き直す) |
| `error gathering device information ... "/dev/dri"` | WSL2 用の設定が重なっていない。`docker compose down` してから `start.sh` で起動し直す |
| Gazebo が `OGRE EXCEPTION(9:UnimplementedException) ... GL3PlusTextureGpu::copyTo` で落ちる | `MESA_GL_VERSION_OVERRIDE=4.3` が効いていない。コンテナ内で `echo $MESA_GL_VERSION_OVERRIDE` を確認 |
| GPU 描画になっているか確認したい | コンテナ内で `glxinfo -B`。`OpenGL renderer string` が `D3D12 (...)` なら GPU、`llvmpipe` なら CPU 描画 |
| GPU だと描画がおかしい | `docker-compose.wsl.yml` の environment に `- LIBGL_ALWAYS_SOFTWARE=1` を足すと CPU 描画になる (確実に動くが重い) |
