# 作業記録 (WORKLOG)

diffbot_sim 環境を作ったときの作業内容と、実行したコマンドの記録です。
同じ手順をたどれば同じ環境を再現できます。

- 作業日: 2026-09-25
- 作業場所: Docker コンテナ内 (`root`, 作業ディレクトリ `/ros2_ws`)
- 作成ファイルはすべて `/ros2_ws/src/` (ホストと共有されるフォルダ) 以下

---

## 0. 環境の確認

```bash
cat /etc/os-release | head -3        # → Ubuntu 22.04.5 LTS
echo $ROS_DISTRO                     # → humble
ign gazebo --versions                # → 6.18.0 (= Gazebo Fortress)
dpkg -l | grep ros-humble-ros-gz     # → ros_gz 0.244.x (Fortress 用) が入っている
mount | grep ros2_ws                 # → src, config, models, worlds のみホストと共有
ls /dev/dri                          # → 無し (GPU はコンテナに渡されていない → CPU 描画)
```

わかったこと:

| 項目 | 状態 |
|---|---|
| ROS 2 | Humble (ros-base + ros_gz, xacro, robot_state_publisher, rviz2, rqt_image_view) |
| Gazebo | Fortress (ign-gazebo 6)。**Garden 以降とはプラグイン名・タグ名が違う**ので注意 (`ignition-gazebo-*`, `ignition::gazebo::systems::*`, `<ignition_frame_id>`, `ignition.msgs.*`) |
| 永続化 | `src/ config/ models/ worlds/` だけがホストに残る。`build/ install/` や apt で入れたものはコンテナ削除で消える |
| 足りないもの | `teleop_twist_keyboard` (キーボード操縦) |

---

## 1. 不足パッケージのインストール

```bash
apt-get update
apt-get install -y ros-humble-teleop-twist-keyboard
```

> ⚠️ コンテナ内の apt install はコンテナを作り直すと消えるので、同じ内容を `docker/Dockerfile` にも書いた (手順 6)。

---

## 2. ROS 2 パッケージ `diffbot_sim` の作成

```bash
mkdir -p /ros2_ws/src/diffbot_sim/{urdf,worlds,launch,config,rviz}
```

(`ros2 pkg create` でも作れるが、C++ ソースが無いので最小構成を手で作成)

作成したファイルと内容:

| ファイル | 内容 |
|---|---|
| `diffbot_sim/package.xml` | パッケージ定義。実行時依存に xacro, robot_state_publisher, ros_gz_sim, ros_gz_bridge, rviz2, teleop_twist_keyboard, rqt_image_view |
| `diffbot_sim/CMakeLists.txt` | `launch urdf worlds config rviz` を `share/diffbot_sim` にインストールするだけ |
| `diffbot_sim/urdf/diffbot.urdf.xacro` | ロボット本体。車体 (0.4×0.3×0.1 m, 5 kg)、左右車輪 (r=0.05 m, 間隔 0.35 m, continuous 関節)、前後キャスター (摩擦 0 の球)、`lidar_link`, `front_camera_link`, `down_camera_link` (+ それぞれの `*_optical_frame`)、`imu_link`。慣性はマクロで自動計算 |
| `diffbot_sim/urdf/diffbot.gazebo.xacro` | Gazebo 専用設定。DiffDrive プラグイン (`/cmd_vel` → 車輪、`/odom` と `/model/diffbot/tf` を出力)、JointStatePublisher (`/joint_states`)、3D LiDAR (`gpu_lidar`, 360×16, ±15°)、前方カメラ (640×480, 80°)、下向きカメラ (320×240, 90°)、IMU |
| `diffbot_sim/worlds/diffbot_world.sdf` | ワールド。Physics / UserCommands / SceneBroadcaster / Sensors(ogre2) / Imu の各システム、地面、10 m 四方の壁、障害物 5 個、床の黒ライン (長方形ループ) |
| `diffbot_sim/config/bridge.yaml` | ros_gz_bridge の対応表 (clock, cmd_vel, odom, tf, joint_states, lidar/points, 各カメラ image/camera_info, imu) |
| `diffbot_sim/launch/sim.launch.py` | Gazebo + robot_state_publisher + spawn (ros_gz_sim create) + bridge + RViz2 をまとめて起動。引数 `world gui rviz x y z yaw use_sim_time` |
| `diffbot_sim/rviz/diffbot.rviz` | RViz2 設定 (Fixed Frame: odom、RobotModel、点群、Odometry、カメラ画像 2 枚) |

