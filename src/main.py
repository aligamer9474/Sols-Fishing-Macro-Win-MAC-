import pyautogui
import keyboard
import time
import ctypes
import threading
from ctypes import wintypes


# ============================================================
# SETTINGS
# ============================================================

FISH_BUTTON = (853, 832)
FISH_RESULT_CLOSE = (1113, 342)

MINIGAME_START_PIXEL = (1176, 836)
MINIGAME_TIMEOUT = 19

BAR_LEFT = 757
BAR_RIGHT = 1161
BAR_Y = 767

BAR_SCAN_TOP = 755
BAR_SCAN_BOTTOM = 780

ADVANCED_FISHING_THRESHOLD = 25

COLOR_SAMPLE_DELAY = 0.050
SCAN_DELAY = 0.010

COLOR_TOLERANCE = 10

REARM_DELAY = 0.08

# Panic speed
PANIC_COOLDOWN = 0.30
PANIC_MAX_TIME = 1.50

RESULT_CLOSE_DELAY = 0.40

INITIAL_GRACE_PERIOD = 1.20
MOVEMENT_REQUIRED = 8

PREDICTION_TIME = 0.30
MIN_DISTANCE_TO_PREDICT = 8


# ============================================================
# WINDOWS MOUSE
# ============================================================

user32 = ctypes.windll.user32

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004


def get_mouse_position():

    point = wintypes.POINT()

    user32.GetCursorPos(ctypes.byref(point))

    return point.x, point.y


def move_mouse_native(target_x, target_y):

    """
    Uses the same native relative-movement method that
    successfully made Roblox recognize the mouse.

    Smaller steps prevent the cursor from accelerating
    past the target.
    """

    current_x, current_y = get_mouse_position()

    dx = target_x - current_x
    dy = target_y - current_y

    distance = max(abs(dx), abs(dy))

    if distance == 0:
        return

    # Small steps = slower, more controlled movement.
    steps = max(1, int(distance / 3))

    for i in range(1, steps + 1):

        if emergency_stop:
            return

        new_x = current_x + int(dx * i / steps)
        new_y = current_y + int(dy * i / steps)

        previous_x = current_x + int(dx * (i - 1) / steps)
        previous_y = current_y + int(dy * (i - 1) / steps)

        move_x = new_x - previous_x
        move_y = new_y - previous_y

        user32.mouse_event(
            MOUSEEVENTF_MOVE,
            move_x,
            move_y,
            0,
            0
        )

        time.sleep(0.004)


def native_click():

    if emergency_stop:
        return

    user32.mouse_event(
        MOUSEEVENTF_LEFTDOWN,
        0,
        0,
        0,
        0
    )

    time.sleep(0.015)

    user32.mouse_event(
        MOUSEEVENTF_LEFTUP,
        0,
        0,
        0,
        0
    )


# ============================================================
# GLOBAL STATE
# ============================================================

running = False
emergency_stop = False

current_bar_color = None

macro_thread = None


# ============================================================
# COLOR HELPERS
# ============================================================

def colors_match(color1, color2, tolerance=COLOR_TOLERANCE):

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
        color[0] > 245
        and color[1] > 245
        and color[2] > 245
    )


def is_dark(color):

    if color is None:
        return False

    return (
        color[0] < 10
        and color[1] < 10
        and color[2] < 10
    )


# ============================================================
# LEARN FISHING BAR COLOR
# ============================================================

def get_bar_color():

    screenshot = pyautogui.screenshot()

    color = screenshot.getpixel((955, BAR_Y))

    if not is_white(color) and not is_dark(color):
        return color

    for x in range(945, 966):

        color = screenshot.getpixel((x, BAR_Y))

        if not is_white(color) and not is_dark(color):
            return color

    for x in range(BAR_LEFT, BAR_RIGHT + 1):

        color = screenshot.getpixel((x, BAR_Y))

        if not is_white(color) and not is_dark(color):
            return color

    return None


# ============================================================
# FIND RECTANGLE
# ============================================================

def find_bar():

    global current_bar_color

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

    if start_x is None:
        return None

    width = end_x - start_x

    return start_x, end_x, width


# ============================================================
# 2D FALLBACK
# ============================================================

