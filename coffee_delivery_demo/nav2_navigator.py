"""
Thin wrapper around the Nav2 ``NavigateToPose`` action client.

Knows nothing about the coffee delivery workflow — just turns a named
waypoint into a navigation goal and reports success/failure.
"""

import time

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node

from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose


class Nav2Navigator:
    STATUS_SUCCEEDED = 4

    def __init__(self, node: Node):
        self._node = node
        self._logger = node.get_logger()
        self._client = ActionClient(node, NavigateToPose, 'navigate_to_pose')

    def go_to(self, location_name: str, waypoint: dict) -> bool:
        """Drive the robot to the given waypoint. Returns True on success."""
        self._logger.info('Waiting for Nav2 action server...')
        self._client.wait_for_server()

        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = self._make_pose(waypoint)

        self._logger.info(f'Navigating to {location_name}...')

        send_goal_future = self._client.send_goal_async(goal_msg)
        goal_handle = self._wait_for_future(send_goal_future)

        if goal_handle is None:
            self._logger.error(f'No response from Nav2 for {location_name}.')
            return False

        if not goal_handle.accepted:
            self._logger.error(f'Goal to {location_name} was rejected.')
            return False

        self._logger.info(f'Goal to {location_name} accepted.')

        result_future = goal_handle.get_result_async()
        result_response = self._wait_for_future(result_future)

        if result_response is None:
            self._logger.error(f'No result received for {location_name}.')
            return False

        if result_response.status == self.STATUS_SUCCEEDED:
            self._logger.info(f'Arrived at {location_name}.')
            return True

        self._logger.error(
            f'Failed to reach {location_name}. Nav2 status: {result_response.status}'
        )
        return False

    def _make_pose(self, waypoint: dict) -> PoseStamped:
        pose = PoseStamped()
        pose.header.frame_id = 'map'
        pose.header.stamp = self._node.get_clock().now().to_msg()
        pose.pose.position.x = waypoint['x']
        pose.pose.position.y = waypoint['y']
        pose.pose.position.z = 0.0
        pose.pose.orientation.z = waypoint['z']
        pose.pose.orientation.w = waypoint['w']
        return pose

    def _wait_for_future(self, future):
        # Poll instead of rclpy.spin_until_future_complete() because the node
        # is already being spun by rclpy.spin() on the main thread.
        while rclpy.ok() and not future.done():
            time.sleep(0.1)
        return future.result()
