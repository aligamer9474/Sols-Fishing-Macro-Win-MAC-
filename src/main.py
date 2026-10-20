import pyautogui
import keyboard
import time
import ctypes
from ctypes import wintypes

# ============================================================
# SETTINGS
# ============================================================

FISH_BUTTON = (853, 832)
FISH_RESULT_CLOSE = (1113, 342)

MINIGAME_START_PIXEL = (1176, 836)
MINIGAME_TIMEOUT = 19

# Fishing bar
BAR_LEFT = 757
BAR_RIGHT = 1161
BAR_Y = 767

# Vertical area used to find the bar when the timer
# covers the original horizontal detection line.
BAR_SCAN_TOP = 755
BAR_SCAN_BOTTOM = 780

# Old macro's advanced fishing threshold
ADVANCED_FISHING_THRESHOLD = 25

COLOR_SAMPLE_DELAY = 0.050
SCAN_DELAY = 0.010

COLOR_TOLERANCE = 10

# Prevent instant re-triggering after a click
REARM_DELAY = 0.08

# Panic click cooldown
MISSING_COLOR_COOLDOWN = 0.50

# Maximum amount of time to blindly panic-click
# before giving up on panic mode.
PANIC_MAX_TIME = 2.0

# Wait before clicking the fish-result X
RESULT_CLOSE_DELAY = 0.50


# ============================================================
# WINDOWS NATIVE MOUSE INPUT
# ============================================================

user32 = ctypes.windll.user32

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004


def get_mouse_position():
    point = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(point))
    return point.x, point.y


def move_mouse_native(x, y):
    current_x, current_y = get_mouse_position()

    dx = x - current_x
    dy = y - current_y

    distance = max(abs(dx), abs(dy))

    if distance == 0:
        return

    steps = max(1, int(distance / 8))

    for i in range(1, steps + 1):

        target_x = current_x + int(dx * i / steps)
        target_y = current_y + int(dy * i / steps)

        last_x, last_y = get_mouse_position()

        move_x = target_x - last_x
        move_y = target_y - last_y

        user32.mouse_event(
            MOUSEEVENTF_MOVE,
            move_x,
            move_y,
            0,
            0
        )

        time.sleep(0.003)


def native_click():
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


# ============================================================
# COLOR FUNCTIONS
# ============================================================

def colors_match(c1, c2, tolerance=COLOR_TOLERANCE):

    if c1 is None or c2 is None:
        return False

    return (
        abs(c1[0] - c2[0]) <= tolerance and
        abs(c1[1] - c2[1]) <= tolerance and
        abs(c1[2] - c2[2]) <= tolerance
    )


def is_white(color):

    if color is None:
        return False

    return (
        color[0] > 245 and
        color[1] > 245 and
        color[2] > 245
    )


def is_dark(color):

    if color is None:
        return True

    return (
        color[0] < 10 and
        color[1] < 10 and
        color[2] < 10
    )


# ============================================================
# LEARN FISHING BAR COLOR
# ============================================================

def get_bar_color():

    screenshot = pyautogui.screenshot()

    # Exact pixel used by the old macro
    color = screenshot.getpixel((955, BAR_Y))

    if not is_white(color) and not is_dark(color):
        return color

    # Nearby pixels
    for x in range(945, 966):

        color = screenshot.getpixel((x, BAR_Y))

        if not is_white(color) and not is_dark(color):
            return color

    # Entire bar fallback
    for x in range(BAR_LEFT, BAR_RIGHT + 1):

        color = screenshot.getpixel((x, BAR_Y))

        if not is_white(color) and not is_dark(color):
            return color

    return None


# ============================================================
# FIND BAR ON ORIGINAL LINE
# ============================================================

def find_bar():

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

    if start_x is None or end_x is None:
        return None

    width = end_x - start_x

    return start_x, end_x, width


# ============================================================
# 2D BAR DETECTION
#
# This is used when the timer covers the original line.
# Instead of checking only y=767, it checks several pixels
# vertically around the fishing bar.
# ============================================================

