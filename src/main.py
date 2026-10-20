import time
import threading
import ctypes
import ctypes.wintypes
import pyautogui
import keyboard


# ============================================================
# SETTINGS
# ============================================================

FISH_BUTTON = (853, 832)
FISH_RESULT_CLOSE = (1113, 342)

MINIGAME_START_PIXEL = (1176, 836)

# Exact 1080p fishing line from the old macro
BAR_LEFT_X = 757
BAR_RIGHT_X = 1161
BAR_Y = 767

# Old macro settings
ADVANCED_THRESHOLD = 25

# Old macro timing
FISHING_DETECTION_TIME = 9.0
BAR_CHECK_DELAY = 0.010
SUCCESS_CLICK_DELAY = 0.025

# Result X timing from old macro
RESULT_MOVE_DELAY = 0.30
RESULT_CLICK_DELAY = 0.70

# Mouse movement
MOUSE_TOLERANCE = 2


# ============================================================
# WINDOWS MOUSE CONTROL
# ============================================================

user32 = ctypes.windll.user32

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004


def get_mouse_position():
    point = ctypes.wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(point))
    return point.x, point.y


def move_mouse_native(target_x, target_y):
    """
    Uses small relative Windows mouse movements and constantly
    checks the REAL cursor position.
    """

    for _ in range(600):

        if not running:
            return False

        current_x, current_y = get_mouse_position()

        dx = target_x - current_x
        dy = target_y - current_y

        if (
            abs(dx) <= MOUSE_TOLERANCE
            and abs(dy) <= MOUSE_TOLERANCE
        ):
            return True

        step_x = max(-3, min(3, dx))
        step_y = max(-3, min(3, dy))

        user32.mouse_event(
            MOUSEEVENTF_MOVE,
            int(step_x),
            int(step_y),
            0,
            0
        )

        time.sleep(0.004)

    print("WARNING: Mouse movement timed out.")
    return False


def native_click():
    user32.mouse_event(
        MOUSEEVENTF_LEFTDOWN,
        0,
        0,
        0,
        0
    )

    time.sleep(0.008)

    user32.mouse_event(
        MOUSEEVENTF_LEFTUP,
        0,
        0,
        0,
        0
    )


# ============================================================
# PIXEL FUNCTIONS
# ============================================================

def get_pixel(x, y):
    try:
        return pyautogui.pixel(x, y)
    except Exception:
        return None


def color_close(color1, color2, tolerance=10):

    if color1 is None or color2 is None:
        return False

    return (
        abs(color1[0] - color2[0]) <= tolerance
        and
        abs(color1[1] - color2[1]) <= tolerance
        and
        abs(color1[2] - color2[2]) <= tolerance
    )


def is_white(color):
    if color is None:
        return False

    return (
        color[0] >= 245
        and color[1] >= 245
        and color[2] >= 245
    )


def is_colored(color):
    """
    Used when the old sample point happens to land on white.

    The fishing rectangle in the working runs has been a
    colored/purple pixel rather than pure white.
    """

    if color is None:
        return False

    r, g, b = color

    if r >= 245 and g >= 245 and b >= 245:
        return False

    if r <= 15 and g <= 15 and b <= 15:
        return False

    maximum = max(r, g, b)
    minimum = min(r, g, b)

    return (maximum - minimum) >= 20


# ============================================================
# LEARN BAR COLOR
# ============================================================

def learn_bar_color():
    """
    First tries the exact sample used by the old macro.

    If that point is white, scan the entire fishing line and
    find a colored pixel instead of incorrectly learning white.
    """

    # --------------------------------------------------------
    # EXACT OLD MACRO SAMPLE
    # --------------------------------------------------------

    sample = get_pixel(955, BAR_Y)

    if sample is not None and not is_white(sample):
        return sample

    # --------------------------------------------------------
    # SAMPLE NEAR THE OLD LOCATION
    # --------------------------------------------------------

    for x in range(940, 971):

        color = get_pixel(x, BAR_Y)

        if color is not None and not is_white(color):

            if is_colored(color):
                return color

    # --------------------------------------------------------
    # SCAN THE WHOLE LINE
    # --------------------------------------------------------

    candidates = []

    for x in range(BAR_LEFT_X, BAR_RIGHT_X + 1):

        color = get_pixel(x, BAR_Y)

        if color is None:
            continue

        if is_colored(color):
            candidates.append((x, color))

    if not candidates:
        return None

    # --------------------------------------------------------
    # Prefer the candidate closest to the old sample point.
    # --------------------------------------------------------

    candidates.sort(
        key=lambda item: abs(item[0] - 955)
    )

    return candidates[0][1]


