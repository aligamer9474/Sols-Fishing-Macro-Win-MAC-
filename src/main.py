import time
import threading
import ctypes
import keyboard
import pyautogui


# ============================================================
# SETTINGS
# ============================================================

FISH_BUTTON = (853, 832)

# Old macro's 1080p fish-result close button
FISH_RESULT_CLOSE = (1113, 342)

MINIGAME_START_PIXEL = (1176, 836)
MINIGAME_TIMEOUT = 19

BAR_LEFT = 757
BAR_RIGHT = 1161
BAR_Y = 767

ADVANCED_FISHING_THRESHOLD = 25

COLOR_SAMPLE_DELAY = 0.050
SCAN_DELAY = 0.010

COLOR_TOLERANCE = 10

running = False

current_bar_color = None

cycle_count = 0


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

        if not running:
            return

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

    if not running:
        return

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

    if not running:
        return

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


def colors_match(color1, color2):

    if color1 is None or color2 is None:
        return False

    return (
        abs(color1[0] - color2[0])
        <= COLOR_TOLERANCE
        and
        abs(color1[1] - color2[1])
        <= COLOR_TOLERANCE
        and
        abs(color1[2] - color2[2])
        <= COLOR_TOLERANCE
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

        if not running:
            return False

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
# GET BAR COLOR
# ============================================================

def get_bar_color():

    color = get_pixel(
        955,
        767
    )

    if not is_white(color):

        return color

    nearby_positions = [
        (954, 767),
        (956, 767),
        (953, 767),
        (957, 767),
        (952, 767),
        (958, 767),
        (951, 767),
        (959, 767),
        (950, 767),
        (960, 767)
    ]

    for x, y in nearby_positions:

        color = get_pixel(
            x,
            y
        )

        if not is_white(color):

            return color

    for x in range(
        BAR_LEFT,
        BAR_RIGHT + 1
    ):

        if not running:
            return None

        color = get_pixel(
            x,
            BAR_Y
        )

        if not is_white(color):

            r, g, b = color

            if (
                r > 10
                or g > 10
                or b > 10
            ):

                return color

    return None


# ============================================================
# FIND BAR
# ============================================================

def find_bar(bar_color):

    if bar_color is None:
        return None

    if not running:
        return None

    width = (
        BAR_RIGHT
        - BAR_LEFT
        + 1
    )

    screenshot = pyautogui.screenshot(
        region=(
            BAR_LEFT,
            BAR_Y,
            width,
            1
        )
    )

    left_x = None

    for i in range(width):

        if not running:
            return None

        color = screenshot.getpixel(
            (i, 0)
        )

        if colors_match(
            color,
            bar_color
        ):

            left_x = (
                BAR_LEFT
                + i
            )

            break

    if left_x is None:

        return None

    right_x = left_x

    while True:

        test_x = (
            right_x
            + 1
        )

        if test_x > BAR_RIGHT:
            break

        pixel_x = (
            test_x
            - BAR_LEFT
        )

        test_color = screenshot.getpixel(
            (pixel_x, 0)
        )

        if colors_match(
            test_color,
            bar_color
        ):

            right_x = test_x

        else:

            break

    bar_width = (
        right_x
        - left_x
    )

    return (
        left_x,
        right_x,
        bar_width
    )


# ============================================================
# FISHING MINIGAME
# ============================================================

def play_fishing_minigame():

    global current_bar_color

    print()
    print("======================================")
    print("FISHING MINIGAME")
    print("OLD MACRO DETECTION")
    print("CLICKS ENABLED")
    print("======================================")

    native_move_to(
        950,
        880
    )

    if not running:
        return False

    time.sleep(
        COLOR_SAMPLE_DELAY
    )

    if not running:
        return False

    current_bar_color = get_bar_color()

    if current_bar_color is None:

        print(
            "Could not determine fishing bar color."
        )

        current_bar_color = None

        return False

    print(
        f"Bar color learned: "
        f"RGB{current_bar_color}"
    )

    print(
        "Tracking bar..."
    )

    start_time = time.time()

    click_count = 0

    last_click_time = 0

    while (
        time.time() - start_time
        < 9.0
    ):

        if not running:
            break

        result = find_bar(
            current_bar_color
        )

        if result is None:

            now = time.time()

            if (
                now - last_click_time
                >= 0.025
            ):

                native_click()

                click_count += 1

                last_click_time = now

                print(
                    f"CLICK #{click_count} "
                    f"| Bar color not found"
                )

            time.sleep(
                SCAN_DELAY
            )

            continue

        left_x, right_x, bar_width = result

        print(
            f"\rBar X={left_x}-{right_x} "
            f"Width={bar_width}",
            end=""
        )

        if (
            bar_width
            < ADVANCED_FISHING_THRESHOLD
        ):

            now = time.time()

            if (
                now - last_click_time
                >= 0.025
            ):

                native_click()

                click_count += 1

                last_click_time = now

                print()

                print(
                    f"CLICK #{click_count} "
                    f"| X={left_x}-{right_x} "
                    f"| Width={bar_width}"
                )

                time.sleep(
                    0.025
                )

        time.sleep(
            SCAN_DELAY
        )

    print()

    print(
        f"Fishing detection finished. "
        f"Clicks: {click_count}"
    )

    current_bar_color = None

    print(
        "Bar color erased."
    )

    return True


# ============================================================
# CLOSE FISH RESULT
# ============================================================

def close_fish_result():

    print()
    print("Closing fish result...")

    # Same basic timing as the old macro.
    time.sleep(0.30)

    if not running:
        return False

    print(
        f"Moving to result X: "
        f"{FISH_RESULT_CLOSE}"
    )

    native_move_to(
        FISH_RESULT_CLOSE[0],
        FISH_RESULT_CLOSE[1]
    )

    if not running:
        return False

    # Old macro waits before clicking.
    time.sleep(0.70)

    if not running:
        return False

    native_click()

    print(
        "Fish result closed."
    )

    time.sleep(0.30)

    return True


# ============================================================
# ONE FISHING CYCLE
# ============================================================

def fishing_cycle():

    global cycle_count

    print()
    print("======================================")
    print(
        f"FISHING CYCLE #{cycle_count + 1}"
    )
    print("======================================")

    print(
        "Moving to Fish button..."
    )

    click_position(
        FISH_BUTTON[0],
        FISH_BUTTON[1]
    )

    if not running:
        return False

    if not wait_for_minigame():

        print(
            "No minigame detected."
        )

        return False

    if not running:
        return False

    caught = play_fishing_minigame()

    if not caught:
        return False

    if not running:
        return False

    if not close_fish_result():
        return False

    cycle_count += 1

    print()
    print(
        f"Cycle complete! "
        f"Total cycles: {cycle_count}"
    )

    return True


# ============================================================
# MAIN MACRO LOOP
# ============================================================

def run_macro():

    while running:

        success = fishing_cycle()

        if not success:

            if running:

                print()
                print(
                    "Fishing cycle failed."
                )

                print(
                    "Stopping macro for now."
                )

                break

            break

        if not running:
            break

        # Small pause before starting
        # the next fishing cycle.
        time.sleep(0.30)


# ============================================================
# HOTKEYS
# ============================================================

def toggle_macro():

    global running
    global cycle_count

    if running:

        running = False

        print()
        print("Macro STOPPED.")

        return

    running = True

    cycle_count = 0

    print()
    print("Macro STARTED.")

    threading.Thread(
        target=run_macro,
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
print("Fishing + fish-result loop enabled.")
print("Advanced threshold: 25 pixels")
print("======================================")

keyboard.wait()
