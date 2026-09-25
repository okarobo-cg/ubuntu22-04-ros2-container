#!/usr/bin/env python3
"""ABU Robocon 2027 フィールドの GLB を Gazebo (Fortress) 用 SDF ワールドに変換する.

Gazebo Fortress は GLB/glTF メッシュを読み込めない (DAE/OBJ/STL のみ) 。
一方この GLB は全パーツが「直方体・円柱・球」だけで作られているので、
各パーツの寸法・位置・色を読み取って SDF の基本形状 (box/cylinder/sphere) に置き換える。
こうすると色も寸法もそのまま保たれ、当たり判定も正確で軽い。

変換ルール:
  * 座標系: glTF (Y-up) -> Gazebo (Z-up)。単位は m のまま。
  * 鏡像補正: この GLB はルールブック (Fig.2, Fig.3) と鏡像の配置になっているため、
    既定で鏡像を取ってルールブックと同じ配置にする (--no-mirror で無効)。
    結果: 赤 = x<0 (左), スタートゾーン = y<0 (手前), Storage/Mustika Pillar = y>0 (奥)
  * 床の塗装 (ゾーン・ビルディングスポット等) は GLB では 2cm 厚の板だが、
    実物は塗装で段差が無いので、厚さ 2mm の見た目だけの板に変換する (当たり判定なし)。
  * Earth Block / Sky Block / Mustika は動かせる物体 (質量はルールブックの値) にする。
  * Mustika Pillar / Central Pillar の上面にはルール通りのくぼみ (φ180, 深さ100) を当たり判定で作る。

使い方:
  python3 glb_to_sdf.py <入力.glb> <出力.sdf> [--start-zones <出力.yaml>] [--no-mirror]
"""

import argparse
import json
import math
import re
import struct
import sys

import numpy as np

# ---- ルールブック由来のパラメータ ----
EARTH_BLOCK_MASS = 0.60   # kg (Earth Block: 約 600 g)
SKY_BLOCK_MASS = 0.22     # kg (Sky Block: 約 220 g)
MUSTIKA_MASS = 0.27       # kg (Mikasa V300W: 260-280 g)
CUP_RADIUS = 0.09         # 柱上面のくぼみ半径 (φ180 mm)
CUP_DEPTH = 0.10          # くぼみの深さ (100 mm)

DECAL_THICKNESS = 0.002   # 床の塗装 1 層の厚さ [m]

# Earth Block は GLB では隙間ゼロで並んでいる。隣同士が面接触したままだと
# 物理計算が極端に重くなる (リアルタイム比 0.05 程度) ので、水平方向だけ少し小さくする。
# 350 -> 345 mm (ルールブックの公差 ±5% の範囲内)
EARTH_BLOCK_SHRINK_XY = 0.005

# 床の塗装パーツ: (名前の先頭, 乗っている面の高さ[m], 重ね順)
DECALS = {
    'ground_red': (0.0, 1), 'ground_blue': (0.0, 1),
    'storage_zone': (0.0, 2), 'share_area_base': (0.0, 2),
    'share_cell': (0.0, 3), 'start_zone': (0.0, 3), 'mustika_pad': (0.0, 3),
    'level1_top_red': (0.6, 1), 'level1_top_blue': (0.6, 1),
    'l1_retry_zone': (0.6, 2), 'l1_shared_pad': (0.6, 2),
    'building_spot': (0.6, 3), 'l1_shared_spot': (0.6, 3),
    'l2_building_spot': (0.9, 1),
}
PILLARS = ('central_pillar', 'mustika_pillar')
PILLAR_CAPS = ('central_pillar_cap', 'mustika_pillar_cap')


