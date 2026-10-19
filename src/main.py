import pyautogui
import keyboard
import time
import ctypes
import threading

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

ADVANCED_FISHING_THRESHOLD = 25

COLOR_SAMPLE_DELAY = 0.050
SCAN_DELAY = 0.010

COLOR_TOLERANCE = 10

# Normal clicking
REARM_DELAY = 0.08

# Panic clicking when the rectangle is hidden
MISSING_COLOR_COOLDOWN = 0.60

# Prevent clicking the exact same danger zone repeatedly
SAME_POSITION_COOLDOWN = 0.25

# ============================================================
# GLOBAL STATE
# ============================================================

running = False
emergency_stop = False
macro_thread = None

current_bar_color = None


# ============================================================
# WINDOWS NATIVE MOUSE
# ============================================================

user32 = ctypes.windll.user32

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004


def native_move_to(target_x, target_y, steps=30):
    current_x, current_y = pyautogui.position()

    dx = target_x - current_x
    dy = target_y - current_y

    for i in range(1, steps + 1):
        if emergency_stop:
            return

        move_x = int(dx * i / steps)
        move_y = int(dy * i / steps)

        user32.mouse_event(
            MOUSEEVENTF_MOVE,
            move_x - int(dx * (i - 1) / steps),
            move_y - int(dy * (i - 1) / steps),
            0,
            0
        )

        time.sleep(0.003)


def native_click():
    if emergency_stop:
        return

    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.02)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)


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


def get_bar_color():
    """
    Same basic method as the old macro:
    sample the fishing bar around X=955, Y=767.
    """

    screenshot = pyautogui.screenshot()

    # First try the original sampling point.
    color = screenshot.getpixel((955, BAR_Y))

    # If it looks usable, use it.
    if (
        color != (255, 255, 255)
        and color[0] + color[1] + color[2] > 40
    ):
        return color

    # Try nearby pixels.
    for x in range(950, 961):
        color = screenshot.getpixel((x, BAR_Y))

        if (
            color != (255, 255, 255)
            and color[0] + color[1] + color[2] > 40
        ):
            return color

    # Final fallback:
    # scan the fishing bar for a usable colored pixel.
    for x in range(BAR_LEFT, BAR_RIGHT + 1):
        color = screenshot.getpixel((x, BAR_Y))

        if (
            color != (255, 255, 255)
            and color[0] + color[1] + color[2] > 40
        ):
            return color

    return None


def find_bar(bar_color):
    """
    Find the contiguous rectangle matching the learned color.
    Returns:
        (left_x, right_x, width)
    or:
        None
    """

    if bar_color is None:
        return None

    screenshot = pyautogui.screenshot()

    matches = []

    for x in range(BAR_LEFT, BAR_RIGHT + 1):
        pixel = screenshot.getpixel((x, BAR_Y))

        if colors_match(pixel, bar_color):
            matches.append(x)

    if not matches:
        return None

    # Find the longest contiguous section.
    best_start = None
    best_end = None

    current_start = matches[0]
    current_end = matches[0]

    for x in matches[1:]:
        if x <= current_end + 1:
            current_end = x
        else:
            if (
                best_start is None
                or current_end - current_start
                > best_end - best_start
            ):
                best_start = current_start
                best_end = current_end

            current_start = x
            current_end = x

    if (
        best_start is None
        or current_end - current_start
        > best_end - best_start
    ):
        best_start = current_start
        best_end = current_end

    width = best_end - best_start

    return best_start, best_end, width


# ============================================================
# MINIGAME DETECTION
# ============================================================

