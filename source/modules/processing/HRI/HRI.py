from core.base_module import BaseModule
from core.event import Event

from services.speech_processing import (
    speech_to_text,
    parse_intent,
    text_to_speech
)

#from services.speaker_service import play_audio
from actuation.speaker import play_audio


import os


class HRIModule(BaseModule):

    def __init__(self, name, event_bus, api_key):

        super().__init__(name, event_bus)

        self.api_key = api_key

    def handle_event(self, event):

        if event.type == "audio_captured":

            audio_data = event.data

            raw_text = speech_to_text(
                audio_data,
                self.api_key
            )

            if not raw_text:
                return

            intent, item, quantity = parse_intent(raw_text)

            self.publish_event(
                Event(
                    type="voice_command",
                    data={
                        "intent": intent,
                        "item": item,
                        "quantity": quantity,
                        "raw_text": raw_text
                    },
                    source=self.name
                )
            )

        elif event.type == "speak":

            text = event.data

            audio_bytes = text_to_speech(
                text,
                self.api_key
            )

            if audio_bytes:
                play_audio(audio_bytes)