設計上のポイント:

- **トピック名を固定**: Gazebo 側のトピックを `/cmd_vel`, `/odom`, `/lidar`, `/front_camera/image` のように絶対名で指定。ワールド名やモデル名が変わってもブリッジ設定を変えなくて済む。
- **frame_id を明示**: Fortress では URDF→SDF 変換時に fixed 関節のリンクが `base_footprint` に統合 (lump) されるため、センサの frame_id がリンク名にならない。`<ignition_frame_id>` で ROS 側の TF 名と一致させた。
- **カメラは optical frame**: 画像の frame_id を `*_optical_frame` (z 前 / x 右 / y 下) にして ROS の画像処理の慣例 (REP-103) に合わせた。
- **下向きカメラ**: 車体前方に張り出し (x=+0.24 m)、床から 0.08 m、pitch +90°。前方カメラの視界に入らない高さにした。画像の上方向 = ロボット前方。
- **寸法は xacro:property に集約**: 車輪半径・車輪間隔を変えると DiffDrive の設定にも自動で反映される。

---

## 3. ビルドと静的チェック

```bash
cd /ros2_ws
colcon build --symlink-install
source install/setup.bash

# URDF の構文・ツリーを確認
xacro src/diffbot_sim/urdf/diffbot.urdf.xacro > /tmp/diffbot.urdf
check_urdf /tmp/diffbot.urdf

# Gazebo が読む SDF に変換して、センサ・摩擦設定が入っているか確認
ign sdf -p /tmp/diffbot.urdf | grep -E "<sensor name|<mu>"

# ワールドファイルの検証
ign sdf -k src/diffbot_sim/worlds/diffbot_world.sdf     # → Valid.
```

---

## 4. 動作確認 (画面なしで)

```bash
# 画面なしで起動 (別端末 or バックグラウンド)
ros2 launch diffbot_sim sim.launch.py gui:=false rviz:=false &

ign topic -l        # Gazebo 側トピック
ros2 topic list     # ROS 2 側トピック
ros2 topic hz /lidar/points            # → 約 8.8 Hz (CPU 描画)
ros2 topic hz /front_camera/image_raw  # → 約 12.9 Hz
ros2 topic hz /down_camera/image_raw   # → 約 12.8 Hz
ros2 topic hz /imu                     # → 約 85 Hz
ros2 topic hz /odom                    # → 約 26 Hz
ros2 run tf2_ros tf2_echo odom lidar_link   # → z = 0.175 m

# 3 秒間 0.3 m/s で直進させて位置を確認
ros2 topic pub -r 10 -t 30 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.3}}"
ros2 topic echo --once /odom           # → x ≈ 0.85 m, y ≈ 0 (まっすぐ進む)
```

カメラ画像も保存して確認した (前方: 床のライン・壁・障害物が見える / 下向き: ラインが画像中央に縦に写る)。
点群の frame_id は `lidar_link`、フィールドは `x y z intensity ring`、1 フレーム 360×16 点。

---

## 5. 修正: 下向きカメラに影が映り込む

最初の確認で、下向きカメラの画像に車体の影が大きく映り、床が暗く・まだらになった。
ライントレースの練習で邪魔になるので、ワールドの影を無効化した。

`diffbot_sim/worlds/diffbot_world.sdf` の変更点:

