from queue import Queue
from collections import deque as Deque
from dotenv import load_dotenv
import os
import sys

from modules.decision_making.planner import Planner
from modules.processing.navigation.navigation import Navigation
from modules.sensor.sensor import SensoryModule
from modules.processing.HRI.HRI import HRI
from modules.processing.data.data_manager import DataModule

event_bus = Queue()
data_task_bus = Queue()
sensor_data = {}
shared_data = {}

api_key = ""
load_dotenv()
api_key = os.getenv("API_KEY")

if not api_key:
    print("error critico: falta la api_key en el archivo .env")
    exit()

planner = Planner(event_bus)
navigation = Navigation("Navigation", event_bus, sensor_data, data_task_bus, shared_data)
sensory = SensoryModule("Sensory", event_bus, sensor_data, data_task_bus, shared_data)
human_interaction = HRI("HRI", event_bus, sensor_data, api_key, data_task_bus, shared_data)
data_manager = DataModule("Data", event_bus, data_task_bus, shared_data)

planner.append_modules([navigation, sensory, human_interaction, data_manager])

planner.start()
navigation.start()
sensory.start()
human_interaction.start()
data_manager.start()

planner.join(60)
