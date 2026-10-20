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

BAR_LEFT = 757
BAR_RIGHT = 1161
BAR_Y = 767

BAR_SAMPLE_X = 955
BAR_SAMPLE_Y = 767

BAR_COLOR_TOLERANCE = 5
BAR_EXPAND_TOLERANCE = 10

ADVANCED_THRESHOLD = 25

MINIGAME_TIME = 9.0

# Slows down repeated successful clicks.
CLICK_COOLDOWN = 0.12

# Slower emergency/panic clicks.
PANIC_COOLDOWN = 0.35

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

        # Small relative movements so Roblox recognizes the movement.
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
# MACRO STATE
# ============================================================

running = False
emergency_stop = False
cycle_count = 0


# ============================================================
# COLOR HELPERS
# ============================================================

def color_matches(pixel, target, tolerance):
    if pixel is None or target is None:
        return False

    return (
        abs(pixel[0] - target[0]) <= tolerance
        and abs(pixel[1] - target[1]) <= tolerance
        and abs(pixel[2] - target[2]) <= tolerance
    )


def color_is_valid_bar_color(color):
    if color is None:
        return False

    r, g, b = color

    # Don't accept white/near-white UI elements.
    if r > 235 and g > 235 and b > 235:
        return False

    # Don't accept pure black/near-black background.
    if r < 5 and g < 5 and b < 5:
        return False

    return True


# ============================================================
# MINIGAME START DETECTION
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
            print(f"Minigame detected after {elapsed:.1f} seconds!")
            return True

        elapsed = time.time() - start

        if elapsed - last_status >= 5:
            print(f"Still waiting... {elapsed:.1f}s")
            last_status = elapsed

        time.sleep(0.03)

    return False


# ============================================================
# GET BAR COLOR
# ============================================================

def get_bar_color():
    """
    Uses the old macro's sample location.

    We give the game a little time to render the minigame.
    If the exact point is white, we retry instead of accepting
    white as the fishing-bar color.
    """

    for _ in range(12):
        screenshot = ImageGrab.grab(
            bbox=(
                BAR_SAMPLE_X,
                BAR_SAMPLE_Y,
                BAR_SAMPLE_X + 1,
                BAR_SAMPLE_Y + 1
            )
        )

        color = screenshot.getpixel((0, 0))

        if color_is_valid_bar_color(color):
            return color

        time.sleep(0.025)

    return None


# ============================================================
# FIND BAR
# ============================================================

def find_bar(screenshot, bar_color):
    pixels = screenshot.load()

    left_x = None
    right_x = None

    for x in range(BAR_LEFT, BAR_RIGHT + 1):
        pixel = pixels[x - BAR_LEFT, 0]

        if color_matches(pixel, bar_color, BAR_COLOR_TOLERANCE):
            left_x = x
            break

    if left_x is None:
        return None

    right_x = left_x

    for x in range(left_x + 1, BAR_RIGHT + 1):
        pixel = pixels[x - BAR_LEFT, 0]

        if color_matches(pixel, bar_color, BAR_EXPAND_TOLERANCE):
            right_x = x
        else:
            break

    width = right_x - left_x

    return left_x, right_x, width


# ============================================================
# FISHING MINIGAME
# ============================================================

