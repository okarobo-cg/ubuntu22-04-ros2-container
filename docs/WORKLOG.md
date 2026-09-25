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

## 11. 影の有効化と Windows 用起動スクリプト

### 11-1. 影を有効にする

手順 5 で無効にした影を、依頼により両方のワールドで有効に戻した。

| ファイル | 変更 |
|---|---|
| `diffbot_sim/worlds/diffbot_world.sdf` | `<shadows>true</shadows>`、太陽の `<cast_shadows>true</cast_shadows>` |
| `robocon2027_field/scripts/glb_to_sdf.py` | 生成するワールドのテンプレートを同様に変更 → 再生成 |

```bash
cd /ros2_ws/src/robocon2027_field
python3 scripts/glb_to_sdf.py glb/robocon2027_field_props.glb worlds/robocon2027.sdf \
    --start-zones config/start_zones.yaml
```

**問題**: 影を有効にすると、床全体に縞模様のノイズ (シャドウアクネ: 床が自分自身に影を落として出る描画ノイズ) が出た。
**対処**: 平らな床 (床の塗装・フィールドの土台・会場の床・練習ワールドの地面とライン) の visual に `<cast_shadows>false</cast_shadows>` を付けた。
床は影を「受ける」ことはできるので、ロボットやブロックの影はそのまま床に映る。

```diff
 def visual(name, p, geom, color, cast_shadows=True):
+    cs = '' if cast_shadows else '<cast_shadows>false</cast_shadows>'
-    return f'<visual name="{name}">{p}{geom}{material(color)}</visual>'
+    return f'<visual name="{name}">{p}{cs}{geom}{material(color)}</visual>'
```

確認: カメラ画像で縞模様が消え、ロボットの影だけが出ることを確認。下向きカメラには車体の影が映る (仕様)。
影ありの実測 (Robocon フィールド, CPU 描画): リアルタイム比 0.6～0.67、LiDAR 5.4 Hz、前方カメラ 6.8 Hz (影なしより 2 割ほど重い)。

### 11-2. 影を元に戻す (無効化)

影を有効にしたところ画面が白飛びし、色検知で状態管理するのにも不向きだったため、影を無効に戻した。

- 途中で試した「会場の天井照明 (真下向きスポットライト 9 灯, 環境光 0.4)」の変更 (中断した作業) も `glb_to_sdf.py` に残っていたため、あわせて取り消した。白飛びは主にこの複数照明の重なりが原因とみられる。
- `glb_to_sdf.py` と `diffbot_world.sdf` は Git の初回コミットの内容に戻した (影なし・太陽光 1 灯・環境光 0.7)。床の `cast_shadows=false` 設定も影が無ければ不要なので一緒に消えている。

```bash
cd /ros2_ws/src
git show HEAD:robocon2027_field/scripts/glb_to_sdf.py > robocon2027_field/scripts/glb_to_sdf.py
git show HEAD:diffbot_sim/worlds/diffbot_world.sdf  > diffbot_sim/worlds/diffbot_world.sdf
cd robocon2027_field
python3 scripts/glb_to_sdf.py glb/robocon2027_field_props.glb worlds/robocon2027.sdf --start-zones config/start_zones.yaml
git diff --stat HEAD -- worlds     # → 差分なし (初回コミットと同一)
```

確認 (カメラ画像の実測):

| 項目 | 結果 |
|---|---|
| 白飛び画素 (255 に張り付き) | 0 % |
| 下向きカメラで見た赤スタートゾーン | 平均 (227, 96, 96)、ばらつき 0.3 以下 (ルールブック値 (223, 34, 34) より淡い) |

→ 色むらは無く色検知しやすいが、環境光が強いため色は淡く写る。色検知は HSV の色相で判定するのがよい。

### 11-3. Windows 用の起動スクリプト

Windows + Docker Desktop で動かすためのファイルを追加した。

| ファイル | 内容 |
|---|---|
| `docker/docker-compose.windows.yml` | WSLg (`/run/desktop/mnt/host/wslg`) で GUI 表示。`network_mode: host` と `/dev/dri` は使わない。`DISPLAY` は環境変数 `DIFFBOT_DISPLAY` で切り替え (WSLg / VcXsrv) |
| `docker/docker-compose.windows-gpu.yml` | GPU (試験的): `/dev/dxg` と `/usr/lib/wsl` を渡し Mesa の d3d12 ドライバを使う |
| `docker/windows/common.ps1` | 共通関数 (Docker 確認・イメージ/コンテナ確認・フォルダ作成など) |
| `docker/windows/start.ps1` | 確認 → ビルド → 起動 → `colcon build` → launch。`-Launch -Team -Display -Gpu -Build -NoRviz -Headless` |
| `docker/windows/teleop.ps1`, `shell.ps1`, `stop.ps1`, `check_env.ps1` | 操縦 / bash / 停止 / 環境チェック |
| `docker/windows/*.bat` | ダブルクリック用。`powershell -ExecutionPolicy Bypass -File` で同名の `.ps1` を呼ぶ |
| `src/.gitattributes` | 改行コードの固定 (`.sh .py .sdf ...` は LF、`.ps1 .bat` は CRLF) |
| `docker/Dockerfile` | `entrypoint.sh` の CRLF を LF に直す `sed` を追加 |

