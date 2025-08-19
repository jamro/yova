from yova_dev_tools.ui import YovaDevToolsUI
from yova_shared.broker.publisher import Publisher

async def status_changed_callback(event_data):
    """Callback for status change events - publishes to broker"""
    publisher = Publisher()
    try:
        await publisher.connect()
        
        await publisher.publish("input", {"active": event_data["is_active"]})
            
    except Exception as e:
        print(f"Failed to publish to broker: {e}")
    finally:
        await publisher.close()

def main():
    """Main entry point for the YOVA Development Tools UI."""
    ui = YovaDevToolsUI()
    
    # Register callback for status change events
    ui.add_event_listener("status_changed", status_changed_callback)
    
    ui.run()

def run():
    """Synchronous wrapper for the main function."""
    main()

if __name__ == "__main__":
    run()
