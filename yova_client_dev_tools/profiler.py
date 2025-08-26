from yova_shared.event_emitter import EventEmitter
from yova_shared.broker.subscriber import Subscriber
import asyncio

class Profiler():
    def __init__(self, ui):
        self.ui = ui
        self.subscriber = Subscriber()
        self.input_time = 0
        self.question_time = 0
        self.answer_time = 0
        self.voice_response_completed = True

    async def start(self):
        await self.subscriber.connect()
        await self.subscriber.subscribe_all([
            "yova.core.input.state", 
            "yova.core.audio.play.start", 
            "yova.core.audio.record.start", 
            "yova.api.tts.chunk", 
            "yova.api.tts.complete", 
            "yova.api.asr.result"
        ])
        asyncio.create_task(self.subscriber.listen(self.on_message))

    async def on_message(self, topic, data):
        if topic == "yova.core.input.state":
            await self.on_input(topic, data)
        elif topic == "yova.core.audio.play.start":
            await self.on_audio_play_start(topic, data)
        elif topic == "yova.core.audio.record.start":
            await self.on_audio_record_start(topic, data)
        elif topic == "yova.api.tts.chunk":
            await self.on_tts_chunk(topic, data)
        elif topic == "yova.api.tts.complete":
            await self.on_tts_complete(topic, data)
        elif topic == "yova.api.asr.result":
            await self.on_asr_result(topic, data)

    async def on_input(self, topic, data):
        if data['active']:
            self.input_time = data['timestamp']
        else:
            self.question_time = data['timestamp']

    async def on_asr_result(self, topic, data):
        if self.question_time is not None:
            dt = data['timestamp'] - self.question_time
            self.question_time = None
            self.ui.set_question_time(round(dt*1000))
            self.ui.loop.draw_screen()

    async def on_audio_play_start(self, topic, data):
        if self.answer_time is not None:
            dt = data['timestamp'] - self.answer_time
            self.answer_time = None
            self.ui.set_answer_time(round(dt*1000))
            self.ui.loop.draw_screen()

    async def on_audio_record_start(self, topic, data):
        if self.input_time is not None:
            dt = data['timestamp'] - self.input_time
            self.input_time = None
            self.ui.set_input_time(round(dt*1000))
            self.ui.loop.draw_screen()

    async def on_tts_chunk(self, topic, data):
        if self.voice_response_completed:
            self.voice_response_completed = False
            self.answer_time = data['timestamp']

    async def on_tts_complete(self, topic, data):
        self.voice_response_completed = True
