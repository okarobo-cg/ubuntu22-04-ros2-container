"""ABU Robocon 2027 フィールドで diffbot を起動する launch ファイル.

ロボットはスタートゾーン (700 x 700 mm) の中央に、フィールド奥 (+y) 向きで置く。

使い方:
  ros2 launch robocon2027_field robocon2027.launch.py                 # 赤チーム, zone1
  ros2 launch robocon2027_field robocon2027.launch.py team:=blue zone:=2
  ros2 launch robocon2027_field robocon2027.launch.py gui:=false rviz:=false

  zone1 = フィールド中央寄りのスタートゾーン, zone2 = 角のスタートゾーン
"""

import math
import os

import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, IncludeLaunchDescription,
                            LogInfo, OpaqueFunction)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

# base_footprint (車輪軸の中心) からロボット外形の中心までの前方オフセット [m]
# scripts/check_robot_size.py の「外形の中心」の値。ロボットを改造したら更新する。
ROBOT_CENTER_OFFSET = 0.0275


def launch_setup(context):
    field_share = get_package_share_directory('robocon2027_field')
    diffbot_share = get_package_share_directory('diffbot_sim')

    team = LaunchConfiguration('team').perform(context)
    zone = LaunchConfiguration('zone').perform(context)
    yaw = float(LaunchConfiguration('yaw').perform(context))

    with open(os.path.join(field_share, 'config', 'start_zones.yaml')) as f:
        zones = yaml.safe_load(f)
    z = zones[team][f'zone{zone}']

    # 外形の中心がゾーン中心に来るよう、向きに合わせて base_footprint をずらす
    x = z['x'] - ROBOT_CENTER_OFFSET * math.cos(yaw)
    y = z['y'] - ROBOT_CENTER_OFFSET * math.sin(yaw)

    sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(diffbot_share, 'launch', 'sim.launch.py')),
        launch_arguments={
            'world': os.path.join(field_share, 'worlds', 'robocon2027.sdf'),
            'x': f'{x:.4f}', 'y': f'{y:.4f}', 'z': '0.02', 'yaw': f'{yaw:.4f}',
            'gui': LaunchConfiguration('gui'),
            'rviz': LaunchConfiguration('rviz'),
        }.items(),
    )

    # フィールド座標系 "map" (原点 = フィールド中央) -> odom (= ロボットの初期位置)
    # これで RViz の Fixed Frame を map にするとフィールド座標でロボット位置が見られる
    map_to_odom = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        arguments=['--x', f'{x:.4f}', '--y', f'{y:.4f}', '--z', '0',
                   '--yaw', f'{yaw:.4f}', '--pitch', '0', '--roll', '0',
                   '--frame-id', 'map', '--child-frame-id', 'odom'],
        parameters=[{'use_sim_time': True}],
    )

    info = LogInfo(msg=f'[robocon2027] team={team} zone{zone}: '
                       f'zone center=({z["x"]:.3f}, {z["y"]:.3f}), spawn=({x:.3f}, {y:.3f}, yaw={yaw:.3f})')
    return [info, sim, map_to_odom]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('team', default_value='red', choices=['red', 'blue'],
                              description='チーム (スタートゾーンの色)'),
        DeclareLaunchArgument('zone', default_value='1', choices=['1', '2'],
                              description='1: 中央寄りのゾーン, 2: 角のゾーン'),
        DeclareLaunchArgument('yaw', default_value=str(math.pi / 2),
                              description='初期の向き [rad] (既定: フィールド奥 +y 向き)'),
        DeclareLaunchArgument('gui', default_value='true'),
        DeclareLaunchArgument('rviz', default_value='true'),
        OpaqueFunction(function=launch_setup),
    ])
