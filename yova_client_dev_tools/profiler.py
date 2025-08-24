from yova_shared.event_emitter import EventEmitter
from yova_shared.broker.subscriber import Subscriber
import asyncio

class Profiler():
    def __init__(self, ui):
        self.ui = ui
        self.input_subscriber = Subscriber()
        self.audio_subscriber = Subscriber()
        self.voice_response_subscriber = Subscriber()
        self.voice_command_detected_subscriber = Subscriber()
        self.input_time = 0
        self.question_time = 0
        self.answer_time = 0
        self.voice_response_completed = True

    async def start(self):
        await self.input_subscriber.connect()
        await self.input_subscriber.subscribe("input")
        asyncio.create_task(self.input_subscriber.listen(self.on_input))

        await self.audio_subscriber.connect()
        await self.audio_subscriber.subscribe("audio")
        asyncio.create_task(self.audio_subscriber.listen(self.on_audio))

        await self.voice_response_subscriber.connect()
        await self.voice_response_subscriber.subscribe("voice_response")
        asyncio.create_task(self.voice_response_subscriber.listen(self.on_voice_response))

        await self.voice_command_detected_subscriber.connect()
        await self.voice_command_detected_subscriber.subscribe("voice_command_detected")
        asyncio.create_task(self.voice_command_detected_subscriber.listen(self.on_voice_command_detected))

    async def on_input(self, topic, data):
        if data['active']:
            self.input_time = data['timestamp']
        else:
            self.question_time = data['timestamp']

    async def on_voice_command_detected(self, topic, data):
        if self.question_time is not None:
            dt = data['timestamp'] - self.question_time
            self.question_time = None
            self.ui.set_question_time(round(dt*1000))
            self.ui.loop.draw_screen()

    async def on_audio(self, topic, data):
        if data['type'] == "recording":
            if self.input_time is not None:
                dt = data['timestamp'] - self.input_time
                self.input_time = None
                self.ui.set_input_time(round(dt*1000))
                self.ui.loop.draw_screen()
        elif data['type'] == "playing":
            if self.answer_time is not None:
                dt = data['timestamp'] - self.answer_time
                self.answer_time = None
                self.ui.set_answer_time(round(dt*1000))
                self.ui.loop.draw_screen()

    async def on_voice_response(self, topic, data):
        if data['type'] == "chunk":
            if self.voice_response_completed:
                self.voice_response_completed = False
                self.answer_time = data['timestamp']
        elif data['type'] == "completed":
            self.voice_response_completed = True