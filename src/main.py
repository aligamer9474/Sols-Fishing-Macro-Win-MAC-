import time
import threading
import ctypes
import keyboard

running = False

# Fish button position
fish_position = (853, 832)

user32 = ctypes.windll.user32

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004


class POINT(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_long),
        ("y", ctypes.c_long),
    ]


def get_mouse_position():
    point = POINT()
    user32.GetCursorPos(ctypes.byref(point))
    return point.x, point.y


def native_move_to(x, y):
    """Move using Windows mouse movement events."""

    start_x, start_y = get_mouse_position()

    distance = max(
        abs(x - start_x),
        abs(y - start_y)
    )

    if distance == 0:
        return

    # Smooth movement
    steps = max(20, int(distance / 8))

    for i in range(1, steps + 1):
        if not running:
            return

        target_x = int(
            start_x + (x - start_x) * i / steps
        )

        target_y = int(
            start_y + (y - start_y) * i / steps
        )

        current_x, current_y = get_mouse_position()

        move_x = target_x - current_x
        move_y = target_y - current_y

        if move_x != 0 or move_y != 0:
            user32.mouse_event(
                MOUSEEVENTF_MOVE,
                move_x,
                move_y,
                0,
                0
            )

        time.sleep(0.008)


def native_click():
    """Perform a Windows native left click."""

    user32.mouse_event(
        MOUSEEVENTF_LEFTDOWN,
        0,
        0,
        0,
        0
    )

    time.sleep(0.05)

    user32.mouse_event(
        MOUSEEVENTF_LEFTUP,
        0,
        0,
        0,
        0
    )


def macro():
    global running

    print("Macro started!")
    print(f"Moving to Fish button: {fish_position}")

    native_move_to(
        fish_position[0],
        fish_position[1]
    )

    if not running:
        return

    # Pause after movement like the old macro
    time.sleep(0.25)

    if not running:
        return

    native_click()

    print("Fish button clicked!")

    while running:
        time.sleep(0.5)


def toggle_macro():
    global running

    if running:
        running = False
        print("Macro stopped!")
    else:
        running = True

        threading.Thread(
            target=macro,
            daemon=True
        ).start()


def emergency_stop():
    global running

    running = False
    print("EMERGENCY STOP")


keyboard.add_hotkey("f8", toggle_macro)
keyboard.add_hotkey("f3", emergency_stop)


print("Sol's Fishing Macro")
print()
print("Fish button: (853, 832)")
print("F8 = Start / Stop")
print("F3 = Emergency stop")
print()

keyboard.wait()
