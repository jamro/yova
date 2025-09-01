import sys
import os
import time
import math
import threading
from typing import Optional

import numpy as np
import logging

from yova_shared.logging_utils import setup_logging, get_clean_logger
from yova_core.speech2text.recording_stream import RecordingStream
from yova_core.voice_id.voice_id_manager import VoiceIdManager


# ----------------------------
# Simple ANSI styling helpers
# ----------------------------
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
ITALIC = "\033[3m"
UNDERLINE = "\033[4m"

FG_GRAY = "\033[90m"
FG_RED = "\033[91m"
FG_GREEN = "\033[92m"
FG_YELLOW = "\033[93m"
FG_BLUE = "\033[94m"
FG_MAGENTA = "\033[95m"
FG_CYAN = "\033[96m"


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def hr(char: str = "─", width: Optional[int] = None) -> str:
    w = width or os.get_terminal_size().columns
    return char * max(10, min(w - 2, 100))


def center(text: str) -> str:
    try:
        width = os.get_terminal_size().columns
    except OSError:
        width = 80
    return text.center(width)


def banner():
    title = f"{BOLD}{FG_CYAN}Y O V A  •  Voice ID Enroller{RESET}"
    print(hr())
    print(center(title))
    print(hr())


def input_prompt(prompt: str) -> str:
    return input(f"{BOLD}{prompt}{RESET} ")


def wait_for_enter(message: str = "Press Enter to continue"):
    input(f"{DIM}{message}{RESET}")


def input_int(prompt: str, default_value: int) -> int:
    raw = input_prompt(f"{prompt} [{default_value}]")
    raw = (raw or "").strip()
    if not raw:
        return default_value
    try:
        return max(1, int(raw))
    except ValueError:
        return default_value


def format_progress_bar(progress_0_1: float, width: int = 30) -> str:
    clamped = max(0.0, min(1.0, progress_0_1))
    filled = int(round(clamped * width))
    bar = f"{FG_CYAN}{'█' * filled}{FG_GRAY}{'░' * (width - filled)}{RESET}"
    return bar


def level_meter(level_0_1: float, width: int = 10) -> str:
    clamped = max(0.0, min(1.0, level_0_1))
    filled = int(round(clamped * width))
    color = FG_GREEN if clamped < 0.6 else (FG_YELLOW if clamped < 0.85 else FG_RED)
    return f"{color}{'▮' * filled}{FG_GRAY}{'▯' * (width - filled)}{RESET}"


def print_info(msg: str):
    print(f"{FG_BLUE}ℹ{RESET} {msg}")


def print_success(msg: str):
    print(f"{FG_GREEN}✔{RESET} {msg}")


def print_warn(msg: str):
    print(f"{FG_YELLOW}⚠{RESET} {msg}")


def print_error(msg: str):
    print(f"{FG_RED}✖{RESET} {msg}")


def soft_sleep(seconds: float):
    end = time.time() + seconds
    while time.time() < end:
        time.sleep(0.01)


def record_pcm16_mono(duration_sec: float, logger, rate: int = 16000, chunk: int = 512) -> np.ndarray:
    """
    Record microphone audio as PCM16 mono at given sample rate.
    Returns numpy array of dtype int16 length ≈ duration_sec * rate.
    """
    rs = RecordingStream(logger, channels=1, rate=rate, chunk=chunk)
    stream = None
    frames = []

    try:
        stream = rs.create()
        start_time = time.time()
        next_ui = 0.0
        last_level = 0.0

        print()
        print(f"  {DIM}Recording... Speak naturally{RESET}")

        while True:
            data = rs.read()
            frames.append(data)

            # Level meter from recent chunk
            if data:
                arr = np.frombuffer(data, dtype=np.int16)
                if arr.size > 0:
                    rms = float(np.sqrt(np.mean(np.square(arr.astype(np.float32)))))
                    last_level = min(1.0, rms / 30000.0)

            elapsed = time.time() - start_time
            if elapsed >= duration_sec:
                break

            # UI progress (rate limit updates)
            if elapsed >= next_ui:
                progress = elapsed / duration_sec
                bar = format_progress_bar(progress)
                meter = level_meter(last_level)
                print(f"\r  {bar}  {meter}  {elapsed:4.1f}s/{duration_sec:.1f}s", end="", flush=True)
                next_ui = elapsed + 0.05

        # Final UI line
        print(f"\r  {format_progress_bar(1.0)}  {level_meter(last_level)}  {duration_sec:4.1f}s/{duration_sec:.1f}s")

    finally:
        if stream is not None:
            rs.close()

    pcm = b"".join(frames)
    return np.frombuffer(pcm, dtype=np.int16)


def load_voice_id_manager(parent_logger) -> VoiceIdManager:
    print_info("Loading Voice ID model (may take a few seconds)...")
    t0 = time.perf_counter()
    manager = VoiceIdManager(parent_logger)
    dt = (time.perf_counter() - t0) * 1000
    print_success(f"Voice ID ready in {dt:.0f} ms")
    return manager


