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

    pyautogui.moveTo(*fish_position, duration=1.0)
    time.sleep(0.8)
    pyautogui.click()

    print("Fish button clicked!")

    while running:
        time.sleep(0.5)


def save_fish_position():
    global fish_position

    fish_position = pyautogui.position()
    print(f"Fish button position saved: {fish_position}")


def toggle_macro():
    global running

    running = not running

    if running:
        threading.Thread(target=macro, daemon=True).start()
    else:
        print("Macro stopped!")


def emergency_stop():
    global running

    running = False
    print("EMERGENCY STOP")


keyboard.add_hotkey("f7", save_fish_position)
keyboard.add_hotkey("f8", toggle_macro)
keyboard.add_hotkey("f3", emergency_stop)

print("Sol's Fishing Macro")
print("Hover over the Fish button and press F7.")
print("Press F8 to start/stop.")
print("Press F3 for emergency stop.")

keyboard.wait()