# ------------------------------------------------------------------
# GLB 読み込み
# ------------------------------------------------------------------
def load_glb(path):
    data = open(path, 'rb').read()
    magic, _, _ = struct.unpack('<4sII', data[:12])
    if magic != b'glTF':
        sys.exit(f'{path} は GLB ファイルではありません')
    json_len = struct.unpack('<I', data[12:16])[0]
    gltf = json.loads(data[20:20 + json_len])
    bin_off = 20 + json_len
    bin_len = struct.unpack('<I', data[bin_off:bin_off + 4])[0]
    binary = data[bin_off + 8:bin_off + 8 + bin_len]

    def accessor(idx):
        acc = gltf['accessors'][idx]
        view = gltf['bufferViews'][acc['bufferView']]
        ncomp = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}[acc['type']]
        dtype = {5126: np.float32, 5125: np.uint32, 5123: np.uint16}[acc['componentType']]
        off = view.get('byteOffset', 0) + acc.get('byteOffset', 0)
        arr = np.frombuffer(binary, dtype, acc['count'] * ncomp, off)
        return arr.reshape(-1, ncomp) if ncomp > 1 else arr

    parts = []
    for node in gltf['nodes']:
        if 'matrix' in node or 'translation' in node or 'rotation' in node or 'scale' in node:
            sys.exit(f"ノード {node['name']} に変換行列があります (未対応)")
        prim = gltf['meshes'][node['mesh']]['primitives'][0]
        verts = accessor(prim['attributes']['POSITION']).astype(float)
        mat = gltf['materials'][prim['material']]
        color = mat['pbrMetallicRoughness']['baseColorFactor']
        parts.append({'name': node['name'], 'verts': verts, 'color': color})
    return parts


def to_gazebo(verts, mirror):
    """glTF (x, y-up, z) -> Gazebo (x, y, z-up)."""
    x, y, z = verts[:, 0], verts[:, 1], verts[:, 2]
    if mirror:
        return np.stack([x, z, y], axis=1)    # 鏡像 (ルールブックの配置に合わせる)
    return np.stack([x, -z, y], axis=1)       # 回転のみ


# ------------------------------------------------------------------
# 形状の推定
# ------------------------------------------------------------------
def fit_box(v):
    """8 頂点から向き付き直方体 (中心, 回転行列, 寸法) を求める."""
    # 頂点 v[0] から出る 3 辺 = 互いに直交するベクトル (近い順に選ぶ。面の対角線は除外される)
    cands = sorted((v[i] - v[0] for i in range(1, len(v))), key=np.linalg.norm)
    edges = []
    for e in cands:
        if all(abs(np.dot(e, u)) < 1e-6 * np.linalg.norm(e) * np.linalg.norm(u) + 1e-9 for u in edges):
            edges.append(e)
        if len(edges) == 3:
            break
    size = np.array([np.linalg.norm(e) for e in edges])
    rot = np.stack([e / s for e, s in zip(edges, size)], axis=1)
    if np.linalg.det(rot) < 0:
        rot[:, 2] *= -1
    # なるべく軸に沿った表現にする (回転していない箱は rpy=0 になるように)
    order = np.argmax(np.abs(rot), axis=0)
    if sorted(order) == [0, 1, 2]:
        perm = np.argsort(order)
        rot, size = rot[:, perm], size[perm]
        for k in range(3):
            if rot[k, k] < 0:
                rot[:, k] *= -1
        if np.linalg.det(rot) < 0:
            rot[:, 2] *= -1
    return v.mean(axis=0), rot, size


def rpy(rot):
    pitch = -math.asin(max(-1.0, min(1.0, rot[2, 0])))
    roll = math.atan2(rot[2, 1], rot[2, 2])
    yaw = math.atan2(rot[1, 0], rot[0, 0])
    return roll, pitch, yaw


def aabb(v):
    mn, mx = v.min(axis=0), v.max(axis=0)
    return mn, mx, (mn + mx) / 2, mx - mn


# ------------------------------------------------------------------
# SDF 文字列の生成
# ------------------------------------------------------------------
def f(x):
    s = f'{x:.4f}'.rstrip('0').rstrip('.')
    return '0' if s in ('-0', '') else s


def pose(xyz, r=(0, 0, 0)):
    return f'<pose>{" ".join(f(a) for a in xyz)} {" ".join(f(a) for a in r)}</pose>'


def material(c):
    rgb = ' '.join(f(a) for a in c[:3])
    return (f'<material><ambient>{rgb} 1</ambient><diffuse>{rgb} 1</diffuse>'
            f'<specular>0.1 0.1 0.1 1</specular></material>')


def box(size):
    return f'<geometry><box><size>{" ".join(f(a) for a in size)}</size></box></geometry>'


def cyl(r, length):
    return f'<geometry><cylinder><radius>{f(r)}</radius><length>{f(length)}</length></cylinder></geometry>'


