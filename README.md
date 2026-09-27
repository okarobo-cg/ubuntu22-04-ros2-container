# diffbot_sim — 教育用 差動二輪ロボット シミュレーション

ROS 2 Humble と Gazebo Fortress で動かす、学習用のシンプルな差動二輪ロボットです。

| 項目 | 内容 |
|---|---|
| OS / ROS | Ubuntu 22.04 / ROS 2 Humble |
| シミュレータ | Gazebo Fortress (ign-gazebo 6)、`ros_gz` で ROS 2 と連携 |
| 駆動 | 差動二輪 (左右の車輪 + 前後キャスター) |
| センサ | 3D LiDAR (16ch)、前方カメラ、下向きカメラ、IMU |

> 関連ドキュメント
> - [docs/DOCKER_GUIDE.md](docs/DOCKER_GUIDE.md) … Docker の基本と、この環境の起動方法 (Docker が初めての人はここから)
> - [docs/WORKLOG.md](docs/WORKLOG.md) … この環境を作ったときの作業記録 (編集内容とコマンド)
> - [robocon2027_field/README.md](robocon2027_field/README.md) … ABU Robocon 2027 フィールドで動かす

---

## 1. Docker コンテナの立ち上げ

Docker (Ubuntu は Docker Engine、Windows は Docker Desktop) は入っている前提です。
コンテナ名は **`ubuntu_22_04_ros2`**、イメージ名は `diffbot_sim:humble` です。
以降の操作はすべて `docker/` のスクリプトが行うので、`docker` コマンドを自分で打つ必要はありません。

### 1-1. 取得 (最初の 1 回だけ)

```bash
git clone https://github.com/okarobo-cg/ubuntu22-04-ros2-container.git
cd ubuntu22-04-ros2-container
```

clone したフォルダ全体がコンテナ内の `/ros2_ws/src/ubuntu22-04-ros2-container` にマウントされ、ここに置いたファイルはコンテナを消しても残ります。フォルダ名や置き場所は自由です (Windows は WSL2 側のフォルダに置くとファイル共有が速くなります)。

### 1-2. 起動 (イメージのビルド → コンテナをバックグラウンド起動)

| OS | やること |
|---|---|
| Ubuntu | `docker/start.sh` を実行 |
| Windows | `docker\windows\start.bat` をダブルクリック (先に `check_env.bat` で環境チェックしておくと安心) |

初回はイメージのビルドで 10 分ほどかかります。シミュレーションはまだ起動しません (起動するだけ)。

### 1-3. コンテナに入る (端末を増やすときも同じ)

| OS | やること |
|---|---|
| Ubuntu | `docker/shell.sh` |
| Windows | `docker\windows\shell.bat` をダブルクリック |

コンテナに入ったら、次の「2. クイックスタート」に進みます。

### 1-4. 停止

| OS | やること |
|---|---|
| Ubuntu | `docker/stop.sh` (削除するなら `docker/stop.sh --remove`) |
| Windows | `docker\windows\stop.bat` (削除するなら `stop.bat -Remove`) |

停止だけなら次回はすぐ再開できます。削除すると `build/ install/` や `apt install` した内容は消えますが、clone したフォルダはホストにあるので残ります。

### 補足

