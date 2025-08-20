from yova_dev_tools.ui import YovaDevToolsUI
from yova_shared.broker.publisher import Publisher
import asyncio
from yova_shared.broker.subscriber import Subscriber


async def push_to_talk_changed_callback(event_data):
    """Callback for push-to-talk change events - publishes to broker"""
    publisher = Publisher()
    try:
        await publisher.connect()
        
        await publisher.publish("input", {"active": event_data["is_active"]})
            
    except Exception as e:
        print(f"Failed to publish to broker: {e}")
    finally:
        await publisher.close()

async def subscribe_to_updates(ui):
    async def on_state_changed(topic, data):
        ui.set_state(data['new_state'])
        ui.loop.draw_screen()

    input_subsciber = Subscriber()
    await input_subsciber.connect()
    await input_subsciber.subscribe("state")
    asyncio.create_task(input_subsciber.listen(on_state_changed))

def main():
    """Main entry point for the YOVA Development Tools UI."""
    ui = YovaDevToolsUI()
    ui.add_event_listener("push_to_talk_changed", push_to_talk_changed_callback)
    ui.set_state("Unknown")

    asyncio.ensure_future(subscribe_to_updates(ui))

    ui.run()

def run():
    """Synchronous wrapper for the main function."""
    main()

if __name__ == "__main__":
    run()