def wait_for_minigame():
    print()
    print("Waiting for minigame...")

    start_time = time.time()
    last_status = 0

    while not emergency_stop:

        elapsed = time.time() - start_time

        if elapsed > MINIGAME_TIMEOUT:
            print("Minigame wait timed out.")
            return False

        try:
            pixel = pyautogui.pixel(
                MINIGAME_START_PIXEL[0],
                MINIGAME_START_PIXEL[1]
            )
        except:
            pixel = (0, 0, 0)

        # Old macro waits for the white indicator.
        if (
            pixel[0] > 240
            and pixel[1] > 240
            and pixel[2] > 240
        ):
            print(
                f"Minigame detected after {elapsed:.1f} seconds!"
            )
            return True

        if elapsed - last_status >= 5:
            print(f"Still waiting... {elapsed:.1f}s")
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
    print("STATE-BASED DETECTION")
    print("CLICKS ENABLED")
    print("======================================")

    # Same positioning used by the old macro.
    native_move_to(950, 880)
    time.sleep(COLOR_SAMPLE_DELAY)

    current_bar_color = get_bar_color()

    if current_bar_color is None:
        print("Could not learn fishing bar color.")
        return

    print(
        f"Bar color learned: RGB{current_bar_color}"
    )

    print("Tracking bar...")

    start_time = time.time()

    clicks = 0

    # --------------------------------------------------------
    # NORMAL STATE
    # --------------------------------------------------------

    danger_locked = False

    # Used to prevent repeatedly clicking the exact same
    # stationary rectangle.
    last_click_left = None
    last_click_right = None
    last_normal_click = 0

    # --------------------------------------------------------
    # PANIC STATE
    # --------------------------------------------------------

    panic_mode = False
    last_panic_click = 0

    while not emergency_stop:

        if time.time() - start_time > 9:
            break

        result = find_bar(current_bar_color)

        # ====================================================
        # RECTANGLE IS NOT CURRENTLY VISIBLE
        # ====================================================

        if result is None:

            # Only enter panic mode if we previously had
            # a visible rectangle.
            if last_click_left is not None:
                panic_mode = True

            # Panic clicking is ONLY allowed while panic mode
            # is active.
            if panic_mode:

                now = time.time()

                if now - last_panic_click >= MISSING_COLOR_COOLDOWN:

                    native_click()

                    clicks += 1
                    last_panic_click = now

                    print(
                        f"PANIC CLICK #{clicks} | "
                        f"Color temporarily hidden"
                    )

            time.sleep(SCAN_DELAY)
            continue

        # ====================================================
        # RECTANGLE IS BACK
        # ====================================================

        # THIS IS THE IMPORTANT FIX:
        # The moment the rectangle is detected again,
        # panic mode is completely disabled.
        if panic_mode:
            panic_mode = False
            print("Rectangle detected again - panic mode OFF.")

        left_x, right_x, width = result

        print(
            f"Bar X={left_x}-{right_x} Width={width}"
        )

        now = time.time()

        # ====================================================
        # DANGER ZONE
        # ====================================================

        if width < ADVANCED_FISHING_THRESHOLD:

            # Only click once when entering the danger zone.
            if not danger_locked:

                # Prevent rapid repeated clicks at the same
                # exact location.
                same_position = (
                    left_x == last_click_left
                    and right_x == last_click_right
                )

                if (
                    not same_position
                    or now - last_normal_click
                    >= SAME_POSITION_COOLDOWN
                ):

                    native_click()

                    clicks += 1
                    last_normal_click = now

                    last_click_left = left_x
                    last_click_right = right_x

                    print(
                        f"CLICK #{clicks} | "
                        f"X={left_x}-{right_x} | "
                        f"Width={width}"
                    )

                danger_locked = True

        # ====================================================
        # SAFE ZONE
        # ====================================================

        else:

            # Once the rectangle gets back above the threshold,
            # re-arm the detector.
            if danger_locked:
                time.sleep(REARM_DELAY)

            danger_locked = False

        time.sleep(SCAN_DELAY)

    print()
    print(
        f"Fishing detection finished. Clicks: {clicks}"
    )

    current_bar_color = None

    print("Bar color erased.")


# ============================================================
# CLOSE FISH RESULT
# ============================================================

def close_fish_result():

    if emergency_stop:
        return

    print()
    print("Closing fish result...")
    print(
        f"Moving to result X: {FISH_RESULT_CLOSE}"
    )

    native_move_to(
        FISH_RESULT_CLOSE[0],
        FISH_RESULT_CLOSE[1]
    )

    time.sleep(0.10)
    native_click()

    print("Fish result closed.")

    time.sleep(0.5)


# ============================================================
# ONE FISHING CYCLE
# ============================================================

def fishing_cycle(cycle_number):

    print()
    print("======================================")
    print(f"FISHING CYCLE #{cycle_number}")
    print("======================================")

    print("Moving to Fish button...")

    native_move_to(
        FISH_BUTTON[0],
        FISH_BUTTON[1]
    )

    time.sleep(0.10)

    if emergency_stop:
        return False

    native_click()

    if emergency_stop:
        return False

    if not wait_for_minigame():
        return False

    if emergency_stop:
        return False

    play_fishing_minigame()

    if emergency_stop:
        return False

    close_fish_result()

    print()
    print(
        f"Cycle complete! Total cycles: {cycle_number}"
    )

    return True


# ============================================================
# MAIN MACRO LOOP
# ============================================================

def macro_loop():

    global running

    cycle_number = 0

    while running and not emergency_stop:

        cycle_number += 1

        success = fishing_cycle(cycle_number)

        if emergency_stop:
            break

        if not success:
            time.sleep(0.5)

    running = False


# ============================================================
# F8 START / STOP
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

    global emergency_stop
    global running

    emergency_stop = True
    running = False

    print()
    print("======================================")
    print("EMERGENCY STOP")
    print("======================================")


# ============================================================
# STARTUP
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
print("Panic cooldown: 0.60 seconds")
print("======================================")

keyboard.add_hotkey("f8", toggle_macro)
keyboard.add_hotkey("f3", emergency)

try:
    while True:
        time.sleep(0.1)

except KeyboardInterrupt:
    emergency()
