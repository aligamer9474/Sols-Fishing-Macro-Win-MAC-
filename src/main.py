import ctypes
import time
import threading
import pyautogui
import keyboard

# ======================================
# SOLS RNG FISHING MACRO
# ======================================

FISH_BUTTON = (853, 832)
FISH_RESULT_CLOSE = (1113, 342)

MINIGAME_START_PIXEL = (1176, 836)

BAR_LEFT_X = 757
BAR_RIGHT_X = 1161
BAR_Y = 767

ADVANCED_THRESHOLD = 25

FISHING_DETECTION_TIME = 9.0

# How often the bar is scanned
BAR_CHECK_DELAY = 0.010

# Delay after a successful click
SUCCESS_CLICK_DELAY = 0.025

# Panic clicks are MUCH slower now
PANIC_CLICK_DELAY = 0.150

# Don't panic immediately when the minigame starts
PANIC_START_DELAY = 0.350

# Re-learn the bar color after this many failed scans
RELEARN_AFTER_MISSES = 12

# Result X timing from old macro
RESULT_MOVE_DELAY = 0.30
RESULT_CLICK_DELAY = 0.70

MOUSE_TOLERANCE = 2


# ======================================
# WINDOWS MOUSE INPUT
# ======================================

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


def native_move_relative(dx, dy):
    user32.mouse_event(
        MOUSEEVENTF_MOVE,
        int(dx),
        int(dy),
        0,
        0
    )


def move_mouse_to(x, y):
    """
    Move using relative Windows mouse input.
    This is the method that Roblox actually recognizes.
    """

    while running:
        current_x, current_y = get_mouse_position()

        dx = x - current_x
        dy = y - current_y

        if abs(dx) <= MOUSE_TOLERANCE and abs(dy) <= MOUSE_TOLERANCE:
            return True

        # Small steps prevent the Windows mouse acceleration
        # from overshooting the target.
        step_x = max(-3, min(3, dx))
        step_y = max(-3, min(3, dy))

        native_move_relative(step_x, step_y)

        time.sleep(0.004)

    return False


def native_click():
    user32.mouse_event(
        MOUSEEVENTF_LEFTDOWN,
        0,
        0,
        0,
        0
    )

    time.sleep(0.010)

    user32.mouse_event(
        MOUSEEVENTF_LEFTUP,
        0,
        0,
        0,
        0
    )


# ======================================
# GLOBAL STATE
# ======================================

running = False
emergency_stop = False

cycle_count = 0


# ======================================
# COLOR HELPERS
# ======================================

def color_distance(c1, c2):
    return (
        abs(c1[0] - c2[0]) +
        abs(c1[1] - c2[1]) +
        abs(c1[2] - c2[2])
    )


def is_white(color):
    r, g, b = color

    return (
        r > 240 and
        g > 240 and
        b > 240
    )


def is_blackish(color):
    r, g, b = color

    return (
        r < 8 and
        g < 8 and
        b < 8
    )


def is_reasonable_bar_color(color):
    r, g, b = color

    # Reject pure white / almost white UI
    if r > 240 and g > 240 and b > 240:
        return False

    # Reject completely black background
    if r < 8 and g < 8 and b < 8:
        return False

    # Reject very gray colors
    maximum = max(r, g, b)
    minimum = min(r, g, b)

    if maximum - minimum < 15:
        return False

    return True


# ======================================
# SCREENSHOT
# ======================================

def take_bar_screenshot():
    """
    Capture the entire fishing line at once.

    This is much faster than calling pyautogui.pixel()
    hundreds of times.
    """

    return pyautogui.screenshot(
        region=(
            BAR_LEFT_X,
            BAR_Y,
            BAR_RIGHT_X - BAR_LEFT_X + 1,
            1
        )
    )


# ======================================
# LEARN BAR COLOR
# ======================================

