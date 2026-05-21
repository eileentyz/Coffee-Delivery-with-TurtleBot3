"""
Coffee delivery workflow.

Owns the long-running delivery state machine, the worker thread, and the
"continue" signal used to advance past waiting steps. Knows nothing about
ROS services — the node layer wires those up.
"""

import threading

import rclpy

from coffee_delivery_demo.nav2_navigator import Nav2Navigator
from coffee_delivery_demo.waypoints import WAYPOINTS


class DeliveryTask:
    def __init__(self, node, navigator: Nav2Navigator):
        self._node = node
        self._logger = node.get_logger()
        self._navigator = navigator

        self._task_running = False
        self._continue_event = threading.Event()

    @property
    def is_running(self) -> bool:
        return self._task_running

    @property
    def has_pending_continue(self) -> bool:
        """True if a continue signal has been set but not yet consumed."""
        return self._continue_event.is_set()

    def start(self) -> bool:
        """Start a new delivery in a worker thread. Returns False if one is
        already running."""
        if self._task_running:
            return False
        self._task_running = True
        self._continue_event.clear()
        threading.Thread(target=self._run, daemon=True).start()
        return True

    def signal_continue(self) -> None:
        self._continue_event.set()

    def _wait_for_user(self, message: str) -> None:
        self._logger.info(message)
        self._continue_event.clear()
        while rclpy.ok() and not self._continue_event.is_set():
            self._continue_event.wait(timeout=0.1)

    def _run(self) -> None:
        try:
            self._run_workflow()
        except Exception as e:
            self._logger.error(f'Coffee delivery task failed: {e}')
        finally:
            self._task_running = False
            self._continue_event.set()

    def _run_workflow(self) -> None:
        self._logger.info('Coffee delivery task started.')

        # Step 1: Go to coffee station
        self._logger.info('Task status: GOING_TO_COFFEE_STATION')
        if not self._navigator.go_to('coffee_station', WAYPOINTS['coffee_station']):
            self._logger.error('Failed to reach coffee station. Task aborted.')
            return

        # Step 2: Wait for coffee loading
        self._logger.info('Task status: WAITING_FOR_COFFEE_LOADING')
        self._wait_for_user(
            'Call /continue_coffee_delivery once coffee is loaded...'
        )

        # Step 3: Go to delivery point
        self._logger.info('Task status: GOING_TO_DELIVERY_POINT')
        if not self._navigator.go_to('delivery_point', WAYPOINTS['delivery_point']):
            self._logger.error('Failed to reach delivery point. Task aborted.')
            return

        # Step 4: Wait for recipient confirmation
        self._logger.info('Task status: WAITING_FOR_COFFEE_DELIVERY_CONFIRMATION')
        self._logger.info('Coffee delivered successfully!')
        self._wait_for_user(
            'Call /continue_coffee_delivery once recipient has collected the coffee...'
        )

        # Step 5: Return home
        self._logger.info('Task status: RETURNING_HOME')
        if not self._navigator.go_to('home', WAYPOINTS['home']):
            self._logger.error('Failed to return home. Task ended with error.')
            return

        # Step 6: Complete task
        self._logger.info('Task status: COMPLETED')
        self._logger.info('Robot returned home.')
        self._logger.info('Coffee delivery task completed.')
