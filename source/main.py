import os
from dotenv import load_dotenv

from core.event_bus import EventBus

from modules.decision_making.planner.planner import Planner
from modules.processing.HRI.HRI import HRIModule
from modules.sensor.sensor import SensoryModule
from modules.processing.data.data_manager import DataModule

def main():

    # =========================
    # Load environment
    # =========================

    load_dotenv()

    api_key = os.getenv("API_KEY")

    if not api_key:
        raise Exception(
            "Missing API_KEY in .env"
        )

    # =========================
    # Create Event Bus
    # =========================

    event_bus = EventBus()

    # =========================
    # Create Modules
    # =========================

    planner = Planner(
        name="Planner",
        event_bus=event_bus
    )

    hri = HRIModule(
        name="HRI",
        event_bus=event_bus,
        api_key=api_key
    )

    sensory = SensoryModule(
        name="Sensory",
        event_bus=event_bus
    )

    data_module = DataModule(
        name="Data",
        event_bus=event_bus
    )

    # =========================
    # Register Subscriptions
    # =========================

    # HRI receives audio
    event_bus.subscribe(
        "audio_captured",
        hri
    )

    # Planner receives parsed commands
    event_bus.subscribe(
        "voice_command",
        planner
    )

    # Data module updates shopping list
    event_bus.subscribe(
        "add_item",
        data_module
    )

    event_bus.subscribe(
        "clear_list",
        data_module
    )

    # HRI speaks messages
    event_bus.subscribe(
        "speak",
        hri
    )

    # =========================
    # Start Modules
    # =========================

    modules = [
        planner,
        hri,
        sensory,
        data_module
    ]

    for module in modules:

        print(f"Starting {module.name}")

        module.start()

    # =========================
    # Initial greeting
    # =========================

    from core.event import Event

    event_bus.publish(
        Event(
            type="speak",
            data="Sistema iniciado. Dime qué necesitas.",
            source="main"
        )
    )

    # =========================
    # Keep alive
    # =========================

    try:

        for module in modules:
            module.join()

    except KeyboardInterrupt:

        print("\nShutting down...")

        for module in modules:
            module.running = False


if __name__ == "__main__":
    main()