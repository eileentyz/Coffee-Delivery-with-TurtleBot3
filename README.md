# coffee_delivery_demo

A ROS 2 demo that drives a TurtleBot3 through a simple coffee-delivery workflow using Nav2:

1. Drive to the coffee station
2. Wait for the user to confirm the coffee has been loaded
3. Drive to the delivery point
4. Wait for the user to confirm the recipient has collected the coffee
5. Return home

The task is started and advanced via two ROS 2 services, so it works headlessly under `ros2 launch` (no terminal `input()` required).

## Prerequisites

- ROS 2 **Jazzy**
- TurtleBot3 simulation + Nav2 stack
- A loaded map matching the waypoint coordinates in `coffee_delivery_demo_node.py` (retune `self.waypoints` for your map)

## Build

```bash
cd ~/turtlebot3_ws
colcon build --packages-select coffee_delivery_demo --symlink-install
source install/setup.bash
```

## Run the demo

Open four terminals. Source ROS 2 and the workspace in each:

```bash
source /opt/ros/jazzy/setup.bash
source ~/turtlebot3_ws/install/setup.bash
```

### Terminal 1 — Gazebo simulation

```bash
export TURTLEBOT3_MODEL=burger
ros2 launch turtlebot3_gazebo turtlebot3_house.launch.py
```

### Terminal 2 — Nav2 with your map

```bash
export TURTLEBOT3_MODEL=burger
ros2 launch turtlebot3_navigation2 navigation2.launch.py use_sim_time:=True map:=$HOME/house_office_map.yaml

```

In RViz, use **2D Pose Estimate** to set the robot's initial pose so AMCL can localize.

### Terminal 3 — Coffee delivery node

```bash
ros2 run coffee_delivery_demo coffee_delivery_demo_node
```

You should see:

```
Coffee delivery node ready.
  Start:    ros2 service call /start_coffee_delivery std_srvs/srv/Trigger
  Continue: ros2 service call /continue_coffee_delivery std_srvs/srv/Trigger
```

### Terminal 4 — Trigger the task

```bash
# 1. Start the delivery (robot drives to coffee station)
ros2 service call /start_coffee_delivery std_srvs/srv/Trigger

# 2. After it arrives at the coffee station, signal coffee is loaded
ros2 service call /continue_coffee_delivery std_srvs/srv/Trigger

# 3. After it arrives at the delivery point, signal coffee has been collected
ros2 service call /continue_coffee_delivery std_srvs/srv/Trigger

# 4. Robot returns home and the task completes
```

Watch Terminal 3 for status logs (`GOING_TO_COFFEE_STATION`, `WAITING_FOR_COFFEE_LOADING`, etc.).

## Services

| Service | Type | Behavior |
|---|---|---|
| `/start_coffee_delivery` | `std_srvs/srv/Trigger` | Starts a new delivery task. Rejected if one is already running. |
| `/continue_coffee_delivery` | `std_srvs/srv/Trigger` | Advances the task past a "waiting for user" step. Rejected if no task is running or the task is not currently waiting. |

## Verifying behavior

You can sanity-check the triggering logic without driving the robot anywhere:

```bash
# Should fail — no task running yet
ros2 service call /continue_coffee_delivery std_srvs/srv/Trigger
# → success=False, message="No coffee delivery task is running."

# Start a task
ros2 service call /start_coffee_delivery std_srvs/srv/Trigger
# → success=True

# Should fail — already running
ros2 service call /start_coffee_delivery std_srvs/srv/Trigger
# → success=False, message="Coffee delivery task is already running."
```

## Package layout

```
coffee_delivery_demo/
├── coffee_delivery_demo_node.py   # ROS node + service callbacks (entry point)
├── delivery_task.py               # 5-step workflow + worker thread + continue signal
├── nav2_navigator.py              # Wrapper around Nav2 NavigateToPose action client
├── waypoints.py                   # Named map-frame waypoints
└── __init__.py
```

Responsibilities are separated so each module has one job:

| Module | What it does |
|---|---|
| `waypoints.py` | Just the coordinates — tune once, used everywhere |
| `nav2_navigator.py` | "Go to this pose" — knows nothing about coffee delivery |
| `delivery_task.py` | The state machine and worker thread that runs the delivery |
| `coffee_delivery_demo_node.py` | ROS plumbing: services, node lifecycle |

## Customizing waypoints

Edit `WAYPOINTS` in `coffee_delivery_demo/waypoints.py`. Each entry takes a position `(x, y)` and an orientation `(z, w)` in the map frame. The easiest way to capture coordinates is to drive the robot to the desired spot in RViz and read `/amcl_pose`:

```bash
ros2 topic echo /amcl_pose --once
```
