#!/usr/bin/env python3
"""3D LiDAR の点群から、車体に当たった点を取り除く (ボックス範囲のクロップ).

入力 : /lidar/points_raw (Gazebo の生の点群)
出力 : /lidar/points     (車体の点を除いた点群。RViz や他のノードはこちらを使う)

ボックスは点群の frame (lidar_link) 基準で、この範囲に入る点を捨てる。
既定値は車体 0.40 x 0.30 x 0.10 m + 余裕 0.02 m (LiDAR の中心は車体上面の 0.025 m 上)。
車体の寸法を変えたら、パラメータ x_min ... z_max も合わせて変えること。

QoS: 入力は sensor_data (Best Effort)。出力は Reliable にしてある。
     Reliable の publisher には Best Effort / Reliable どちらの subscriber もつながるので、
     RViz や ros2 topic echo などを QoS を気にせず使える。
"""

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, qos_profile_sensor_data
from sensor_msgs.msg import PointCloud2


class LidarBodyFilter(Node):
    def __init__(self):
        super().__init__('lidar_body_filter')
        self.declare_parameter('input_topic', '/lidar/points_raw')
        self.declare_parameter('output_topic', '/lidar/points')
        self.declare_parameter('x_min', -0.22)
        self.declare_parameter('x_max', 0.22)
        self.declare_parameter('y_min', -0.17)
        self.declare_parameter('y_max', 0.17)
        self.declare_parameter('z_min', -0.20)
        self.declare_parameter('z_max', 0.0)

        p = self.get_parameter
        self.lo = np.array([p('x_min').value, p('y_min').value, p('z_min').value])
        self.hi = np.array([p('x_max').value, p('y_max').value, p('z_max').value])

        self.pub = self.create_publisher(
            PointCloud2, p('output_topic').value, QoSProfile(depth=5))  # Reliable
        self.create_subscription(
            PointCloud2, p('input_topic').value, self.on_cloud, qos_profile_sensor_data)

    def on_cloud(self, msg):
        offsets = {f.name: f.offset for f in msg.fields}
        dtype = np.dtype({
            'names': ['x', 'y', 'z'],
            'formats': ['<f4'] * 3,
            'offsets': [offsets['x'], offsets['y'], offsets['z']],
            'itemsize': msg.point_step,
        })
        n = msg.width * msg.height
        raw = np.frombuffer(msg.data, dtype=np.uint8, count=n * msg.point_step)
        raw = raw.reshape(n, msg.point_step)
        xyz = np.frombuffer(raw.tobytes(), dtype=dtype, count=n)
        pts = np.stack([xyz['x'], xyz['y'], xyz['z']], axis=1)

        inside = np.all((pts >= self.lo) & (pts <= self.hi), axis=1)
        kept = raw[~inside]

        out = PointCloud2()
        out.header = msg.header
        out.height = 1
        out.width = int(kept.shape[0])
        out.fields = msg.fields
        out.is_bigendian = msg.is_bigendian
        out.point_step = msg.point_step
        out.row_step = msg.point_step * out.width
        out.is_dense = msg.is_dense
        out.data = kept.tobytes()
        self.pub.publish(out)


def main():
    rclpy.init()
    node = LidarBodyFilter()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.try_shutdown()


if __name__ == '__main__':
    main()
