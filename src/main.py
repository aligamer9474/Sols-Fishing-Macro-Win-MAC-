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

# How long we spend learning the color
COLOR_LEARNING_TIME = 2.0

# How similar a pixel must be to the learned color
COLOR_TOLERANCE = 12

# AHK used 25 as the advanced detection threshold
CLICK_WIDTH = 25

CLICK_COOLDOWN = 0.025

SCAN_DELAY = 0.006

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


def color_close(color1, color2):

    return (
        abs(color1[0] - color2[0]) <= COLOR_TOLERANCE
        and
        abs(color1[1] - color2[1]) <= COLOR_TOLERANCE
        and
        abs(color1[2] - color2[2]) <= COLOR_TOLERANCE
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
# GET BAR COLORS
# ============================================================

def scan_pixels():

    pixels = []

    for x in range(
        BAR_LEFT,
        BAR_RIGHT + 1
    ):

        pixels.append(
            (
                x,
                get_pixel(x, BAR_Y)
            )
        )

    return pixels


# ============================================================
# LEARN THE COLOR FOR THIS ROUND
# ============================================================

def learn_round_color():

    print()
    print("Learning color for this fish...")

    start_time = time.time()

    color_counts = {}

    # We look for colors that repeatedly appear
    # in a small moving section.
    while (
        time.time() - start_time
        < COLOR_LEARNING_TIME
    ):

        if not running:
            return None

        pixels = scan_pixels()

        for x, color in pixels:

            # Ignore white target/background
            if is_white(color):
                continue

            # Ignore extremely dark pixels
            if (
                color[0] < 10
                and color[1] < 10
                and color[2] < 10
            ):
                continue

            # Round colors slightly so anti-aliasing
            # doesn't create hundreds of tiny colors.
            grouped = (
                (color[0] // 4) * 4,
                (color[1] // 4) * 4,
                (color[2] // 4) * 4
            )

            color_counts[grouped] = (
                color_counts.get(grouped, 0) + 1
            )

        time.sleep(SCAN_DELAY)

    if not color_counts:

        print("Could not learn a color.")

        return None

    # Find the most frequently appearing color.
    learned = max(
        color_counts,
        key=color_counts.get
    )

    print(
        f"Learned round color: RGB{learned}"
    )

    return learned


# ============================================================
# FIND THE LEARNED COLOR
# ============================================================

def find_color_width(learned_color):

    pixels = scan_pixels()

    sections = []

    current_start = None

    for x, color in pixels:

        matches = color_close(
            color,
            learned_color
        )

        if matches:

            if current_start is None:

                current_start = x

        else:

            if current_start is not None:

                width = x - current_start

                if width > 0:

                    sections.append(
                        (
                            current_start,
                            x - 1
                        )
                    )

                current_start = None

    # Handle section touching right edge
    if current_start is not None:

        sections.append(
            (
                current_start,
                BAR_RIGHT
            )
        )

    if not sections:

        return None

    # Choose the widest matching section.
    section = max(
        sections,
        key=lambda s:
            s[1] - s[0]
    )

    left_x, right_x = section

    width = (
        right_x
        - left_x
        + 1
    )

    return left_x, right_x, width


# ============================================================
# FISHING MINIGAME
# ============================================================

def play_fishing_minigame():

    print()
    print("======================================")
    print("FISHING MINIGAME")
    print("ROUND COLOR LEARNING")
    print("CLICKS ENABLED")
    print("======================================")

    # --------------------------------------------------------
    # Learn color ONLY for this fish.
    # --------------------------------------------------------

    learned_color = learn_round_color()

    if learned_color is None:

        print("No usable color learned.")

        return False

    start_time = time.time()

    last_click = 0
    click_count = 0

    print(
        "Tracking learned color..."
    )

    # --------------------------------------------------------
    # Track learned color
    # --------------------------------------------------------

    while (
        time.time() - start_time
        < MINIGAME_TIMEOUT
    ):

        if not running:
            return False

        result = find_color_width(
            learned_color
        )

        if result is not None:

            left_x, right_x, width = result

            print(
                f"\rColor bar: "
                f"X={left_x}-{right_x} "
                f"Width={width}",
                end=""
            )

            # ------------------------------------------------
            # Same basic idea as the old AHK:
            #
            # When the visible matching bar gets narrow,
            # click.
            # ------------------------------------------------

            if (
                width < CLICK_WIDTH
                and
                time.time() - last_click
                > CLICK_COOLDOWN
            ):

                native_click()

                click_count += 1
                last_click = time.time()

                print()

                print(
                    f"CLICK #{click_count} "
                    f"| Width={width}"
                )

        time.sleep(SCAN_DELAY)

    print()

    print(
        f"Fishing detection finished. "
        f"Clicks: {click_count}"
    )

    # --------------------------------------------------------
    # IMPORTANT:
    # Forget the color after the fish.
    # --------------------------------------------------------

    learned_color = None

    print(
        "Round color erased."
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
print("Round-by-round color learning enabled.")
print("Each fish gets its own temporary color.")
print("======================================")

keyboard.wait()
