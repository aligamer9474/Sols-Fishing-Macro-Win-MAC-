import time
import threading
import ctypes
import keyboard
import pyautogui


# ============================================================
# SETTINGS
# ============================================================

FISH_BUTTON = (853, 832)

MINIGAME_START_PIXEL = (1176, 836)
MINIGAME_TIMEOUT = 19

BAR_LEFT = 757
BAR_RIGHT = 1161
BAR_Y = 767

BAR_SAMPLE_X = 955

FISHING_THRESHOLD = 25

SCAN_DELAY = 0.01

running = False


# ============================================================
# WINDOWS MOUSE
# ============================================================

user32 = ctypes.windll.user32

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004


class POINT(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_long),
        ("y", ctypes.c_long)
    ]


def get_mouse_position():
    point = POINT()

    user32.GetCursorPos(
        ctypes.byref(point)
    )

    return point.x, point.y


def native_move_to(x, y):

    start_x, start_y = get_mouse_position()

    dx = x - start_x
    dy = y - start_y

    distance = max(
        abs(dx),
        abs(dy)
    )

    steps = max(
        20,
        int(distance / 8)
    )

    for i in range(1, steps + 1):

        target_x = (
            start_x
            + int(dx * i / steps)
        )

        target_y = (
            start_y
            + int(dy * i / steps)
        )

        current_x, current_y = (
            get_mouse_position()
        )

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

    time.sleep(0.025)

    user32.mouse_event(
        MOUSEEVENTF_LEFTUP,
        0,
        0,
        0,
        0
    )


def click_position(x, y):

    native_move_to(x, y)

    time.sleep(0.25)

    native_click()

    time.sleep(0.25)


# ============================================================
# PIXELS
# ============================================================

def get_pixel(x, y):

    return pyautogui.pixel(
        x,
        y
    )


def is_white(color):

    r, g, b = color

    return (
        r >= 245
        and g >= 245
        and b >= 245
    )


def colors_match(
    color1,
    color2,
    tolerance=10
):

    return (
        abs(color1[0] - color2[0]) <= tolerance
        and
        abs(color1[1] - color2[1]) <= tolerance
        and
        abs(color1[2] - color2[2]) <= tolerance
    )


# ============================================================
# WAIT FOR MINIGAME
# ============================================================

def wait_for_minigame():

    print()
    print("Waiting for minigame...")

    start_time = time.time()
    last_message = 0

    while (
        time.time() - start_time
        < MINIGAME_TIMEOUT
    ):

        color = get_pixel(
            MINIGAME_START_PIXEL[0],
            MINIGAME_START_PIXEL[1]
        )

        if is_white(color):

            elapsed = (
                time.time()
                - start_time
            )

            print(
                f"Minigame detected "
                f"after {elapsed:.1f} seconds!"
            )

            return True

        elapsed = (
            time.time()
            - start_time
        )

        if int(elapsed) >= last_message + 5:

            print(
                f"Still waiting... "
                f"{elapsed:.1f}s"
            )

            last_message = int(elapsed)

        time.sleep(0.05)

    print("Minigame timed out.")

    return False


# ============================================================
# GET FRESH RECTANGLE COLOR
# ============================================================

def get_fishing_color():

    color = get_pixel(
        BAR_SAMPLE_X,
        BAR_Y
    )

    print(
        f"Sampled fishing color: RGB{color}"
    )

    return color


# ============================================================
# FIND COLOR RANGE
# ============================================================

def find_color_range(bar_color):

    left_x = None
    right_x = None

    # Find first matching pixel
    for x in range(
        BAR_LEFT,
        BAR_RIGHT + 1
    ):

        color = get_pixel(
            x,
            BAR_Y
        )

        if colors_match(
            color,
            bar_color,
            10
        ):

            left_x = x
            break

    if left_x is None:
        return None

    # Follow the matching pixels
    right_x = left_x

    for x in range(
        left_x + 1,
        BAR_RIGHT + 1
    ):

        color = get_pixel(
            x,
            BAR_Y
        )

        if colors_match(
            color,
            bar_color,
            10
        ):

            right_x = x

        else:
            break

    return (
        left_x,
        right_x
    )


# ============================================================
# FISHING MINIGAME
# ============================================================

def play_fishing_minigame():

    print()
    print("======================================")
    print("FISHING MINIGAME")
    print("CLICKS ENABLED")
    print("======================================")

    # The rectangle color can change every fish,
    # so sample it every new minigame.
    bar_color = get_fishing_color()

    start_time = time.time()

    click_count = 0

    last_click = 0

    # Give the UI a moment to fully appear.
    time.sleep(0.10)

    while (
        time.time() - start_time
        < MINIGAME_TIMEOUT
    ):

        if not running:
            return False

        color_range = find_color_range(
            bar_color
        )

        current_time = time.time()

        if color_range is not None:

            left_x, right_x = color_range

            width = right_x - left_x

            center = (
                left_x + right_x
            ) // 2

            # Click when the detected bar becomes
            # small, matching the old macro's
            # advanced fishing logic.
            if (
                width < FISHING_THRESHOLD
                and
                current_time - last_click > 0.025
            ):

                native_click()

                click_count += 1

                last_click = current_time

                print(
                    f"CLICK #{click_count} | "
                    f"X={center} | "
                    f"Width={width}"
                )

        else:

            # If the sampled color disappeared,
            # click once, matching the old macro's
            # fallback behavior.
            if (
                current_time - last_click
                > 0.08
            ):

                native_click()

                click_count += 1

                last_click = current_time

                print(
                    f"CLICK #{click_count} | "
                    f"Bar color not found"
                )

        time.sleep(SCAN_DELAY)

    print()
    print(
        f"Fishing detection finished. "
        f"Clicks: {click_count}"
    )

    return True


# ============================================================
# TEST FISHING
# ============================================================

def test_fishing():

    print()
    print("Moving to Fish button...")

    click_position(
        FISH_BUTTON[0],
        FISH_BUTTON[1]
    )

    if not wait_for_minigame():

        print("No minigame detected.")

        return

    play_fishing_minigame()


# ============================================================
# HOTKEYS
# ============================================================

def toggle_macro():

    global running

    if running:

        running = False

        print()
        print("Macro STOPPED.")

        return

    running = True

    print()
    print("Macro STARTED.")

    threading.Thread(
        target=test_fishing,
        daemon=True
    ).start()


def emergency_stop():

    global running

    running = False

    print()
    print("======================================")
    print("EMERGENCY STOP")
    print("======================================")


# ============================================================
# START
# ============================================================

keyboard.add_hotkey(
    "f8",
    toggle_macro
)

keyboard.add_hotkey(
    "f3",
    emergency_stop
)

print("======================================")
print("SOLS RNG FISHING MACRO")
print("======================================")
print("F8 = Start")
print("F3 = Emergency Stop")
print()
print("Fishing clicks are ENABLED.")
print("======================================")

keyboard.wait()
