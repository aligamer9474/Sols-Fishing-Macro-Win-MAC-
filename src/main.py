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

# Same threshold used by the old macro
ADVANCED_FISHING_THRESHOLD = 25

# Old macro waits 50ms before getting the bar color
COLOR_SAMPLE_DELAY = 0.050

# Old macro loops around every 10ms
SCAN_DELAY = 0.010

# Same basic RGB tolerance used by old macro
COLOR_TOLERANCE = 10

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


def colors_match(color1, color2):

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
# GET RANDOMIZED BAR COLOR
# ============================================================

def get_bar_color():

    # --------------------------------------------------------
    # This is the exact point used by the old macro:
    #
    # PixelGetColor, barColor, 955, 767, RGB
    #
    # --------------------------------------------------------

    color = get_pixel(
        955,
        767
    )

    # If it isn't white, use it immediately.
    if not is_white(color):

        return color

    # --------------------------------------------------------
    # Python can occasionally catch the white target at the
    # exact instant the old macro would have caught the bar.
    #
    # Try nearby pixels instead.
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Last fallback:
    # scan the whole bar for the first useful color.
    # --------------------------------------------------------

    for x in range(
        BAR_LEFT,
        BAR_RIGHT + 1
    ):

        color = get_pixel(
            x,
            BAR_Y
        )

        if not is_white(color):

            r, g, b = color

            # Avoid nearly-black background pixels
            if (
                r > 10
                or g > 10
                or b > 10
            ):

                return color

    return None


# ============================================================
# FIND BAR WIDTH
# ============================================================

def find_bar():

    # --------------------------------------------------------
    # Same idea as:
    #
    # PixelSearch, leftX, leftY,
    # 757, 767, 1161, 767,
    # barColor, 5, Fast RGB
    # --------------------------------------------------------

    left_x = None

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
            current_bar_color
        ):

            left_x = x

            break

    # --------------------------------------------------------
    # Old macro: if PixelSearch failed,
    # immediately click.
    # --------------------------------------------------------

    if left_x is None:

        return None

    # --------------------------------------------------------
    # Expand right exactly like the old macro.
    # --------------------------------------------------------

    right_x = left_x

    while True:

        test_x = right_x + 1

        if test_x > BAR_RIGHT:

            break

        test_color = get_pixel(
            test_x,
            BAR_Y
        )

        if colors_match(
            test_color,
            current_bar_color
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

current_bar_color = None


def play_fishing_minigame():

    global current_bar_color

    print()
    print("======================================")
    print("FISHING MINIGAME")
    print("OLD MACRO DETECTION")
    print("CLICKS ENABLED")
    print("======================================")

    # --------------------------------------------------------
    # Old macro moves mouse to 950,880 and waits 50ms.
    # --------------------------------------------------------

    native_move_to(
        950,
        880
    )

    time.sleep(
        COLOR_SAMPLE_DELAY
    )

    # --------------------------------------------------------
    # Get randomized bar color.
    # --------------------------------------------------------

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

    last_click = 0

    # --------------------------------------------------------
    # Old macro's detection loop runs for about 9 seconds.
    # --------------------------------------------------------

    while (
        time.time() - start_time
        < 9.0
    ):

        if not running:

            current_bar_color = None

            return False

        result = find_bar()

        # ----------------------------------------------------
        # If the old PixelSearch cannot find the color,
        # the old macro clicks.
        # ----------------------------------------------------

        if result is None:

            native_click()

            click_count += 1

            print(
                f"CLICK #{click_count} "
                f"| Bar color not found"
            )

            time.sleep(
                0.025
            )

            continue

        left_x, right_x, bar_width = result

        print(
            f"\rBar X={left_x}-{right_x} "
            f"Width={bar_width}",
            end=""
        )

        # ----------------------------------------------------
        # EXACT OLD MACRO THRESHOLD:
        #
        # if (barWidth < advancedFishingThreshold)
        #     MouseClick, left
        #
        # Default threshold = 25.
        # ----------------------------------------------------

        if bar_width < ADVANCED_FISHING_THRESHOLD:

            native_click()

            click_count += 1

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

    # --------------------------------------------------------
    # Forget the color after this fish.
    # --------------------------------------------------------

    current_bar_color = None

    print(
        "Bar color erased."
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

        print(
            "No minigame detected."
        )

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
    global current_bar_color

    running = False

    current_bar_color = None

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
print("Using old macro fishing detection.")
print("Advanced threshold: 25 pixels")
print("======================================")

keyboard.wait()