def visual(name, p, geom, color):
    return f'<visual name="{name}">{p}{geom}{material(color)}</visual>'


def collision(name, p, geom, mu=None):
    surf = ''
    if mu is not None:
        surf = f'<surface><friction><ode><mu>{f(mu)}</mu><mu2>{f(mu)}</mu2></ode></friction></surface>'
    return f'<collision name="{name}">{p}{geom}{surf}</collision>'


def inertial_box(m, s):
    ixx = m * (s[1] ** 2 + s[2] ** 2) / 12
    iyy = m * (s[0] ** 2 + s[2] ** 2) / 12
    izz = m * (s[0] ** 2 + s[1] ** 2) / 12
    return (f'<inertial><mass>{f(m)}</mass><inertia><ixx>{ixx:.6g}</ixx><iyy>{iyy:.6g}</iyy>'
            f'<izz>{izz:.6g}</izz><ixy>0</ixy><ixz>0</ixz><iyz>0</iyz></inertia></inertial>')


def inertial_sphere(m, r):
    i = 2 * m * r * r / 5
    return (f'<inertial><mass>{f(m)}</mass><inertia><ixx>{i:.6g}</ixx><iyy>{i:.6g}</iyy>'
            f'<izz>{i:.6g}</izz><ixy>0</ixy><ixz>0</ixz><iyz>0</iyz></inertia></inertial>')


def pillar_elements(name, v, color):
    """円柱 (見た目) + 上面にくぼみのある当たり判定."""
    mn, mx, c, s = aabb(v)
    r, top = s[0] / 2, mx[2]
    out = [visual(name, pose((c[0], c[1], c[2])), cyl(r, s[2]), color)]
    solid_h = s[2] - CUP_DEPTH
    out.append(collision(f'{name}_c', pose((c[0], c[1], mn[2] + solid_h / 2)), cyl(r, solid_h)))
    # くぼみの壁: 内接半径 CUP_RADIUS の 16 角形リング
    n = 16
    thick = r - CUP_RADIUS
    length = 2 * r * math.tan(math.pi / n)
    for i in range(n):
        a = 2 * math.pi * i / n
        rc = CUP_RADIUS + thick / 2
        p = pose((c[0] + rc * math.cos(a), c[1] + rc * math.sin(a), top - CUP_DEPTH / 2), (0, 0, a))
        out.append(collision(f'{name}_rim{i}', p, box((thick, length, CUP_DEPTH))))
    return out, (c[0], c[1], top)


