import ctypes
import time
import threading
import pyautogui
import keyboard

# ======================================
# SOLS RNG FISHING MACRO
# ======================================

FISH_BUTTON = (853, 832)
FISH_RESULT_CLOSE = (1113, 342)

MINIGAME_START_PIXEL = (1176, 836)

BAR_LEFT_X = 757
BAR_RIGHT_X = 1161
BAR_Y = 767

ADVANCED_THRESHOLD = 25

FISHING_DETECTION_TIME = 9.0

# Old macro timing
BAR_CHECK_DELAY = 0.010
SUCCESS_CLICK_DELAY = 0.025

# Slower panic clicking
PANIC_CLICK_DELAY = 0.300
PANIC_START_DELAY = 0.500

# Result X timing
RESULT_MOVE_DELAY = 0.30
RESULT_CLICK_DELAY = 0.70


# ======================================
# WINDOWS MOUSE INPUT
# ======================================

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
    user32.GetCursorPos(ctypes.byref(point))
    return point.x, point.y


def native_move_relative(dx, dy):
    user32.mouse_event(
        MOUSEEVENTF_MOVE,
        int(dx),
        int(dy),
        0,
        0
    )


def move_mouse_to(x, y):
    while running:

        current_x, current_y = get_mouse_position()

        dx = x - current_x
        dy = y - current_y

        if abs(dx) <= 2 and abs(dy) <= 2:
            return True

        step_x = max(-3, min(3, dx))
        step_y = max(-3, min(3, dy))

        native_move_relative(step_x, step_y)

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

    time.sleep(0.010)

    user32.mouse_event(
        MOUSEEVENTF_LEFTUP,
        0,
        0,
        0,
        0
    )


# ======================================
# GLOBAL STATE
# ======================================

running = False
emergency_stop = False
cycle_count = 0


# ======================================
# COLOR HELPERS
# ======================================

def color_matches(color, target, tolerance):
    return (
        abs(color[0] - target[0]) <= tolerance and
        abs(color[1] - target[1]) <= tolerance and
        abs(color[2] - target[2]) <= tolerance
    )


def is_white(color):
    return (
        color[0] > 240 and
        color[1] > 240 and
        color[2] > 240
    )


# ======================================
# BAR SCREENSHOT
# ======================================

def take_bar_screenshot():
    return pyautogui.screenshot(
        region=(
            BAR_LEFT_X,
            BAR_Y,
            BAR_RIGHT_X - BAR_LEFT_X + 1,
            1
        )
    )


# ======================================
# LEARN BAR COLOR
# ======================================

def learn_bar_color():
    """
    EXACTLY follows the old macro's sample location:
    X=955, Y=767.

    We do NOT dynamically guess random colors.
    """

    screenshot = take_bar_screenshot()

    sample_x = 955 - BAR_LEFT_X

    color = screenshot.getpixel(
        (sample_x, 0)
    )

    print(
        f"Using old sample point: RGB{color}"
    )

    return color


# ======================================
# FIND BAR
# ======================================

def find_bar(bar_color, screenshot):
    """
    Recreates the old AHK PixelSearch behavior.

    First matching pixel:
        tolerance 5

    Then expand to the right:
        tolerance 10

    No mouse movement happens here.
    """

    pixels = screenshot.load()

    left = None

    # ----------------------------------
    # Find first matching pixel
    # ----------------------------------

    for x in range(screenshot.width):

        color = pixels[x, 0]

        if color_matches(
            color,
            bar_color,
            5
        ):

            left = x
            break

    if left is None:
        return None

    # ----------------------------------
    # Expand right
    # ----------------------------------

    right = left

    while right + 1 < screenshot.width:

        test_color = pixels[
            right + 1,
            0
        ]

        if color_matches(
            test_color,
            bar_color,
            10
        ):

            right += 1

        else:
            break

    left_x = BAR_LEFT_X + left
    right_x = BAR_LEFT_X + right

    width = right_x - left_x

    center_x = (
        left_x + right_x
    ) // 2

    return (
        left_x,
        right_x,
        width,
        center_x
    )


# ======================================
# WAIT FOR MINIGAME
# ======================================

def wait_for_minigame():

    print()
    print("Waiting for minigame...")

    start = time.time()
    last_report = 0

    while running:

        try:

            color = pyautogui.pixel(
                MINIGAME_START_PIXEL[0],
                MINIGAME_START_PIXEL[1]
            )

        except Exception:

            time.sleep(0.05)
            continue

        if is_white(color):

            elapsed = time.time() - start

            print(
                f"Minigame detected after "
                f"{elapsed:.1f} seconds!"
            )

            return True

        elapsed = time.time() - start

        if elapsed - last_report >= 5:

            print(
                f"Still waiting... "
                f"{elapsed:.1f}s"
            )

            last_report = elapsed

        time.sleep(0.05)

    return False


# ======================================
# FISHING MINIGAME
# ======================================

