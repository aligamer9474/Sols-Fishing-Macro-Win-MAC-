import time
import threading
import ctypes
import pyautogui
import keyboard


# ============================================================
# SETTINGS
# ============================================================

FISH_BUTTON = (853, 832)
FISH_RESULT_CLOSE = (1113, 342)

MINIGAME_START_PIXEL = (1176, 836)

# Fishing bar line
BAR_LEFT_X = 757
BAR_RIGHT_X = 1161
BAR_Y = 767

# Used only if the exact line temporarily fails
BAR_2D_TOP = 755
BAR_2D_BOTTOM = 780

# Old macro threshold
ADVANCED_THRESHOLD = 25

# NEW panic timing
PANIC_COOLDOWN = 0.22

# How close the mouse must get to a target
MOUSE_TOLERANCE = 2

# Minigame timeout
MINIGAME_TIMEOUT = 19

# Result close delay
RESULT_CLOSE_DELAY = 0.40


# ============================================================
# WINDOWS MOUSE CONTROL
# ============================================================

user32 = ctypes.windll.user32

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004


def get_mouse_position():
    point = ctypes.wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(point))
    return point.x, point.y


def move_mouse_native(target_x, target_y):
    """
    Moves using relative Windows mouse input.

    The important part is that we repeatedly check the REAL
    cursor position instead of assuming the mouse went exactly
    where we told it to go.
    """

    for _ in range(500):
        if not running:
            return False

        current_x, current_y = get_mouse_position()

        dx = target_x - current_x
        dy = target_y - current_y

        if abs(dx) <= MOUSE_TOLERANCE and abs(dy) <= MOUSE_TOLERANCE:
            return True

        # Small relative movements prevent huge overshoots.
        step_x = max(-3, min(3, dx))
        step_y = max(-3, min(3, dy))

        user32.mouse_event(
            MOUSEEVENTF_MOVE,
            int(step_x),
            int(step_y),
            0,
            0
        )

        time.sleep(0.004)

    print("WARNING: Mouse movement did not reach target.")
    return False


def native_click():
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.01)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)


# ============================================================
# PIXEL FUNCTIONS
# ============================================================

def get_pixel(x, y):
    try:
        return pyautogui.pixel(x, y)
    except Exception:
        return None


def color_close(color1, color2, tolerance=10):
    if color1 is None or color2 is None:
        return False

    return (
        abs(color1[0] - color2[0]) <= tolerance
        and abs(color1[1] - color2[1]) <= tolerance
        and abs(color1[2] - color2[2]) <= tolerance
    )


# ============================================================
# FIND RECTANGLE ON THE SPECIFIC FISHING LINE
# ============================================================

def find_bar(bar_color):
    """
    Scan the exact fishing line.

    This is based on the old macro's method:
    find the first matching pixel, then continue right until
    the matching color ends.

    Returns:
        left_x, right_x, width, center_x
    """

    left_x = None

    for x in range(BAR_LEFT_X, BAR_RIGHT_X + 1):
        pixel = get_pixel(x, BAR_Y)

        if color_close(pixel, bar_color, 10):
            left_x = x
            break

    if left_x is None:
        return None

    right_x = left_x

    for x in range(left_x + 1, BAR_RIGHT_X + 1):
        pixel = get_pixel(x, BAR_Y)

        if color_close(pixel, bar_color, 10):
            right_x = x
        else:
            break

    width = right_x - left_x
    center_x = (left_x + right_x) // 2

    return left_x, right_x, width, center_x


# ============================================================
# 2D FALLBACK
# ============================================================

def find_bar_2d(bar_color):
    """
    Small fallback region around the fishing line.

    This is NOT the main detector.
    The main detector always checks Y=767 first.
    """

    for y in range(BAR_2D_TOP, BAR_2D_BOTTOM + 1):

        left_x = None

        for x in range(BAR_LEFT_X, BAR_RIGHT_X + 1):

            pixel = get_pixel(x, y)

            if color_close(pixel, bar_color, 10):
                left_x = x
                break

        if left_x is None:
            continue

        right_x = left_x

        for x in range(left_x + 1, BAR_RIGHT_X + 1):

            pixel = get_pixel(x, y)

            if color_close(pixel, bar_color, 10):
                right_x = x
            else:
                break

        width = right_x - left_x
        center_x = (left_x + right_x) // 2

        return left_x, right_x, width, center_x

    return None