def find_bar_2d():

    if current_bar_color is None:
        return None

    screenshot = pyautogui.screenshot()

    matching_x = []

    for x in range(BAR_LEFT, BAR_RIGHT + 1):

        match_count = 0

        for y in range(BAR_SCAN_TOP, BAR_SCAN_BOTTOM + 1):

            color = screenshot.getpixel((x, y))

            if colors_match(color, current_bar_color):
                match_count += 1

        # Require multiple matching pixels vertically.
        # This helps avoid random single-pixel matches.
        if match_count >= 2:
            matching_x.append(x)

    if not matching_x:
        return None

    # Find the largest contiguous horizontal section.
    groups = []

    group_start = matching_x[0]
    group_end = matching_x[0]

    for x in matching_x[1:]:

        if x <= group_end + 1:
            group_end = x

        else:
            groups.append((group_start, group_end))

            group_start = x
            group_end = x

    groups.append((group_start, group_end))

    # Choose the widest group.
    best_group = max(
        groups,
        key=lambda group: group[1] - group[0]
    )

    start_x, end_x = best_group

    width = end_x - start_x

    return start_x, end_x, width


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

        if elapsed - last_status >= 5:

            print(f"Still waiting... {elapsed:.1f}s")

            last_status = elapsed

        screenshot = pyautogui.screenshot()

        pixel = screenshot.getpixel(MINIGAME_START_PIXEL)

        if is_white(pixel):

            print(
                f"Minigame detected after "
                f"{elapsed:.1f} seconds!"
            )

            return True

        if elapsed >= MINIGAME_TIMEOUT:

            print("Minigame detection timed out.")

            return False

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
    print("STATE-BASED DETECTION")
    print("CLICKS ENABLED")
    print("======================================")

    time.sleep(COLOR_SAMPLE_DELAY)

    current_bar_color = get_bar_color()

    if current_bar_color is None:

        print("Could not learn fishing bar color.")

        return

    print(
        f"Bar color learned: RGB("
        f"{current_bar_color[0]}, "
        f"{current_bar_color[1]}, "
        f"{current_bar_color[2]})"
    )

    print("Tracking bar...")

    start_time = time.time()

    click_count = 0

    # --------------------------------------------------------
    # STATE VARIABLES
    # --------------------------------------------------------

    danger_locked = False

    bar_was_visible = False

    panic_mode = False

    panic_start_time = 0

    last_panic_click = 0

    while running and not emergency_stop:

        elapsed = time.time() - start_time

        if elapsed >= 9:
            break

        # ----------------------------------------------------
        # NORMAL DETECTION
        # ----------------------------------------------------

        result = find_bar()

        # ----------------------------------------------------
        # IF NORMAL LINE CAN'T SEE IT
        # ----------------------------------------------------

        if result is None:

            # If we've already seen the rectangle, try the
            # wider 2D detector before entering panic mode.
            if bar_was_visible:

                wider_result = find_bar_2d()

                if wider_result is not None:

                    start_x, end_x, width = wider_result

                    if panic_mode:

                        print(
                            "Rectangle found in scan area - "
                            "panic mode OFF."
                        )

                    panic_mode = False
                    panic_start_time = 0
                    last_panic_click = 0

                    bar_was_visible = True

                    print(
                        f"2D Bar X={start_x}-{end_x} "
                        f"Width={width}"
                    )

                    # Treat this as a normal detection.
                    if width < ADVANCED_FISHING_THRESHOLD:

                        if not danger_locked:

                            native_click()

                            click_count += 1

                            print(
                                f"CLICK #{click_count} | "
                                f"2D X={start_x}-{end_x} | "
                                f"Width={width}"
                            )

                            danger_locked = True

                            time.sleep(REARM_DELAY)

                    else:

                        danger_locked = False

                    time.sleep(SCAN_DELAY)

                    continue

                # ------------------------------------------------
                # NOTHING FOUND EVEN WITH 2D SCAN
                # ------------------------------------------------

                if not panic_mode:

                    panic_mode = True
                    panic_start_time = time.time()

                    print(
                        "Rectangle hidden - "
                        "PANIC MODE ON."
                    )

                panic_elapsed = (
                    time.time() - panic_start_time
                )

                # Don't panic-click forever.
                if panic_elapsed <= PANIC_MAX_TIME:

                    now = time.time()

                    if (
                        now - last_panic_click
                        >= MISSING_COLOR_COOLDOWN
                    ):

                        native_click()

                        click_count += 1

                        last_panic_click = now

                        print(
                            f"PANIC CLICK #{click_count} | "
                            f"Cooldown: 0.50s"
                        )

                else:

                    # Stop blindly clicking.
                    if panic_mode:

                        print(
                            "Panic timeout - "
                            "stopping panic clicks."
                        )

                    panic_mode = False
                    danger_locked = False

            time.sleep(SCAN_DELAY)

            continue

        # ====================================================
        # NORMAL BAR DETECTED
        # ====================================================

        start_x, end_x, width = result

        if panic_mode:

            print(
                "Rectangle detected again - "
                "panic mode OFF."
            )

        panic_mode = False
        panic_start_time = 0
        last_panic_click = 0

        bar_was_visible = True

        print(
            f"Bar X={start_x}-{end_x} "
            f"Width={width}"
        )

        # ====================================================
        # DANGER ZONE
        # ====================================================

        if width < ADVANCED_FISHING_THRESHOLD:

            if not danger_locked:

                native_click()

                click_count += 1

                print(
                    f"CLICK #{click_count} | "
                    f"X={start_x}-{end_x} | "
                    f"Width={width}"
                )

                danger_locked = True

                time.sleep(REARM_DELAY)

        else:

            # Re-arm once the rectangle leaves the danger zone.
            danger_locked = False

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

    if not running or emergency_stop:
        return

    print()
    print("Waiting 0.5 seconds before closing result...")

    time.sleep(RESULT_CLOSE_DELAY)

    if not running or emergency_stop:
        return

    print("Closing fish result...")
    print(f"Moving to result X: {FISH_RESULT_CLOSE}")

    move_mouse_native(
        FISH_RESULT_CLOSE[0],
        FISH_RESULT_CLOSE[1]
    )

    time.sleep(0.05)

    native_click()

    time.sleep(0.4)

    print("Fish result closed.")


