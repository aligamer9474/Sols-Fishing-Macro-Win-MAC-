import ctypes
import time
import threading
import keyboard


# ============================================================
# SETTINGS
# ============================================================

FISH_BUTTON = (853, 832)
FISH_RESULT_CLOSE = (1113, 342)

MINIGAME_START_PIXEL = (1176, 836)

BAR_LEFT = 757
BAR_RIGHT = 1161
BAR_Y = 767

BAR_SAMPLE = (955, 767)

ADVANCED_THRESHOLD = 25

# Slows down repeated clicks.
# The old macro used about 0.025 seconds.
CLICK_COOLDOWN = 0.15

# How long to watch each fishing minigame.
MINIGAME_TIMEOUT = 9.0

# Timing from the old macro.
RESULT_WAIT = 0.30
RESULT_CLOSE_WAIT = 0.70

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


def native_click():
    user32.mouse_event(
        MOUSEEVENTF_LEFTDOWN,
        0,
        0,
        0,
        0
    )

    time.sleep(0.01)

    user32.mouse_event(
        MOUSEEVENTF_LEFTUP,
        0,
        0,
        0,
        0
    )


def move_mouse_smooth(target_x, target_y):
    """
    Uses relative Windows mouse movement.
    This is the method that Roblox successfully recognized.
    """

    while True:
        current_x, current_y = get_mouse_position()

        dx = target_x - current_x
        dy = target_y - current_y

        if abs(dx) <= 1 and abs(dy) <= 1:
            break

        step_x = max(-3, min(3, dx))
        step_y = max(-3, min(3, dy))

        user32.mouse_event(
            MOUSEEVENTF_MOVE,
            step_x,
            step_y,
            0,
            0
        )

        time.sleep(0.004)


# ============================================================
# PIXEL FUNCTIONS
# ============================================================

def get_pixel(x, y):
    """
    Gets a screen pixel using Windows.
    Returns RGB tuple.
    """

    hdc = user32.GetDC(0)

    color = user32.GetPixel(
        hdc,
        x,
        y
    )

    user32.ReleaseDC(0, hdc)

    if color == -1:
        return None

    r = color & 0xFF
    g = (color >> 8) & 0xFF
    b = (color >> 16) & 0xFF

    return r, g, b


def color_matches(color1, color2, tolerance=5):
    if color1 is None or color2 is None:
        return False

    return (
        abs(color1[0] - color2[0]) <= tolerance
        and
        abs(color1[1] - color2[1]) <= tolerance
        and
        abs(color1[2] - color2[2]) <= tolerance
    )


def find_bar(bar_color):
    """
    Searches the same horizontal row used by the old macro.

    Returns:
        (left_x, right_x, width)
    or:
        None
    """

    left_x = None

    for x in range(BAR_LEFT, BAR_RIGHT + 1):
        pixel = get_pixel(x, BAR_Y)

        if color_matches(pixel, bar_color, 5):
            left_x = x
            break

    if left_x is None:
        return None

    right_x = left_x

    for x in range(left_x + 1, BAR_RIGHT + 1):
        pixel = get_pixel(x, BAR_Y)

        if color_matches(pixel, bar_color, 10):
            right_x = x
        else:
            break

    width = right_x - left_x

    return left_x, right_x, width


# ============================================================
# MINIGAME START DETECTION
# ============================================================

def wait_for_minigame():
    print("Waiting for minigame...")

    start_time = time.time()
    last_report = 0

    while running:

        color = get_pixel(
            MINIGAME_START_PIXEL[0],
            MINIGAME_START_PIXEL[1]
        )

        if color == (255, 255, 255):
            return True

        elapsed = time.time() - start_time

        if elapsed - last_report >= 5:
            print(f"Still waiting... {elapsed:.1f}s")
            last_report = elapsed

        time.sleep(0.01)

    return False


# ============================================================
# FISHING MINIGAME
# ============================================================

