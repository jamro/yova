from yova_client_dev_tools.ui import YovaDevToolsUI
from yova_shared.broker.subscriber import Subscriber
from yova_client_dev_tools.profiler import Profiler
from yova_shared.broker.publisher import Publisher
import uuid
import asyncio

answer = ''
input_timestamp = None
answer_timestamp = None
chunk_counter = 0

async def push_to_talk_changed_callback(event_data):
    """Callback for push-to-talk change events - publishes to broker"""

    publisher = Publisher()
    try:
        await publisher.connect()
        
        await publisher.publish("dev_tools", "yova.core.input.state", {
            "active": event_data["is_active"]
        })
            
    except Exception as e:
        print(f"Failed to publish to broker: {e}")
    finally:
        await publisher.close()

async def test_question_callback(event_data):
    """Callback for test question events - publishes to broker"""
    publisher = Publisher()
    await publisher.connect()
    await publisher.publish("dev_tools", "yova.api.asr.result", {
        "id": str(uuid.uuid4()),
        "transcript": "Jaka jest stolica Polski?"
    })

async def test_error_callback(event_data):
    publisher = Publisher()
    await publisher.connect()
    await publisher.publish("dev_tools", "yova.core.error", {
        "error": "Test error",
        "details": "Test error details"
    })

async def subscribe_to_updates(ui):
    global answer, chunk_counter
    async def on_message(topic, message):
        data = message['data']
        global answer, chunk_counter
        
        # yova.core.state.change ========================================================================
        if topic == "yova.core.state.change":
            ui.set_state(data['new_state'])
            ui.loop.draw_screen()

        # yova.api.asr.result ================================================================
        if topic == "yova.api.asr.result":
            ui.set_question(data['transcript'])
            answer = ""
            ui.set_answer(answer)
            ui.loop.draw_screen()

        # yova.api.tts.chunk ================================================================
        if topic == "yova.api.tts.chunk":
            answer += data['content']
            chunk_counter += 1
            ui.set_answer(answer[:100] + "...")
            ui.loop.draw_screen()

        # yova.api.tts.complete ================================================================
        if topic == "yova.api.tts.complete":
            answer = data['content']
            chunk_counter = 0
            ui.set_answer(answer[:100] + "...")
            ui.loop.draw_screen()

        # yova.*.error ================================================================
        if topic == "yova.core.error" or topic == "yova.api.error":
            ui.set_error_message(data['error'])
            ui.loop.draw_screen()

    subsciber = Subscriber()
    await subsciber.connect()
    await subsciber.subscribe_all([
        "yova"
    ])
    asyncio.create_task(subsciber.listen(on_message))
    
def main():
    """Main entry point for the YOVA Development Tools UI."""
    ui = YovaDevToolsUI()
    profiler = Profiler(ui)
    ui.add_event_listener("push_to_talk_changed", push_to_talk_changed_callback)
    ui.add_event_listener("test_question", test_question_callback)
    ui.add_event_listener("test_error", test_error_callback)
    ui.set_state("Unknown")

    asyncio.ensure_future(profiler.start())
    asyncio.ensure_future(subscribe_to_updates(ui))

    ui.run()

def run():
    """Synchronous wrapper for the main function."""
    main()

if __name__ == "__main__":
    run()
