import rclpy
from rclpy.node import Node # Python library for ROS2 nodes
from rclpy.action import ActionClient   # Used to create your own ROS2 node

from nav2_msgs.action import NavigateToPose # ROS2 action used to send navigation goals to Nav2
from geometry_msgs.msg import PoseStamped   # ROS2 message type used to specify the target pose for navigation goals


class CoffeeDeliveryNode(Node):
    def __init__(self):
        super().__init__('coffee_delivery_node')

        # Creating Nav2 action client to send navigation goals
        self.nav_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')

        # Dictionary of waypoints (locations that the turtlebot should go to)
        self.waypoints = {
            # Three locations: coffee station, delivery point and home
            # Coordinates are based on the map used in the demo, x and y are turtlebot's target coordinates on the map
            # z and w are turtlebot's target orientation in quaternion format
            'coffee_station': {
                'x': 8.611273765563965,
                'y': 3.054003953933716,
                'z': 0.0,   # z and w set to 0 and 1 respectively as it is treated as facing "forward"
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

    # Creating goal pose
    def create_goal_pose(self, location_name):
        waypoint = self.waypoints[location_name]    # Get the coordinates of the specified location from the waypoints dictionary

        goal_pose = PoseStamped()
        goal_pose.header.frame_id = 'map'
        goal_pose.header.stamp = self.get_clock().now().to_msg()

        # Set the target position
        goal_pose.pose.position.x = waypoint['x']
        goal_pose.pose.position.y = waypoint['y']
        goal_pose.pose.position.z = 0.0

        # Set the target orientation (final facing direction when it reaches the goal)
        goal_pose.pose.orientation.z = waypoint['z']
        goal_pose.pose.orientation.w = waypoint['w']

        return goal_pose

    # Sending turtlebot to a location
    def go_to_location(self, location_name):    # Tells turtlebot to go to one location
        self.get_logger().info(f'Waiting for Nav2 action server...')
        self.nav_client.wait_for_server()

        # Create a navigation goal message with the target pose
        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = self.create_goal_pose(location_name)

        self.get_logger().info(f'Navigating to {location_name}...')

        # Send the goal to Nav2 and wait for the result (whether it successfully reached the location or not)
        send_goal_future = self.nav_client.send_goal_async(goal_msg)
        rclpy.spin_until_future_complete(self, send_goal_future)

        # Response from Nav2 after sending the goal
        goal_handle = send_goal_future.result()

        # If Nav2 rejected the goal, log an error and return False to indicate failure
        if not goal_handle.accepted:
            self.get_logger().error(f'Goal to {location_name} was rejected.')
            return False

        self.get_logger().info(f'Goal to {location_name} accepted.')

        # This waits until the turtlebot finishes navigating
        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)

        result = result_future.result().result

        # Check is the turtlebot successfully arrived
        status = result_future.result().status

        if status == 4: # STATUS_SUCCEEDED
            self.get_logger().info(f'Arrived at {location_name}.')
            return True
        else:
            self.get_logger().error(f'Failed to reach {location_name}. Status: {status}')
            return False

    # Starts the main coffee delivery task
    # The turtlebot will first go to the coffee station
    # Then after the user confirms that the coffee is loaded
    # It will go to the delivery point
    # After coffee is delivered, the bot will back to the home location
    def run_delivery(self):
        self.get_logger().info('Coffee delivery task started.')

        # Go to coffee station first
        success = self.go_to_location('coffee_station')
        if not success:
            self.get_logger().error('Failed to reach coffee station. Task aborted.')
            return

        # Wait for coffee loading
        input('Arrived at coffee station. Press Enter after coffee is loaded...')

        # Go to delivery point
        success = self.go_to_location('delivery_point')
        if not success:
            self.get_logger().error('Failed to reach delivery point. Task aborted.')
            return

        # Coffee delivered
        self.get_logger().info('Coffee delivered successfully!')

        input('Press Enter to confirm your pickup...')
        
        # Return home
        success = self.go_to_location('home')
        self.get_logger().info('Robot returned home.')
        self.get_logger().info('Coffee delivery task completed.')

# Main function to run the node
def main(args=None):
    rclpy.init(args=args)

    node = CoffeeDeliveryNode()

    try:
        node.run_delivery() # Start the coffee delivery task
    except KeyboardInterrupt:
        node.get_logger().info('Coffee delivery interrupted.')  # Allow graceful shutdown on Ctrl+C
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()