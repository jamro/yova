import urwid
import sys
from yova_shared.event_emitter import EventEmitter


class YovaDevToolsUI(EventEmitter):
    def __init__(self):
        super().__init__()
        self.is_active = False
        self.setup_ui()
        
    def setup_ui(self):
        # Create the main push-to-talk button with padding to look like a button
        self.push_to_talk_button = urwid.Text(("push_to_talk_inactive", "  INACTIVE  "), align="center")
        button_box = urwid.LineBox(self.push_to_talk_button, title="Push-to-Talk")
        
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
            urwid.Divider(),
            instructions_text,
        ])
        
        # Create the main frame
        self.main_frame = urwid.Frame(
            body=urwid.Filler(self.main_pile, valign="middle"),
            footer=urwid.Text("Press Q to quit", align="center")
        )
        
        # Create the main loop
        self.loop = urwid.MainLoop(
            self.main_frame,
            palette=self.get_palette(),
            unhandled_input=self.handle_input
        )
        
    def get_palette(self):
        return [
            ("title", "white", "dark blue", "bold"),
            ("push_to_talk_label", "white", "default"),
            ("push_to_talk_value", "white", "default"),
            ("push_to_talk_active", "black", "light green", "bold"),
            ("push_to_talk_inactive", "white", "dark red", "bold"),
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
            # Emit active event
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.emit_event("push_to_talk_changed", {"status": "active", "is_active": True}))
                else:
                    loop.run_until_complete(self.emit_event("push_to_talk_changed", {"status": "active", "is_active": True}))
            except RuntimeError:
                # No event loop, create a new one
                asyncio.run(self.emit_event("push_to_talk_changed", {"status": "active", "is_active": True}))
        else:
            self.push_to_talk_button.set_text(("push_to_talk_inactive", "  INACTIVE  "))
            # Emit inactive event
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.emit_event("push_to_talk_changed", {"status": "inactive", "is_active": False}))
                else:
                    loop.run_until_complete(self.emit_event("push_to_talk_changed", {"status": "inactive", "is_active": False}))
            except RuntimeError:
                # No event loop, create a new one
                asyncio.run(self.emit_event("push_to_talk_changed", {"status": "inactive", "is_active": False}))
            
    def run(self):
        try:
            self.loop.run()
        except KeyboardInterrupt:
            pass
        finally:
            # Clean up terminal
            sys.stdout.write("\033[?25h")  # Show cursor
            sys.stdout.flush()
