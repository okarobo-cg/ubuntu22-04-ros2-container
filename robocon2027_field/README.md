# robocon2027_field — ABU Robocon 2027 フィールド

ABU Robocon 2027「The Pursuit of Mustika Nusantara」のフィールドを Gazebo Fortress で再現したパッケージです。
`glb/robocon2027_field_props.glb` から自動変換したワールドに diffbot を置いて動かせます。

## 起動

```bash
cd /ros2_ws && colcon build --symlink-install && source install/setup.bash

ros2 launch robocon2027_field robocon2027.launch.py                  # 赤チーム・中央寄りのスタートゾーン
ros2 launch robocon2027_field robocon2027.launch.py zone:=2          # 赤チーム・角のスタートゾーン
ros2 launch robocon2027_field robocon2027.launch.py team:=blue       # 青チーム
ros2 launch robocon2027_field robocon2027.launch.py gui:=false rviz:=false   # 画面なし
```

| 引数 | 既定値 | 説明 |
|---|---|---|
| `team` | `red` | `red` / `blue` |
| `zone` | `1` | `1`: フィールド中央寄りのスタートゾーン, `2`: 角のスタートゾーン |
| `yaw` | `1.5708` | 初期の向き [rad] (既定はフィールド奥 = +y 向き) |
| `gui`, `rviz` | `true` | Gazebo GUI / RViz2 を出すか |

ロボットは外形の中心がスタートゾーン (700 × 700 mm) の中心に来るように置かれます。
`map` (フィールド原点) → `odom` の静的 TF も出すので、RViz の Fixed Frame を `map` にするとフィールド座標で位置が見られます。

## フィールドの座標系

```
          y (奥)
          ^      Storage(赤)   Mustika Pillar   Storage(青)
          |
          |        [ramp]  ┌── L1 (0.6 m) ──┐  [ramp]
          |                │   L2 (0.9 m)   │
          |     [Transfer] │ Central Pillar │ [Transfer]
          |       [stairs] └────────────────┘ [stairs]
          |                 Ground Shared Area
          |   Start(赤) ■■                      ■■ Start(青)
          +-------------------------------------------> x
     原点 = フィールド中央の床面 (11 m × 11 m, x・y とも -5.5 ～ 5.5 m)
```

| 項目 | 値 |
|---|---|
| 赤スタートゾーン zone1 / zone2 の中心 | (-4.35, -5.15) / (-5.15, -5.15) |
| 青スタートゾーン zone1 / zone2 の中心 | (4.35, -5.15) / (5.15, -5.15) |
| Mustika Pillar | (0, 3.5)、高さ 0.5 m |
| Central Pillar | (0, 0)、L2 上、高さ 0.8 m |

(`config/start_zones.yaml` に自動で書き出されます)

## ゲームオブジェクト (動かせる物体)

| 物体 | 数 | 寸法 | 質量 (ルールブック) |
|---|---|---|---|
| Earth Block (赤/青) | 各 20 | 345 × 345 × 350 mm ※ | 0.60 kg |
| Sky Block | 12 | 200 mm 立方 (上下の面が赤/青) | 0.22 kg |
| Mustika | 1 | φ200 mm 球 (Mustika Pillar のくぼみの上) | 0.27 kg |

※ Earth Block は GLB では 350 mm で隙間なく並んでいますが、隣同士が接していると物理計算が極端に重くなる (リアルタイム比 0.05) ため、水平方向だけ 345 mm にしています (ルールの公差 ±5% の範囲内)。

## GLB からの変換 (`scripts/glb_to_sdf.py`)

Gazebo Fortress は GLB を読み込めません。この GLB は全パーツが直方体・円柱・球なので、寸法・位置・色を読み取って SDF の基本形状に置き換えています。GLB を更新したら再生成してください。

```bash
cd /ros2_ws/src/ubuntu22-04-ros2-container/robocon2027_field
python3 scripts/glb_to_sdf.py glb/robocon2027_field_props.glb worlds/robocon2027.sdf \
    --start-zones config/start_zones.yaml
```

