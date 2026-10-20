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

# EXACT old 1080p fishing line
BAR_LEFT_X = 757
BAR_RIGHT_X = 1161
BAR_Y = 767

ADVANCED_THRESHOLD = 25

# Old macro timing
FISHING_DETECTION_TIME = 9.0
BAR_CHECK_DELAY = 0.010
SUCCESS_CLICK_DELAY = 0.025

# After minigame
RESULT_MOVE_DELAY = 0.30
RESULT_CLICK_DELAY = 0.70

# Mouse movement
MOUSE_TOLERANCE = 2


# ============================================================
# WINDOWS MOUSE
# ============================================================

user32 = ctypes.windll.user32

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004


def get_mouse_position():

    point = ctypes.wintypes.POINT()

    user32.GetCursorPos(
        ctypes.byref(point)
    )

    return point.x, point.y


def move_mouse_native(target_x, target_y):

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
# SCREENSHOT
# ============================================================

def take_bar_screenshot():

    try:

        return pyautogui.screenshot(
            region=(
                BAR_LEFT_X,
                BAR_Y,
                BAR_RIGHT_X - BAR_LEFT_X + 1,
                1
            )
        )

    except Exception:
        return None


# ============================================================
# COLOR HELPERS
# ============================================================

def color_close(color1, color2, tolerance):

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


# ============================================================
# LEARN BAR COLOR
# ============================================================

def learn_bar_color():

    # --------------------------------------------------------
    # EXACT OLD MACRO SAMPLE
    # --------------------------------------------------------

    try:

        screenshot = pyautogui.screenshot(
            region=(
                BAR_LEFT_X,
                BAR_Y,
                BAR_RIGHT_X - BAR_LEFT_X + 1,
                1
            )
        )

    except Exception:

        return None

    # 955 - 757 = 198
    old_sample_x = 955 - BAR_LEFT_X

    color = screenshot.getpixel(
        (old_sample_x, 0)
    )

    # If the old sample is usable, use it.
    if color is not None and not is_white(color):

        print(
            f"Using old sample point: "
            f"RGB{color}"
        )

        return color

    # --------------------------------------------------------
    # If the sample happens to be white, find a nearby
    # non-white pixel.
    # --------------------------------------------------------

    for offset in range(-20, 21):

        x = old_sample_x + offset

        if x < 0 or x >= screenshot.width:
            continue

        color = screenshot.getpixel(
            (x, 0)
        )

        if color is None:
            continue

        if not is_white(color):

            print(
                f"Using nearby bar color: "
                f"RGB{color}"
            )

            return color

    return None


# ============================================================
# FIND RECTANGLE
# ============================================================