Windows 特有の注意点として対処したこと:

- **文字コード**: Windows PowerShell 5.1 は BOM 無し UTF-8 の `.ps1` を Shift-JIS として読み、日本語が化けて構文エラーになる → `.ps1` は **UTF-8 (BOM 付き) + CRLF** で保存。`.bat` は ASCII のみ。
- **エラー処理**: PowerShell 5.1 で `$ErrorActionPreference='Stop'` にすると、docker が標準エラーに何か出すだけで例外になる → `'Continue'` にして `$LASTEXITCODE` で判定。
- **引数渡し**: PowerShell 5.1 は外部コマンドに渡す文字列内の `"` を正しく渡せないことがある → コンテナで実行する `bash -c` の文字列にダブルクォートを使わない。
- **改行コード**: Git for Windows の autocrlf で `entrypoint.sh` が CRLF になると、コンテナが起動しない → `.gitattributes` と Dockerfile の両方で対策。
- **実行ポリシー**: 既定では `.ps1` をダブルクリック実行できない → `.bat` から `-ExecutionPolicy Bypass` で呼ぶ。
- **Gazebo の残骸**: 起動前に `pkill -f '[i]gn gazebo'` で前回の Gazebo を止める (`[i]` は pkill が自分自身のコマンドラインにマッチしないための書き方)。

検証 (Windows 実機は無いため、この Linux コンテナでできる範囲):

```bash
# PowerShell 7 (Linux 版) を scratch 領域に展開して構文チェック
curl -fsSL -o pwsh.tar.gz https://github.com/PowerShell/PowerShell/releases/download/v7.4.6/powershell-7.4.6-linux-x64.tar.gz
tar xzf pwsh.tar.gz
./pwsh -NoProfile -Command '[System.Management.Automation.Language.Parser]::ParseFile(...)'   # → 全 .ps1 で OK

# 引数を表示するだけの偽 docker コマンドを PATH に置いて start.ps1 を実行し、
# docker compose -f docker-compose.windows.yml build / up -d / exec ... が正しく組み立てられることを確認
PATH=./mock:$PATH ./pwsh -File start.ps1 -Team blue -NoRviz

# start.ps1 がコンテナ内で実行する bash コマンド文字列をこの環境でそのまま実行し、
# ビルド → 青チームのスタートゾーンにロボットが出現することを確認
```

> ⚠️ **Windows 実機では未検証**。特に WSLg のマウントパス、`-Gpu` (D3D12)、VcXsrv モードは実機で要確認。

---

## 12. コンテナ名の変更と README への起動手順の追記

### 12-1. コンテナ名を `ubuntu_22_04_ros2` に変更

| ファイル | 変更 |
|---|---|
| `docker/docker-compose.yml`, `docker/docker-compose.windows.yml` | `container_name: diffbot_sim` → `container_name: ubuntu_22_04_ros2` |
| `docker/windows/common.ps1` | `$Script:Container = 'ubuntu_22_04_ros2'` (UTF-8 BOM + CRLF を維持) |
| `docs/DOCKER_GUIDE.md` | コンテナ名の記載、`docker run --name` / `docker exec -it` の例 |

イメージ名 (`diffbot_sim:humble`)、compose のサービス名 (`ros2`)、パッケージ名 (`diffbot_sim`) は変更していない。

```bash
sed -i 's/container_name: diffbot_sim/container_name: ubuntu_22_04_ros2/' \
    docker/docker-compose.yml docker/docker-compose.windows.yml
```

### 12-2. README に Docker の立ち上げ手順 (Ubuntu / Windows) を追加

`src/README.md` に「1. Docker コンテナの立ち上げ」を追加し、既存の章を 1 つずつ繰り下げた。
内容: 共通のフォルダ構成、Ubuntu ホストの手順 (`xhost` → `docker compose build / up -d / exec`)、
Windows ホストの手順 (`.bat` をダブルクリックする方法と、`docker compose -f docker-compose.windows.yml` を手で打つ方法)。
Docker 自体のインストール手順は省略 (入っている前提)。

---

## 最終的なファイル構成

```
/ros2_ws/src/
├── README.md
├── docs/{DOCKER_GUIDE.md, WORKLOG.md, COLCON_IGNORE}
├── .gitattributes
├── docker/
│   ├── Dockerfile, docker-compose.yml, entrypoint.sh, COLCON_IGNORE
│   ├── docker-compose.windows.yml, docker-compose.windows-gpu.yml
│   └── windows/{start,teleop,shell,stop,check_env}.{bat,ps1}, common.ps1
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

Windows の場合: `src\docker\windows\start.bat` をダブルクリック → 操縦は `teleop.bat` (詳細は DOCKER_GUIDE の 6 章)。