def find_bar_2d():

    global current_bar_color

    if current_bar_color is None:
        return None

    screenshot = pyautogui.screenshot()

    matching_x = []

    for x in range(BAR_LEFT, BAR_RIGHT + 1):

        matches = 0

        for y in range(BAR_SCAN_TOP, BAR_SCAN_BOTTOM + 1):

            color = screenshot.getpixel((x, y))

            if colors_match(color, current_bar_color):
                matches += 1

        if matches >= 2:
            matching_x.append(x)

    if not matching_x:
        return None

    groups = []

    group_start = matching_x[0]
    previous = matching_x[0]

    for x in matching_x[1:]:

        if x == previous + 1:
            previous = x

        else:
            groups.append((group_start, previous))

            group_start = x
            previous = x

    groups.append((group_start, previous))

    group_start, group_end = max(
        groups,
        key=lambda g: g[1] - g[0]
    )

    width = group_end - group_start

    return group_start, group_end, width


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

        if elapsed >= MINIGAME_TIMEOUT:

            print("Minigame timeout.")

            return False

        screenshot = pyautogui.screenshot()

        color = screenshot.getpixel(MINIGAME_START_PIXEL)

        if is_white(color):

            print(
                f"Minigame detected after "
                f"{elapsed:.1f} seconds!"
            )

            return True

        if elapsed - last_status >= 5:

            print(
                f"Still waiting... "
                f"{elapsed:.1f}s"
            )

            last_status = elapsed

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
    print("PREDICTIVE DETECTION")
    print("CLICKS ENABLED")
    print("======================================")

    time.sleep(COLOR_SAMPLE_DELAY)

    current_bar_color = get_bar_color()

    if current_bar_color is None:

        print("Could not learn bar color.")

        return

    print(
        f"Bar color learned: "
        f"RGB{current_bar_color}"
    )

    print("Tracking bar...")

    start_time = time.time()

    click_count = 0

    danger_locked = False

    previous_center = None
    previous_time = None

    velocity = 0

    rectangle_seen = False
    rectangle_moved = False

    panic_mode = False
    panic_start_time = 0
    last_panic_click = 0

    last_predictive_click = 0

    while (
        running
        and not emergency_stop
        and time.time() - start_time < 9
    ):

        now = time.time()

        result = find_bar()

        if result is None:

            if now - start_time < INITIAL_GRACE_PERIOD:

                time.sleep(SCAN_DELAY)

                continue

            result_2d = find_bar_2d()

            if result_2d is not None:
                result = result_2d

        if result is not None:

            left_x, right_x, width = result

            center = (left_x + right_x) / 2

            rectangle_seen = True

            # ------------------------------------------------
            # MOVEMENT TRACKING
            # ------------------------------------------------

            if previous_center is not None and previous_time is not None:

                dt = now - previous_time

                if dt > 0:

                    movement = center - previous_center

                    if abs(movement) >= MOVEMENT_REQUIRED:

                        rectangle_moved = True

                    instant_velocity = movement / dt

                    velocity = (
                        velocity * 0.65
                        +
                        instant_velocity * 0.35
                    )

            previous_center = center
            previous_time = now

            # ------------------------------------------------
            # NORMAL DETECTION
            # ------------------------------------------------

            print(
                f"Bar X={left_x}-{right_x} "
                f"Width={width}"
            )

            if width < ADVANCED_FISHING_THRESHOLD:

                if not danger_locked:

                    native_click()

                    click_count += 1

                    print(
                        f"CLICK #{click_count} | "
                        f"X={left_x}-{right_x} | "
                        f"Width={width}"
                    )

                    danger_locked = True

                panic_mode = False

            else:

                danger_locked = False

                # ------------------------------------------------
                # PREDICTIVE CLICK
                # ------------------------------------------------

                if rectangle_moved:

                    if velocity > 20:

                        predicted_center = (
                            center
                            +
                            velocity * PREDICTION_TIME
                        )

                        if (
                            predicted_center - center
                            >= MIN_DISTANCE_TO_PREDICT
                        ):

                            if (
                                now - last_predictive_click
                                >= PANIC_COOLDOWN
                            ):

                                native_click()

                                click_count += 1

                                print(
                                    f"PREDICTIVE CLICK "
                                    f"#{click_count} | "
                                    f"Center={center:.0f} | "
                                    f"Velocity={velocity:.0f} | "
                                    f"Predicted={predicted_center:.0f}"
                                )

                                last_predictive_click = now

                    elif velocity < -20:

                        predicted_center = (
                            center
                            +
                            velocity * PREDICTION_TIME
                        )

                        if (
                            center - predicted_center
                            >= MIN_DISTANCE_TO_PREDICT
                        ):

                            if (
                                now - last_predictive_click
                                >= PANIC_COOLDOWN
                            ):

                                native_click()

                                click_count += 1

                                print(
                                    f"PREDICTIVE CLICK "
                                    f"#{click_count} | "
                                    f"Center={center:.0f} | "
                                    f"Velocity={velocity:.0f} | "
                                    f"Predicted={predicted_center:.0f}"
                                )

                                last_predictive_click = now

            panic_mode = False

        else:

            # ====================================================
            # RECTANGLE HIDDEN
            # ====================================================

            if rectangle_seen and rectangle_moved:

                if not panic_mode:

                    panic_mode = True
                    panic_start_time = now

                    print(
                        "Rectangle hidden - "
                        "predictive panic mode."
                    )

                panic_elapsed = now - panic_start_time

                if panic_elapsed <= PANIC_MAX_TIME:

                    if (
                        now - last_panic_click
                        >= PANIC_COOLDOWN
                    ):

                        native_click()

                        click_count += 1

                        print(
                            f"PREDICTIVE PANIC CLICK "
                            f"#{click_count} | "
                            f"Cooldown: "
                            f"{PANIC_COOLDOWN:.2f}s"
                        )

                        last_panic_click = now

                else:

                    panic_mode = False

                    print(
                        "Prediction timeout - "
                        "waiting for rectangle."
                    )

        time.sleep(SCAN_DELAY)

    print()

    print(
        f"Fishing detection finished. "
        f"Clicks: {click_count}"
    )

    current_bar_color = None

    print("Bar color erased.")