# ============================================================
# WAIT FOR MINIGAME
# ============================================================

def wait_for_minigame():
    print()
    print("Waiting for minigame...")

    start_time = time.time()
    last_message = 0

    while running:

        elapsed = time.time() - start_time

        if elapsed - last_message >= 5:
            print(f"Still waiting... {elapsed:.1f}s")
            last_message = elapsed

        pixel = get_pixel(
            MINIGAME_START_PIXEL[0],
            MINIGAME_START_PIXEL[1]
        )

        # White pixel indicates minigame
        if pixel and all(value >= 245 for value in pixel):
            print(f"Minigame detected after {elapsed:.1f} seconds!")
            return True

        if elapsed >= MINIGAME_TIMEOUT:
            print("Minigame timeout reached.")
            return False

        time.sleep(0.01)

    return False


# ============================================================
# SAMPLE BAR COLOR
# ============================================================

def learn_bar_color():
    """
    The old macro sampled the bar around the center area.
    """

    # Primary sample
    color = get_pixel(955, BAR_Y)

    if color:
        return color

    # Nearby samples
    for x in range(940, 971):
        color = get_pixel(x, BAR_Y)

        if color:
            return color

    return None


# ============================================================
# FISHING MINIGAME
# ============================================================

def fishing_minigame():

    print()
    print("======================================")
    print("FISHING MINIGAME")
    print("RECTANGLE POSITION DETECTION")
    print("CLICKS ENABLED")
    print("======================================")

    bar_color = learn_bar_color()

    if bar_color is None:
        print("Could not learn bar color.")
        return False

    print(
        f"Bar color learned: "
        f"RGB({bar_color[0]}, {bar_color[1]}, {bar_color[2]})"
    )

    print(
        f"Tracking line: X={BAR_LEFT_X}-{BAR_RIGHT_X}, "
        f"Y={BAR_Y}"
    )

    clicks = 0
    panic_clicks = 0

    last_panic_click = 0
    last_bar_center = None
    last_bar_time = None

    # Prevent infinite fishing detection
    start_time = time.time()

    while running:

        # ----------------------------------------------------
        # Stop after a reasonable amount of time
        # ----------------------------------------------------

        if time.time() - start_time > 12:
            break

        # ----------------------------------------------------
        # Find rectangle on exact line
        # ----------------------------------------------------

        bar = find_bar(bar_color)

        # ----------------------------------------------------
        # If exact line fails, try tiny 2D fallback
        # ----------------------------------------------------

        if bar is None:
            bar = find_bar_2d(bar_color)

        # ----------------------------------------------------
        # RECTANGLE FOUND
        # ----------------------------------------------------

        if bar is not None:

            left_x, right_x, width, center_x = bar

            print(
                f"Bar X={left_x}-{right_x} "
                f"Width={width} "
                f"Center={center_x}"
            )

            current_time = time.time()

            # ------------------------------------------------
            # Calculate movement of rectangle
            # ------------------------------------------------

            velocity = 0

            if (
                last_bar_center is not None
                and last_bar_time is not None
            ):
                time_difference = current_time - last_bar_time

                if time_difference > 0:
                    velocity = (
                        center_x - last_bar_center
                    ) / time_difference

            last_bar_center = center_x
            last_bar_time = current_time

            # ------------------------------------------------
            # Main old-macro-style detection
            # ------------------------------------------------

            if width < ADVANCED_THRESHOLD:

                native_click()

                clicks += 1

                print(
                    f"CLICK #{clicks} | "
                    f"X={left_x}-{right_x} | "
                    f"Width={width} | "
                    f"Center={center_x}"
                )

                time.sleep(0.025)

            # ------------------------------------------------
            # Rectangle is large.
            #
            # We don't click yet, but we continue tracking
            # its position so we know which direction it is
            # moving.
            # ------------------------------------------------

            else:

                if abs(velocity) > 20:

                    direction = "RIGHT" if velocity > 0 else "LEFT"

                    print(
                        f"Tracking movement: "
                        f"{direction} | "
                        f"Velocity={velocity:.1f}px/s"
                    )

            time.sleep(0.008)

        # ----------------------------------------------------
        # RECTANGLE NOT FOUND
        # ----------------------------------------------------

        else:

            now = time.time()

            if now - last_panic_click >= PANIC_COOLDOWN:

                native_click()

                clicks += 1
                panic_clicks += 1

                last_panic_click = now

                print(
                    f"PANIC CLICK #{panic_clicks} "
                    f"| Cooldown: {PANIC_COOLDOWN:.2f}s"
                )

            time.sleep(0.008)

    print()
    print(
        f"Fishing detection finished. "
        f"Clicks: {clicks}"
    )

    return True


