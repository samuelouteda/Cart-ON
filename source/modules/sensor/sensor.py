from core.base_module import BaseModule
from core.event import Event

from services.audio_sensor import capture_audio

class SensoryModule(BaseModule):

    def loop(self):

        audio_data = capture_audio()

        if audio_data:

            self.publish_event(
                Event(
                    type="audio_captured",
                    data=audio_data,
                    source=self.name
                )
            )