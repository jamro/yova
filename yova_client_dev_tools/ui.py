import urwid
import sys
import asyncio
from yova_shared.event_emitter import EventEmitter


class YovaDevToolsUI(EventEmitter):
    def __init__(self):
        super().__init__()
        self.is_active = False
        self._state = "unknown"  # Add state field
        self._question = ""  # Add question field
        self._answer = ""    # Add answer field
        self._question_time = 0  # Add question time field (in ms)
        self._answer_time = 0    # Add answer time field (in ms)
        self.setup_ui()
        
    def setup_ui(self):
        # Create the main push-to-talk button with padding to look like a button
        self.push_to_talk_button = urwid.Text(("push_to_talk_inactive", "  INACTIVE  "), align="center")
        button_box = urwid.LineBox(self.push_to_talk_button, title="Push-to-Talk")
        
        # Create state display
        self.state_display = urwid.Text(("state_value", "unknown"), align="center")
        state_box = urwid.LineBox(self.state_display, title="Current State")
        
        # Place state and push-to-talk in the same row since they are short fields
        controls_row = urwid.Columns([
            state_box,      # State fills available width
            button_box,     # Push-to-talk fills available width
        ], dividechars=1)  # Add divider between columns
        
        # Create question and answer fields (grouped together)
        self.question_display = urwid.Text(("question_value", ""), align="left")
        self.answer_display = urwid.Text(("answer_value", ""), align="left")
        
        # Group question and answer in a single box
        qa_content = urwid.Pile([
            urwid.Text(("qa_label", "Question:"), align="left"),
            self.question_display,
            urwid.Divider(),
            urwid.Text(("qa_label", "Answer:"), align="left"),
            self.answer_display,
        ])
        qa_box = urwid.LineBox(qa_content, title="Q&A")
        
        # Create response time fields in one row for compact design
        self.question_time_display = urwid.Text(("time_value", "0 ms"), align="center")
        self.answer_time_display = urwid.Text(("time_value", "0 ms"), align="center")
        
        question_time_box = urwid.LineBox(self.question_time_display, title="Question Time")
        answer_time_box = urwid.LineBox(self.answer_time_display, title="Answer Time")
        
        # Place response times in the same row
        time_row = urwid.Columns([
            question_time_box,  # Question time fills available width
            answer_time_box,    # Answer time fills available width
        ], dividechars=1)      # Add divider between columns
        
        # Create title and instructions
        title_text = urwid.Text(("title", "YOVA Development Tools"), align="center")
        instructions_text = urwid.Text(("instructions", "Press SPACEBAR to toggle, T to submit test question"), align="center")
        
        # Create the main pile widget
        self.main_pile = urwid.Pile([
            title_text,
            urwid.Divider(),
            urwid.Text("", align="center"),  # Spacer
            controls_row,  # State and push-to-talk in same row
            urwid.Text("", align="center"),  # Spacer
            qa_box,
            urwid.Text("", align="center"),  # Spacer
            time_row,      # Response times in same row
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
            ("question_value", "white", "default"),
            ("answer_value", "white", "default"),
            ("qa_label", "yellow", "default"),
            ("time_value", "white", "dark green", "bold"),
            ("instructions", "yellow", "default"),
            ("info", "light blue", "default"),
            ("footer", "white", "dark blue"),
        ]
        
    def handle_input(self, key):
        if key == " ":
            self.toggle_push_to_talk()
        elif key == "t":
            self.ask_test_question()
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
    
    def ask_test_question(self):
        asyncio.create_task(self.emit_event("test_question", {}))
    
    # State getter and setter methods
    def get_state(self) -> str:
        """Get the current state"""
        return self._state
    
    def set_state(self, state: str):
        """Set the current state and update the UI"""
        self._state = state
        self.state_display.set_text(("state_value", state))
    
    # Question getter and setter methods
    def get_question(self) -> str:
        """Get the current question"""
        return self._question
    
    def set_question(self, question: str):
        """Set the current question and update the UI"""
        self._question = question
        self.question_display.set_text(("question_value", question))
    
    # Answer getter and setter methods
    def get_answer(self) -> str:
        """Get the current answer"""
        return self._answer
    
    def set_answer(self, answer: str):
        """Set the current answer and update the UI"""
        self._answer = answer
        self.answer_display.set_text(("answer_value", answer))
    
    # Question time getter and setter methods
    def get_question_time(self) -> int:
        """Get the current question time in milliseconds"""
        return self._question_time
    
    def set_question_time(self, question_time: int):
        """Set the current question time in milliseconds and update the UI"""
        self._question_time = question_time
        self.question_time_display.set_text(("time_value", f"{question_time} ms"))
    
    # Answer time getter and setter methods
    def get_answer_time(self) -> int:
        """Get the current answer time in milliseconds"""
        return self._answer_time
    
    def set_answer_time(self, answer_time: int):
        """Set the current answer time in milliseconds and update the UI"""
        self._answer_time = answer_time
        self.answer_time_display.set_text(("time_value", f"{answer_time} ms"))
            
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
