cmake_minimum_required(VERSION 3.8)
project(diffbot_sim)

find_package(ament_cmake REQUIRED)

# launch / urdf / worlds / config / rviz を install/share/diffbot_sim にコピーする
install(
  DIRECTORY launch urdf worlds config rviz
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
