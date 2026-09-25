"""diffbot を Gazebo (Fortress) で起動し、ROS 2 とつなぐ launch ファイル.

起動するもの:
  1. Gazebo (ワールド)
  2. robot_state_publisher (URDF を /robot_description に publish, TF を出す)
  3. ros_gz_sim create (/robot_description から Gazebo にロボットを出現させる)
  4. ros_gz_bridge parameter_bridge (Gazebo <-> ROS 2 のトピック変換)
  5. RViz2 (rviz:=false で無効)

使い方:
  ros2 launch diffbot_sim sim.launch.py
  ros2 launch diffbot_sim sim.launch.py gui:=false rviz:=false   # 画面なし (サーバのみ)
  ros2 launch diffbot_sim sim.launch.py world:=/ros2_ws/worlds/my_world.sdf x:=1.0 yaw:=1.57
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (AppendEnvironmentVariable, DeclareLaunchArgument,
                            IncludeLaunchDescription)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (Command, LaunchConfiguration,
                                  PythonExpression)
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg_share = get_package_share_directory('diffbot_sim')
    ros_gz_sim_share = get_package_share_directory('ros_gz_sim')

    default_world = os.path.join(pkg_share, 'worlds', 'diffbot_world.sdf')
    xacro_file = os.path.join(pkg_share, 'urdf', 'diffbot.urdf.xacro')
    bridge_config = os.path.join(pkg_share, 'config', 'bridge.yaml')
    rviz_config = os.path.join(pkg_share, 'rviz', 'diffbot.rviz')

    world = LaunchConfiguration('world')
    gui = LaunchConfiguration('gui')
    rviz = LaunchConfiguration('rviz')
    use_sim_time = LaunchConfiguration('use_sim_time')

    declare_args = [
        DeclareLaunchArgument('world', default_value=default_world,
                              description='読み込む SDF ワールドファイルのパス'),
        DeclareLaunchArgument('gui', default_value='true',
                              description='Gazebo の GUI を表示するか'),
        DeclareLaunchArgument('rviz', default_value='true',
                              description='RViz2 を起動するか'),
        DeclareLaunchArgument('use_sim_time', default_value='true',
                              description='シミュレーション時刻 (/clock) を使うか'),
        DeclareLaunchArgument('x', default_value='0.0', description='初期位置 x [m]'),
        DeclareLaunchArgument('y', default_value='0.0', description='初期位置 y [m]'),
        DeclareLaunchArgument('z', default_value='0.05', description='初期位置 z [m]'),
        DeclareLaunchArgument('yaw', default_value='0.0', description='初期姿勢 yaw [rad]'),
    ]

    # Gazebo がモデルを探すパスに /ros2_ws/models (自作モデル置き場) を追加
    set_resource_path = AppendEnvironmentVariable(
        'IGN_GAZEBO_RESOURCE_PATH', '/ros2_ws/models')

    # 1. Gazebo 本体
    #    -r: 起動と同時にシミュレーション開始
    #    gui:=false のときは -s (サーバのみ) + --headless-rendering (画面なしでもカメラが動く)
    gz_args = PythonExpression([
        "'-r ", world, "' + ('' if '", gui, "' == 'true' else ' -s --headless-rendering')"
    ])
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(ros_gz_sim_share, 'launch', 'gz_sim.launch.py')),
        launch_arguments={'gz_args': gz_args, 'on_exit_shutdown': 'true'}.items(),
    )

    # 2. robot_state_publisher: xacro を展開して /robot_description に流す
    robot_description = ParameterValue(Command(['xacro ', xacro_file]), value_type=str)
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_description,
                     'use_sim_time': use_sim_time}],
    )

    # 3. Gazebo にロボットを spawn
    spawn = Node(
        package='ros_gz_sim',
        executable='create',
        output='screen',
        arguments=[
            '-topic', 'robot_description',
            '-name', 'diffbot',
            '-x', LaunchConfiguration('x'),
            '-y', LaunchConfiguration('y'),
            '-z', LaunchConfiguration('z'),
            '-Y', LaunchConfiguration('yaw'),
        ],
    )

    # 4. Gazebo <-> ROS 2 ブリッジ (対応表は config/bridge.yaml)
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        output='screen',
        parameters=[{'config_file': bridge_config,
                     'use_sim_time': use_sim_time}],
    )

    # 5. RViz2
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        arguments=['-d', rviz_config],
        parameters=[{'use_sim_time': use_sim_time}],
        condition=IfCondition(rviz),
    )

    return LaunchDescription(declare_args + [
        set_resource_path,
        gazebo,
        robot_state_publisher,
        spawn,
        bridge,
        rviz_node,
    ])