```diff
     <scene>
       ...
-      <shadows>true</shadows>
+      <!-- 影を切る: 下向きカメラに車体の影が映り込むのを防ぐ -->
+      <shadows>false</shadows>
     </scene>

     <light type="directional" name="sun">
-      <cast_shadows>true</cast_shadows>
+      <cast_shadows>false</cast_shadows>
```

再度起動して、下向きカメラでラインがくっきり写ることを確認。

---

## 6. GUI での確認

```bash
ros2 launch diffbot_sim sim.launch.py      # Gazebo と RViz2 のウィンドウが開く
```

ログに `amdgpu: drmGetDevice2 failed.` と出る → ホストに AMD GPU があるが `/dev/dri` がコンテナに渡っていないため CPU 描画になっている (動作はする)。
→ 配布用 `docker-compose.yml` では `/dev/dri` を渡すようにした。

また、`Ctrl+C` で launch を止めたときに Gazebo サーバ (`ign gazebo`) が裏で残ることがあった (Fortress の `ign` コマンドが ruby ラッパー経由で起動するため)。
→ README のトラブルシューティングに `pkill -f "ign gazebo"` を記載。

---

## 7. 配布用 Docker ファイルの作成

現在のコンテナを再現するため `src/docker/` に以下を作成 (マウントされている `src/` 以下に置かないとコンテナ削除で消えるため)。

| ファイル | 内容 |
|---|---|
| `docker/Dockerfile` | `ros:humble-ros-base-jammy` に ros_gz, xacro, robot_state_publisher, rviz2, rqt_image_view, teleop_twist_keyboard, colcon, vim/nano/git を追加。`.bashrc` で ROS と `install/setup.bash` を自動 source |
| `docker/entrypoint.sh` | 今のコンテナの `/entrypoint.sh` をコピー (ROS 環境を読み込んでからコマンド実行) |
| `docker/docker-compose.yml` | GUI (X11)、`network_mode: host`、`ipc: host`、`src/config/models/worlds` のマウント、GPU (`/dev/dri`) |
| `docker/COLCON_IGNORE`, `docs/COLCON_IGNORE` | colcon がこれらのフォルダをパッケージとして探さないようにする空ファイル |

```bash
mkdir -p /ros2_ws/src/docker /ros2_ws/src/docs
touch /ros2_ws/src/docker/COLCON_IGNORE /ros2_ws/src/docs/COLCON_IGNORE
cp /entrypoint.sh /ros2_ws/src/docker/entrypoint.sh
```

> ⚠️ Dockerfile はコンテナ内から `docker build` できないため**未検証**。ホストで `docker compose build` して確認すること。

---

## 8. ドキュメント作成

| ファイル | 内容 |
|---|---|
| `src/README.md` | 概要・クイックスタート・トピック一覧・仕様・改造のヒント・トラブルシューティング |
| `src/docs/DOCKER_GUIDE.md` | Docker の基本概念、起動方法、コマンド早見表、GPU、注意点 |
| `src/docs/WORKLOG.md` | この作業記録 |

---

## 9. ファイル所有者の修正

コンテナ内 (root) で作ったファイルはホストから root 所有に見え、ホストのエディタで編集できない。
マウント元のフォルダ (`src/` など) の所有者 UID=1000 に合わせた。

```bash
chown -R 1000:1000 /ros2_ws/src
```

---

## 10. ABU Robocon 2027 フィールドの追加

依頼: ホストの `robocon2027_field_props.glb` をフィールドにし、ルールブック (`Robocon_2027_Rulebook_v1-1.pdf`) でロボット寸法を確認しながら、赤チームのスタートゾーンに置く。

### 10-1. ファイルをコンテナから見えるようにする

ホストのファイルはマウント外でコンテナから見えないため、ホストでマウント済みの `models/` にコピーしてもらった。

```bash
# ホストで
cp /home/hidayat/devel/robocon2027_field_props.glb \
   /home/hidayat/Downloads/Robocon_2027_Rulebook_v1-1.pdf \
   /home/hidayat/devel/ros2/docker/ubuntu22-04-ros2/models/
```

(マウント元のホストパスは `grep ros2_ws /proc/self/mountinfo` で確認できる)