# ============================================================
# CLOSE FISH RESULT
# ============================================================

def close_fish_result():

    print()

    print(
        f"Waiting {RESULT_CLOSE_DELAY:.1f} "
        f"seconds before closing result..."
    )

    time.sleep(RESULT_CLOSE_DELAY)

    if emergency_stop:
        return

    print("Closing fish result...")

    print(
        f"Moving to result X: "
        f"{FISH_RESULT_CLOSE}"
    )

    move_mouse_native(
        FISH_RESULT_CLOSE[0],
        FISH_RESULT_CLOSE[1]
    )

    time.sleep(0.05)

    native_click()

    time.sleep(0.4)

    print("Fish result closed.")


# ============================================================
# FISHING CYCLE
# ============================================================

def fishing_cycle(cycle_number):

    print()
    print("======================================")
    print(f"FISHING CYCLE #{cycle_number}")
    print("======================================")

    if emergency_stop:
        return

    print("Moving to Fish button...")

    move_mouse_native(
        FISH_BUTTON[0],
        FISH_BUTTON[1]
    )

    if emergency_stop:
        return

    time.sleep(0.05)

    native_click()

    if emergency_stop:
        return

    if wait_for_minigame():

        play_fishing_minigame()

        if not emergency_stop:

            close_fish_result()


# ============================================================
# MAIN MACRO THREAD
# ============================================================

def macro_loop():

    global running

    cycle_number = 0

    while running and not emergency_stop:

        cycle_number += 1

        fishing_cycle(cycle_number)

        if emergency_stop:
            break

        print()
        print(
            f"Cycle complete! "
            f"Total cycles: {cycle_number}"
        )

        time.sleep(0.2)

    print()
    print("Macro loop stopped.")


# ============================================================
# F8
# ============================================================

def toggle_macro():

    global running
    global emergency_stop
    global macro_thread

    if not running:

        emergency_stop = False
        running = True

        print()
        print("Macro STARTED.")

        # Run macro separately so F3 remains responsive.
        macro_thread = threading.Thread(
            target=macro_loop,
            daemon=True
        )

        macro_thread.start()

    else:

        running = False

        print()
        print("Macro PAUSED.")


# ============================================================
# F3 EMERGENCY STOP
# ============================================================

def emergency():

    global running
    global emergency_stop

    emergency_stop = True
    running = False

    print()
    print("!!! EMERGENCY STOP !!!")


# ============================================================
# START
# ============================================================

print("======================================")
print("SOLS RNG FISHING MACRO")
print("======================================")
print("F8 = Start / Pause")
print("F3 = Emergency Stop")
print()
print("Fishing + fish-result loop enabled.")
print(
    f"Advanced threshold: "
    f"{ADVANCED_FISHING_THRESHOLD} pixels"
)
print("Predictive clicking enabled.")
print(
    f"Panic cooldown: "
    f"{PANIC_COOLDOWN:.2f} seconds"
)
print("F3 emergency stop is threaded.")
print(
    f"Result close delay: "
    f"{RESULT_CLOSE_DELAY:.2f} seconds"
)
print("======================================")


keyboard.add_hotkey("f8", toggle_macro)
keyboard.add_hotkey("f3", emergency)

keyboard.wait()
