# ROS 2 と ~/ws 以下のワークスペースを読み込む (~/.bashrc と entrypoint.sh から source する)。
# ros2_ws 以外を先に、ros2_ws を最後 (最上位の overlay) に読み込むので、
# ros2_ws のパッケージから他のワークスペースのパッケージを使える。
# ワークスペースを増やすときは ~/ws/<名前>_ws を作って colcon build するだけでよい。

source /opt/ros/humble/setup.bash

for _ws in "$HOME"/ws/*/; do
  if [ "$_ws" != "$HOME/ws/ros2_ws/" ] && [ -f "${_ws}install/local_setup.bash" ]; then
    source "${_ws}install/local_setup.bash"
  fi
done
if [ -f "$HOME/ws/ros2_ws/install/local_setup.bash" ]; then
  source "$HOME/ws/ros2_ws/install/local_setup.bash"
fi
unset _ws
