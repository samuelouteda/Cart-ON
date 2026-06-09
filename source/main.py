from queue import Queue
from collections import deque as Deque
from dotenv import load_dotenv
import os
import sys

linux_mode = 1
if sys.platform.startswith("linux"):
    linux_mode = 1

if linux_mode:
    import rclpy
    rclpy.init()
    from modules.processing.navigation.ros_module import ROSModule

from modules.decision_making.planner import Planner
from modules.processing.navigation.navigation import Navigation
from modules.processing.HRI.HRI import HRI
from modules.processing.data.data_manager import DataModule
from modules.sensor.sensor import SensoryModule

event_bus = Queue()
data_task_bus = Queue()
sensor_data = {}
shared_data = {}

api_key = ""
load_dotenv()
api_key = os.getenv("API_KEY")

if not api_key:
    print("Error critico: falta la api_key en el archivo .env")
    exit()

planner = Planner(event_bus)
navigation = Navigation("Navigation", event_bus, sensor_data, data_task_bus, shared_data)
#sensory = SensoryModule("Sensory", event_bus, sensor_data, data_task_bus, shared_data)
#human_interaction = HRI("HRI", event_bus, sensor_data, api_key, data_task_bus, shared_data)
data_manager = DataModule("Data", event_bus, data_task_bus, shared_data)

planner.append_modules([navigation, data_manager])
#planner.append_modules([navigation, sensory, human_interaction, data_manager])

if linux_mode:
    ros_module = ROSModule("ROS", event_bus, shared_data)
    planner.append_single_module(ros_module)

planner.start()
navigation.start()
#sensory.start()
#human_interaction.start()
data_manager.start()

if linux_mode:
    ros_module.start()

planner.join()

if linux_mode:
    rclpy.shutdown()