def learn_bar_color():
    """
    First uses the old macro's sample point:
        X = 955
        Y = 767

    If that point is bad, search nearby for a reasonable
    colored pixel.
    """

    screenshot = take_bar_screenshot()

    sample_offset = 955 - BAR_LEFT_X

    if 0 <= sample_offset < screenshot.width:
        color = screenshot.getpixel((sample_offset, 0))

        if is_reasonable_bar_color(color):
            print(
                f"Using old sample point: RGB{color}"
            )

            return color

    # Old sample was bad.
    # Search around the old point.
    for radius in range(1, 31):

        for offset in (
            sample_offset - radius,
            sample_offset + radius
        ):

            if 0 <= offset < screenshot.width:

                color = screenshot.getpixel((offset, 0))

                if is_reasonable_bar_color(color):

                    print(
                        f"Using nearby bar color: RGB{color}"
                    )

                    return color

    # If nothing useful was found, return None.
    return None


# ======================================
# FIND BAR
# ======================================

def find_bar(bar_color, screenshot):
    """
    Find a contiguous rectangle matching the learned
    fishing-bar color.

    Returns:
        left_x
        right_x
        width
        center_x
    """

    if bar_color is None:
        return None

    pixels = screenshot.load()

    best_left = None
    best_right = None
    best_width = 0

    current_left = None

    for x in range(screenshot.width):

        color = pixels[x, 0]

        if color_distance(color, bar_color) <= 5 * 3:

            if current_left is None:
                current_left = x

        else:

            if current_left is not None:

                current_right = x - 1
                width = current_right - current_left + 1

                if width > best_width:
                    best_width = width
                    best_left = current_left
                    best_right = current_right

                current_left = None

    # Handle a run that reaches the end.
    if current_left is not None:

        current_right = screenshot.width - 1
        width = current_right - current_left + 1

        if width > best_width:
            best_width = width
            best_left = current_left
            best_right = current_right

    if best_left is None:
        return None

    # Convert screenshot coordinates back to screen coordinates.
    left_x = BAR_LEFT_X + best_left
    right_x = BAR_LEFT_X + best_right

    width = right_x - left_x

    center_x = (left_x + right_x) // 2

    return (
        left_x,
        right_x,
        width,
        center_x
    )


# ======================================
# DYNAMIC BAR SEARCH
# ======================================

def find_possible_bar(screenshot):
    """
    Backup detector.

    If the original sampled color stops working,
    look for a strong contiguous colored section
    instead of immediately panic-clicking.
    """

    pixels = screenshot.load()

    best_left = None
    best_right = None
    best_width = 0

    current_left = None
    previous_color = None

    for x in range(screenshot.width):

        color = pixels[x, 0]

        valid = is_reasonable_bar_color(color)

        if valid and previous_color is not None:

            # Require neighboring pixels to have similar colors.
            if color_distance(color, previous_color) > 90:
                valid = False

        if valid:

            if current_left is None:
                current_left = x

            previous_color = color

        else:

            if current_left is not None:

                current_right = x - 1
                width = current_right - current_left + 1

                # Fishing rectangle is normally more than 1 pixel.
                if width >= 3 and width > best_width:
                    best_width = width
                    best_left = current_left
                    best_right = current_right

            current_left = None
            previous_color = None

    if current_left is not None:

        current_right = screenshot.width - 1
        width = current_right - current_left + 1

        if width >= 3 and width > best_width:
            best_width = width
            best_left = current_left
            best_right = current_right

    if best_left is None:
        return None

    left_x = BAR_LEFT_X + best_left
    right_x = BAR_LEFT_X + best_right

    width = right_x - left_x

    center_x = (left_x + right_x) // 2

    return (
        left_x,
        right_x,
        width,
        center_x
    )


# ======================================
# MINIGAME DETECTION
# ======================================

