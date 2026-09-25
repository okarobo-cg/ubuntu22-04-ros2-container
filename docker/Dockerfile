# =============================================================
#  diffbot_sim 用 Docker イメージ
#   Ubuntu 22.04 + ROS 2 Humble + Gazebo Fortress (ros_gz)
# =============================================================
FROM ros:humble-ros-base-jammy

ENV DEBIAN_FRONTEND=noninteractive

# シミュレーションに必要なパッケージ
#  - ros-humble-ros-gz        : Gazebo Fortress 本体 + ROS 2 連携 (ros_gz_sim, ros_gz_bridge)
#  - ros-humble-xacro         : URDF マクロ展開
#  - ros-humble-robot-state-publisher
#  - ros-humble-rviz2         : 可視化
#  - ros-humble-rqt-image-view: カメラ画像の確認
#  - ros-humble-teleop-twist-keyboard : キーボード操縦
RUN apt-get update && apt-get install -y --no-install-recommends \
      ros-humble-ros-gz \
      ros-humble-xacro \
      ros-humble-robot-state-publisher \
      ros-humble-rviz2 \
      ros-humble-rqt-image-view \
      ros-humble-teleop-twist-keyboard \
      python3-colcon-common-extensions \
      vim nano git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /ros2_ws

COPY entrypoint.sh /entrypoint.sh
# Windows で clone すると改行が CRLF になり "bash\r: No such file" で起動しなくなるので LF に直す
RUN sed -i 's/\r$//' /entrypoint.sh \
 && chmod +x /entrypoint.sh \
 && echo 'source /opt/ros/humble/setup.bash' >> /root/.bashrc \
 && echo 'if [ -f /ros2_ws/install/setup.bash ]; then source /ros2_ws/install/setup.bash; fi' >> /root/.bashrc

ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash"]
