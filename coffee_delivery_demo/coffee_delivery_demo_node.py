import threading
import time

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient

from nav2_msgs.action import NavigateToPose
from geometry_msgs.msg import PoseStamped
from std_srvs.srv import Trigger


class CoffeeDeliveryNode(Node):
    def __init__(self):
        super().__init__('coffee_delivery_node')

        # Create Nav2 action client to send navigation goals
        self.nav_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')

        # Prevent multiple coffee delivery tasks from running at the same time
        self.task_running = False

        # Signals the delivery thread to advance past a "waiting for user" step
        self.continue_event = threading.Event()

        # Service to start a new delivery task
        self.start_service = self.create_service(
            Trigger,
            'start_coffee_delivery',
            self.start_delivery_callback
        )

        # Service to advance the task past a "waiting for user" step
        self.continue_service = self.create_service(
            Trigger,
            'continue_coffee_delivery',
            self.continue_delivery_callback
        )

        # Dictionary of waypoints
        self.waypoints = {
            'coffee_station': {
                'x': 8.611273765563965,
                'y': 3.054003953933716,
                'z': 0.0,
                'w': 1.0
            },
            'delivery_point': {
                'x': -2.029632806777954,
                'y': 2.441532850265503,
                'z': 0.0,
                'w': 1.0
            },
            'home': {
                'x': 8.405553817749023,
                'y': -3.751394748687744,
                'z': 0.0,
                'w': 1.0
            }
        }

        self.get_logger().info('Coffee delivery node ready.')
        self.get_logger().info(
            '  Start:    ros2 service call /start_coffee_delivery std_srvs/srv/Trigger'
        )
        self.get_logger().info(
            '  Continue: ros2 service call /continue_coffee_delivery std_srvs/srv/Trigger'
        )

    def wait_for_future(self, future):
        """
        Wait for an async ROS 2 future to complete.

        This avoids using rclpy.spin_until_future_complete(),
        because the main node is already spinning in rclpy.spin(node).
        """
        while rclpy.ok() and not future.done():
            time.sleep(0.1)

        return future.result()

    def create_goal_pose(self, location_name):
        """
        Create a PoseStamped goal for Nav2 based on the selected waypoint.
        """
        waypoint = self.waypoints[location_name]

        goal_pose = PoseStamped()
        goal_pose.header.frame_id = 'map'
        goal_pose.header.stamp = self.get_clock().now().to_msg()

        # Target position
        goal_pose.pose.position.x = waypoint['x']
        goal_pose.pose.position.y = waypoint['y']
        goal_pose.pose.position.z = 0.0

        # Target orientation
        goal_pose.pose.orientation.z = waypoint['z']
        goal_pose.pose.orientation.w = waypoint['w']

        return goal_pose

    def go_to_location(self, location_name):
        """
        Send TurtleBot to a selected location using Nav2.
        """
        self.get_logger().info('Waiting for Nav2 action server...')
        self.nav_client.wait_for_server()

        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = self.create_goal_pose(location_name)

        self.get_logger().info(f'Navigating to {location_name}...')

        # Send goal asynchronously
        send_goal_future = self.nav_client.send_goal_async(goal_msg)

        # Wait for Nav2 to accept or reject the goal
        goal_handle = self.wait_for_future(send_goal_future)

        if goal_handle is None:
            self.get_logger().error(f'No response from Nav2 for {location_name}.')
            return False

        if not goal_handle.accepted:
            self.get_logger().error(f'Goal to {location_name} was rejected.')
            return False

        self.get_logger().info(f'Goal to {location_name} accepted.')

        # Wait for navigation result
        result_future = goal_handle.get_result_async()
        result_response = self.wait_for_future(result_future)

        if result_response is None:
            self.get_logger().error(f'No result received for {location_name}.')
            return False

        status = result_response.status

        if status == 4:  # STATUS_SUCCEEDED
            self.get_logger().info(f'Arrived at {location_name}.')
            return True

        self.get_logger().error(
            f'Failed to reach {location_name}. Nav2 status: {status}'
        )
        return False

    def wait_for_user(self, message):
        """
        Block the delivery thread until /continue_coffee_delivery is called.
        """
        self.get_logger().info(message)
        self.continue_event.clear()
        while rclpy.ok() and not self.continue_event.is_set():
            self.continue_event.wait(timeout=0.1)

    def run_delivery(self):
        """
        Main coffee delivery workflow.
        """
        self.get_logger().info('Coffee delivery task started.')

        # Step 1: Go to coffee station
        self.get_logger().info('Task status: GOING_TO_COFFEE_STATION')
        success = self.go_to_location('coffee_station')

        if not success:
            self.get_logger().error('Failed to reach coffee station. Task aborted.')
            return

        # Step 2: Wait for coffee loading
        self.get_logger().info('Task status: WAITING_FOR_COFFEE_LOADING')
        self.wait_for_user(
            'Call /continue_coffee_delivery once coffee is loaded...'
        )

        # Step 3: Go to delivery point
        self.get_logger().info('Task status: GOING_TO_DELIVERY_POINT')
        success = self.go_to_location('delivery_point')

        if not success:
            self.get_logger().error('Failed to reach delivery point. Task aborted.')
            return

        # Step 4: Wait for recipient confirmation
        self.get_logger().info('Task status: WAITING_FOR_COFFEE_DELIVERY_CONFIRMATION')
        self.get_logger().info('Coffee delivered successfully!')
        self.wait_for_user(
            'Call /continue_coffee_delivery once recipient has collected the coffee...'
        )

        # Step 5: Return home
        self.get_logger().info('Task status: RETURNING_HOME')
        success = self.go_to_location('home')

        if not success:
            self.get_logger().error('Failed to return home. Task ended with error.')
            return

        # Step 6: Complete task
        self.get_logger().info('Task status: COMPLETED')
        self.get_logger().info('Robot returned home.')
        self.get_logger().info('Coffee delivery task completed.')

    def start_delivery_callback(self, request, response):
        """
        ROS 2 service callback to start coffee delivery.
        """
        if self.task_running:
            response.success = False
            response.message = 'Coffee delivery task is already running.'
            return response

        self.get_logger().info('Received coffee delivery request.')

        self.task_running = True
        self.continue_event.clear()

        threading.Thread(target=self.delivery_thread, daemon=True).start()

        response.success = True
        response.message = 'Coffee delivery task started.'
        return response

    def continue_delivery_callback(self, request, response):
        """
        ROS 2 service callback to advance past a "waiting for user" step.
        """
        if not self.task_running:
            response.success = False
            response.message = 'No coffee delivery task is running.'
            return response

        if self.continue_event.is_set():
            response.success = False
            response.message = 'Task is not currently waiting for confirmation.'
            return response

        self.continue_event.set()
        response.success = True
        response.message = 'Continue signal sent.'
        return response

    def delivery_thread(self):
        """
        Runs the delivery workflow in a separate thread.

        This allows the service callback to return immediately while the
        robot continues executing the task.
        """
        try:
            self.run_delivery()
        except Exception as e:
            self.get_logger().error(f'Coffee delivery task failed: {str(e)}')
        finally:
            self.task_running = False
            self.continue_event.set()


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