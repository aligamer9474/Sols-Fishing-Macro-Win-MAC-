import pyautogui
import keyboard
import time
import ctypes
from ctypes import wintypes

# ============================================================
# SETTINGS
# ============================================================

FISH_BUTTON = (853, 832)
FISH_RESULT_CLOSE = (1113, 342)

MINIGAME_START_PIXEL = (1176, 836)
MINIGAME_TIMEOUT = 19

# Fishing bar
BAR_LEFT = 757
BAR_RIGHT = 1161
BAR_Y = 767

# Old macro's advanced fishing threshold
ADVANCED_FISHING_THRESHOLD = 25

COLOR_SAMPLE_DELAY = 0.050
SCAN_DELAY = 0.010

COLOR_TOLERANCE = 10

# Prevent instant re-triggering after a click
REARM_DELAY = 0.08

# Panic click cooldown
MISSING_COLOR_COOLDOWN = 0.60

# ============================================================
# WINDOWS NATIVE MOUSE INPUT
# ============================================================

user32 = ctypes.windll.user32

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004


def get_mouse_position():
    point = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(point))
    return point.x, point.y


def move_mouse_native(x, y):
    current_x, current_y = get_mouse_position()

    dx = x - current_x
    dy = y - current_y

    distance = max(abs(dx), abs(dy))

    if distance == 0:
        return

    steps = max(1, int(distance / 8))

    for i in range(1, steps + 1):
        target_x = current_x + int(dx * i / steps)
        target_y = current_y + int(dy * i / steps)

        last_x, last_y = get_mouse_position()

        move_x = target_x - last_x
        move_y = target_y - last_y

        user32.mouse_event(
            MOUSEEVENTF_MOVE,
            move_x,
            move_y,
            0,
            0
        )

        time.sleep(0.003)


def native_click():
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.015)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)


# ============================================================
# GLOBAL STATE
# ============================================================

running = False
emergency_stop = False

current_bar_color = None


# ============================================================
# COLOR FUNCTIONS
# ============================================================

def colors_match(c1, c2, tolerance=COLOR_TOLERANCE):
    if c1 is None or c2 is None:
        return False

    return (
        abs(c1[0] - c2[0]) <= tolerance and
        abs(c1[1] - c2[1]) <= tolerance and
        abs(c1[2] - c2[2]) <= tolerance
    )


def is_white(color):
    if color is None:
        return False

    return (
        color[0] > 245 and
        color[1] > 245 and
        color[2] > 245
    )


def is_dark(color):
    if color is None:
        return True

    return (
        color[0] < 10 and
        color[1] < 10 and
        color[2] < 10
    )


# ============================================================
# LEARN FISHING BAR COLOR
# ============================================================

def get_bar_color():

    screenshot = pyautogui.screenshot()

    # First try the exact pixel used by the old macro
    color = screenshot.getpixel((955, BAR_Y))

    if not is_white(color) and not is_dark(color):
        return color

    # Try nearby pixels
    for x in range(945, 966):
        color = screenshot.getpixel((x, BAR_Y))

        if not is_white(color) and not is_dark(color):
            return color

    # Last fallback:
    # scan the entire fishing bar
    for x in range(BAR_LEFT, BAR_RIGHT + 1):
        color = screenshot.getpixel((x, BAR_Y))

        if not is_white(color) and not is_dark(color):
            return color

    return None


# ============================================================
# FIND CURRENT BAR
# ============================================================

def find_bar():

    if current_bar_color is None:
        return None

    screenshot = pyautogui.screenshot()

    start_x = None
    end_x = None

    for x in range(BAR_LEFT, BAR_RIGHT + 1):

        color = screenshot.getpixel((x, BAR_Y))

        if colors_match(color, current_bar_color):

            if start_x is None:
                start_x = x

            end_x = x

        else:

            if start_x is not None:
                break

    if start_x is None or end_x is None:
        return None

    width = end_x - start_x

    return start_x, end_x, width


# ============================================================
# WAIT FOR MINIGAME
# ============================================================

def wait_for_minigame():

    print()
    print("Waiting for minigame...")

    start_time = time.time()
    last_status = 0

    while running and not emergency_stop:

        elapsed = time.time() - start_time

        if elapsed - last_status >= 5:
            print(f"Still waiting... {elapsed:.1f}s")
            last_status = elapsed

        screenshot = pyautogui.screenshot()

        pixel = screenshot.getpixel(MINIGAME_START_PIXEL)

        # White pixel means minigame has appeared
        if is_white(pixel):

            print(f"Minigame detected after {elapsed:.1f} seconds!")
            return True

        if elapsed >= MINIGAME_TIMEOUT:

            print("Minigame detection timed out.")
            return False

        time.sleep(0.05)

    return False


# ============================================================
# FISHING MINIGAME
# ============================================================

