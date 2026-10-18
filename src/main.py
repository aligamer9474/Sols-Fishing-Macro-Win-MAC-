import time
import threading
import pyautogui
import keyboard

running = False


def macro():
    global running

    print("Macro started!")

    while running:
        print("Macro is running...")
        time.sleep(1)

    print("Macro stopped!")


def toggle_macro():
    global running

    running = not running

    if running:
        threading.Thread(target=macro, daemon=True).start()
    else:
        print("Stopping macro...")


keyboard.add_hotkey("f8", toggle_macro)

print("Sol's Fishing Macro")
print("Press F8 to start/stop.")

keyboard.wait()