def fishing_minigame():

    print()
    print("======================================")
    print("FISHING MINIGAME")
    print("OLD MACRO STYLE")
    print("FAST SCREENSHOT SCANNING")
    print("======================================")

    print(
        f"Fishing line: "
        f"X={BAR_LEFT_X}-{BAR_RIGHT_X}, "
        f"Y={BAR_Y}"
    )

    # Learn ONLY from the old sample point.
    bar_color = learn_bar_color()

    print(
        f"Bar color learned: RGB{bar_color}"
    )

    print(
        f"Advanced threshold: "
        f"{ADVANCED_THRESHOLD}"
    )

    start_time = time.time()

    clicks = 0
    detections = 0
    missed_scans = 0

    last_panic_click = (
        time.time() - PANIC_CLICK_DELAY
    )

    panic_allowed_at = (
        time.time() + PANIC_START_DELAY
    )

    while running:

        if (
            time.time() - start_time
            >= FISHING_DETECTION_TIME
        ):
            break

        # One fast screenshot
        screenshot = take_bar_screenshot()

        found = find_bar(
            bar_color,
            screenshot
        )

        # ==================================
        # BAR FOUND
        # ==================================

        if found is not None:

            left_x, right_x, width, center_x = found

            detections += 1

            # Print useful detections only
            if width < ADVANCED_THRESHOLD:

                print(
                    f"BAR FOUND: "
                    f"{left_x}-{right_x} "
                    f"Width={width} "
                    f"Center={center_x}"
                )

                # IMPORTANT:
                # DO NOT MOVE THE MOUSE.
                #
                # The bar's screen position is only
                # being used for detection.
                #
                # The mouse stays where it already is.

                native_click()

                clicks += 1

                print(
                    f"CLICK #{clicks}"
                )

                time.sleep(
                    SUCCESS_CLICK_DELAY
                )

            else:

                # Bar exists but is too wide.
                # Don't click yet.
                time.sleep(
                    BAR_CHECK_DELAY
                )

        # ==================================
        # BAR NOT FOUND
        # ==================================

        else:

            missed_scans += 1

            now = time.time()

            # Slow panic click.
            if (
                now >= panic_allowed_at
                and
                now - last_panic_click
                >= PANIC_CLICK_DELAY
            ):

                native_click()

                clicks += 1

                print(
                    f"PANIC CLICK #{clicks} "
                    f"(bar not detected)"
                )

                last_panic_click = time.time()

            time.sleep(
                BAR_CHECK_DELAY
            )

    print()
    print("Fishing detection finished.")

    print(
        f"Bar detections: "
        f"{detections}"
    )

    print(
        f"Missed scans: "
        f"{missed_scans}"
    )

    print(
        f"Total clicks: "
        f"{clicks}"
    )


# ======================================
# FISHING CYCLE
# ======================================

def fishing_cycle():

    global cycle_count

    cycle_count += 1

    print()
    print("======================================")
    print(
        f"FISHING CYCLE #{cycle_count}"
    )
    print("======================================")

    # ----------------------------------
    # Fish button
    # ----------------------------------

    print(
        "Moving to Fish button..."
    )

    move_mouse_to(
        FISH_BUTTON[0],
        FISH_BUTTON[1]
    )

    if not running:
        return

    print(
        f"Mouse position: "
        f"{get_mouse_position()}"
    )

    print(
        "Clicking Fish..."
    )

    native_click()

    time.sleep(0.20)

    # ----------------------------------
    # Minigame
    # ----------------------------------

    if not wait_for_minigame():
        return

    if not running:
        return

    fishing_minigame()

    if not running:
        return

    # ----------------------------------
    # Result X
    # ----------------------------------

    print()
    print(
        "Moving to fish-result X..."
    )

    time.sleep(
        RESULT_MOVE_DELAY
    )

    move_mouse_to(
        FISH_RESULT_CLOSE[0],
        FISH_RESULT_CLOSE[1]
    )

    if not running:
        return

    print(
        f"Mouse at X: "
        f"{get_mouse_position()}"
    )

    time.sleep(
        RESULT_CLICK_DELAY
    )

    native_click()

    print(
        "Fish-result X clicked."
    )

    time.sleep(0.30)

    print(
        f"Cycle complete! "
        f"Total cycles: {cycle_count}"
    )


# ======================================
# MACRO LOOP
# ======================================

def macro_loop():

    global running

    while running:

        fishing_cycle()

        if not running:
            break

        time.sleep(0.30)


# ======================================
# HOTKEYS
# ======================================

def toggle_macro():

    global running

    if running:

        running = False

        print()
        print(
            "Macro PAUSED."
        )

    else:

        running = True

        print()
        print(
            "Macro STARTED."
        )

        thread = threading.Thread(
            target=macro_loop,
            daemon=True
        )

        thread.start()


def emergency_stop():

    global running
    global emergency_stop

    emergency_stop = True
    running = False

    print()
    print(
        "!!! EMERGENCY STOP !!!"
    )


# ======================================
# MAIN
# ======================================

print("======================================")
print("SOLS RNG FISHING MACRO")
print("======================================")
print("F8 = Start / Pause")
print("F3 = Emergency Stop")
print()
print("Old fishing behavior restored.")
print("Fast screenshot-based bar scanning.")
print(
    "Mouse does NOT follow the rectangle."
)
print(
    "Panic clicks: 300ms apart."
)
print(
    "No dynamic color re-learning."
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
    f"{FISHING_DETECTION_TIME}s"
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
    emergency_stop
)

try:

    while True:
        time.sleep(0.1)

except KeyboardInterrupt:

    running = False

    print()
    print(
        "Program closed."
    )