def find_bar(bar_color, screenshot):

    if screenshot is None:
        return None

    left_x = None

    # --------------------------------------------------------
    # Same idea as old PixelSearch:
    # scan left -> right for matching color.
    # --------------------------------------------------------

    for local_x in range(
        screenshot.width
    ):

        pixel = screenshot.getpixel(
            (local_x, 0)
        )

        if color_close(
            pixel,
            bar_color,
            5
        ):

            left_x = BAR_LEFT_X + local_x

            break

    # --------------------------------------------------------
    # Nothing found
    # --------------------------------------------------------

    if left_x is None:
        return None

    # --------------------------------------------------------
    # Expand right using tolerance 10,
    # exactly like the old macro.
    # --------------------------------------------------------

    right_x = left_x

    start_local = left_x - BAR_LEFT_X + 1

    for local_x in range(
        start_local,
        screenshot.width
    ):

        pixel = screenshot.getpixel(
            (local_x, 0)
        )

        if color_close(
            pixel,
            bar_color,
            10
        ):

            right_x = BAR_LEFT_X + local_x

        else:

            break

    width = right_x - left_x

    center = (
        left_x + right_x
    ) // 2

    return (
        left_x,
        right_x,
        width,
        center
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

        elapsed = (
            time.time() - start_time
        )

        if elapsed - last_message >= 5:

            print(
                f"Still waiting... "
                f"{elapsed:.1f}s"
            )

            last_message = elapsed

        try:

            pixel = pyautogui.pixel(
                MINIGAME_START_PIXEL[0],
                MINIGAME_START_PIXEL[1]
            )

        except Exception:

            pixel = None

        if pixel is not None:

            if (
                pixel[0] >= 245
                and pixel[1] >= 245
                and pixel[2] >= 245
            ):

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
    print("OLD MACRO STYLE")
    print("FAST SCREENSHOT SCANNING")
    print("======================================")

    # --------------------------------------------------------
    # Learn bar color
    # --------------------------------------------------------

    bar_color = learn_bar_color()

    if bar_color is None:

        print(
            "Could not learn bar color."
        )

        return False

    print(
        f"Bar color learned: "
        f"RGB({bar_color[0]}, "
        f"{bar_color[1]}, "
        f"{bar_color[2]})"
    )

    print(
        f"Fishing line: "
        f"X={BAR_LEFT_X}-{BAR_RIGHT_X}, "
        f"Y={BAR_Y}"
    )

    # --------------------------------------------------------
    # OLD 9 SECOND LOOP
    # --------------------------------------------------------

    start_time = time.time()

    clicks = 0
    detections = 0
    misses = 0

    while running:

        if (
            time.time() - start_time
            >= FISHING_DETECTION_TIME
        ):
            break

        # ----------------------------------------------------
        # ONE screenshot instead of 400+ individual
        # pyautogui.pixel() calls.
        # ----------------------------------------------------

        screenshot = take_bar_screenshot()

        bar = find_bar(
            bar_color,
            screenshot
        )

        # ----------------------------------------------------
        # RECTANGLE FOUND
        # ----------------------------------------------------

        if bar is not None:

            left_x, right_x, width, center = bar

            detections += 1

            # Only print every few detections so CMD
            # doesn't become insanely huge.
            if detections % 5 == 0:

                print(
                    f"Bar X={left_x}-{right_x} "
                    f"Width={width} "
                    f"Center={center}"
                )

            # ------------------------------------------------
            # OLD MACRO RULE
            # ------------------------------------------------

            if width < ADVANCED_THRESHOLD:

                native_click()

                clicks += 1

                print(
                    f"CLICK #{clicks} "
                    f"| Bar {left_x}-{right_x} "
                    f"| Width {width}"
                )

                time.sleep(
                    SUCCESS_CLICK_DELAY
                )

        # ----------------------------------------------------
        # BAR NOT FOUND
        #
        # This is what the old macro did:
        # CLICK.
        # ----------------------------------------------------

        else:

            misses += 1

            native_click()

            clicks += 1

            if misses % 5 == 0:

                print(
                    f"Rapid click #{clicks} "
                    f"| bar not detected"
                )

        time.sleep(
            BAR_CHECK_DELAY
        )

    print()
    print(
        "Fishing detection finished."
    )

    print(
        f"Bar detections: {detections}"
    )

    print(
        f"Missed scans: {misses}"
    )

    print(
        f"Total clicks: {clicks}"
    )

    return True


# ============================================================
# CLOSE RESULT
# ============================================================

def close_fish_result():

    if not running:
        return False

    # --------------------------------------------------------
    # OLD MACRO:
    # sleep 300
    # MouseMove X
    # Sleep 700
    # Click
    # --------------------------------------------------------

    print()
    print("Moving to fish-result X...")

    time.sleep(
        RESULT_MOVE_DELAY
    )

    if not running:
        return False

    if not move_mouse_native(
        FISH_RESULT_CLOSE[0],
        FISH_RESULT_CLOSE[1]
    ):
        return False

    print(
        f"Mouse at X: "
        f"{get_mouse_position()}"
    )

    time.sleep(
        RESULT_CLICK_DELAY
    )

    if not running:
        return False

    native_click()

    print(
        "Fish-result X clicked."
    )

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
    # FISH BUTTON
    # --------------------------------------------------------

    print(
        "Moving to Fish button..."
    )

    if not move_mouse_native(
        FISH_BUTTON[0],
        FISH_BUTTON[1]
    ):
        return False

    print(
        f"Mouse position: "
        f"{get_mouse_position()}"
    )

    time.sleep(0.10)

    if not running:
        return False

    print(
        "Clicking Fish..."
    )

    native_click()

    # --------------------------------------------------------
    # WAIT FOR MINIGAME
    # --------------------------------------------------------

    if not wait_for_minigame():
        return False

    if not running:
        return False

    # --------------------------------------------------------
    # MINIGAME
    # --------------------------------------------------------

    fishing_minigame()

    if not running:
        return False

    # --------------------------------------------------------
    # RESULT X
    #
    # Immediately proceeds to the X after the detection
    # period. No extra 5-second wait.
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
print("Old fishing behavior restored.")
print(
    "Fast screenshot-based bar scanning."
)
print(
    f"Fishing line: "
    f"{BAR_LEFT_X}-{BAR_RIGHT_X} "
    f"at Y={BAR_Y}"
)
print(
    f"Threshold: "
    f"{ADVANCED_THRESHOLD}"
)
print(
    f"Detection time: "
    f"{FISHING_DETECTION_TIME:.1f}s"
)
print(
    "No slow panic cooldown."
)
print(
    "Result X has old 300ms/700ms timing."
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