def main():
    clear_screen()
    setup_logging("ERROR")
    # Disable all logging output; keep only our styled prints
    logging.disable(logging.CRITICAL)
    logger = get_clean_logger("voice_id_cli")

    banner()
    print("\n" + center(f"{DIM}Lightweight speaker enrollment and verification{RESET}"))
    print("\n" + hr())

    # Ask for username
    print()
    username = ""
    while not username.strip():
        username = input_prompt("Enter a user name to enroll:")
        if not username.strip():
            print_warn("User name cannot be empty.")

    # Load manager (heavy)
    print()
    manager = load_voice_id_manager(logger)

    # Prevent accidental overwrite of an existing user profile
    append_to_existing = False
    if username.strip():
        while manager.speaker_verifier.profile_exists_on_disk(username):
            existing_count = manager.speaker_verifier.get_speaker_sample_count(username)
            print()
            print_warn(f"User '{username}' already exists with {existing_count} enrolled sample(s).")
            print(center(f"{DIM}Choose: [A]dd samples, [R]ename, [C]ancel{RESET}"))
            choice = input_prompt("Your choice [R]").strip().lower()
            if choice in ("a", "add"):
                append_to_existing = True
                print_info(f"Will add new samples to existing user '{username}'.")
                break
            if choice in ("c", "cancel", "q", "quit"):
                print_info("Enrollment canceled.")
                sys.exit(0)
            # Default to rename flow
            new_name = ""
            while not new_name.strip():
                new_name = input_prompt("Enter a different user name:").strip()
            username = new_name
        else:
            # Not existing on disk
            pass

    # Enrollment (exactly 3 samples, 5.0s each)
    print("\n" + hr())
    print(center(f"{BOLD}Enrollment samples{RESET}"))
    print(center(f"{DIM}We will record 3 samples, 4.0s each. Any language is fine. Speak naturally at normal volume.{RESET}"))

    suggestions = [
        "Count from 1, 2, 3... in your language.",
        f"Say a short self-introduction, e.g., \"Hello, I'm {username}\" in your language.",
        "Read any short sentence of your choice in your language.",
    ]

    num_samples = 3
    successful = 0
    for i in range(num_samples):
        print("\n" + center(f"Sample {i+1}/{num_samples}"))
        print(center(f"{FG_MAGENTA}{ITALIC}{suggestions[i]}{RESET}"))
        wait_for_enter("Press Enter to start recording (4.0s)...")
        try:
            enroll_audio = record_pcm16_mono(duration_sec=4.0, logger=logger)
            print_success(f"Recorded {enroll_audio.shape[0]/16000.0:.1f}s of audio")
        except Exception as e:
            print_error(f"Failed to record audio: {e}")
            continue

        print_info("Enrolling sample...")
        try:
            manager.enroll_speaker(username, enroll_audio)
            successful += 1
            print_success(f"Enrolled sample {i+1}/{num_samples} for '{username}'")
        except Exception as e:
            print_error(f"Enrollment failed for this sample: {e}")

    if successful == 0:
        print_error("No enrollment samples were successfully recorded. Exiting.")
        sys.exit(1)
    else:
        print_success(f"Enrollment completed: {successful}/{num_samples} samples stored for '{username}'")

    # Verification
    print("\n" + hr())
    print(center(f"{BOLD}Verification sample{RESET}"))
    print(center(f"{DIM}We will verify with a short 4.0s test{RESET}"))
    wait_for_enter("Press Enter to start recording (4.0s)...")

    try:
        verify_audio = record_pcm16_mono(duration_sec=4.0, logger=logger)
        print_success(f"Recorded {verify_audio.shape[0]/16000.0:.1f}s of audio")
    except Exception as e:
        print_error(f"Failed to record verification audio: {e}")
        sys.exit(1)

    print_info("Identifying speaker...")
    try:
        result = manager.identify_speaker(verify_audio)
    except Exception as e:
        print_error(f"Identification failed: {e}")
        sys.exit(1)

    matched_user = result.get("user_id") or "unknown"
    similarity = float(result.get("similarity") or 0.0)
    confidence = (result.get("confidence_level") or "unknown").lower()
    latency_ms = float(result.get("processing_time") or 0.0)

    print()
    print(center(f"{BOLD}Verification Result{RESET}"))

    color = FG_GREEN if confidence == "high" else (FG_YELLOW if confidence == "medium" else FG_RED)
    verdict_icon = "✔" if matched_user == username and similarity >= 0.5 else "?"

    print(hr())
    print(center(f"{color}{verdict_icon}  user: '{matched_user}'  •  similarity: {similarity:.2f}  •  confidence: {confidence}{RESET}"))
    print(center(f"{DIM}embedding latency: {latency_ms:.0f} ms{RESET}"))
    print(hr())

    if matched_user == username:
        print_success("Verification matched the enrolled user.")
    else:
        if matched_user and matched_user != "unknown":
            print_warn(f"Verification did not match the enrolled user. Instead, matched user: '{matched_user}'. Consider enrolling more samples.")
        else:
            print_warn(f"Verification did not match the enrolled user. No matching user was found. Consider enrolling more samples.")

    print()
    print(center(f"{ITALIC}{DIM}Done. You can re-run to add more samples for robustness.{RESET}"))


def run():
    main()


if __name__ == "__main__":
    run()