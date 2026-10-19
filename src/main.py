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

# Fishing bar region
BAR_LEFT = 757
BAR_TOP = 762
BAR_WIDTH = 405
BAR_HEIGHT = 21

SCAN_DELAY = 0.08

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
    user32.GetCursorPos(ctypes.byref(point))
    return point.x, point.y


def native_move_to(x, y):
    start_x, start_y = get_mouse_position()

    dx = x - start_x
    dy = y - start_y

    distance = max(abs(dx), abs(dy))
    steps = max(20, int(distance / 8))

    for i in range(1, steps + 1):

        target_x = start_x + int(dx * i / steps)
        target_y = start_y + int(dy * i / steps)

        current_x, current_y = get_mouse_position()

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

    time.sleep(0.05)

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
# PIXEL FUNCTIONS
# ============================================================

def get_pixel(x, y):
    return pyautogui.pixel(x, y)


def is_white_pixel(color):
    r, g, b = color
    return r >= 245 and g >= 245 and b >= 245


# ============================================================
# WAIT FOR MINIGAME
# ============================================================

def wait_for_minigame():

    print()
    print("Waiting for minigame...")

    start_time = time.time()
    last_message = 0

    while time.time() - start_time < MINIGAME_TIMEOUT:

        color = get_pixel(
            MINIGAME_START_PIXEL[0],
            MINIGAME_START_PIXEL[1]
        )

        if is_white_pixel(color):

            elapsed = time.time() - start_time

            print(
                f"Minigame detected after "
                f"{elapsed:.1f} seconds!"
            )

            return True

        elapsed = time.time() - start_time

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
# SCREENSHOT
# ============================================================

def get_bar_image():

    return pyautogui.screenshot(
        region=(
            BAR_LEFT,
            BAR_TOP,
            BAR_WIDTH,
            BAR_HEIGHT
        )
    )


# ============================================================
# WHITE TARGET
# ============================================================

def find_white_target(image):

    columns = []

    for x in range(BAR_WIDTH):

        white_pixels = 0

        for y in range(BAR_HEIGHT):

            r, g, b = image.getpixel((x, y))

            if (
                r >= 245
                and g >= 245
                and b >= 245
            ):
                white_pixels += 1

        if white_pixels >= 2:
            columns.append(x)

    if not columns:
        return None

    groups = []

    start = columns[0]
    previous = columns[0]

    for x in columns[1:]:

        if x <= previous + 2:
            previous = x

        else:

            groups.append(
                (start, previous)
            )

            start = x
            previous = x

    groups.append(
        (start, previous)
    )

    # Remove extremely tiny groups
    groups = [
        group
        for group in groups
        if group[1] - group[0] >= 4
    ]

    if not groups:
        return None

    # The target is normally the widest white area
    groups.sort(
        key=lambda group:
        group[1] - group[0],
        reverse=True
    )

    left, right = groups[0]

    center = (left + right) // 2

    return (
        BAR_LEFT + left,
        BAR_LEFT + right,
        BAR_LEFT + center
    )


# ============================================================
# BUILD A BRIGHTNESS MAP
# ============================================================

def get_column_brightness(image):

    brightness = []

    for x in range(BAR_WIDTH):

        total = 0

        for y in range(BAR_HEIGHT):

            r, g, b = image.getpixel((x, y))

            total += r + g + b

        average = total / (BAR_HEIGHT * 3)

        brightness.append(average)

    return brightness


# ============================================================
# FIND RECTANGLE SHAPE
# ============================================================

