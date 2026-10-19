import time
import threading
import ctypes
import keyboard
import pyautogui

running = False

# ============================================================
# COORDINATES
# ============================================================

FISH_BUTTON = (853, 832)

MINIGAME_START_PIXEL = (1176, 836)

BAR_SCAN_LEFT = 757
BAR_SCAN_RIGHT = 1161
BAR_SCAN_Y = 767

MINIGAME_TIMEOUT = 19

# ============================================================
# WINDOWS MOUSE INPUT
# ============================================================

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

    user32.GetCursorPos(
        ctypes.byref(point)
    )

    return point.x, point.y


def native_move_to(x, y):

    start_x, start_y = get_mouse_position()

    distance = max(
        abs(x - start_x),
        abs(y - start_y)
    )

    if distance == 0:
        return

    steps = max(
        20,
        int(distance / 8)
    )

    for i in range(1, steps + 1):

        if not running:
            return

        target_x = int(
            start_x +
            (x - start_x) * i / steps
        )

        target_y = int(
            start_y +
            (y - start_y) * i / steps
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


def click_position(position, name):

    print(
        f"Moving to {name}: {position}"
    )

    native_move_to(
        position[0],
        position[1]
    )

    if not running:
        return

    time.sleep(0.25)

    native_click()

    print(
        f"Clicked {name}."
    )


# ============================================================
# PIXEL FUNCTIONS
# ============================================================

def get_pixel(x, y):

    try:
        return pyautogui.pixel(x, y)

    except Exception:
        return None


def is_white_pixel(x, y):

    color = get_pixel(x, y)

    if color is None:
        return False

    return (
        color[0] >= 245
        and color[1] >= 245
        and color[2] >= 245
    )


# ============================================================
# WAIT FOR MINIGAME
# ============================================================

def wait_for_minigame():

    print()
    print("Waiting for fishing minigame...")

    start_time = time.time()

    while running:

        elapsed = time.time() - start_time

        if elapsed >= MINIGAME_TIMEOUT:

            print()
            print(
                f"Could not detect minigame "
                f"after {elapsed:.1f} seconds."
            )

            return False

        if is_white_pixel(
            MINIGAME_START_PIXEL[0],
            MINIGAME_START_PIXEL[1]
        ):

            print()
            print(
                f"Minigame detected after "
                f"{elapsed:.1f} seconds!"
            )

            return True

        time.sleep(0.01)

    return False


# ============================================================
# COLOR SCANNER
# ============================================================

def scan_bar():

    screenshot = pyautogui.screenshot(
        region=(
            BAR_SCAN_LEFT,
            BAR_SCAN_Y,
            BAR_SCAN_RIGHT - BAR_SCAN_LEFT + 1,
            1
        )
    )

    pixels = []

    for x in range(
        BAR_SCAN_RIGHT - BAR_SCAN_LEFT + 1
    ):

        color = screenshot.getpixel(
            (x, 0)
        )

        pixels.append(
            (
                BAR_SCAN_LEFT + x,
                color
            )
        )

    return pixels


def summarize_colors(pixels):

    color_positions = {}

    for x, color in pixels:

        if color not in color_positions:

            color_positions[color] = []

        color_positions[color].append(x)

    # Sort colors by number of pixels.
    sorted_colors = sorted(
        color_positions.items(),
        key=lambda item: len(item[1]),
        reverse=True
    )

    return sorted_colors


def print_scan():

    pixels = scan_bar()

    colors = summarize_colors(pixels)

    print()
    print(
        "--------------------------------"
    )
    print("FISHING BAR COLOR SCAN")
    print(
        "--------------------------------"
    )

    print(
        f"Scanning X={BAR_SCAN_LEFT} "
        f"to X={BAR_SCAN_RIGHT}"
    )

    print()

    # Show the most common colors.
    # This helps identify the background,
    # orange rectangle, target area, etc.

    for color, positions in colors[:15]:

        first_x = positions[0]
        last_x = positions[-1]

        print(
            f"RGB {color} | "
            f"pixels: {len(positions):3d} | "
            f"X: {first_x}-{last_x}"
        )

    print(
        "--------------------------------"
    )


# ============================================================
# SCANNER
# ============================================================

def run_scanner():

    global running

    print()
    print("================================")
    print("FISHING COLOR SCANNER")
    print("================================")
    print()

    print(
        "The scanner will NOT click "
        "during the minigame."
    )

    print()

    # Click Fish
    click_position(
        FISH_BUTTON,
        "Fish button"
    )

    if not running:
        return

    # Wait for minigame
    if not wait_for_minigame():

        running = False

        print()
        print(
            "Scanner stopped because "
            "the minigame was not detected."
        )

        return

    print()
    print(
        "MINIGAME FOUND!"
    )

    print()
    print(
        "Keep watching the minigame."
    )

    print(
        "The scanner will take several "
        "samples while the orange "
        "rectangle moves."
    )

    print()

    # Take several scans so we can see
    # how the moving rectangle changes.
    for scan_number in range(1, 11):

        if not running:
            break

        print()
        print(
            f"========== SCAN "
            f"{scan_number}/10 =========="
        )

        print_scan()

        time.sleep(0.25)

    print()
    print("================================")
    print("SCANNING FINISHED")
    print("================================")
    print()

    print(
        "Send me the CMD output from "
        "these scans."
    )

    running = False


# ============================================================
# HOTKEYS
# ============================================================

def start_scanner():

    global running

    if running:

        print(
            "Scanner is already running."
        )

        return

    running = True

    threading.Thread(
        target=run_scanner,
        daemon=True
    ).start()


def emergency_stop():

    global running

    running = False

    print()
    print(
        "!!! EMERGENCY STOP !!!"
    )


keyboard.add_hotkey(
    "f8",
    start_scanner
)

keyboard.add_hotkey(
    "f3",
    emergency_stop
)


# ============================================================
# START
# ============================================================

print("Sol's Fishing Color Scanner")
print()

print(
    "F8 = Start Scanner"
)

print(
    "F3 = Emergency Stop"
)

print()

print(
    "Ready."
)

keyboard.wait()
