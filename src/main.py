import time
import threading
import pyautogui
import keyboard

running = False
fish_position = None


def macro():
    global running, fish_position

    print("Macro started!")

    if fish_position is None:
        print("No Fish button position saved!")
        running = False
        return

    print(f"Moving to Fish button: {fish_position}")

    # Move the mouse smoothly, similar to the old AutoHotkey macro
    pyautogui.moveTo(
        fish_position.x,
        fish_position.y,
        duration=0.3
    )

    # Give Roblox a moment to recognize the hover
    time.sleep(0.25)

    # Click the Fish button
    pyautogui.click()

    print("Fish button clicked!")

    while running:
        time.sleep(0.5)


def save_fish_position():
    global fish_position

    fish_position = pyautogui.position()

    print()
    print("================================")
    print(f"Fish button position saved: {fish_position}")
    print("================================")
    print()


def toggle_macro():
    global running

    if running:
        running = False
        print("Macro stopped!")
    else:
        running = True
        threading.Thread(target=macro, daemon=True).start()


def emergency_stop():
    global running

    running = False
    print("EMERGENCY STOP")


keyboard.add_hotkey("f7", save_fish_position)
keyboard.add_hotkey("f8", toggle_macro)
keyboard.add_hotkey("f3", emergency_stop)

print("Sol's Fishing Macro")
print()
print("Hover over the Fish button and press F7.")
print("Press F8 to start/stop.")
print("Press F3 for emergency stop.")
print()

keyboard.wait()
