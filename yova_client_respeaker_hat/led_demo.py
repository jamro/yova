#!/usr/bin/env python3
import time
from anim import Animator

def demo():
    # Create animator (LED strip is created automatically)
    animator = Animator()
    
    try:
        print("Available AI Voice Assistant animations:", animator.list_animations())
        print("\n=== AI Voice Assistant Animation Demo ===\n")
        

        # Thinking animation
        print("🤔 Thinking animation...")
        animator.play('thinking', repetitions=0, brightness=0.05)
        time.sleep(10) 
        animator.stop()


        # Welcome animation
        print("👋 Welcome animation...")
        animator.play('welcome', repetitions=1, brightness=0.05)
        time.sleep(5) 
        animator.stop()



        # Listening/Recording state
        print("🎤 Listening animation (recording voice input)...")
        animator.play('listening', repetitions=0, brightness=0.5)
        time.sleep(5) 
        animator.stop()

        # Speaking/Generating response
        print("🗣️ Speaking animation (generating voice response)...")
        animator.play('speaking', repetitions=0, brightness=0.1) # green seems to be too bright
        time.sleep(5) 
        animator.stop()
        
        
        
    finally:
        animator.close()

if __name__ == "__main__":
    demo()