def fishing_minigame():

    print()
    print("======================================")
    print("FISHING MINIGAME")
    print("OLD MACRO DETECTION - SLOWED")
    print("======================================")
    print(f"Fishing line: X={BAR_LEFT}-{BAR_RIGHT}, Y={BAR_Y}")
    print(f"Advanced threshold: {ADVANCED_THRESHOLD}")
    print(f"Click cooldown: {CLICK_COOLDOWN}s")

    # --------------------------------------------------------
    # Sample the bar color exactly like the old macro.
    # --------------------------------------------------------

    time.sleep(0.05)

    bar_color = get_pixel(
        BAR_SAMPLE[0],
        BAR_SAMPLE[1]
    )

    if bar_color is None:
        print("Could not read bar color.")
        return False

    print(
        f"Bar color learned: "
        f"RGB({bar_color[0]}, {bar_color[1]}, {bar_color[2]})"
    )

    start_time = time.time()

    detections = 0
    missed_scans = 0
    total_clicks = 0

    last_click_time = 0

    # Prevent repeatedly clicking the exact same bar
    # while the screen has not meaningfully changed.
    last_bar_left = None
    last_bar_right = None

    while running:

        if time.time() - start_time > MINIGAME_TIMEOUT:
            break

        result = find_bar(bar_color)

        if result is not None:

            left_x, right_x, width = result

            detections += 1

            print(
                f"BAR FOUND: "
                f"{left_x}-{right_x} "
                f"Width={width} "
                f"Center={(left_x + right_x) // 2}"
            )

            current_time = time.time()

            # ------------------------------------------------
            # Only click when:
            #
            # 1. The bar is newly detected, OR
            # 2. The bar has moved enough,
            # AND
            # 3. Cooldown has expired.
            #
            # This stops the same 939-959 bar from causing
            # 6+ clicks in a row.
            # ------------------------------------------------

            bar_moved = (
                last_bar_left is None
                or
                abs(left_x - last_bar_left) >= 4
                or
                abs(right_x - last_bar_right) >= 4
            )

            cooldown_ready = (
                current_time - last_click_time
                >= CLICK_COOLDOWN
            )

            should_click = False

            if width < ADVANCED_THRESHOLD:
                if bar_moved and cooldown_ready:
                    should_click = True

            # If the bar disappears completely, the old macro
            # clicked. We DO NOT panic spam here.
            #
            # The last known state is retained instead.

            if should_click:

                native_click()

                total_clicks += 1
                last_click_time = current_time

                print(f"CLICK #{total_clicks}")

                last_bar_left = left_x
                last_bar_right = right_x

            else:
                # Remember where the bar currently is even if
                # we did not click it.
                last_bar_left = left_x
                last_bar_right = right_x

        else:

            missed_scans += 1

        # Small scan delay.
        time.sleep(0.01)

    print()
    print("Fishing detection finished.")
    print(f"Bar detections: {detections}")
    print(f"Missed scans: {missed_scans}")
    print(f"Total clicks: {total_clicks}")

    return running


# ============================================================
# FISHING CYCLE
# ============================================================

def fishing_cycle():

    global cycle_count

    print()
    print("======================================")
    print(f"FISHING CYCLE #{cycle_count + 1}")
    print("======================================")

    # --------------------------------------------------------
    # Move to Fish button.
    # --------------------------------------------------------

    print("Moving to Fish button...")

    move_mouse_smooth(
        FISH_BUTTON[0],
        FISH_BUTTON[1]
    )

    print(
        f"Mouse position: "
        f"{get_mouse_position()}"
    )

    if not running:
        return False

    print("Clicking Fish...")

    native_click()

    # --------------------------------------------------------
    # Wait for minigame.
    # --------------------------------------------------------

    if not wait_for_minigame():
        return False

    print(
        f"Minigame detected after "
        f"{time.time() - cycle_start_time:.1f} seconds!"
    )

    # --------------------------------------------------------
    # Move to the old sample position before detection.
    #
    # IMPORTANT:
    # The mouse stays here during the actual minigame.
    # We do NOT move it with the bar.
    # --------------------------------------------------------

    move_mouse_smooth(
        950,
        880
    )

    if not running:
        return False

    fishing_minigame()

    if not running:
        return False

    # --------------------------------------------------------
    # Fish-result X
    # --------------------------------------------------------

    print()
    print("Moving to fish-result X...")

    time.sleep(RESULT_WAIT)

    move_mouse_smooth(
        FISH_RESULT_CLOSE[0],
        FISH_RESULT_CLOSE[1]
    )

    print(
        f"Mouse at X: "
        f"{get_mouse_position()}"
    )

    if not running:
        return False

    time.sleep(RESULT_CLOSE_WAIT)

    native_click()

    time.sleep(0.30)

    cycle_count += 1

    print("Fish-result X clicked.")
    print(
        f"Cycle complete! "
        f"Total cycles: {cycle_count}"
    )

    return True


# ============================================================
# MACRO CONTROL
# ============================================================

running = False
macro_thread = None
cycle_count = 0
cycle_start_time = 0


def macro_loop():

    global cycle_start_time

    while running:

        cycle_start_time = time.time()

        success = fishing_cycle()

        if not success:
            break

        time.sleep(0.2)


def toggle_macro():

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
# HOTKEYS
# ============================================================

keyboard.add_hotkey(
    "f8",
    toggle_macro
)

keyboard.add_hotkey(
    "f3",
    emergency_stop
)


# ============================================================
# START
# ============================================================

print("======================================")
print("SOLS RNG FISHING MACRO")
print("======================================")
print("F8 = Start / Pause")
print("F3 = Emergency Stop")
print()
print(f"Fish button: {FISH_BUTTON}")
print(f"Result X: {FISH_RESULT_CLOSE}")
print()
print("Ready.")

keyboard.wait()