変換時に行っている補正:

| 補正 | 理由 |
|---|---|
| **鏡像補正** (既定で有効, `--no-mirror` で無効) | GLB の配置がルールブック Fig.2 / Fig.3 と鏡像だったため。補正後は赤が左 (x<0)、スタートゾーンが手前 (y<0)、Storage と Mustika Pillar が奥 (y>0) で、Fig.3 と同じ見た目になる |
| 床の塗装を厚さ 2 mm の見た目だけの板に変換 | GLB ではゾーン等が 2 cm 厚の板で、そのままだと床に段差ができるため |
| スロープを 9 mm 下げる | GLB では上面の下端が床から 9 mm 浮いていたため。下げると上端が Transfer Area の高さ 0.600 m にちょうど一致する |
| 柱の上面にくぼみの当たり判定 (φ180, 深さ 100 mm) | ルールブックの仕様。Mustika が柱の上に安定して乗る |
| 影は無効 | 有効にすると白飛びし、色検知 (ゾーン・ブロックの色で状態を判定する処理) がしにくくなるため |
| 物理ステップ 2 ms (diffbot_world は 1 ms) | ブロックが多く、1 ms では CPU 描画環境でリアルタイムを保てないため |

## ロボット寸法のルールチェック (`scripts/check_robot_size.py`)

ロボットを改造したら、ルール 11.4 (開始時 700 × 700 × 700 mm 以内) と 11.7 (50 kg 以下) を満たすか確認できます。

```bash
ros2 run robocon2027_field check_robot_size.py                 # diffbot を確認
ros2 run robocon2027_field check_robot_size.py <xacro ファイル>  # 別のロボット
```

現在の diffbot: 長さ 455 mm × 幅 390 mm × 高さ 200 mm、6.5 kg → **ルール内**
(外形の中心は base_footprint より 27.5 mm 前。この値は `launch/robocon2027.launch.py` の `ROBOT_CENTER_OFFSET` で使用)

※ collision 形状 (box / cylinder / sphere) から計算します。mesh の collision は対象外 (警告が出ます)。
※ 伸縮機構の最大展開寸法 (11.5 / 11.6: 1000 × 1400 × 1200 mm) は対象外。

## 既知の問題

- **diffbot はスロープを登れない**: スロープ下端 (y ≈ 3.0 m) で前キャスターが乗り上げたところで止まり、その後向きが乱れて側面に落ちる。スロープ自体の当たり判定は正しいことを確認済み (物体を落として表面高さを測定)。原因として「前後キャスター配置のため前キャスターが持ち上がると駆動輪の荷重が抜ける」ことを疑い、キャスターを 3 mm 浮かせる対策を試したが改善しなかったため、元に戻した。未解決。
- 階段 (1 段 150 mm) は車輪半径 50 mm の diffbot では登れない (仕様)。
- **Ctrl+C で終了すると Gazebo が裏で残ることがある**: `pkill -f "ign gazebo"` で止める。
- 実測 (GPU なし・CPU 描画): リアルタイム比 約 0.75～0.8、LiDAR 約 7 Hz、前方カメラ 約 9 Hz。GPU をコンテナに渡すと改善が見込める (WSL2 は [DOCKER_GUIDE の 7 章](../docs/DOCKER_GUIDE.md#7-wsl2-の-ubuntu-で動かす))。
- カメラに写る色はルールブックの RGB 値より淡い (環境光が強めのため)。例: 赤スタートゾーン (223, 34, 34) → 下向きカメラでは約 (227, 96, 96)。色相 (赤/青の区別) は保たれるので、色検知は RGB の固定値ではなく HSV の色相で判定するのがおすすめ。
- DiffDrive は最後の `/cmd_vel` を保持し続ける。止めるときは速度 0 を送ること。

## 参考

- ルールブック: `Robocon_2027_Rulebook_v1-1.pdf` (著作物のため本パッケージには含めていない)
- 公式サイト: http://www.aburobocon2027.id
