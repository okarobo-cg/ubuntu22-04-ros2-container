# =============================================================
#  diffbot_sim 用 Docker イメージ
#   Ubuntu 22.04 + ROS 2 Humble + Gazebo Fortress (ros_gz)
# =============================================================
FROM ros:humble-ros-base-jammy

ENV DEBIAN_FRONTEND=noninteractive
# プロンプトの絵文字を正しく表示するため UTF-8 にする
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# シミュレーションに必要なパッケージ
#  - ros-humble-ros-gz        : Gazebo Fortress 本体 + ROS 2 連携 (ros_gz_sim, ros_gz_bridge)
#  - ros-humble-xacro         : URDF マクロ展開
#  - ros-humble-robot-state-publisher
#  - ros-humble-rviz2         : 可視化
#  - ros-humble-rqt-image-view: カメラ画像の確認
#  - ros-humble-teleop-twist-keyboard : キーボード操縦
#  - python3-numpy            : lidar_body_filter.py で使う
#  - mesa-utils               : glxinfo (GPU 描画になっているかの確認用)
RUN apt-get update && apt-get install -y --no-install-recommends \
      ros-humble-ros-gz \
      ros-humble-xacro \
      ros-humble-robot-state-publisher \
      ros-humble-rviz2 \
      ros-humble-rqt-image-view \
      ros-humble-teleop-twist-keyboard \
      python3-colcon-common-extensions \
      python3-numpy \
      mesa-utils \
      vim nano git sudo \
    && rm -rf /var/lib/apt/lists/*

# 一般ユーザ okarobo (sudo はパスワードなしで使える)。
# UID/GID はホストのユーザに合わせる (start.sh が渡す。既定 1000)。
# こうするとマウントしたフォルダのファイルがホスト側でも自分の所有になる。
ARG USER_UID=1000
ARG USER_GID=1000
RUN groupadd --gid ${USER_GID} okarobo \
 && useradd --uid ${USER_UID} --gid ${USER_GID} --groups video --create-home --shell /bin/bash okarobo \
 && echo 'okarobo ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/okarobo \
 && chmod 0440 /etc/sudoers.d/okarobo \
 && mkdir -p /ros2_ws && chown okarobo:okarobo /ros2_ws

COPY entrypoint.sh /entrypoint.sh
# Windows で clone すると改行が CRLF になり "bash\r: No such file" で起動しなくなるので LF に直す
RUN sed -i 's/\r$//' /entrypoint.sh \
 && chmod +x /entrypoint.sh

USER okarobo
WORKDIR /ros2_ws
RUN echo 'source /opt/ros/humble/setup.bash' >> ~/.bashrc \
 && echo 'if [ -f /ros2_ws/install/setup.bash ]; then source /ros2_ws/install/setup.bash; fi' >> ~/.bashrc

# カラープロンプト: okarobo(蛍光オレンジ) 🤖 パス(蛍光水色) / 改行 / >(蛍光水色)
# /bin/sh の echo は \n や \e を変換してしまうので printf '%s\n' でそのまま書き込む
RUN printf '%s\n' \
      '' \
      '# custom prompt' \
      'PS1="\[\e[1;38;5;208m\]\u\[\e[0m\] 🤖 \[\e[1;38;5;51m\]\w\[\e[0m\]\n\[\e[1;38;5;51m\]>\[\e[0m\] "' \
      >> ~/.bashrc

ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash"]
