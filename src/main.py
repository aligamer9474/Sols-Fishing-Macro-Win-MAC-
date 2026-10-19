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

# Fishing bar
BAR_LEFT = 757
BAR_TOP = 762
BAR_WIDTH = 405
BAR_HEIGHT = 21

SCAN_DELAY = 0.10

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
# FIND WHITE TARGET
# ============================================================

def find_white_target(image):

    white_columns = []

    for x in range(BAR_WIDTH):

        white_count = 0

        for y in range(BAR_HEIGHT):

            r, g, b = image.getpixel((x, y))

            if (
                r >= 245
                and g >= 245
                and b >= 245
            ):
                white_count += 1

        if white_count >= 2:
            white_columns.append(x)

    if not white_columns:
        return None

    groups = []

    start = white_columns[0]
    previous = white_columns[0]

    for x in white_columns[1:]:

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

    # The target is normally one of the larger
    # white sections.
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
# FIND CHANGED AREA
# ============================================================

def find_changed_area(previous, current):

    changed_columns = []

    for x in range(BAR_WIDTH):

        changed_pixels = 0

        for y in range(BAR_HEIGHT):

            old_pixel = previous.getpixel(
                (x, y)
            )

            new_pixel = current.getpixel(
                (x, y)
            )

            difference = (
                abs(old_pixel[0] - new_pixel[0])
                +
                abs(old_pixel[1] - new_pixel[1])
                +
                abs(old_pixel[2] - new_pixel[2])
            )

            if difference >= 30:
                changed_pixels += 1

        if changed_pixels >= 3:
            changed_columns.append(x)

    if not changed_columns:
        return None

    groups = []

    start = changed_columns[0]
    previous_x = changed_columns[0]

    for x in changed_columns[1:]:

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

    # Remove tiny noise
    groups = [
        group
        for group in groups
        if group[1] - group[0] >= 4
    ]

    if not groups:
        return None

    # Largest changed section
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
# FIND RECTANGLE
# ============================================================

def find_rectangle(previous, current, target):

    movement = find_changed_area(
        previous,
        current
    )

    if movement is None:
        return None

    left, right, center = movement

    # If the detected movement is extremely large,
    # it is probably the UI/background changing
    # rather than the rectangle.
    width = right - left

    if width > 100:
        return None

    # If we have a target, avoid treating the target
    # itself as the rectangle.
    if target is not None:

        target_left = target[0]
        target_right = target[1]

        overlap = (
            left <= target_right
            and right >= target_left
        )

        if overlap and width > 35:
            return None

    return movement


# ============================================================
# TRACK MINIGAME
# ============================================================

def track_minigame():

    print()
    print("======================================")
    print("TRACKER STARTED")
    print("NO MINIGAME CLICKS")
    print("======================================")
    print()

    previous_image = None

    last_rectangle = None

    start_time = time.time()

    while time.time() - start_time < 8:

        current_image = pyautogui.screenshot(
            region=(
                BAR_LEFT,
                BAR_TOP,
                BAR_WIDTH,
                BAR_HEIGHT
            )
        )

        target = find_white_target(
            current_image
        )

        rectangle = None

        if previous_image is not None:

            rectangle = find_rectangle(
                previous_image,
                current_image,
                target
            )

        # Keep the last known rectangle if the
        # current frame has no usable detection.
        if rectangle is not None:
            last_rectangle = rectangle

        if rectangle is not None:

            rectangle_center = rectangle[2]

        elif last_rectangle is not None:

            rectangle_center = last_rectangle[2]

        else:

            rectangle_center = None

        # Target center
        if target is not None:
            target_center = target[2]
        else:
            target_center = None

        # Distance between rectangle and target
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
            f"Movement={rectangle} | "
            f"RectangleCenter={rectangle_center} | "
            f"Distance={distance}"
        )

        previous_image = current_image

        time.sleep(SCAN_DELAY)

    print()
    print("======================================")
    print("TRACKER FINISHED")
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
print("This version DOES NOT click")
print("during the minigame.")
print("======================================")

keyboard.wait()