# ------------------------------------------------------------------
# メイン
# ------------------------------------------------------------------
def convert(parts, mirror):
    static_elems = []     # フィールド (静的) の visual / collision
    dynamic_models = []   # 動かせる物体
    pillar_tops = {}
    sky = {}              # Sky Block をまとめるための辞書
    start_zones = []

    for p in parts:
        name, color = p['name'], p['color']
        kind = re.sub(r'_\d+$', '', name)
        v = to_gazebo(p['verts'], mirror)

        if kind in DECALS:
            base, layer = DECALS[kind]
            mn, mx, c, s = aabb(v)
            z0 = base + (layer - 1) * DECAL_THICKNESS
            static_elems.append(visual(name, pose((c[0], c[1], z0 + DECAL_THICKNESS / 2)),
                                       box((s[0], s[1], DECAL_THICKNESS)), color))
            if kind == 'start_zone':
                team = 'red' if c[0] < 0 else 'blue'
                start_zones.append({'team': team, 'x': float(c[0]), 'y': float(c[1]),
                                    'size_x': float(s[0]), 'size_y': float(s[1])})
        elif kind in PILLARS:
            elems, top = pillar_elements(name, v, color)
            static_elems += elems
            pillar_tops[kind] = top
        elif kind in PILLAR_CAPS:
            # 柱上面のくぼみ (見た目): 薄い円板
            mn, mx, c, s = aabb(v)
            top = mn[2]
            static_elems.append(visual(name, pose((c[0], c[1], top + 0.0005)), cyl(s[0] / 2, 0.001), color))
        elif kind == 'earthblock':
            c, rot, s = fit_box(v)
            s = s - np.array([EARTH_BLOCK_SHRINK_XY, EARTH_BLOCK_SHRINK_XY, 0.0])
            team = 'red' if c[0] < 0 else 'blue'
            dynamic_models.append(
                f'<model name="earth_block_{team}_{name.split("_")[-1]}">{pose(c)}<link name="link">'
                f'{inertial_box(EARTH_BLOCK_MASS, s)}'
                f'{collision("c", "", box(s), mu=0.5)}{visual("v", "", box(s), color)}</link></model>')
        elif kind.startswith('skyblock_'):
            mn, mx, c, s = aabb(v)
            key = (round(c[0], 3), round(c[1], 3))
            sky.setdefault(key, {})[kind] = (mn, mx, c, s, color)
        elif kind == 'mustika':
            mn, mx, c, s = aabb(v)
            r = s[0] / 2
            dynamic_models.append(('mustika', r, color))
        else:
            # その他の構造物 (地面・壁・L1/L2・階段・スロープ・柵など): 見た目 + 当たり判定
            c, rot, s = fit_box(v)
            if kind == 'ramp':
                # GLB のスロープ (傾けた板) は上面の下端が床から 9 mm 浮いていて段差になり、
                # 小さい車輪だと登れない。上面の下端が床 (z=0) に来るよう下げる。
                # (下げると上端が Transfer Area の高さ 0.6 m にちょうど一致する)
                up = rot[:, np.argmax(np.abs(rot[2, :]))]
                up = up if up[2] > 0 else -up
                top_corners = [x for x in v if np.dot(x - c, up) > 0]
                c = c - np.array([0.0, 0.0, min(x[2] for x in top_corners)])
            r = rpy(rot)
            static_elems.append(visual(name, pose(c, r), box(s), color))
            static_elems.append(collision(f'{name}_c', pose(c, r), box(s)))

    # Sky Block: body + top + bottom をまとめて 1 つの物体にする
    for i, (key, d) in enumerate(sorted(sky.items())):
        mn = np.min([d[k][0] for k in d], axis=0)
        mx = np.max([d[k][1] for k in d], axis=0)
        c, s = (mn + mx) / 2, mx - mn
        vis = ''
        for k in ('skyblock_bottom', 'skyblock_body', 'skyblock_top'):
            pmn, pmx, pc, ps, col = d[k]
            vis += visual(k.split('_')[1], pose(pc - c), box(ps), col)
        top_color = d['skyblock_top'][4]
        team = 'red' if top_color[0] > top_color[2] else 'blue'
        dynamic_models.append(
            f'<model name="sky_block_{i:02d}_{team}_up">{pose(c)}<link name="link">'
            f'{inertial_box(SKY_BLOCK_MASS, s)}{collision("c", "", box(s), mu=0.5)}{vis}</link></model>')

    # Mustika: Mustika Pillar のくぼみに乗る高さに置く
    out_dynamic = []
    for m in dynamic_models:
        if isinstance(m, tuple):
            _, r, color = m
            px, py, top = pillar_tops['mustika_pillar']
            z = top + math.sqrt(max(r * r - CUP_RADIUS ** 2, 0.0))
            out_dynamic.append(
                f'<model name="mustika">{pose((px, py, z))}<link name="link">'
                f'{inertial_sphere(MUSTIKA_MASS, r)}'
                f'<collision name="c"><geometry><sphere><radius>{f(r)}</radius></sphere></geometry>'
                f'<surface><friction><ode><mu>0.8</mu><mu2>0.8</mu2></ode></friction></surface></collision>'
                f'<visual name="v"><geometry><sphere><radius>{f(r)}</radius></sphere></geometry>'
                f'{material(color)}</visual></link></model>')
        else:
            out_dynamic.append(m)

    return static_elems, out_dynamic, start_zones