def wait_for_minigame():
    print()
    print("Waiting for minigame...")

    start = time.time()
    last_report = 0

    while running:

        try:
            color = pyautogui.pixel(
                MINIGAME_START_PIXEL[0],
                MINIGAME_START_PIXEL[1]
            )

        except Exception:
            time.sleep(0.05)
            continue

        # Old macro checks for white at this location.
        if is_white(color):

            elapsed = time.time() - start

            print(
                f"Minigame detected after {elapsed:.1f} seconds!"
            )

            return True

        elapsed = time.time() - start

        if elapsed - last_report >= 5:

            print(
                f"Still waiting... {elapsed:.1f}s"
            )

            last_report = elapsed

        time.sleep(0.05)

    return False


# ======================================
# FISHING MINIGAME
# ======================================

def fishing_minigame():

    print()
    print("======================================")
    print("FISHING MINIGAME")
    print("SMART BAR TRACKING")
    print("======================================")

    print(
        f"Fishing line: X={BAR_LEFT_X}-{BAR_RIGHT_X}, "
        f"Y={BAR_Y}"
    )

    bar_color = learn_bar_color()

    if bar_color is not None:

        print(
            f"Bar color learned: RGB{bar_color}"
        )

    else:

        print(
            "Could not learn initial bar color."
        )

    print(
        f"Advanced threshold: {ADVANCED_THRESHOLD}"
    )

    start_time = time.time()

    clicks = 0
    detections = 0
    misses = 0

    last_panic_click = time.time()

    # Don't click immediately when minigame starts.
    panic_allowed_at = (
        time.time() + PANIC_START_DELAY
    )

    while running:

        if time.time() - start_time >= FISHING_DETECTION_TIME:
            break

        screenshot = take_bar_screenshot()

        found = None

        # --------------------------------------
        # PRIMARY DETECTION
        # --------------------------------------

        if bar_color is not None:

            found = find_bar(
                bar_color,
                screenshot
            )

        # --------------------------------------
        # BACKUP DETECTION
        # --------------------------------------

        if found is None:

            misses += 1

            # Re-learn color occasionally.
            if misses >= RELEARN_AFTER_MISSES:

                new_color = learn_bar_color()

                if new_color is not None:

                    bar_color = new_color

                misses = 0

                # Take a fresh screenshot after learning.
                screenshot = take_bar_screenshot()

                if bar_color is not None:

                    found = find_bar(
                        bar_color,
                        screenshot
                    )

        # --------------------------------------
        # BAR FOUND
        # --------------------------------------

        if found is not None:

            left_x, right_x, width, center_x = found

            detections += 1

            # Ignore microscopic false detections.
            if width >= 2:

                print(
                    f"BAR FOUND: "
                    f"{left_x}-{right_x} "
                    f"Width={width} "
                    f"Center={center_x}"
                )

                # THIS IS THE IMPORTANT CHANGE:
                # Actually move the mouse to the rectangle.
                move_mouse_to(center_x, BAR_Y)

                if not running:
                    break

                # Click when the bar is small enough,
                # matching the old advanced detector.
                if width < ADVANCED_THRESHOLD:

                    native_click()

                    clicks += 1

                    print(
                        f"CLICK #{clicks} "
                        f"at X={center_x}"
                    )

                    time.sleep(
                        SUCCESS_CLICK_DELAY
                    )

                else:

                    # The bar is currently too wide.
                    # DO NOT panic-click.
                    time.sleep(
                        BAR_CHECK_DELAY
                    )

                continue

        # --------------------------------------
        # BAR NOT FOUND
        # --------------------------------------

        # This is where the old Python version went crazy.
        # We now wait before doing a panic click.
        now = time.time()

        if (
            now >= panic_allowed_at
            and now - last_panic_click >= PANIC_CLICK_DELAY
        ):

            # Before panic clicking, move to the middle
            # of the fishing area instead of randomly
            # clicking wherever the cursor currently is.
            move_mouse_to(
                (BAR_LEFT_X + BAR_RIGHT_X) // 2,
                BAR_Y
            )

            if not running:
                break

            native_click()

            clicks += 1

            print(
                f"PANIC CLICK #{clicks} "
                f"(bar not detected)"
            )

            last_panic_click = time.time()

        time.sleep(BAR_CHECK_DELAY)

    print()
    print("Fishing detection finished.")
    print(
        f"Bar detections: {detections}"
    )
    print(
        f"Missed scans: {misses}"
    )
    print(
        f"Total clicks: {clicks}"
    )


