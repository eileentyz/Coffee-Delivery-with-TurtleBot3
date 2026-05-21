"""
ROS 2 entry point for the coffee delivery demo.

Wires the Nav2Navigator and DeliveryTask together and exposes the
``/start_coffee_delivery`` and ``/continue_coffee_delivery`` services.
"""

import rclpy
from rclpy.node import Node

from std_srvs.srv import Trigger

from coffee_delivery_demo.delivery_task import DeliveryTask
from coffee_delivery_demo.nav2_navigator import Nav2Navigator


class CoffeeDeliveryNode(Node):
    def __init__(self):
        super().__init__('coffee_delivery_node')

        navigator = Nav2Navigator(self)
        self._task = DeliveryTask(self, navigator)

        self.create_service(
            Trigger, 'start_coffee_delivery', self._start_callback
        )
        self.create_service(
            Trigger, 'continue_coffee_delivery', self._continue_callback
        )

        self.get_logger().info('Coffee delivery node ready.')
        self.get_logger().info(
            '  Start:    ros2 service call /start_coffee_delivery std_srvs/srv/Trigger'
        )
        self.get_logger().info(
            '  Continue: ros2 service call /continue_coffee_delivery std_srvs/srv/Trigger'
        )

    def _start_callback(self, request, response):
        if not self._task.start():
            response.success = False
            response.message = 'Coffee delivery task is already running.'
            return response

        self.get_logger().info('Received coffee delivery request.')
        response.success = True
        response.message = 'Coffee delivery task started.'
        return response

    def _continue_callback(self, request, response):
        if not self._task.is_running:
            response.success = False
            response.message = 'No coffee delivery task is running.'
            return response

        if self._task.has_pending_continue:
            response.success = False
            response.message = 'Task is not currently waiting for confirmation.'
            return response

        self._task.signal_continue()
        response.success = True
        response.message = 'Continue signal sent.'
        return response


def main(args=None):
    rclpy.init(args=args)

    node = CoffeeDeliveryNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Coffee delivery node stopped.')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
