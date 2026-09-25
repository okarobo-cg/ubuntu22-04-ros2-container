cmake_minimum_required(VERSION 3.8)
project(robocon2027_field)

find_package(ament_cmake REQUIRED)

# worlds/robocon2027.sdf と config/start_zones.yaml は scripts/glb_to_sdf.py で生成したもの
install(
  DIRECTORY launch worlds config glb
  DESTINATION share/${PROJECT_NAME}
)

install(
  PROGRAMS scripts/glb_to_sdf.py scripts/check_robot_size.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