# ======================================
# FISHING CYCLE
# ======================================

def fishing_cycle():

    global cycle_count

    cycle_count += 1

    print()
    print("======================================")
    print(f"FISHING CYCLE #{cycle_count}")
    print("======================================")

    # --------------------------------------
    # FISH BUTTON
    # --------------------------------------

    print("Moving to Fish button...")

    move_mouse_to(
        FISH_BUTTON[0],
        FISH_BUTTON[1]
    )

    if not running:
        return

    print(
        f"Mouse position: {get_mouse_position()}"
    )

    print("Clicking Fish...")

    native_click()

    time.sleep(0.20)

    # --------------------------------------
    # WAIT FOR MINIGAME
    # --------------------------------------

    if not wait_for_minigame():
        return

    if not running:
        return

    # --------------------------------------
    # MINIGAME
    # --------------------------------------

    fishing_minigame()

    if not running:
        return

    # --------------------------------------
    # RESULT X
    # OLD MACRO TIMING
    # --------------------------------------

    print()
    print("Moving to fish-result X...")

    time.sleep(RESULT_MOVE_DELAY)

    move_mouse_to(
        FISH_RESULT_CLOSE[0],
        FISH_RESULT_CLOSE[1]
    )

    if not running:
        return

    print(
        f"Mouse at X: {get_mouse_position()}"
    )

    time.sleep(RESULT_CLICK_DELAY)

    native_click()

    print(
        "Fish-result X clicked."
    )

    time.sleep(0.30)

    print(
        f"Cycle complete! Total cycles: {cycle_count}"
    )


# ======================================
# MACRO LOOP
# ======================================

def macro_loop():

    global running

    while running:

        fishing_cycle()

        if not running:
            break

        time.sleep(0.30)


# ======================================
# HOTKEYS
# ======================================

def toggle_macro():

    global running

    if running:

        running = False

        print()
        print("Macro PAUSED.")

    else:

        running = True

        print()
        print("Macro STARTED.")

        thread = threading.Thread(
            target=macro_loop,
            daemon=True
        )

        thread.start()


def emergency_stop():

    global running
    global emergency_stop

    emergency_stop = True
    running = False

    print()
    print("!!! EMERGENCY STOP !!!")


# ======================================
# MAIN
# ======================================

print("======================================")
print("SOLS RNG FISHING MACRO")
print("======================================")
print("F8 = Start / Pause")
print("F3 = Emergency Stop")
print()
print("Smart rectangle tracking enabled.")
print("Mouse will move to detected rectangle.")
print("Panic clicks slowed to 150ms.")
print("No instant panic clicking at minigame start.")
print("Fast screenshot-based bar scanning.")
print(
    f"Fishing line: {BAR_LEFT_X}-{BAR_RIGHT_X} "
    f"at Y={BAR_Y}"
)
print(
    f"Threshold: {ADVANCED_THRESHOLD}"
)
print(
    f"Detection time: {FISHING_DETECTION_TIME}s"
)
print(
    "Result X has old 300ms/700ms timing."
)
print("======================================")
print()

keyboard.add_hotkey(
    "f8",
    toggle_macro
)

keyboard.add_hotkey(
    "f3",
    emergency_stop
)

try:

    while True:
        time.sleep(0.1)

except KeyboardInterrupt:

    running = False

    print()
    print("Program closed.")
