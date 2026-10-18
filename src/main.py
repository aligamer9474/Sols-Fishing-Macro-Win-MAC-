import time
import threading
import ctypes
import pyautogui
import keyboard

running = False
fish_position = None

user32 = ctypes.windll.user32

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004


def native_move_to(x, y):
    """Move the mouse using Windows native cursor movement."""
    start_x, start_y = user32.GetCursorPos(ctypes.byref(POINT()))

    point = POINT()
    user32.GetCursorPos(ctypes.byref(point))

    start_x = point.x
    start_y = point.y

    distance = max(abs(x - start_x), abs(y - start_y))

    if distance == 0:
        return

    # Similar idea to the old AHK MouseMove speed:
    # move in many small steps instead of teleporting.
    steps = max(20, int(distance / 8))

    for i in range(1, steps + 1):
        if not running:
            return

        new_x = int(start_x + (x - start_x) * i / steps)
        new_y = int(start_y + (y - start_y) * i / steps)

        user32.SetCursorPos(new_x, new_y)
        time.sleep(0.008)


def native_click():
    """Perform a native Windows left click."""
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.05)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)


class POINT(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_long),
        ("y", ctypes.c_long),
    ]


def macro():
    global running, fish_position

    print("Macro started!")

    if fish_position is None:
        print("No Fish button position saved!")
        running = False
        return

    print(f"Moving to Fish button: {fish_position}")

    native_move_to(
        fish_position.x,
        fish_position.y
    )

    if not running:
        return

    # Same kind of pause used by the old macro.
    time.sleep(0.25)

    if not running:
        return

    native_click()

    print("Fish button clicked!")

    while running:
        time.sleep(0.5)


def save_fish_position():
    global fish_position

    fish_position = pyautogui.position()

    print()
    print("Fish button position saved:", fish_position)
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
print("F7 = Save Fish button")
print("F8 = Start / Stop")
print("F3 = Emergency stop")
print()

keyboard.wait()
