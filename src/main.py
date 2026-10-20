import time
import threading
import ctypes
from ctypes import wintypes

import keyboard
from PIL import ImageGrab


# ============================================================
# SETTINGS
# ============================================================

FISH_BUTTON = (853, 832)
FISH_RESULT_CLOSE = (1113, 342)

MINIGAME_START_PIXEL = (1176, 836)

MINIGAME_MOUSE_POSITION = (950, 880)

BAR_LEFT = 757
BAR_RIGHT = 1161
BAR_Y = 767

BAR_SAMPLE_X = 955
BAR_SAMPLE_Y = 767

BAR_COLOR_TOLERANCE = 5
BAR_EXPAND_TOLERANCE = 10

ADVANCED_THRESHOLD = 25

MINIGAME_TIME = 9.0

SUCCESS_CLICK_DELAY = 0.025

# ============================================================
# ONLY CHANGE:
# When the bar cannot be detected, use short click bursts.
# ============================================================

PANIC_BURST_CLICKS = 2
PANIC_BURST_DELAY = 0.025
PANIC_BURST_COOLDOWN = 0.35

# Old result timing.
RESULT_MOVE_DELAY = 0.30
RESULT_CLICK_DELAY = 0.70


# ============================================================
# WINDOWS MOUSE
# ============================================================

user32 = ctypes.windll.user32

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004


class POINT(ctypes.Structure):
    _fields_ = [
        ("x", wintypes.LONG),
        ("y", wintypes.LONG),
    ]


def get_mouse_position():
    point = POINT()
    user32.GetCursorPos(ctypes.byref(point))
    return point.x, point.y


def move_mouse_native(target_x, target_y):
    while True:
        current_x, current_y = get_mouse_position()

        dx = target_x - current_x
        dy = target_y - current_y

        if abs(dx) <= 1 and abs(dy) <= 1:
            break

        move_x = max(-3, min(3, dx))
        move_y = max(-3, min(3, dy))

        user32.mouse_event(
            MOUSEEVENTF_MOVE,
            move_x,
            move_y,
            0,
            0
        )

        time.sleep(0.004)


def native_click():
    user32.mouse_event(
        MOUSEEVENTF_LEFTDOWN,
        0,
        0,
        0,
        0
    )

    time.sleep(0.01)

    user32.mouse_event(
        MOUSEEVENTF_LEFTUP,
        0,
        0,
        0,
        0
    )


# ============================================================
# STATE
# ============================================================

running = False
emergency_stop = False
cycle_count = 0


# ============================================================
# COLOR
# ============================================================

def color_matches(pixel, target, tolerance):
    if pixel is None or target is None:
        return False

    return (
        abs(pixel[0] - target[0]) <= tolerance
        and abs(pixel[1] - target[1]) <= tolerance
        and abs(pixel[2] - target[2]) <= tolerance
    )


# ============================================================
# MINIGAME START
# ============================================================

def minigame_started():
    screenshot = ImageGrab.grab(
        bbox=(
            MINIGAME_START_PIXEL[0],
            MINIGAME_START_PIXEL[1],
            MINIGAME_START_PIXEL[0] + 1,
            MINIGAME_START_PIXEL[1] + 1
        )
    )

    pixel = screenshot.getpixel((0, 0))

    return (
        pixel[0] > 235
        and pixel[1] > 235
        and pixel[2] > 235
    )


def wait_for_minigame():
    print()
    print("Waiting for minigame...")

    start = time.time()
    last_status = 0

    while running and not emergency_stop:

        if minigame_started():
            elapsed = time.time() - start

            print(
                f"Minigame detected after "
                f"{elapsed:.1f} seconds!"
            )

            return True

        elapsed = time.time() - start

        if elapsed - last_status >= 5:
            print(f"Still waiting... {elapsed:.1f}s")
            last_status = elapsed

        time.sleep(0.03)

    return False


# ============================================================
# BAR COLOR
# ============================================================

def get_bar_color():

    move_mouse_native(
        MINIGAME_MOUSE_POSITION[0],
        MINIGAME_MOUSE_POSITION[1]
    )

    time.sleep(0.05)

    screenshot = ImageGrab.grab(
        bbox=(
            BAR_SAMPLE_X,
            BAR_SAMPLE_Y,
            BAR_SAMPLE_X + 1,
            BAR_SAMPLE_Y + 1
        )
    )

    return screenshot.getpixel((0, 0))


# ============================================================
# FIND BAR
# ============================================================

def find_bar(screenshot, bar_color):

    pixels = screenshot.load()

    left_x = None

    for x in range(BAR_LEFT, BAR_RIGHT + 1):

        pixel = pixels[x - BAR_LEFT, 0]

        if color_matches(
            pixel,
            bar_color,
            BAR_COLOR_TOLERANCE
        ):
            left_x = x
            break

    if left_x is None:
        return None

    right_x = left_x

    for x in range(left_x + 1, BAR_RIGHT + 1):

        pixel = pixels[x - BAR_LEFT, 0]

        if color_matches(
            pixel,
            bar_color,
            BAR_EXPAND_TOLERANCE
        ):
            right_x = x
        else:
            break

    bar_width = right_x - left_x

    return left_x, right_x, bar_width


# ============================================================
# FISHING MINIGAME
# ============================================================

