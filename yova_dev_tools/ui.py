import urwid
import sys
from yova_shared.event_emitter import EventEmitter


class YovaDevToolsUI(EventEmitter):
    def __init__(self):
        super().__init__()
        self.is_active = False
        self.setup_ui()
        
    def setup_ui(self):
        # Create the main status button with padding to look like a button
        self.status_button = urwid.Text(("status_inactive", "  INACTIVE  "), align="center")
        button_box = urwid.LineBox(self.status_button, title="Status")
        
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
            ("status_label", "white", "default"),
            ("status_value", "white", "default"),
            ("status_active", "black", "light green", "bold"),
            ("status_inactive", "white", "dark red", "bold"),
            ("instructions", "yellow", "default"),
            ("info", "light blue", "default"),
            ("footer", "white", "dark blue"),
        ]
        
    def handle_input(self, key):
        if key == " ":
            self.toggle_status()
        elif key in ("q", "Q"):
            raise urwid.ExitMainLoop()
            
    def toggle_status(self):
        self.is_active = not self.is_active
        
        if self.is_active:
            self.status_button.set_text(("status_active", "  ACTIVE   "))
            # Emit active event
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.emit_event("status_changed", {"status": "active", "is_active": True}))
                else:
                    loop.run_until_complete(self.emit_event("status_changed", {"status": "active", "is_active": True}))
            except RuntimeError:
                # No event loop, create a new one
                asyncio.run(self.emit_event("status_changed", {"status": "active", "is_active": True}))
        else:
            self.status_button.set_text(("status_inactive", "  INACTIVE  "))
            # Emit inactive event
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.emit_event("status_changed", {"status": "inactive", "is_active": False}))
                else:
                    loop.run_until_complete(self.emit_event("status_changed", {"status": "inactive", "is_active": False}))
            except RuntimeError:
                # No event loop, create a new one
                asyncio.run(self.emit_event("status_changed", {"status": "inactive", "is_active": False}))
            
    def run(self):
        try:
            self.loop.run()
        except KeyboardInterrupt:
            pass
        finally:
            # Clean up terminal
            sys.stdout.write("\033[?25h")  # Show cursor
            sys.stdout.flush()
