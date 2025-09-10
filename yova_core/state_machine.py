from yova_shared import get_clean_logger
from enum import Enum
from yova_shared import EventEmitter
import asyncio
from yova_core.cost_tracker import CostTracker

# define states as enum 
class State(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    SPEAKING = "speaking"

class StateMachine(EventEmitter):

    def __init__(self, logger, speech_handler, transcriber, cost_tracker=None):
        super().__init__(logger)
        self.logger = get_clean_logger("state_machine", logger)
        self.state = State.IDLE
        self.transcriber = transcriber
        self.speech_handler = speech_handler
        self.speech_handler.add_event_listener("message_completed", self.on_speech_completed)
        self.cost_tracker = cost_tracker or CostTracker(logger)

    def get_state(self):
        return self.state
    
    async def start(self):
        await self.speech_handler.start()
        await self.transcriber.initialize()

    async def close(self):
        await self.speech_handler.stop()
        await self.transcriber.cleanup()
    
    async def _set_state(self, new_state):
        if self.state == new_state:
            return
        previous_state = self.state
        self.state = new_state
        await self.emit_event("state_changed", {"previous_state": previous_state.value, "new_state": new_state.value})

    # transition triggers ======================================================
    async def on_speech_completed(self, data):
        if self.state == State.IDLE:
            pass # already idle
        elif self.state == State.LISTENING:
            pass # ignore
        elif self.state == State.SPEAKING:
            await self._set_state(State.IDLE)
        else:
            raise Exception("Invalid state " + self.state)

    async def on_response_chunk(self, id, text, priority_score=0):
        if self.state == State.IDLE:
            if self.cost_tracker.is_budget_exceeded():
                await self.emit_event("error", {
                    "error": "Budget exceeded",
                    "details": "Unable to process response chunk due to budget exceeded"
                })
                return
            await self._set_state(State.SPEAKING)
            await self.speech_handler.process_chunk(id, text, priority_score)
        elif self.state == State.LISTENING:
            await self.speech_handler.terminate_all_tasks()
            self.speech_handler.ignore_message(id)
        elif self.state == State.SPEAKING:
            await self.speech_handler.process_chunk(id, text, priority_score)
        else:
            raise Exception("Invalid state " + self.state)

    async def on_response_complete(self, id, text):
        if self.state == State.IDLE:
            await self._set_state(State.SPEAKING)
            await self.speech_handler.process_complete(id, text)
        elif self.state == State.LISTENING:
            await self.speech_handler.terminate_all_tasks()
            self.speech_handler.ignore_message(id)
        elif self.state == State.SPEAKING:
            await self.speech_handler.process_complete(id, text)
        else:
            raise Exception("Invalid state " + self.state)

    async def on_input_activated(self):
        if self.cost_tracker.is_budget_exceeded():
            await self.emit_event("error", {
                "error": "Budget exceeded",
                "details": "Unable to start listening due to budget exceeded"
            })
            return

        if self.state == State.IDLE:
            await self._set_state(State.LISTENING)
            await self.transcriber.start_listening()
        elif self.state == State.LISTENING:
            pass # already listening
        elif self.state == State.SPEAKING:
            await self.speech_handler.terminate_all_tasks()
            await self._set_state(State.LISTENING)
            await self.transcriber.start_listening()
        else:
            raise Exception("Invalid state " + self.state)
    
    async def on_input_deactivated(self):
        if self.state == State.IDLE:
            pass # already idle
        elif self.state == State.LISTENING:
            await self._set_state(State.IDLE)
            await self.transcriber.stop_listening()
        elif self.state == State.SPEAKING:
            await self.speech_handler.terminate_all_tasks()
            await self.transcriber.stop_listening()
        else:
            raise Exception("Invalid state " + self.state)