# ============================================================
# FIND RECTANGLE
# ============================================================

def find_bar(bar_color):
    """
    Direct translation of the old macro's advanced detection:

    1. Search the exact fishing line.
    2. Find the first matching pixel.
    3. Continue right while the color remains close.
    4. Calculate width.
    """

    left_x = None

    # Equivalent to old PixelSearch:
    #
    # 757,767 -> 1161,767
    #
    for x in range(BAR_LEFT_X, BAR_RIGHT_X + 1):

        pixel = get_pixel(x, BAR_Y)

        if color_close(pixel, bar_color, 5):

            left_x = x
            break

    if left_x is None:
        return None

    # --------------------------------------------------------
    # Find right edge
    # --------------------------------------------------------

    right_x = left_x

    for x in range(left_x + 1, BAR_RIGHT_X + 1):

        pixel = get_pixel(x, BAR_Y)

        if color_close(pixel, bar_color, 10):
            right_x = x
        else:
            break

    width = right_x - left_x

    center_x = (left_x + right_x) // 2

    return (
        left_x,
        right_x,
        width,
        center_x
    )


# ============================================================
# WAIT FOR MINIGAME
# ============================================================

def wait_for_minigame():

    print()
    print("Waiting for minigame...")

    start_time = time.time()
    last_message = 0

    while running:

        elapsed = time.time() - start_time

        if elapsed - last_message >= 5:

            print(
                f"Still waiting... "
                f"{elapsed:.1f}s"
            )

            last_message = elapsed

        pixel = get_pixel(
            MINIGAME_START_PIXEL[0],
            MINIGAME_START_PIXEL[1]
        )

        if is_white(pixel):

            print(
                f"Minigame detected after "
                f"{elapsed:.1f} seconds!"
            )

            return True

        time.sleep(0.01)

    return False


# ============================================================
# FISHING MINIGAME
# ============================================================

def fishing_minigame():

    print()
    print("======================================")
    print("FISHING MINIGAME")
    print("OLD MACRO DETECTION MODE")
    print("======================================")

    # --------------------------------------------------------
    # Learn the rectangle color
    # --------------------------------------------------------

    bar_color = learn_bar_color()

    if bar_color is None:

        print(
            "WARNING: Could not find a colored "
            "fishing-bar pixel."
        )

        print(
            "Falling back to direct rapid clicking."
        )

        # Still behave like the old macro if color
        # detection completely fails.
        start = time.time()

        while running:

            if time.time() - start >= FISHING_DETECTION_TIME:
                break

            native_click()

            time.sleep(BAR_CHECK_DELAY)

        return True

    print(
        f"Bar color learned: "
        f"RGB({bar_color[0]}, "
        f"{bar_color[1]}, "
        f"{bar_color[2]})"
    )

    print(
        f"Tracking line: "
        f"X={BAR_LEFT_X}-{BAR_RIGHT_X}, "
        f"Y={BAR_Y}"
    )

    print(
        f"Advanced threshold: "
        f"{ADVANCED_THRESHOLD}"
    )

    # --------------------------------------------------------
    # OLD MACRO LOOP
    #
    # The old macro ran this for 9 seconds.
    # --------------------------------------------------------

    start_time = time.time()

    clicks = 0
    detected_bars = 0
    missed_bars = 0

    while running:

        if (
            time.time() - start_time
            >= FISHING_DETECTION_TIME
        ):
            break

        # ----------------------------------------------------
        # Find rectangle
        # ----------------------------------------------------

        bar = find_bar(bar_color)

        # ----------------------------------------------------
        # RECTANGLE FOUND
        # ----------------------------------------------------

        if bar is not None:

            left_x, right_x, width, center_x = bar

            detected_bars += 1

            print(
                f"Bar X={left_x}-{right_x} "
                f"Width={width} "
                f"Center={center_x}"
            )

            # ------------------------------------------------
            # EXACT OLD MACRO RULE
            # ------------------------------------------------

            if width < ADVANCED_THRESHOLD:

                if not running:
                    break

                native_click()

                clicks += 1

                print(
                    f"CLICK #{clicks} | "
                    f"Width={width}"
                )

                time.sleep(
                    SUCCESS_CLICK_DELAY
                )

        # ----------------------------------------------------
        # RECTANGLE NOT FOUND
        #
        # IMPORTANT:
        # The old macro clicked immediately here.
        # No 0.22 second panic cooldown.
        # ----------------------------------------------------

        else:

            missed_bars += 1

            if not running:
                break

            native_click()

            clicks += 1

            print(
                f"PANIC CLICK #{clicks}"
            )

        # ----------------------------------------------------
        # Old macro checks approximately every 10ms.
        # ----------------------------------------------------

        time.sleep(BAR_CHECK_DELAY)

    print()
    print(
        f"Fishing detection finished."
    )

    print(
        f"Detected bars: {detected_bars}"
    )

    print(
        f"Missed scans: {missed_bars}"
    )

    print(
        f"Total clicks: {clicks}"
    )

    return True


