import urwid
import sys
import asyncio
from yova_shared.event_emitter import EventEmitter


class YovaDevToolsUI(EventEmitter):
    def __init__(self):
        super().__init__()
        self.is_active = False
        self._state = "unknown"  # Add state field
        self.setup_ui()
        
    def setup_ui(self):
        # Create the main push-to-talk button with padding to look like a button
        self.push_to_talk_button = urwid.Text(("push_to_talk_inactive", "  INACTIVE  "), align="center")
        button_box = urwid.LineBox(self.push_to_talk_button, title="Push-to-Talk")
        
        # Create state display
        self.state_display = urwid.Text(("state_value", "unknown"), align="center")
        state_box = urwid.LineBox(self.state_display, title="Current State")
        
        # Create title and instructions
        title_text = urwid.Text(("title", "YOVA Development Tools"), align="center")
        instructions_text = urwid.Text(("instructions", "Press SPACEBAR to toggle"), align="center")
        
        # Create the main pile widget
        self.main_pile = urwid.Pile([
            title_text,
            urwid.Divider(),
            urwid.Text("", align="center"),  # Spacer
            button_box,
            urwid.Text("", align="center"),  # Spacer
            state_box,
            urwid.Text("", align="center"),  # Spacer
            urwid.Divider(),
            instructions_text,
        ])
        
        # Create the main frame
        self.main_frame = urwid.Frame(
            body=urwid.Filler(self.main_pile, valign="middle"),
            footer=urwid.Text("Press Q to quit", align="center")
        )
        
        # Create the main loop using AsyncioEventLoop for async integration
        self.loop = urwid.MainLoop(
            self.main_frame,
            palette=self.get_palette(),
            unhandled_input=self.handle_input,
            event_loop=urwid.AsyncioEventLoop(loop=asyncio.get_event_loop())
        )
        
    def get_palette(self):
        return [
            ("title", "white", "dark blue", "bold"),
            ("push_to_talk_label", "white", "default"),
            ("push_to_talk_value", "white", "default"),
            ("push_to_talk_active", "black", "light green", "bold"),
            ("push_to_talk_inactive", "white", "dark red", "bold"),
            ("state_value", "white", "dark blue", "bold"),
            ("instructions", "yellow", "default"),
            ("info", "light blue", "default"),
            ("footer", "white", "dark blue"),
        ]
        
    def handle_input(self, key):
        if key == " ":
            self.toggle_push_to_talk()
        elif key in ("q", "Q"):
            raise urwid.ExitMainLoop()
            
    def toggle_push_to_talk(self):
        self.is_active = not self.is_active
        
        if self.is_active:
            self.push_to_talk_button.set_text(("push_to_talk_active", "  PRESSED  "))
            # Emit active event - now simpler with AsyncioEventLoop
            asyncio.create_task(self.emit_event("push_to_talk_changed", {"status": "active", "is_active": True}))
        else:
            self.push_to_talk_button.set_text(("push_to_talk_inactive", "  INACTIVE  "))
            # Emit inactive event - now simpler with AsyncioEventLoop
            asyncio.create_task(self.emit_event("push_to_talk_changed", {"status": "inactive", "is_active": False}))
    
    # State getter and setter methods
    def get_state(self) -> str:
        """Get the current state"""
        return self._state
    
    def set_state(self, state: str):
        """Set the current state and update the UI"""
        self._state = state
        self.state_display.set_text(("state_value", state))
            
    def run(self):
        try:
            self.loop.run()
        except KeyboardInterrupt:
            pass
        finally:
            # Clean up terminal
            sys.stdout.write("\033[?25h")  # Show cursor
            sys.stdout.flush()
            
    async def run_async(self):
        """Alternative async method to run the UI"""
        try:
            # For MainLoop with AsyncioEventLoop, we can just call run()
            # The event loop will be handled by the AsyncioEventLoop
            self.loop.run()
        except KeyboardInterrupt:
            pass
        finally:
            # Clean up terminal
            sys.stdout.write("\033[?25h")  # Show cursor
            sys.stdout.flush()
