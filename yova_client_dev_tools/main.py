from yova_client_dev_tools.ui import YovaDevToolsUI
from yova_shared.broker.publisher import Publisher
import asyncio
from yova_shared.broker.subscriber import Subscriber
import uuid

answer = ''
input_timestamp = None
answer_timestamp = None
chunk_counter = 0

async def push_to_talk_changed_callback(event_data):
    """Callback for push-to-talk change events - publishes to broker"""
    global input_timestamp

    publisher = Publisher()
    try:
        await publisher.connect()

        if event_data["is_active"] == False:
            input_timestamp = asyncio.get_event_loop().time()
        
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
    global answer, input_timestamp, answer_timestamp, chunk_counter
    async def on_state_changed(topic, data):
        ui.set_state(data['new_state'])
        ui.loop.draw_screen()

    input_subsciber = Subscriber()
    await input_subsciber.connect()
    await input_subsciber.subscribe("state")
    asyncio.create_task(input_subsciber.listen(on_state_changed))

    async def on_audio(topic, data):
        global answer_timestamp
        if data['type'] == "playing":
            if answer_timestamp is not None:
                dt = asyncio.get_event_loop().time() - answer_timestamp
                answer_timestamp = None
                ui.set_answer_time(round(dt*1000))

    audio_subsciber = Subscriber()
    await audio_subsciber.connect()
    await audio_subsciber.subscribe("audio")
    asyncio.create_task(audio_subsciber.listen(on_audio))

    async def on_voice_command(topic, data):
        global answer, input_timestamp
        ui.set_question(data['transcript'])
        answer = ""
        ui.set_answer(answer)
        if input_timestamp is not None:
            dt = asyncio.get_event_loop().time() - input_timestamp
            input_timestamp = None
            ui.set_question_time(round(dt*1000))
        ui.loop.draw_screen()

    voice_command_subsciber = Subscriber()
    await voice_command_subsciber.connect()
    await voice_command_subsciber.subscribe("voice_command_detected")
    asyncio.create_task(voice_command_subsciber.listen(on_voice_command))

    async def on_voice_response(topic, data):
        global answer, answer_timestamp, chunk_counter
        if data['type'] == 'chunk':
            answer += data['text']
            chunk_counter += 1
        elif data['type'] == 'completed':
            answer = data['text']
            chunk_counter = 0
        ui.set_answer(answer[:100] + "...")
        if answer_timestamp is None and chunk_counter == 1:
            answer_timestamp = asyncio.get_event_loop().time()
        ui.loop.draw_screen()

    voice_response_subsciber = Subscriber()
    await voice_response_subsciber.connect()
    await voice_response_subsciber.subscribe("voice_response")
    asyncio.create_task(voice_response_subsciber.listen(on_voice_response))
    
def main():
    """Main entry point for the YOVA Development Tools UI."""
    ui = YovaDevToolsUI()
    ui.add_event_listener("push_to_talk_changed", push_to_talk_changed_callback)
    ui.add_event_listener("test_question", test_question_callback)
    ui.set_state("Unknown")

    asyncio.ensure_future(subscribe_to_updates(ui))

    ui.run()

def run():
    """Synchronous wrapper for the main function."""
    main()

if __name__ == "__main__":
    run()
