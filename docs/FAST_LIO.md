# FAST_LIO でシミュレータの LiDAR + IMU を使う

コマンドはすべてコンテナ内で実行する。

## 1. Livox-SDK2

```bash
cd ~/ws
git clone https://github.com/Livox-SDK/Livox-SDK2.git
cd Livox-SDK2 && mkdir build && cd build
cmake .. && make -j
sudo make install
```

## 2. livox_ros_driver2 (ws_livox)

```bash
cd ~/ws
git clone https://github.com/Livox-SDK/livox_ros_driver2.git ws_livox/src/livox_ros_driver2
cd ws_livox/src/livox_ros_driver2
source /opt/ros/humble/setup.sh
./build.sh humble
source ~/.bashrc
```

## 3. FAST_LIO_ROS2 (ros2_ws)

```bash
cd ~/ws/ros2_ws/src
git clone https://github.com/Ericsii/FAST_LIO_ROS2.git --recursive
cd ..
rosdep update
rosdep install --from-paths src --ignore-src -y --skip-keys livox_ros_driver2
colcon build --symlink-install
source ~/.bashrc
```

## 4. 設定ファイル (mid360.yaml → robocon_sim.yaml)

```bash
cd ~/ws/ros2_ws/src/FAST_LIO_ROS2/config
cp mid360.yaml robocon_sim.yaml
sed -i \
  -e 's|lid_topic:  "/livox/lidar"|lid_topic:  "/lidar/points"|' \
  -e 's|imu_topic:  "/livox/imu"|imu_topic:  "/imu"|' \
  -e 's|lidar_type: 1 |lidar_type: 2 |' \
  -e 's|scan_line:  4|scan_line:  16|' \
  -e 's|extrinsic_T: \[ -0.011, -0.02329, 0.04412 \]|extrinsic_T: [ 0.0, 0.0, 0.075 ]|' \
  robocon_sim.yaml
```

値の確認:

```bash
ros2 topic echo /lidar/points --once --field fields         # ring がある → lidar_type: 2
ros2 topic echo /lidar/points_raw --once --field height     # 16 → scan_line: 16
ros2 run tf2_ros tf2_echo imu_link lidar_link               # Translation → extrinsic_T
```

## 5. 起動

```bash
# 端末 1
ros2 launch robocon2027_field robocon2027.launch.py
# 端末 2
ros2 launch fast_lio mapping.launch.py \
  config_file:=$HOME/ws/ros2_ws/src/FAST_LIO_ROS2/config/robocon_sim.yaml use_sim_time:=true
# 端末 3
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```
