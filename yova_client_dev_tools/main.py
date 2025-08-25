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
        
        await publisher.publish("input", {
            "active": event_data["is_active"],
            "timestamp": asyncio.get_event_loop().time()
        })
            
    except Exception as e:
        print(f"Failed to publish to broker: {e}")
    finally:
        await publisher.close()

async def test_question_callback(event_data):
    """Callback for test question events - publishes to broker"""
    publisher = Publisher()
    await publisher.connect()
    await publisher.publish("voice_command_detected", {
        "id": str(uuid.uuid4()),
        "transcript": "Jaka jest stolica Polski?",
        "timestamp": asyncio.get_event_loop().time()
    })

async def subscribe_to_updates(ui):
    global answer, chunk_counter
    async def on_message(topic, data):
        global answer, chunk_counter
        
        # state ========================================================================
        if topic == "state":
            ui.set_state(data['new_state'])
            ui.loop.draw_screen()

        # voice command detected ================================================================
        if topic == "voice_command_detected":
            ui.set_question(data['transcript'])
            answer = ""
            ui.set_answer(answer)
            ui.loop.draw_screen()

        # voice response ================================================================
        if topic == "voice_response":
            if data['type'] == 'chunk':
                answer += data['content']
                chunk_counter += 1
            elif data['type'] == 'completed':
                answer = data['content']
                chunk_counter = 0
            ui.set_answer(answer[:100] + "...")
            ui.loop.draw_screen()

    subsciber = Subscriber()
    await subsciber.connect()
    await subsciber.subscribe_all(["state", "voice_command_detected", "voice_response"])
    asyncio.create_task(subsciber.listen(on_message))
    
def main():
    """Main entry point for the YOVA Development Tools UI."""
    ui = YovaDevToolsUI()
    profiler = Profiler(ui)
    ui.add_event_listener("push_to_talk_changed", push_to_talk_changed_callback)
    ui.add_event_listener("test_question", test_question_callback)
    ui.set_state("Unknown")

    asyncio.ensure_future(profiler.start())
    asyncio.ensure_future(subscribe_to_updates(ui))

    ui.run()

def run():
    """Synchronous wrapper for the main function."""
    main()

if __name__ == "__main__":
    run()