def play_fishing_minigame():

    global current_bar_color

    print()
    print("======================================")
    print("FISHING MINIGAME")
    print("STATE-BASED DETECTION")
    print("CLICKS ENABLED")
    print("======================================")

    time.sleep(COLOR_SAMPLE_DELAY)

    current_bar_color = get_bar_color()

    if current_bar_color is None:
        print("Could not learn fishing bar color.")
        return

    print(
        f"Bar color learned: RGB("
        f"{current_bar_color[0]}, "
        f"{current_bar_color[1]}, "
        f"{current_bar_color[2]})"
    )

    print("Tracking bar...")

    start_time = time.time()

    click_count = 0

    # --------------------------------------------------------
    # STATE VARIABLES
    # --------------------------------------------------------

    # True = we already clicked while inside the danger zone.
    # We cannot click again until the bar leaves it.
    danger_locked = False

    # True when the rectangle was successfully detected.
    bar_was_visible = False

    # True while we're temporarily using panic mode.
    panic_mode = False

    last_panic_click = 0

    while running and not emergency_stop:

        elapsed = time.time() - start_time

        # Fishing minigame should not run forever
        if elapsed >= 9:
            break

        result = find_bar()

        # ====================================================
        # BAR NOT DETECTED
        # ====================================================

        if result is None:

            # Enter panic mode only after we had actually
            # detected the bar earlier.
            if bar_was_visible:

                panic_mode = True

                now = time.time()

                if now - last_panic_click >= MISSING_COLOR_COOLDOWN:

                    native_click()

                    click_count += 1
                    last_panic_click = now

                    print(
                        f"PANIC CLICK #{click_count} | "
                        f"Color temporarily hidden"
                    )

            time.sleep(SCAN_DELAY)
            continue

        # ====================================================
        # BAR DETECTED AGAIN
        # ====================================================

        start_x, end_x, width = result

        # The SECOND the bar is visible again, panic mode ends.
        if panic_mode:

            print("Bar detected again - panic mode OFF.")

        panic_mode = False
        bar_was_visible = True

        # Reset panic timer so a future disappearance gets
        # a fresh 0.6 second window.
        last_panic_click = 0

        print(
            f"Bar X={start_x}-{end_x} "
            f"Width={width}"
        )

        # ====================================================
        # DANGER ZONE
        # ====================================================

        if width < ADVANCED_FISHING_THRESHOLD:

            # Only click when ENTERING the danger zone.
            # This prevents repeatedly clicking the same
            # stationary rectangle.
            if not danger_locked:

                native_click()

                click_count += 1

                print(
                    f"CLICK #{click_count} | "
                    f"X={start_x}-{end_x} | "
                    f"Width={width}"
                )

                danger_locked = True

                time.sleep(REARM_DELAY)

        else:

            # Rectangle is safely outside the danger zone.
            # This re-arms the detector for the next entry.
            danger_locked = False

        time.sleep(SCAN_DELAY)

    print()
    print(f"Fishing detection finished. Clicks: {click_count}")

    current_bar_color = None

    print("Bar color erased.")


# ============================================================
# CLOSE FISH RESULT
# ============================================================

def close_fish_result():

    if not running or emergency_stop:
        return

    print()
    print("Closing fish result...")
    print(f"Moving to result X: {FISH_RESULT_CLOSE}")

    move_mouse_native(
        FISH_RESULT_CLOSE[0],
        FISH_RESULT_CLOSE[1]
    )

    time.sleep(0.05)

    native_click()

    time.sleep(0.4)

    print("Fish result closed.")


# ============================================================
# ONE FISHING CYCLE
# ============================================================

def fishing_cycle(cycle_number):

    if not running or emergency_stop:
        return False

    print()
    print("======================================")
    print(f"FISHING CYCLE #{cycle_number}")
    print("======================================")

    print("Moving to Fish button...")

    move_mouse_native(
        FISH_BUTTON[0],
        FISH_BUTTON[1]
    )

    time.sleep(0.05)

    native_click()

    if not wait_for_minigame():
        return False

    play_fishing_minigame()

    if not running or emergency_stop:
        return False

    close_fish_result()

    print()
    print(f"Cycle complete! Total cycles: {cycle_number}")

    return True


# ============================================================
# MACRO LOOP
# ============================================================

def macro_loop():

    global running

    cycle_number = 1

    while running and not emergency_stop:

        success = fishing_cycle(cycle_number)

        if not success:
            break

        cycle_number += 1

        time.sleep(0.5)

    print()
    print("Macro loop stopped.")


# ============================================================
# F8 START / STOP
# ============================================================

def toggle_macro():

    global running
    global emergency_stop

    if running:

        print()
        print("Macro PAUSED.")
        running = False

    else:

        emergency_stop = False
        running = True

        print()
        print("Macro STARTED.")

        macro_loop()


# ============================================================
# F3 EMERGENCY STOP
# ============================================================

def emergency():

    global running
    global emergency_stop

    emergency_stop = True
    running = False

    print()
    print("======================================")
    print("EMERGENCY STOP")
    print("======================================")


# ============================================================
# MAIN
# ============================================================

print("======================================")
print("SOLS RNG FISHING MACRO")
print("======================================")
print("F8 = Start")
print("F3 = Emergency Stop")
print()
print("Fishing + fish-result loop enabled.")
print(f"Advanced threshold: {ADVANCED_FISHING_THRESHOLD} pixels")
print("State-based clicking enabled.")
print("Panic cooldown: 0.60 seconds")
print("======================================")

keyboard.add_hotkey("f8", toggle_macro)
keyboard.add_hotkey("f3", emergency)

try:

    while True:
        time.sleep(0.1)

except KeyboardInterrupt:

    emergency()