# ============================================================
# CLOSE FISH RESULT
# ============================================================

def close_fish_result():

    if not running:
        return False

    print()
    print("Preparing to close fish result...")

    # --------------------------------------------------------
    # Old macro waited 300ms before moving to X
    # --------------------------------------------------------

    time.sleep(RESULT_MOVE_DELAY)

    if not running:
        return False

    print("Moving to result X...")

    if not move_mouse_native(
        FISH_RESULT_CLOSE[0],
        FISH_RESULT_CLOSE[1]
    ):
        return False

    if not running:
        return False

    print(
        f"Mouse position at X: "
        f"{get_mouse_position()}"
    )

    # --------------------------------------------------------
    # Old macro waited 700ms before clicking
    # --------------------------------------------------------

    time.sleep(RESULT_CLICK_DELAY)

    if not running:
        return False

    native_click()

    print("Fish result X clicked.")

    return True


# ============================================================
# FISHING CYCLE
# ============================================================

def fishing_cycle(cycle_number):

    print()
    print("======================================")
    print(
        f"FISHING CYCLE #{cycle_number}"
    )
    print("======================================")

    # --------------------------------------------------------
    # Move to Fish button
    # --------------------------------------------------------

    print("Moving to Fish button...")

    if not move_mouse_native(
        FISH_BUTTON[0],
        FISH_BUTTON[1]
    ):
        return False

    print(
        f"Mouse position after movement: "
        f"{get_mouse_position()}"
    )

    if not running:
        return False

    time.sleep(0.10)

    # --------------------------------------------------------
    # Click Fish
    # --------------------------------------------------------

    print("Clicking Fish...")

    native_click()

    # --------------------------------------------------------
    # Wait for minigame
    # --------------------------------------------------------

    if not wait_for_minigame():
        return False

    if not running:
        return False

    # --------------------------------------------------------
    # Play minigame
    # --------------------------------------------------------

    fishing_minigame()

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # Even if detection isn't perfect, we still go to the
    # result X just like the old macro did after its 9-second
    # detection loop.
    # --------------------------------------------------------

    if not running:
        return False

    # --------------------------------------------------------
    # Close result
    # --------------------------------------------------------

    if not close_fish_result():
        return False

    if not running:
        return False

    time.sleep(0.30)

    return True


# ============================================================
# MACRO LOOP
# ============================================================

running = False
macro_thread = None
cycle_count = 0


def macro_loop():

    global cycle_count

    cycle_count = 0

    while running:

        cycle_count += 1

        success = fishing_cycle(
            cycle_count
        )

        if not running:
            break

        if not success:

            print()
            print(
                "Fishing cycle stopped."
            )

            break

        print()
        print(
            f"Cycle complete! "
            f"Total cycles: {cycle_count}"
        )

        time.sleep(0.20)

    print()
    print("Macro loop stopped.")


# ============================================================
# HOTKEYS
# ============================================================

def start_pause_macro():

    global running
    global macro_thread

    if running:

        running = False

        print()
        print("Macro PAUSED.")

        return

    running = True

    print()
    print("Macro STARTED.")

    macro_thread = threading.Thread(
        target=macro_loop,
        daemon=True
    )

    macro_thread.start()


def emergency_stop():

    global running

    running = False

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
print("Old-style fishing detection restored.")
print(
    f"Fishing line: "
    f"X={BAR_LEFT_X}-{BAR_RIGHT_X}, "
    f"Y={BAR_Y}"
)
print(
    f"Advanced threshold: "
    f"{ADVANCED_THRESHOLD}"
)
print(
    f"Fishing detection time: "
    f"{FISHING_DETECTION_TIME:.1f}s"
)
print(
    "Rapid missed-bar clicking enabled."
)
print(
    "Native Roblox-compatible mouse enabled."
)
print("======================================")
print()

keyboard.add_hotkey(
    "f8",
    start_pause_macro
)

keyboard.add_hotkey(
    "f3",
    emergency_stop
)

try:

    while True:
        time.sleep(0.1)

except KeyboardInterrupt:

    running = False

    print()
    print("Program closed.")
