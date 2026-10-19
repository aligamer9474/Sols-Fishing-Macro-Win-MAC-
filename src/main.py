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

SCAN_DELAY = 0.008

# How different a pixel must be from the background
COLOR_DIFFERENCE = 25

# Minimum number of pixels needed to count as a section
MIN_SECTION_WIDTH = 3

# Fishing timing
TARGET_DISTANCE = 8
CLICK_COOLDOWN = 0.025

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


def color_difference(color1, color2):

    return (
        abs(color1[0] - color2[0])
        + abs(color1[1] - color2[1])
        + abs(color1[2] - color2[2])
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
# FIND COLORED SECTIONS
# ============================================================

def scan_bar():

    pixels = []

    for x in range(
        BAR_LEFT,
        BAR_RIGHT + 1
    ):

        color = get_pixel(
            x,
            BAR_Y
        )

        pixels.append(
            (x, color)
        )

    # --------------------------------------------------------
    # Find the most common non-white background color.
    # --------------------------------------------------------

    color_counts = {}

    for x, color in pixels:

        if is_white(color):
            continue

        color_counts[color] = (
            color_counts.get(color, 0) + 1
        )

    if not color_counts:
        return []

    background = max(
        color_counts,
        key=color_counts.get
    )

    # --------------------------------------------------------
    # Find sections that are significantly different
    # from the background.
    # --------------------------------------------------------

    sections = []

    current_start = None

    for x, color in pixels:

        different = (
            not is_white(color)
            and
            color_difference(
                color,
                background
            ) >= COLOR_DIFFERENCE
        )

        if different:

            if current_start is None:
                current_start = x

        else:

            if current_start is not None:

                width = x - current_start

                if width >= MIN_SECTION_WIDTH:

                    sections.append(
                        (
                            current_start,
                            x - 1
                        )
                    )

                current_start = None

    # Handle section reaching the right edge.
    if current_start is not None:

        width = (
            BAR_RIGHT
            + 1
            - current_start
        )

        if width >= MIN_SECTION_WIDTH:

            sections.append(
                (
                    current_start,
                    BAR_RIGHT
                )
            )

    return sections


# ============================================================
# CHOOSE MOVING SECTION
# ============================================================

def choose_moving_section(
    sections,
    previous_center
):

    if not sections:
        return None

    # If we have a previous position,
    # prefer the section closest to it.
    if previous_center is not None:

        closest = min(
            sections,
            key=lambda section:
                abs(
                    (
                        section[0]
                        + section[1]
                    ) // 2
                    - previous_center
                )
        )

        return closest

    # Otherwise choose the largest section.
    return max(
        sections,
        key=lambda section:
            section[1] - section[0]
    )


# ============================================================
# FISHING MINIGAME
# ============================================================

def play_fishing_minigame():

    print()
    print("======================================")
    print("FISHING MINIGAME")
    print("NEW COLOR TRACKING")
    print("CLICKS ENABLED")
    print("======================================")

    start_time = time.time()

    previous_center = None
    last_click = 0
    click_count = 0

    time.sleep(0.10)

    while (
        time.time() - start_time
        < MINIGAME_TIMEOUT
    ):

        if not running:
            return False

        sections = scan_bar()

        section = choose_moving_section(
            sections,
            previous_center
        )

        if section is not None:

            left_x, right_x = section

            center = (
                left_x + right_x
            ) // 2

            width = (
                right_x - left_x
            )

            previous_center = center

            current_time = time.time()

            print(
                f"\rSection X={center} "
                f"Width={width} "
                f"Sections={len(sections)}",
                end=""
            )

            # ------------------------------------------------
            # Click when the tracked section reaches
            # the left side of the fishing range.
            # ------------------------------------------------

            if (
                center <= BAR_LEFT + TARGET_DISTANCE
                and
                current_time - last_click
                > CLICK_COOLDOWN
            ):

                native_click()

                click_count += 1
                last_click = current_time

                print()
                print(
                    f"CLICK #{click_count} "
                    f"| X={center}"
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
print("New fishing color tracking enabled.")
print("Fishing clicks are ENABLED.")
print("======================================")

keyboard.wait()
