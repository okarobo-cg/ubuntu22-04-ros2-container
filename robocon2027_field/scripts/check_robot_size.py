#!/usr/bin/env python3
"""ロボットの外形寸法・質量を URDF (xacro) から計算し、ABU Robocon 2027 のルールと照合する.

  ルール 11.4: 開始時の寸法は 700 x 700 x 700 mm 以内 (スタートゾーンも 700 x 700 mm)
  ルール 11.7: 質量は 50 kg 以下 (バッテリ等込み)

使い方:
  python3 check_robot_size.py [xacro ファイル]   (省略時は diffbot_sim の diffbot.urdf.xacro)
※ collision 形状で計算する。伸縮機構の最大展開時 (11.5/11.6) は対象外。
"""
import sys
import subprocess, itertools, numpy as np, xml.etree.ElementTree as ET
from math import cos, sin
if len(sys.argv) > 1:
    xacro_file = sys.argv[1]
else:
    from ament_index_python.packages import get_package_share_directory
    xacro_file = get_package_share_directory('diffbot_sim') + '/urdf/diffbot.urdf.xacro'
xml = subprocess.check_output(['xacro', xacro_file])
r = ET.fromstring(xml)
def T(o):
    xyz = [float(a) for a in (o.get('xyz', '0 0 0') if o is not None else '0 0 0').split()]
    rr, p, y = [float(a) for a in (o.get('rpy', '0 0 0') if o is not None else '0 0 0').split()]
    Rx = np.array([[1,0,0],[0,cos(rr),-sin(rr)],[0,sin(rr),cos(rr)]]); Ry = np.array([[cos(p),0,sin(p)],[0,1,0],[-sin(p),0,cos(p)]]); Rz = np.array([[cos(y),-sin(y),0],[sin(y),cos(y),0],[0,0,1]])
    M = np.eye(4); M[:3,:3] = Rz@Ry@Rx; M[:3,3] = xyz; return M
parent = {j.find('child').get('link'): (j.find('parent').get('link'), T(j.find('origin'))) for j in r.findall('joint')}
def world(l):
    M = np.eye(4)
    while l in parent: p, J = parent[l]; M = J@M; l = p
    return M
pts = []; mass = 0
for l in r.findall('link'):
    W = world(l.get('name'))
    m = l.find('inertial/mass'); mass += float(m.get('value')) if m is not None else 0
    for c in l.findall('collision'):
        M = W@T(c.find('origin')); g = c.find('geometry')[0]
        if g.tag == 'box': h = np.array([float(a) for a in g.get('size').split()])/2
        elif g.tag == 'cylinder': rad, L = float(g.get('radius')), float(g.get('length')); h = np.array([rad, rad, L/2])
        elif g.tag == 'sphere': h = np.array([float(g.get('radius'))]*3)
        for s in itertools.product([-1,1], repeat=3): pts.append((M@np.append(np.array(s)*h, 1))[:3])
P = np.array(pts); mn, mx = P.min(0), P.max(0)
print(f'x (前後): {mn[0]:+.3f} ~ {mx[0]:+.3f} m -> 長さ {mx[0]-mn[0]:.3f} m')
print(f'y (左右): {mn[1]:+.3f} ~ {mx[1]:+.3f} m -> 幅   {mx[1]-mn[1]:.3f} m')
print(f'z (高さ): {mn[2]:+.3f} ~ {mx[2]:+.3f} m -> 高さ {mx[2]-mn[2]:.3f} m')
print(f'外形の中心 (base_footprint から): x={(mn[0]+mx[0])/2:+.4f} y={(mn[1]+mx[1])/2:+.4f}')
print(f'質量: {mass:.2f} kg')

LIMIT, MASS_LIMIT = 0.700, 50.0
size = mx - mn
ok = all(size <= LIMIT) and mass <= MASS_LIMIT
print('--- ABU Robocon 2027 ルール照合 ---')
for name, v in zip(('長さ', '幅', '高さ'), size):
    print(f'  {name}: {v*1000:6.0f} mm / 上限 {LIMIT*1000:.0f} mm  {"OK" if v <= LIMIT else "NG"}')
print(f'  質量: {mass:6.2f} kg / 上限 {MASS_LIMIT:.0f} kg  {"OK" if mass <= MASS_LIMIT else "NG"}')
print('結果:', 'ルール内 (OK)' if ok else 'ルール違反 (NG)')
sys.exit(0 if ok else 1)
