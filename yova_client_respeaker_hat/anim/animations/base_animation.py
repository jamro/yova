#!/usr/bin/env python3
from abc import ABC, abstractmethod
from typing import Optional
import time

class BaseAnimation(ABC):
    """Base class for all LED animations."""
    
    def __init__(self, led_strip):
        self.led_strip = led_strip
        self._running = False
        self._stop_requested = False
        self._brightness_scale = 1.0
    
    @property
    def name(self) -> str:
        """Return the name/ID of this animation."""
        return self.__class__.__name__.lower()
    
    def set_brightness_scale(self, scale: float):
        """Set brightness scale factor (0.0 to 1.0)."""
        self._brightness_scale = max(0.0, min(1.0, scale))

    @property
    def num_leds(self) -> int:
        """Return the number of LEDs in the strip."""
        return self.led_strip.num_leds
    
    @abstractmethod
    def _animate_frame(self) -> bool:
        """
        Animate one frame of the animation.
        
        Returns:
            True if animation should continue, False if it's complete
        """
        pass
    
    def play(self, repetitions: int = 1, frame_delay: float = 0.1) -> None:
        """
        Play the animation.
        
        Args:
            repetitions: Number of times to repeat (0 = infinite)
            frame_delay: Delay between frames in seconds
        """
        self._running = True
        self._stop_requested = False
        
        if repetitions == 0:
            # Infinite loop
            while self._running and not self._stop_requested:
                completed = not self._animate_frame()
                time.sleep(frame_delay)
                if completed:
                    self.reset()
        else:
            # Finite repetitions
            for _ in range(repetitions):
                while self._running and not self._stop_requested:
                    completed = not self._animate_frame()
                    time.sleep(frame_delay)
                    if completed:
                        break
                # Reset animation for next repetition
                if self._running and not self._stop_requested:
                    self.reset()
        
        self._running = False
        self.led_strip.off()
    
    def stop(self) -> None:
        """Stop the animation immediately."""
        self._running = False
        self._stop_requested = True
    
    @property
    def is_running(self) -> bool:
        """Check if animation is currently running."""
        return self._running
    
    def reset(self) -> None:
        """Reset animation to initial state."""
        self._stop_requested = False
        # Subclasses can override to reset their internal state

    def set_lights(self, colors):
        """Set the lights to the given colors and brightness."""
        self.led_strip.show(colors,  self._brightness_scale)