### 10-2. ルールブックと GLB の調査

```bash
apt-get install -y poppler-utils assimp-utils     # PDF → テキスト/画像 (assimp は結局未使用)
pdftotext -layout Robocon_2027_Rulebook_v1-1.pdf rules.txt
pdftoppm -f 12 -l 12 -r 110 -png Robocon_2027_Rulebook_v1-1.pdf page12   # 図を画像で確認
```

> poppler-utils / assimp-utils は調査用なので Dockerfile には入れていない。

ルールブックから使った値:

| 項目 | 値 |
|---|---|
| フィールド | 11000 × 11000 mm |
| スタートゾーン | 700 × 700 mm × 2 (チームごと) |
| ロボット開始時寸法 (11.4) | 700 × 700 × 700 mm 以内 |
| ロボット質量 (11.7) | 50 kg 以下 |
| L1 / L2 | 高さ 600 / 900 mm |
| Earth / Sky Block | 350 mm 立方 約 600 g / 200 mm 立方 約 220 g |
| Mustika | φ210 mm 約 270 g、柱上面のくぼみ φ180 深さ 100 mm |

GLB の調査 (Python + numpy で直接パース): trimesh 製、162 ノード、変換行列なし、単位 m、Y-up。
全パーツが直方体 (8 頂点)・円柱・球のみ。寸法はルールブックと一致。

**Gazebo Fortress は GLB を読めない** (ign-common4 のローダは DAE/OBJ/STL のみ) ため、
メッシュ変換ではなく「各パーツの寸法・位置・色を読んで SDF の基本形状に置き換える」スクリプトを作った。

### 10-3. 鏡像の発見

ルールブック Fig.2 / Fig.3 と比べると、GLB は鏡像の配置だった
(スタートゾーン側から Storage 側を見たとき、ルールブックでは赤が左、GLB では右)。
変換時に鏡像を取って (glTF (x, y, z) → Gazebo (x, z, y)) ルールブックと同じ配置にした。`--no-mirror` で無効化できる。

### 10-4. パッケージ `robocon2027_field` の作成

```bash
mkdir -p /ros2_ws/src/robocon2027_field/{glb,scripts,worlds,launch,config}
cp /ros2_ws/models/robocon2027_field_props.glb /ros2_ws/src/robocon2027_field/glb/
```

| ファイル | 内容 |
|---|---|
| `scripts/glb_to_sdf.py` | GLB → SDF ワールド変換。静的構造は 1 モデルに、Earth/Sky Block・Mustika は動かせるモデルに。スタートゾーン位置を YAML に出力 |
| `scripts/check_robot_size.py` | xacro の collision 形状から外形寸法と質量を計算し、ルール 11.4 / 11.7 と照合 |
| `launch/robocon2027.launch.py` | `start_zones.yaml` を読み、ロボット外形の中心がゾーン中心に来るように diffbot を配置 (`team`, `zone`, `yaw`)。`map`→`odom` の静的 TF も出す |
| `package.xml`, `CMakeLists.txt`, `README.md` | |

```bash
cd /ros2_ws/src/robocon2027_field
python3 scripts/glb_to_sdf.py glb/robocon2027_field_props.glb worlds/robocon2027.sdf \
    --start-zones config/start_zones.yaml
ign sdf -k worlds/robocon2027.sdf        # → Valid.
cd /ros2_ws && colcon build --symlink-install
```

検証: 全 85 個の直方体パーツについて、推定した箱の 8 頂点が GLB の頂点と一致することを確認 (誤差 0.1 mm 未満)。

### 10-5. ロボット寸法の確認

```bash
ros2 run robocon2027_field check_robot_size.py
# 長さ 455 mm / 幅 390 mm / 高さ 200 mm / 6.50 kg → ルール内 (OK)
# 外形の中心は base_footprint より 27.5 mm 前 → launch の ROBOT_CENTER_OFFSET に使用
```

diffbot はそのままでスタートゾーン (700 × 700 mm) に収まるので、ロボット側は変更していない。