- GPU (`/dev/dri`) が無い Ubuntu PC では、`docker/docker-compose.yml` の `devices:` の 2 行をコメントアウトしてください (CPU 描画で動きます)。
- WSL2 の Ubuntu に Docker Engine を入れて使う場合も `docker/start.sh` で起動します。WSL2 だと自動で判定し、WSLg での表示と GPU 描画 (`/dev/dxg`) の設定を使います ([DOCKER_GUIDE の 7 章](docs/DOCKER_GUIDE.md#7-wsl2-の-ubuntu-で動かす))。
- Windows は WSL2 (Windows 11 推奨) + Docker Desktop が必要です。GUI は WSLg で表示されるので `xhost` は不要です。準備手順やオプション (`-Gpu` / `-Display vcxsrv` / `-Build`)、トラブル対応は [DOCKER_GUIDE の 6 章](docs/DOCKER_GUIDE.md#6-windows-で動かす) を参照してください。
- キーボード操縦は Ubuntu / Windows 共通で、コンテナに入って `ros2 run teleop_twist_keyboard teleop_twist_keyboard` を実行します (Windows は `teleop.bat` でも同じことができます)。
- `docker compose` を直接使いたい場合の対応表は [DOCKER_GUIDE の早見表](docs/DOCKER_GUIDE.md#3-よく使うコマンド早見表) を参照してください。

> ⚠️ Windows 用の設定・スクリプトは Windows 実機ではまだ動作確認していません。

---

## 2. クイックスタート

コンテナの中で次を実行します (コンテナの入り方は「1. Docker コンテナの立ち上げ」を参照)。

```bash
# (1) ビルド (初回・ファイルを追加したとき・コンテナを作り直したとき)
cd /ros2_ws
colcon build --symlink-install
source install/setup.bash

# (2) シミュレーション起動 (Gazebo + RViz2)
ros2 launch diffbot_sim sim.launch.py
```

別の端末 (ホストで `docker/shell.sh` を実行してもう 1 つコンテナに入る。Windows は `shell.bat` または `teleop.bat`) で操縦します。

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
#   i: 前進   ,: 後退   j / l: 左右旋回   k: 停止   q / z: 速度を上げる / 下げる
```

コマンド 1 行で動かすこともできます。

```bash
ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2}, angular: {z: 0.3}}"
# Ctrl+C で送信を止めても、ロボットは最後の指令で動き続ける。止めるには速度 0 を送る:
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{}"
```

### ABU Robocon 2027 フィールドで動かす

```bash
ros2 launch robocon2027_field robocon2027.launch.py   # 赤チームのスタートゾーンに置いて起動
```

詳細 (青チーム・ゾーン切替・ロボット寸法のルールチェック・既知の問題) は [robocon2027_field/README.md](robocon2027_field/README.md)。

### launch 引数 (`diffbot_sim sim.launch.py`)

| 引数 | 既定値 | 説明 |
|---|---|---|
| `world` | `diffbot_sim/worlds/diffbot_world.sdf` | 読み込むワールド。自作ワールドはこのリポジトリ内に置いて `world:=/ros2_ws/src/ubuntu22-04-ros2-container/xxx.sdf` |
| `gui` | `true` | `false` で Gazebo を画面なし (サーバのみ) で起動 |
| `rviz` | `true` | `false` で RViz2 を起動しない |
| `x` `y` `z` `yaw` | `0 0 0.05 0` | ロボットの初期位置・向き |
| `use_sim_time` | `true` | シミュレーション時刻を使う |

例: `ros2 launch diffbot_sim sim.launch.py gui:=false x:=-1.0 yaw:=1.57`

---

## 3. ROS 2 トピック一覧

| トピック | 型 | 向き | 内容 |
|---|---|---|---|
| `/cmd_vel` | `geometry_msgs/msg/Twist` | ROS → Gazebo | 速度指令 (linear.x [m/s], angular.z [rad/s]) |
| `/odom` | `nav_msgs/msg/Odometry` | Gazebo → ROS | オドメトリ (30 Hz) |
| `/tf` | `tf2_msgs/msg/TFMessage` | Gazebo → ROS | `odom` → `base_footprint` |
| `/tf_static`, `/tf` | | robot_state_publisher | ロボット内部の座標系 |
| `/joint_states` | `sensor_msgs/msg/JointState` | Gazebo → ROS | 車輪の角度 |
| `/lidar/points` | `sensor_msgs/msg/PointCloud2` | lidar_body_filter | 3D LiDAR 点群 (10 Hz, 最大 360×16 点, frame: `lidar_link`)。車体に当たった点は除去済み |
| `/lidar/points_raw` | `sensor_msgs/msg/PointCloud2` | Gazebo → ROS | 上のフィルタ前の生データ |
| `/front_camera/image_raw` | `sensor_msgs/msg/Image` | Gazebo → ROS | 前方カメラ 640×480 (15 Hz) |
| `/front_camera/camera_info` | `sensor_msgs/msg/CameraInfo` | Gazebo → ROS | 前方カメラの内部パラメータ |
| `/down_camera/image_raw` | `sensor_msgs/msg/Image` | Gazebo → ROS | 下向きカメラ 320×240 (15 Hz)、画像の上 = ロボットの前 |
| `/down_camera/camera_info` | `sensor_msgs/msg/CameraInfo` | Gazebo → ROS | 下向きカメラの内部パラメータ |
| `/imu` | `sensor_msgs/msg/Imu` | Gazebo → ROS | IMU (100 Hz) |
| `/clock` | `rosgraph_msgs/msg/Clock` | Gazebo → ROS | シミュレーション時刻 |
| `/robot_description` | `std_msgs/msg/String` | robot_state_publisher | URDF |

※ 実測値 (GPU なし・CPU 描画の環境): LiDAR 約 9 Hz、カメラ 約 13 Hz。PC の性能で変わります。

### 確認に便利なコマンド

```bash
ros2 topic list                       # トピック一覧
ros2 topic hz /lidar/points           # 周期を測る
ros2 topic echo /odom --once          # 1 回だけ中身を表示
ros2 run rqt_image_view rqt_image_view  # カメラ画像を見る (トピックを選択)
ros2 run tf2_tools view_frames        # TF ツリーを frames.pdf に出力
ign topic -l                          # Gazebo 側のトピック一覧
```

---

## 4. ロボットの仕様

```
上から見た図 (x: 前 → / y: 左 ↑)

          ▆▆▆▆▆  left wheel
   ┌──────────────────┐
   │                  │■ front_camera (車体前面, 床から 0.12 m)
   │ o       ◎      o │ ▣ down_camera (前方に張り出し, 床から 0.08 m, 真下向き)
   │rear   lidar front│
   └──────────────────┘
          ▆▆▆▆▆  right wheel
      0.40 m × 0.30 m

横から見た図

             ▅ lidar (床から 0.175 m)
   ┌──────────────────┐■ front_camera
   │       body       │
   └──o──────●──────o─┘ ▣ down_camera ↓
 ─────────────────────────────── 床
    caster  wheel  caster
```

| パラメータ | 値 |
|---|---|
| 車体サイズ | 0.40 × 0.30 × 0.10 m、5 kg |
| 車輪半径 / 幅 | 0.05 m / 0.04 m |
| 車輪間距離 (wheel_separation) | 0.35 m |
| 最大速度 | 並進 1.0 m/s、旋回 2.0 rad/s (`urdf/diffbot.gazebo.xacro` で変更可) |
| 3D LiDAR | 水平 360° / 360 点、垂直 ±15° / 16 ch、0.1 – 30 m、ノイズ σ=0.01 m |
| 前方カメラ | 640×480、水平画角 80° |
| 下向きカメラ | 320×240、水平画角 90° (床の約 0.16 m 幅が見える) |

### TF ツリー

```
odom
 └─ base_footprint            (Gazebo の DiffDrive が publish)
     └─ base_link             (以下 robot_state_publisher が publish)
         ├─ left_wheel_link / right_wheel_link
         ├─ front_caster_link / rear_caster_link
         ├─ lidar_link
         ├─ front_camera_link ─ front_camera_optical_frame
         ├─ down_camera_link  ─ down_camera_optical_frame
         └─ imu_link
```

`*_optical_frame` は画像処理用の座標系 (z: 前方 / x: 右 / y: 下) です。

### ワールド (`worlds/diffbot_world.sdf`)

- 10 m × 10 m の壁で囲まれたアリーナ
- 色付きの箱・円柱 (LiDAR・カメラの確認用)
- 床に黒いラインの長方形ループ (x: -1.5 ～ 2.5 m, y: 0 ～ 2 m)。ロボットはライン上 (原点) からスタートするので、下向きカメラでライントレースの練習ができます。
- 影は無効にしています。有効にすると画面が白飛びし、下向きカメラに車体の影が映り込んで、色検知やライントレースがしにくくなるためです。

---

## 5. ファイル構成

```
ubuntu22-04-ros2-container/
├── README.md                    … このファイル
├── docs/
│   ├── DOCKER_GUIDE.md          … Docker の使い方
│   └── WORKLOG.md               … 作業記録
├── docker/
│   ├── Dockerfile               … 環境を再現するイメージ定義
│   ├── docker-compose.yml       … コンテナ起動設定 (Linux 用: GUI・マウント・GPU)
│   ├── docker-compose.wsl.yml   … WSL2 の Ubuntu で使う追加設定 (start.sh が自動で重ねる)
│   ├── docker-compose.windows.yml     … Windows (Docker Desktop + WSLg) 用
│   ├── docker-compose.windows-gpu.yml … Windows で GPU を使う追加設定 (試験的)
│   ├── entrypoint.sh
│   ├── start.sh / shell.sh / stop.sh  … Ubuntu 用起動スクリプト
│   └── windows/                 … Windows 用起動スクリプト
│       ├── start.bat / start.ps1       … ビルド・コンテナ起動 (バックグラウンド)
│       ├── teleop.bat / teleop.ps1     … キーボード操縦
│       ├── shell.bat / shell.ps1       … コンテナの bash を開く
│       ├── stop.bat / stop.ps1         … 停止 (-Remove で削除)
│       ├── check_env.bat / check_env.ps1 … 環境チェック
│       └── common.ps1                  … 共通処理
├── diffbot_sim/                 … ROS 2 パッケージ本体
│   ├── package.xml / CMakeLists.txt
│   ├── urdf/
│   │   ├── diffbot.urdf.xacro   … ロボットの形・関節 (寸法はここの property を変える)
│   │   └── diffbot.gazebo.xacro … Gazebo 用: センサ・DiffDrive プラグイン
│   ├── worlds/diffbot_world.sdf … ワールド
│   ├── config/bridge.yaml       … Gazebo ⇔ ROS 2 のトピック対応表
│   ├── rviz/diffbot.rviz        … RViz2 の表示設定
│   ├── scripts/lidar_body_filter.py … LiDAR 点群から車体の点を除く
│   └── launch/sim.launch.py     … 全部まとめて起動
└── robocon2027_field/           … ABU Robocon 2027 フィールド
    ├── README.md
    ├── glb/robocon2027_field_props.glb  … 元のフィールドモデル
    ├── scripts/glb_to_sdf.py    … GLB → SDF ワールド変換
    ├── scripts/check_robot_size.py … ロボット寸法のルールチェック
    ├── worlds/robocon2027.sdf   … 生成されたワールド (直接編集しない)
    ├── config/start_zones.yaml  … スタートゾーン位置 (自動生成)
    └── launch/robocon2027.launch.py … フィールド + diffbot をスタートゾーンに置いて起動
```

### 改造するときのヒント

| やりたいこと | 編集するファイル |
|---|---|
| 車体・車輪の寸法を変える | `urdf/diffbot.urdf.xacro` の `xacro:property` (DiffDrive にも自動反映)。車体を変えたら `lidar_body_filter.py` の除去範囲と、Robocon フィールドを使うなら `check_robot_size.py` の結果も見直す |
| センサの解像度・周期・画角を変える | `urdf/diffbot.gazebo.xacro` |
| センサを増やす | 両 xacro にリンクとセンサを追加 → `config/bridge.yaml` にトピックを追加 |
| 障害物を置く | `worlds/diffbot_world.sdf` に `<model>` を追加 |
| RViz の表示を保存したい | RViz で「File → Save Config As」→ `rviz/diffbot.rviz` に上書き |

`--symlink-install` でビルドしているので、urdf / world / yaml / launch / scripts の編集は **再ビルド不要** (launch し直すだけ) です。
新しいファイルやディレクトリを追加したときは `colcon build --symlink-install` をやり直してください。

---

## 6. トラブルシューティング

| 症状 | 対処 |
|---|---|
| `Could not connect to display` / 画面が出ない (Ubuntu) | `xhost +local:` は `start.sh` が実行するので、`start.sh` からやり直す。コンテナ内で `echo $DISPLAY` が空でないか確認 |
| `Package 'diffbot_sim' not found` | `cd /ros2_ws && colcon build --symlink-install && source install/setup.bash` |
| 終了後にもう一度起動するとロボットが 2 台 / 動作がおかしい | 前回の Gazebo が裏で残っている。`pkill -f "ign gazebo"` してから再起動 |
| 動作が重い・カメラの周期が低い | GPU をコンテナに渡す (`docker-compose.yml` の `devices: /dev/dri`)。または `gui:=false` で起動。GPU 描画になっているかはコンテナ内で `glxinfo -B` の `OpenGL renderer string` を見る (`llvmpipe` なら CPU 描画) |
| `error gathering device information ... "/dev/dri"` で起動しない | その PC に `/dev/dri` が無い。WSL2 なら `start.sh` から起動し直す (自動で `/dev/dxg` を使う)。それ以外は `devices:` の 2 行をコメントアウト |
| Gazebo が `OGRE EXCEPTION ... GL3PlusTextureGpu::copyTo` で落ち、RViz も一緒に閉じる | WSL2 の GPU (D3D12) が OpenGL 4.2 までのため。`MESA_GL_VERSION_OVERRIDE=4.3` が必要 (`docker-compose.wsl.yml` / `-Gpu` に設定済み)。Gazebo が落ちると launch 全体が終了する仕様 |
| `amdgpu: drmGetDevice2 failed` と出る | GPU がコンテナに渡っていない (CPU 描画で動作はする)。上と同じく `/dev/dri` を渡す |
| RViz に点群・画像が出ない | Fixed Frame が `odom` か確認 (Robocon フィールドでは `map` も可)。`ros2 topic hz /lidar/points` でデータが来ているか確認 |
| `docker/start.sh: Permission denied` | 実行権限が外れている (zip でコピーした場合など)。`chmod +x docker/*.sh` するか `bash docker/start.sh` で実行 |
| ロボットが止まらない | `/cmd_vel` は最後の指令を保持する。`ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{}"` |
| 別 PC の ROS 2 と混信する | `export ROS_DOMAIN_ID=<0-101 の好きな数字>` を人ごとに変える |