def fishing_minigame():

    print()
    print("======================================")
    print("FISHING MINIGAME")
    print("OLD MACRO DETECTION")
    print("======================================")
    print(
        f"Fishing line: X={BAR_LEFT}-{BAR_RIGHT}, "
        f"Y={BAR_Y}"
    )

    bar_color = get_bar_color()

    print(
        f"Bar color learned: RGB"
        f"{bar_color}"
    )

    print(
        f"Advanced threshold: "
        f"{ADVANCED_THRESHOLD}"
    )

    start_time = time.time()

    total_clicks = 0
    detections = 0
    missed_scans = 0

    # Used ONLY for the no-bar-detected burst behavior.
    last_panic_burst = 0

    while (
        running
        and not emergency_stop
        and time.time() - start_time < MINIGAME_TIME
    ):

        screenshot = ImageGrab.grab(
            bbox=(
                BAR_LEFT,
                BAR_Y,
                BAR_RIGHT + 1,
                BAR_Y + 1
            )
        )

        result = find_bar(
            screenshot,
            bar_color
        )

        now = time.time()

        # ====================================================
        # NORMAL DETECTION
        # ====================================================

        if result is not None:

            left_x, right_x, bar_width = result

            detections += 1

            if bar_width < ADVANCED_THRESHOLD:

                print(
                    f"BAR FOUND: "
                    f"{left_x}-{right_x} "
                    f"Width={bar_width} "
                    f"Center={(left_x + right_x) // 2}"
                )

                native_click()

                total_clicks += 1

                print(
                    f"CLICK #{total_clicks}"
                )

                time.sleep(
                    SUCCESS_CLICK_DELAY
                )

        # ====================================================
        # BAR NOT DETECTED
        # ====================================================

        else:

            missed_scans += 1

            # Instead of continuously panic-clicking,
            # do a small burst, then STOP for a moment.
            if (
                now - last_panic_burst
                >= PANIC_BURST_COOLDOWN
            ):

                print(
                    "BAR NOT DETECTED - "
                    "CENTER CLICK BURST"
                )

                for _ in range(PANIC_BURST_CLICKS):

                    if (
                        not running
                        or emergency_stop
                    ):
                        break

                    native_click()

                    total_clicks += 1

                    print(
                        f"BURST CLICK #{total_clicks}"
                    )

                    time.sleep(
                        PANIC_BURST_DELAY
                    )

                last_panic_burst = time.time()

        time.sleep(0.01)

    print()
    print("Fishing detection finished.")
    print(
        f"Bar detections: {detections}"
    )
    print(
        f"Missed scans: {missed_scans}"
    )
    print(
        f"Total clicks: {total_clicks}"
    )


# ============================================================
# FISH RESULT
# ============================================================

def close_fish_result():

    print()
    print("Moving to fish-result X...")

    time.sleep(
        RESULT_MOVE_DELAY
    )

    move_mouse_native(
        FISH_RESULT_CLOSE[0],
        FISH_RESULT_CLOSE[1]
    )

    x, y = get_mouse_position()

    print(
        f"Mouse at X: ({x}, {y})"
    )

    time.sleep(
        RESULT_CLICK_DELAY
    )

    native_click()

    print(
        "Fish-result X clicked."
    )


# ============================================================
# FISHING CYCLE
# ============================================================

def fishing_cycle():

    global cycle_count

    cycle_count += 1

    print()
    print("======================================")
    print(
        f"FISHING CYCLE #{cycle_count}"
    )
    print("======================================")

    print(
        "Moving to Fish button..."
    )

    move_mouse_native(
        FISH_BUTTON[0],
        FISH_BUTTON[1]
    )

    x, y = get_mouse_position()

    print(
        f"Mouse position: ({x}, {y})"
    )

    print(
        "Clicking Fish..."
    )

    native_click()

    if not wait_for_minigame():
        return

    fishing_minigame()

    if not running or emergency_stop:
        return

    close_fish_result()

    print(
        f"Cycle complete! "
        f"Total cycles: {cycle_count}"
    )


# ============================================================
# MACRO LOOP
# ============================================================

def macro_loop():

    while running and not emergency_stop:

        fishing_cycle()

        if running and not emergency_stop:
            time.sleep(0.3)


# ============================================================
# F8
# ============================================================

def toggle_macro():

    global running

    if running:

        running = False

        print()
        print("Macro PAUSED.")

    else:

        running = True

        print()
        print("Macro STARTED.")

        thread = threading.Thread(
            target=macro_loop,
            daemon=True
        )

        thread.start()


# ============================================================
# F3
# ============================================================

def emergency():

    global running
    global emergency_stop

    running = False
    emergency_stop = True

    print()
    print(
        "!!! EMERGENCY STOP !!!"
    )


# ============================================================
# MAIN
# ============================================================

print("======================================")
print("SOLS RNG FISHING MACRO")
print("======================================")
print("F8 = Start / Pause")
print("F3 = Emergency Stop")
print()
print("Old AHK fishing detection restored.")
print("Mouse does NOT follow the rectangle.")
print("No dynamic color re-learning.")
print(
    f"Fishing line: "
    f"{BAR_LEFT}-{BAR_RIGHT} "
    f"at Y={BAR_Y}"
)
print(
    f"Threshold: "
    f"{ADVANCED_THRESHOLD}"
)
print(
    f"Detection time: "
    f"{MINIGAME_TIME}s"
)
print(
    "Result X has old 300ms/700ms timing."
)
print("======================================")
print()

keyboard.add_hotkey(
    "f8",
    toggle_macro
)

keyboard.add_hotkey(
    "f3",
    emergency
)

try:

    while not emergency_stop:
        time.sleep(0.1)

except KeyboardInterrupt:

    emergency()