# ============================================================
# FISHING CYCLE
# ============================================================

def fishing_cycle(cycle_number):

    print()
    print("======================================")
    print(f"FISHING CYCLE #{cycle_number}")
    print("======================================")

    # --------------------------------------------------------
    # Move to Fish button
    # --------------------------------------------------------

    print("Moving to Fish button...")

    if not move_mouse_native(
        FISH_BUTTON[0],
        FISH_BUTTON[1]
    ):
        return False

    actual_position = get_mouse_position()

    print(
        f"Mouse position after movement: "
        f"{actual_position}"
    )

    if not running:
        return False

    time.sleep(0.10)

    # --------------------------------------------------------
    # Click Fish
    # --------------------------------------------------------

    native_click()

    # --------------------------------------------------------
    # Wait for minigame
    # --------------------------------------------------------

    if not wait_for_minigame():
        return False

    if not running:
        return False

    # --------------------------------------------------------
    # Play minigame
    # --------------------------------------------------------

    fishing_minigame()

    if not running:
        return False

    # --------------------------------------------------------
    # Wait before closing result
    # --------------------------------------------------------

    print()
    print(
        f"Waiting {RESULT_CLOSE_DELAY:.2f} seconds "
        f"before closing result..."
    )

    time.sleep(RESULT_CLOSE_DELAY)

    if not running:
        return False

    # --------------------------------------------------------
    # Close fish result
    # --------------------------------------------------------

    print("Closing fish result...")

    move_mouse_native(
        FISH_RESULT_CLOSE[0],
        FISH_RESULT_CLOSE[1]
    )

    if not running:
        return False

    time.sleep(0.10)

    native_click()

    print("Fish result closed.")

    time.sleep(0.30)

    return True


# ============================================================
# MACRO LOOP
# ============================================================

running = False
macro_thread = None
cycle_count = 0


def macro_loop():

    global cycle_count

    cycle_count = 0

    while running:

        cycle_count += 1

        success = fishing_cycle(cycle_count)

        if not running:
            break

        if not success:
            print("Fishing cycle stopped.")
            break

        print()
        print(
            f"Cycle complete! "
            f"Total cycles: {cycle_count}"
        )

        time.sleep(0.20)

    print()
    print("Macro loop stopped.")


# ============================================================
# HOTKEYS
# ============================================================

def start_pause_macro():

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
# MAIN
# ============================================================

print("======================================")
print("SOLS RNG FISHING MACRO")
print("======================================")
print("F8 = Start / Pause")
print("F3 = Emergency Stop")
print()
print("Fishing + fish-result loop enabled.")
print(f"Advanced threshold: {ADVANCED_THRESHOLD} pixels")
print("Specific fishing line detection enabled.")
print(f"Fishing line: X={BAR_LEFT_X}-{BAR_RIGHT_X}, Y={BAR_Y}")
print(f"Panic cooldown: {PANIC_COOLDOWN:.2f} seconds")
print("Mouse position correction enabled.")
print(f"Result close delay: {RESULT_CLOSE_DELAY:.2f} seconds")
print("======================================")
print()

keyboard.add_hotkey("f8", start_pause_macro)
keyboard.add_hotkey("f3", emergency_stop)

try:
    while True:
        time.sleep(0.1)

except KeyboardInterrupt:
    running = False
    print()
    print("Program closed.")