def fishing_minigame():
    print()
    print("======================================")
    print("FISHING MINIGAME")
    print("OLD MACRO STYLE")
    print("FAST SCREENSHOT SCANNING")
    print("======================================")
    print(f"Fishing line: X={BAR_LEFT}-{BAR_RIGHT}, Y={BAR_Y}")

    # Give the minigame time to fully appear.
    time.sleep(0.05)

    bar_color = get_bar_color()

    if bar_color is None:
        print("Could not get a valid bar color.")
        print("Stopping fishing detection safely.")
        return

    print(
        f"Bar color learned: RGB"
        f"{bar_color}"
    )

    print(f"Advanced threshold: {ADVANCED_THRESHOLD}")

    start_time = time.time()

    total_clicks = 0
    detections = 0
    missed_scans = 0

    last_successful_click = 0
    last_panic_click = 0

    # Prevent clicking the exact same visual bar over and over.
    waiting_for_bar_change = False

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

        result = find_bar(screenshot, bar_color)

        now = time.time()

        if result is not None:
            left_x, right_x, width = result

            detections += 1

            # Once we've clicked this bar, don't immediately click
            # the exact same bar again until it changes/disappears.
            if waiting_for_bar_change:
                if width >= ADVANCED_THRESHOLD:
                    waiting_for_bar_change = False

                elif left_x < BAR_LEFT + 10 or right_x > BAR_RIGHT - 10:
                    waiting_for_bar_change = False

                time.sleep(0.01)
                continue

            if width < ADVANCED_THRESHOLD:
                if now - last_successful_click >= CLICK_COOLDOWN:
                    print(
                        f"BAR FOUND: {left_x}-{right_x} "
                        f"Width={width} "
                        f"Center={(left_x + right_x) // 2}"
                    )

                    native_click()

                    total_clicks += 1
                    last_successful_click = now
                    waiting_for_bar_change = True

                    print(f"CLICK #{total_clicks}")

                    time.sleep(0.02)
            else:
                # Bar exists but is too wide.
                waiting_for_bar_change = False

        else:
            missed_scans += 1

            if (
                not waiting_for_bar_change
                and now - last_panic_click >= PANIC_COOLDOWN
            ):
                native_click()

                total_clicks += 1
                last_panic_click = now

                print(
                    f"PANIC CLICK #{total_clicks} "
                    f"(bar not detected)"
                )

        time.sleep(0.01)

    print()
    print("Fishing detection finished.")
    print(f"Bar detections: {detections}")
    print(f"Missed scans: {missed_scans}")
    print(f"Total clicks: {total_clicks}")


# ============================================================
# FISH RESULT
# ============================================================

def close_fish_result():
    print()
    print("Moving to fish-result X...")

    time.sleep(RESULT_MOVE_DELAY)

    move_mouse_native(
        FISH_RESULT_CLOSE[0],
        FISH_RESULT_CLOSE[1]
    )

    x, y = get_mouse_position()

    print(f"Mouse at X: ({x}, {y})")

    time.sleep(RESULT_CLICK_DELAY)

    native_click()

    print("Fish-result X clicked.")


# ============================================================
# ONE FISHING CYCLE
# ============================================================

def fishing_cycle():
    global cycle_count

    cycle_count += 1

    print()
    print("======================================")
    print(f"FISHING CYCLE #{cycle_count}")
    print("======================================")

    print("Moving to Fish button...")

    move_mouse_native(
        FISH_BUTTON[0],
        FISH_BUTTON[1]
    )

    x, y = get_mouse_position()

    print(f"Mouse position: ({x}, {y})")

    print("Clicking Fish...")

    native_click()

    if not wait_for_minigame():
        return

    fishing_minigame()

    if not running or emergency_stop:
        return

    close_fish_result()

    print(
        f"Cycle complete! Total cycles: {cycle_count}"
    )


# ============================================================
# MACRO THREAD
# ============================================================

def macro_loop():
    while running and not emergency_stop:
        fishing_cycle()

        if running and not emergency_stop:
            time.sleep(0.3)


# ============================================================
# F8 START / PAUSE
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
# F3 EMERGENCY STOP
# ============================================================

def emergency():
    global running
    global emergency_stop

    running = False
    emergency_stop = True

    print()
    print("!!! EMERGENCY STOP !!!")


# ============================================================
# MAIN
# ============================================================

print("======================================")
print("SOLS RNG FISHING MACRO")
print("======================================")
print("F8 = Start / Pause")
print("F3 = Emergency Stop")
print()
print("Old fishing behavior restored.")
print("Fast screenshot-based bar scanning.")
print("Mouse does NOT follow the rectangle.")
print("Successful clicks have a cooldown.")
print("Panic clicks are slowed down.")
print("No dynamic color re-learning.")
print(f"Fishing line: {BAR_LEFT}-{BAR_RIGHT} at Y={BAR_Y}")
print(f"Threshold: {ADVANCED_THRESHOLD}")
print(f"Detection time: {MINIGAME_TIME}s")
print("Result X has old 300ms/700ms timing.")
print("======================================")
print()

keyboard.add_hotkey("f8", toggle_macro)
keyboard.add_hotkey("f3", emergency)

try:
    while not emergency_stop:
        time.sleep(0.1)

except KeyboardInterrupt:
    emergency()