### 10-6. 動作確認と修正

```bash
ros2 launch robocon2027_field robocon2027.launch.py gui:=false rviz:=false
# → spawn=(-4.350, -5.178, yaw=1.571) : 赤 zone1 (中心 -4.35, -5.15) に外形中心が一致
```

テスト用に真上からのカメラを一時的に置いて撮影し、ルールブック Fig.3 と配置が一致することを確認した。
(`ros2 run ros_gz_sim create -file overhead.sdf -z 16 -P 1.5708 -Y 1.5708` のように、`create` は SDF 内の pose を使わないので引数で指定する)

発生した問題と修正:

| 問題 | 原因 | 対処 |
|---|---|---|
| リアルタイム比 0.05 (極端に遅い) | Earth Block 40 個が隙間ゼロで面接触し、巨大な接触問題になっていた (静的部分だけなら 1.0、衝突判定ライブラリを ode/bullet に変えても改善せず) | Earth Block の水平寸法を 350 → 345 mm (公差内) にして隙間を作る → 0.58 |
| まだ遅い | 物理ステップ 1 ms | 2 ms に変更 → ロボットなしで 0.99、ロボット+センサ込みで約 0.77 |
| スロープ下端に 9 mm の段差 | GLB のスロープ板が 9 mm 浮いていた | 9 mm 下げる (上端が Transfer Area の 0.600 m に一致) |

最終確認: 赤 zone1 に出現し、直進で 0.64 m 前進、Mustika は柱のくぼみに安定 (z = 0.5437 m)。GUI (Gazebo + RViz2) もエラーなし。
センサ周期 (CPU 描画): LiDAR 約 7 Hz、前方カメラ 約 9 Hz、下向きカメラ 約 11 Hz、IMU 約 71 Hz。

### 10-7. 未解決: diffbot がスロープを登れない

スロープ下端で前キャスターが乗り上げたところで止まり、その後向きが乱れて側面に落ちる。

- スロープの当たり判定が正しいことは、箱を落として表面高さを測って確認済み。
- 前後キャスターのせいで駆動輪の荷重が抜けると考え、キャスターを 3 mm 浮かせてみたが改善しなかったので、元に戻した。
- 依頼者の判断で、この問題は保留とした。

テスト時の注意: DiffDrive は最後の `/cmd_vel` を保持するため、`ros2 topic pub -t N` の後もロボットは走り続ける。必ず速度 0 を送ること。

---

## 最終的なファイル構成

```
/ros2_ws/src/
├── README.md
├── docs/{DOCKER_GUIDE.md, WORKLOG.md, COLCON_IGNORE}
├── docker/{Dockerfile, docker-compose.yml, entrypoint.sh, COLCON_IGNORE}
├── robocon2027_field/
│   ├── README.md, package.xml, CMakeLists.txt
│   ├── glb/robocon2027_field_props.glb
│   ├── scripts/{glb_to_sdf.py, check_robot_size.py}
│   ├── worlds/robocon2027.sdf, config/start_zones.yaml (自動生成)
│   └── launch/robocon2027.launch.py
└── diffbot_sim/
    ├── package.xml, CMakeLists.txt
    ├── urdf/{diffbot.urdf.xacro, diffbot.gazebo.xacro}
    ├── worlds/diffbot_world.sdf
    ├── config/bridge.yaml
    ├── rviz/diffbot.rviz
    └── launch/sim.launch.py
```

## ゼロから再現する手順 (まとめ)

```bash
# ホスト
cd <プロジェクト>/src/docker
xhost +local:
docker compose build
docker compose up -d
docker compose exec ros2 bash

# コンテナ内
cd /ros2_ws
colcon build --symlink-install
source install/setup.bash
ros2 launch diffbot_sim sim.launch.py
ros2 launch robocon2027_field robocon2027.launch.py   # Robocon 2027 フィールド (赤スタート)

# 別端末 (docker compose exec ros2 bash で入る)
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```