def find_rectangle_shape(previous, current, target):

    if previous is None:
        return None

    old_brightness = get_column_brightness(
        previous
    )

    new_brightness = get_column_brightness(
        current
    )

    differences = []

    for x in range(BAR_WIDTH):

        difference = abs(
            new_brightness[x]
            - old_brightness[x]
        )

        differences.append(difference)

    # Find columns that changed significantly
    changed = []

    for x in range(BAR_WIDTH):

        if differences[x] >= 12:
            changed.append(x)

    if not changed:
        return None

    # Group nearby changed columns
    groups = []

    start = changed[0]
    previous_x = changed[0]

    for x in changed[1:]:

        if x <= previous_x + 2:

            previous_x = x

        else:

            groups.append(
                (start, previous_x)
            )

            start = x
            previous_x = x

    groups.append(
        (start, previous_x)
    )

    # Remove tiny changes
    groups = [
        group
        for group in groups
        if 4 <= group[1] - group[0] <= 70
    ]

    if not groups:
        return None

    # If there is a target, prefer movement
    # closest to it or around the central game area.
    if target is not None:

        target_center = target[2]

        groups.sort(
            key=lambda group:
            abs(
                (
                    BAR_LEFT
                    + (group[0] + group[1]) // 2
                )
                - target_center
            )
        )

    else:

        groups.sort(
            key=lambda group:
            group[1] - group[0],
            reverse=True
        )

    left, right = groups[0]

    center = (left + right) // 2

    return (
        BAR_LEFT + left,
        BAR_LEFT + right,
        BAR_LEFT + center
    )


# ============================================================
# FIND RECTANGLE USING MULTIPLE FRAMES
# ============================================================

def stabilize_rectangle(history, target):

    if not history:
        return None

    candidates = []

    for rectangle in history:

        if rectangle is None:
            continue

        center = rectangle[2]

        # Ignore obviously huge/full-bar detections
        width = rectangle[1] - rectangle[0]

        if width > 70:
            continue

        candidates.append(
            (
                center,
                rectangle
            )
        )

    if not candidates:
        return None

    # If target exists, favor candidates that appear
    # near the target rather than random full-bar changes.
    if target is not None:

        target_center = target[2]

        candidates.sort(
            key=lambda item:
            abs(item[0] - target_center)
        )

    return candidates[0][1]


# ============================================================
# TRACK MINIGAME
# ============================================================

def track_minigame():

    print()
    print("======================================")
    print("SHAPE TRACKER STARTED")
    print("NO MINIGAME CLICKS")
    print("======================================")
    print()

    previous_image = None

    rectangle_history = []

    start_time = time.time()

    while time.time() - start_time < 8:

        current_image = get_bar_image()

        target = find_white_target(
            current_image
        )

        rectangle = find_rectangle_shape(
            previous_image,
            current_image,
            target
        )

        rectangle_history.append(
            rectangle
        )

        # Keep only recent detections
        if len(rectangle_history) > 5:
            rectangle_history.pop(0)

        best_rectangle = stabilize_rectangle(
            rectangle_history,
            target
        )

        if target is not None:
            target_center = target[2]
        else:
            target_center = None

        if best_rectangle is not None:
            rectangle_center = best_rectangle[2]
        else:
            rectangle_center = None

        distance = None

        if (
            rectangle_center is not None
            and target_center is not None
        ):
            distance = (
                rectangle_center
                - target_center
            )

        elapsed = time.time() - start_time

        print(
            f"[{elapsed:4.1f}s] "
            f"Target={target} | "
            f"Rectangle={best_rectangle} | "
            f"Distance={distance}"
        )

        previous_image = current_image

        time.sleep(SCAN_DELAY)

    print()
    print("======================================")
    print("SHAPE TRACKER FINISHED")
    print("======================================")


# ============================================================
# FISHING TEST
# ============================================================

def test_fishing():

    print()
    print("Moving to Fish button...")

    click_position(
        FISH_BUTTON[0],
        FISH_BUTTON[1]
    )

    if not wait_for_minigame():
        return

    track_minigame()


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
    print("EMERGENCY STOP")


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
print("SOLS RNG FISHING TRACKER")
print("======================================")
print("F8 = Start")
print("F3 = Emergency Stop")
print()
print("This version DOES NOT CLICK")
print("during the minigame.")
print("======================================")

keyboard.wait()
