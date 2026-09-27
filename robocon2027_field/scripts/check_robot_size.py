#!/usr/bin/env python3
"""ロボットの外形寸法・質量を URDF (xacro) から計算し、ABU Robocon 2027 のルールと照合する.

  ルール 11.4: 開始時の寸法は 700 x 700 x 700 mm 以内 (スタートゾーンも 700 x 700 mm)
  ルール 11.7: 質量は 50 kg 以下 (バッテリ等込み)

使い方:
  python3 check_robot_size.py [xacro ファイル]   (省略時は diffbot_sim の diffbot.urdf.xacro)

※ collision 形状 (box / cylinder / sphere) の頂点から外形を求める。mesh は対象外 (警告を出す)。
※ 伸縮機構の最大展開時 (11.5 / 11.6) は対象外。
"""

import itertools
import subprocess
import sys
import xml.etree.ElementTree as ET
from math import cos, sin

import numpy as np

SIZE_LIMIT = 0.700   # [m] ルール 11.4
MASS_LIMIT = 50.0    # [kg] ルール 11.7


def default_xacro():
    from ament_index_python.packages import get_package_share_directory
    return get_package_share_directory('diffbot_sim') + '/urdf/diffbot.urdf.xacro'


def transform(origin):
    """<origin xyz rpy> を 4x4 の同次変換行列にする (URDF の rpy = Rz * Ry * Rx)."""
    xyz = [float(a) for a in (origin.get('xyz', '0 0 0') if origin is not None else '0 0 0').split()]
    r, p, y = [float(a) for a in (origin.get('rpy', '0 0 0') if origin is not None else '0 0 0').split()]
    rx = np.array([[1, 0, 0], [0, cos(r), -sin(r)], [0, sin(r), cos(r)]])
    ry = np.array([[cos(p), 0, sin(p)], [0, 1, 0], [-sin(p), 0, cos(p)]])
    rz = np.array([[cos(y), -sin(y), 0], [sin(y), cos(y), 0], [0, 0, 1]])
    m = np.eye(4)
    m[:3, :3] = rz @ ry @ rx
    m[:3, 3] = xyz
    return m


def half_extents(geom):
    """collision 形状の半寸法 (その形状の座標系で)。未対応の形状なら None."""
    if geom.tag == 'box':
        return np.array([float(a) for a in geom.get('size').split()]) / 2
    if geom.tag == 'cylinder':   # 軸は z
        r, length = float(geom.get('radius')), float(geom.get('length'))
        return np.array([r, r, length / 2])
    if geom.tag == 'sphere':
        return np.full(3, float(geom.get('radius')))
    return None


def main():
    xacro_file = sys.argv[1] if len(sys.argv) > 1 else default_xacro()
    robot = ET.fromstring(subprocess.check_output(['xacro', xacro_file]))

    # 子リンク -> (親リンク, 関節の変換)
    parent = {j.find('child').get('link'): (j.find('parent').get('link'), transform(j.find('origin')))
              for j in robot.findall('joint')}

    def link_to_root(link):
        """リンク座標 -> ルート (base_footprint) 座標の変換."""
        m = np.eye(4)
        while link in parent:
            link, joint = parent[link]
            m = joint @ m
        return m

    corners, mass = [], 0.0
    for link in robot.findall('link'):
        name = link.get('name')
        m = link.find('inertial/mass')
        if m is not None:
            mass += float(m.get('value'))
        for col in link.findall('collision'):
            geom = col.find('geometry')[0]
            h = half_extents(geom)
            if h is None:
                print(f'警告: {name} の collision ({geom.tag}) は未対応のため外形の計算から除外', file=sys.stderr)
                continue
            m_col = link_to_root(name) @ transform(col.find('origin'))
            for s in itertools.product([-1, 1], repeat=3):
                corners.append((m_col @ np.append(np.array(s) * h, 1))[:3])

    pts = np.array(corners)
    # 丸めてから + 0.0 して、計算誤差による -0.000 表示を防ぐ
    mn, mx = np.round(pts.min(axis=0), 6) + 0.0, np.round(pts.max(axis=0), 6) + 0.0
    size = mx - mn
    center = (mn + mx) / 2 + 0.0

    print(f'x (前後): {mn[0]:+.3f} ~ {mx[0]:+.3f} m -> 長さ {size[0]:.3f} m')
    print(f'y (左右): {mn[1]:+.3f} ~ {mx[1]:+.3f} m -> 幅   {size[1]:.3f} m')
    print(f'z (高さ): {mn[2]:+.3f} ~ {mx[2]:+.3f} m -> 高さ {size[2]:.3f} m')
    print(f'外形の中心 (base_footprint から): x={center[0]:+.4f} y={center[1]:+.4f}')
    print(f'質量: {mass:.2f} kg')

    ok = bool(np.all(size <= SIZE_LIMIT)) and mass <= MASS_LIMIT
    print('--- ABU Robocon 2027 ルール照合 ---')
    for label, v in zip(('長さ', '幅', '高さ'), size):
        print(f'  {label}: {v * 1000:6.0f} mm / 上限 {SIZE_LIMIT * 1000:.0f} mm  {"OK" if v <= SIZE_LIMIT else "NG"}')
    print(f'  質量: {mass:6.2f} kg / 上限 {MASS_LIMIT:.0f} kg  {"OK" if mass <= MASS_LIMIT else "NG"}')
    print('結果:', 'ルール内 (OK)' if ok else 'ルール違反 (NG)')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
