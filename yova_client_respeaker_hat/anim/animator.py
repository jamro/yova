#!/usr/bin/env python3
import threading
from typing import Dict, Optional
from .animations import (
    BaseAnimation,
    PulseAnimation,
    LightUpAnimation,
    SparkAnimation
)
from .apa102 import APA102, NUM_LEDS

class Animator:
    """Main animator class that manages and plays LED animations."""
    
    def __init__(self):
        """Initialize the Animator with hardcoded LED strip and parameters."""
        self.num_leds = NUM_LEDS
        self.led_strip = APA102(NUM_LEDS)
        self._using_external_strip = False
        
        # Create animation instances with meaningful IDs for AI voice assistant
        self._animations: Dict[str, BaseAnimation] = {
            'welcome': LightUpAnimation(self.led_strip, (255, 255, 255)),
            'thinking': SparkAnimation(self.led_strip, (255, 255, 255)),
            'listening': PulseAnimation(self.led_strip, (0, 0, 255)),
            'speaking': PulseAnimation(self.led_strip, (0, 255, 0)),
            'error': PulseAnimation(self.led_strip, (255, 0, 0), total_steps=15)
        }
        
        # Animation state
        self._current_animation: Optional[BaseAnimation] = None
        self._animation_thread: Optional[threading.Thread] = None
        self._stop_requested = False
    
    def get_animation(self, animation_id: str) -> Optional[BaseAnimation]:
        """Get an animation by ID."""
        return self._animations.get(animation_id)
    
    def list_animations(self) -> list:
        """List all available animation IDs."""
        return list(self._animations.keys())
    
    def play(self, animation_id: str, repetitions: int = 1, brightness: float = 1.0) -> bool:
        """
        Play an animation at 60 FPS.
        
        Args:
            animation_id: ID of the animation to play
            repetitions: Number of times to repeat (0 = infinite)
            brightness: Brightness scale factor (0.0 to 1.0)
            
        Returns:
            True if animation started successfully, False otherwise
        """
        if animation_id not in self._animations:
            return False
        
        # Stop any currently running animation
        self.stop()
        
        # Get the animation and reset it
        animation = self._animations[animation_id]
        animation.reset()
        
        # Apply brightness scaling to the animation
        animation.set_brightness_scale(brightness)
        
        # Start animation in a separate thread at 60 FPS
        self._current_animation = animation
        self._stop_requested = False
        
        self._animation_thread = threading.Thread(
            target=self._run_animation,
            args=(animation, repetitions),
            daemon=True
        )
        self._animation_thread.start()
        
        return True
    
    def _run_animation(self, animation: BaseAnimation, repetitions: int):
        """Run animation in a separate thread at 60 FPS."""
        try:
            # Use 60 FPS (1/60 seconds delay)
            animation.play(repetitions, 1/60)
        except Exception as e:
            print(f"Animation error: {e}")
        finally:
            self._current_animation = None
    
    def stop(self) -> None:
        """Stop the current animation immediately."""
        if self._current_animation:
            self._current_animation.stop()
            self._current_animation = None
        
        if self._animation_thread and self._animation_thread.is_alive():
            self._stop_requested = True
            # Wait a bit for the thread to finish
            self._animation_thread.join(timeout=0.1)
    
    def is_playing(self) -> bool:
        """Check if an animation is currently playing."""
        return (self._current_animation is not None and 
                self._current_animation.is_running)
    
    def get_current_animation(self) -> Optional[str]:
        """Get the ID of the currently playing animation."""
        if self._current_animation:
            for anim_id, anim in self._animations.items():
                if anim is self._current_animation:
                    return anim_id
        return None
    
    def off(self) -> None:
        """Turn off all LEDs."""
        self.stop()
        if self.led_strip:
            self.led_strip.off()
    
    def close(self) -> None:
        """Close the LED strip."""
        self.stop()
        if self.led_strip:
            self.led_strip.close()

    def get_current_animation_id(self) -> Optional[str]:
        """Get the ID of the currently playing animation."""
        
        for anim_id, anim in self._animations.items():
            if anim is self._current_animation:
                return anim_id
        return None