WORLD_HEADER = """<?xml version="1.0"?>
<!--
  ABU Robocon 2027 "The Pursuit of Mustika Nusantara" フィールド (Gazebo Fortress)
  このファイルは scripts/glb_to_sdf.py で glb/robocon2027_field_props.glb から自動生成したもの。
  直接編集せず、GLB かスクリプトを直してから再生成すること。

  座標系: 原点 = フィールド中央の床面, x = 赤→青 方向, y = スタートゾーン→Storage 方向, z = 上
  mirror = {mirror}
-->
<sdf version="1.8">
  <world name="robocon2027">
    <!-- ステップ 2 ms: 1 ms だとブロックが多く CPU 描画環境でリアルタイムを保てないため -->
    <physics name="2ms" type="ignored">
      <max_step_size>0.002</max_step_size>
      <real_time_factor>1.0</real_time_factor>
    </physics>

    <plugin filename="ignition-gazebo-physics-system" name="ignition::gazebo::systems::Physics"/>
    <plugin filename="ignition-gazebo-user-commands-system" name="ignition::gazebo::systems::UserCommands"/>
    <plugin filename="ignition-gazebo-scene-broadcaster-system" name="ignition::gazebo::systems::SceneBroadcaster"/>
    <plugin filename="ignition-gazebo-sensors-system" name="ignition::gazebo::systems::Sensors">
      <render_engine>ogre2</render_engine>
    </plugin>
    <plugin filename="ignition-gazebo-imu-system" name="ignition::gazebo::systems::Imu"/>

    <scene>
      <ambient>0.7 0.7 0.7 1</ambient>
      <background>0.75 0.8 0.85 1</background>
      <shadows>false</shadows>
    </scene>

    <light type="directional" name="sun">
      <cast_shadows>false</cast_shadows>
      <pose>0 0 10 0 0 0</pose>
      <diffuse>0.8 0.8 0.8 1</diffuse>
      <specular>0.1 0.1 0.1 1</specular>
      <direction>-0.3 0.2 -0.9</direction>
    </light>

    <!-- 会場の床 (フィールドの土台の下) -->
    <model name="venue_floor">
      <static>true</static>
      <pose>0 0 {floor_z} 0 0 0</pose>
      <link name="link">
        <collision name="c"><geometry><plane><normal>0 0 1</normal><size>40 40</size></plane></geometry></collision>
        <visual name="v"><geometry><plane><normal>0 0 1</normal><size>40 40</size></plane></geometry>
          <material><ambient>0.5 0.5 0.5 1</ambient><diffuse>0.5 0.5 0.5 1</diffuse></material></visual>
      </link>
    </model>
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('glb')
    ap.add_argument('sdf')
    ap.add_argument('--start-zones', help='スタートゾーンの位置を書き出す YAML')
    ap.add_argument('--no-mirror', action='store_true', help='鏡像補正をしない (GLB の配置のまま)')
    args = ap.parse_args()
    mirror = not args.no_mirror

    parts = load_glb(args.glb)
    static_elems, dynamic, zones = convert(parts, mirror)
    floor_z = min(to_gazebo(p['verts'], mirror)[:, 2].min() for p in parts)

    with open(args.sdf, 'w') as fp:
        fp.write(WORLD_HEADER.format(mirror=mirror, floor_z=f(floor_z)))
        fp.write('\n    <!-- フィールド本体 (静的) -->\n')
        fp.write('    <model name="robocon2027_field">\n      <static>true</static>\n      <link name="link">\n')
        for e in static_elems:
            fp.write(f'        {e}\n')
        fp.write('      </link>\n    </model>\n\n    <!-- ゲームオブジェクト (動かせる) -->\n')
        for m in dynamic:
            fp.write(f'    {m}\n')
        fp.write('  </world>\n</sdf>\n')

    if args.start_zones:
        with open(args.start_zones, 'w') as fp:
            fp.write('# glb_to_sdf.py が自動生成。スタートゾーン (700x700 mm) の中心 [m]\n')
            fp.write('# zone 1 = フィールド中央寄り, zone 2 = 角\n')
            for team in ('red', 'blue'):
                zs = sorted([z for z in zones if z['team'] == team], key=lambda z: abs(z['x']))
                fp.write(f'{team}:\n')
                for i, z in enumerate(zs, 1):
                    fp.write(f"  zone{i}: {{x: {z['x']:.4f}, y: {z['y']:.4f}, "
                             f"size_x: {z['size_x']:.3f}, size_y: {z['size_y']:.3f}}}\n")

    n_static = sum(1 for e in static_elems if e.startswith('<visual'))
    print(f'parts={len(parts)} static_visuals={n_static} dynamic_models={len(dynamic)} mirror={mirror}')
    for z in zones:
        print(f"start_zone {z['team']}: ({z['x']:.3f}, {z['y']:.3f})")


if __name__ == '__main__':
    main()