# ============================================================
# ONE FISHING CYCLE
# ============================================================

def fishing_cycle(cycle_number):

    if not running or emergency_stop:
        return False

    print()
    print("======================================")
    print(f"FISHING CYCLE #{cycle_number}")
    print("======================================")

    print("Moving to Fish button...")

    move_mouse_native(
        FISH_BUTTON[0],
        FISH_BUTTON[1]
    )

    time.sleep(0.05)

    native_click()

    if not wait_for_minigame():
        return False

    play_fishing_minigame()

    if not running or emergency_stop:
        return False

    close_fish_result()

    print()
    print(
        f"Cycle complete! "
        f"Total cycles: {cycle_number}"
    )

    return True


# ============================================================
# MACRO LOOP
# ============================================================

def macro_loop():

    global running

    cycle_number = 1

    while running and not emergency_stop:

        success = fishing_cycle(cycle_number)

        if not success:
            break

        cycle_number += 1

        time.sleep(0.5)

    print()
    print("Macro loop stopped.")


# ============================================================
# F8 START / STOP
# ============================================================

def toggle_macro():

    global running
    global emergency_stop

    if running:

        print()
        print("Macro PAUSED.")

        running = False

    else:

        emergency_stop = False
        running = True

        print()
        print("Macro STARTED.")

        macro_loop()


# ============================================================
# F3 EMERGENCY STOP
# ============================================================

def emergency():

    global running
    global emergency_stop

    emergency_stop = True
    running = False

    print()
    print("======================================")
    print("EMERGENCY STOP")
    print("======================================")


# ============================================================
# MAIN
# ============================================================

print("======================================")
print("SOLS RNG FISHING MACRO")
print("======================================")
print("F8 = Start")
print("F3 = Emergency Stop")
print()
print("Fishing + fish-result loop enabled.")
print(
    f"Advanced threshold: "
    f"{ADVANCED_FISHING_THRESHOLD} pixels"
)
print("State-based clicking enabled.")
print("Panic cooldown: 0.50 seconds")
print("2D rectangle recovery detection enabled.")
print("Result close delay: 0.50 seconds")
print("======================================")

keyboard.add_hotkey("f8", toggle_macro)
keyboard.add_hotkey("f3", emergency)

try:

    while True:
        time.sleep(0.1)

except KeyboardInterrupt:

    emergency()
