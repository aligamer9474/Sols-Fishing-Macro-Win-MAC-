import time
import ctypes
import threading
import keyboard
import pyautogui


# ============================================================
# SETTINGS
# ============================================================

FISH_BUTTON_X = 853
FISH_BUTTON_Y = 832

RESULT_X = 1113
RESULT_Y = 342

# Minigame starts when this pixel becomes white
MINIGAME_CHECK_X = 1176
MINIGAME_CHECK_Y = 836

# Bar color sample
BAR_SAMPLE_X = 955
BAR_SAMPLE_Y = 767

# Fishing bar scan area
BAR_LEFT = 757
BAR_RIGHT = 1161
BAR_Y = 767

# Advanced detection
BAR_COLOR_TOLERANCE = 5
BAR_EDGE_TOLERANCE = 10
ADVANCED_THRESHOLD = 25

# Player line fallback
CENTER_X = 959
CENTER_TOLERANCE = 8

LINE_BRIGHTNESS = 215
LINE_MIN_HEIGHT = 5

# False detections seen around this area
IGNORE_LINE_LEFT = 765
IGNORE_LINE_RIGHT = 800

# IMPORTANT:
# This is ONLY used when:
# 1. Rectangle is NOT detected
# 2. Player line IS detected
# 3. Player line is in the center
CENTER_FALLBACK_CLICK_INTERVAL = 0.20

# Maximum time for one fishing minigame
MINIGAME_TIMEOUT = 9.0


# ============================================================
# WINDOWS MOUSE
# ============================================================

user32 = ctypes.windll.user32

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_MOVE = 0x0001


def get_mouse_position():
    point = ctypes.wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(point))
    return point.x, point.y


def move_mouse_native(target_x, target_y):
    """
    Moves the mouse using small relative Windows mouse movements.
    This is what makes Roblox recognize the movement correctly.
    """

    while True:
        current_x, current_y = get_mouse_position()

        dx = target_x - current_x
        dy = target_y - current_y

        if abs(dx) <= 1 and abs(dy) <= 1:
            break

        # Keep each movement small so Roblox receives real mouse movement
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


# ============================================================
# GLOBAL STATE
# ============================================================

running = False
emergency_stop = False

cycle_count = 0


# ============================================================
# HOTKEYS
# ============================================================

def toggle_macro():
    global running

    running = not running

    if running:
        print("\n==============================")
        print("MACRO STARTED")
        print("==============================\n")
    else:
        print("\n==============================")
        print("MACRO PAUSED")
        print("==============================\n")


def emergency_stop_macro():
    global emergency_stop
    global running

    emergency_stop = True
    running = False

    print("\n==============================")
    print("EMERGENCY STOP")
    print("==============================\n")


keyboard.add_hotkey("f8", toggle_macro)
keyboard.add_hotkey("f3", emergency_stop_macro)


# ============================================================
# COLOR FUNCTIONS
# ============================================================

def get_pixel(x, y):
    try:
        return pyautogui.pixel(x, y)
    except Exception:
        return (0, 0, 0)


def is_white(pixel):
    r, g, b = pixel
    return r > 240 and g > 240 and b > 240


def color_matches(color1, color2, tolerance):
    return (
        abs(color1[0] - color2[0]) <= tolerance
        and
        abs(color1[1] - color2[1]) <= tolerance
        and
        abs(color1[2] - color2[2]) <= tolerance
    )


# ============================================================
# BAR DETECTION
# ============================================================

def find_bar(bar_color):
    """
    Finds the rectangle/bar using the sampled color.

    Returns:
        (left_x, right_x)
    or
        None
    """

    screenshot = pyautogui.screenshot()

    left_x = None

    # Find the left side
    for x in range(BAR_LEFT, BAR_RIGHT + 1):

        pixel = screenshot.getpixel((x, BAR_Y))

        if color_matches(
            pixel,
            bar_color,
            BAR_COLOR_TOLERANCE
        ):
            left_x = x
            break

    if left_x is None:
        return None

    # Find the right side
    right_x = left_x

    for x in range(left_x + 1, BAR_RIGHT + 1):

        pixel = screenshot.getpixel((x, BAR_Y))

        if color_matches(
            pixel,
            bar_color,
            BAR_EDGE_TOLERANCE
        ):
            right_x = x
        else:
            break

    return left_x, right_x


# ============================================================
# PLAYER LINE DETECTION
# ============================================================

def find_player_line():
    """
    Finds the bright vertical player line.

    Returns the X position or None.

    Known false-positive region around 765-800
    is ignored.
    """

    screenshot = pyautogui.screenshot()

    candidates = []

    for x in range(BAR_LEFT, BAR_RIGHT + 1):

        # Ignore known false detections
        if IGNORE_LINE_LEFT <= x <= IGNORE_LINE_RIGHT:
            continue

        bright_pixels = 0

        for y in range(750, 785):

            r, g, b = screenshot.getpixel((x, y))

            if (
                r >= LINE_BRIGHTNESS
                and
                g >= LINE_BRIGHTNESS
                and
                b >= LINE_BRIGHTNESS
            ):
                bright_pixels += 1

        if bright_pixels >= LINE_MIN_HEIGHT:
            candidates.append(x)

    if not candidates:
        return None

    # Group nearby pixels together
    groups = []

    current_group = [candidates[0]]

    for x in candidates[1:]:

        if x <= current_group[-1] + 2:
            current_group.append(x)
        else:
            groups.append(current_group)
            current_group = [x]

    groups.append(current_group)

    # Pick the strongest group
    best_group = max(groups, key=len)

    return int(sum(best_group) / len(best_group))


# ============================================================
# CENTER FALLBACK
# ============================================================

def center_fallback(line_x, last_fallback_click):
    """
    Used ONLY when the rectangle is undetectable.

    Behavior:

    LINE LEFT OF CENTER:
        Click toward center.

    LINE RIGHT OF CENTER:
        Do NOT click.

    LINE IN CENTER:
        Click ONE time every 0.20 seconds.

    LINE UNDETECTABLE:
        Do NOTHING.

    NEVER double-clicks.
    """

    if line_x is None:
        print("LINE HIDDEN - NO CLICK")
        return last_fallback_click

    distance = line_x - CENTER_X

    print(
        f"LINE FOUND: {line_x} "
        f"(distance from center: {distance:+d})"
    )

    # --------------------------------------------------------
    # LINE IS LEFT OF CENTER
    # --------------------------------------------------------

    if distance < -CENTER_TOLERANCE:

        native_click()

        print("LINE LEFT - CLICK")

        # Reset the center timer because this is a normal
        # movement correction, not a center hold.
        return time.monotonic()

    # --------------------------------------------------------
    # LINE IS RIGHT OF CENTER
    # --------------------------------------------------------

    if distance > CENTER_TOLERANCE:

        print("LINE RIGHT - NO CLICK")

        return last_fallback_click

    # --------------------------------------------------------
    # LINE IS IN THE CENTER
    # --------------------------------------------------------

    now = time.monotonic()

    if now - last_fallback_click >= CENTER_FALLBACK_CLICK_INTERVAL:

        native_click()

        print("LINE CENTER - CLICK")

        return now

    return last_fallback_click


# ============================================================
# WAIT FOR MINIGAME
# ============================================================

def wait_for_minigame():

    while running and not emergency_stop:

        pixel = get_pixel(
            MINIGAME_CHECK_X,
            MINIGAME_CHECK_Y
        )

        if is_white(pixel):
            return True

        time.sleep(0.01)

    return False


# ============================================================
# FISHING MINIGAME
# ============================================================

def run_fishing_minigame():

    print("Waiting for minigame...")

    if not wait_for_minigame():
        return False

    print("MINIGAME DETECTED")

    # Move to the fishing area before detection starts.
    # This is NOT moved around during the minigame.
    move_mouse_native(950, 880)

    time.sleep(0.05)

    # Sample the rectangle color
    bar_color = get_pixel(
        BAR_SAMPLE_X,
        BAR_SAMPLE_Y
    )

    print(f"BAR COLOR: {bar_color}")

    start_time = time.monotonic()

    # Used ONLY for fallback center clicking
    last_fallback_click = 0.0

    # Prevent jumping between wildly different fake line detections
    last_line_x = None

    while running and not emergency_stop:

        elapsed = time.monotonic() - start_time

        if elapsed > MINIGAME_TIMEOUT:
            print("MINIGAME TIMEOUT")
            break

        # ====================================================
        # FIRST: TRY RECTANGLE DETECTION
        # ====================================================

        bar = find_bar(bar_color)

        if bar is not None:

            left_x, right_x = bar
            bar_width = right_x - left_x
            bar_center = int((left_x + right_x) / 2)

            print(
                f"BAR FOUND: {left_x}-{right_x} "
                f"Width={bar_width} "
                f"Center={bar_center}"
            )

            # ------------------------------------------------
            # NORMAL RECTANGLE FOLLOWING
            #
            # IMPORTANT:
            # We DO NOT throttle this based on position.
            #
            # The 0.20-second center clicking is ONLY for
            # the fallback case when the rectangle is missing.
            # ------------------------------------------------

            if bar_width < ADVANCED_THRESHOLD:

                native_click()

                print("RECTANGLE CLICK")

            # Rectangle is visible, so fallback state is reset.
            last_line_x = None
            last_fallback_click = time.monotonic()

        else:

            # =================================================
            # RECTANGLE NOT DETECTED
            #
            # ONLY NOW do we use the player line fallback.
            # =================================================

            print("BAR HIDDEN - USING LINE FALLBACK")

            line_x = find_player_line()

            # -----------------------------------------------
            # No line either
            # -----------------------------------------------

            if line_x is None:

                print("LINE HIDDEN - NO CLICK")

                # IMPORTANT:
                # Do NOT use the old line position.
                # Do NOT rapid click.
                last_line_x = None

            else:

                # -------------------------------------------
                # Reject impossible huge jumps
                # -------------------------------------------

                if last_line_x is not None:

                    jump = abs(line_x - last_line_x)

                    if jump > 120:

                        print(
                            f"LINE REJECTED: {line_x} "
                            f"(jump={jump})"
                        )

                        line_x = None

                # -------------------------------------------
                # Valid line
                # -------------------------------------------

                if line_x is not None:

                    last_line_x = line_x

                    last_fallback_click = center_fallback(
                        line_x,
                        last_fallback_click
                    )

        # Small scan delay
        time.sleep(0.01)

    # ========================================================
    # CAUGHT FISH / CLOSE RESULT
    # ========================================================

    if not emergency_stop:

        time.sleep(0.30)

        move_mouse_native(
            RESULT_X,
            RESULT_Y
        )

        time.sleep(0.70)

        native_click()

        print("RESULT X CLICKED")

        time.sleep(0.30)

    return True


# ============================================================
# MAIN FISHING LOOP
# ============================================================

def fishing_loop():

    global cycle_count

    while not emergency_stop:

        if not running:
            time.sleep(0.1)
            continue

        cycle_count += 1

        print("\n==============================")
        print(f"FISHING CYCLE #{cycle_count}")
        print("==============================")

        # Move to Fish button
        move_mouse_native(
            FISH_BUTTON_X,
            FISH_BUTTON_Y
        )

        time.sleep(0.05)

        # Click Fish
        native_click()

        print("FISH BUTTON CLICKED")

        time.sleep(0.05)

        # Run minigame
        run_fishing_minigame()

        if emergency_stop:
            break

        time.sleep(0.10)


# ============================================================
# START
# ============================================================

print("")
print("====================================")
print("      SOL'S RNG FISHING MACRO")
print("====================================")
print("")
print("F8 = Start / Pause")
print("F3 = Emergency Stop")
print("")
print("Waiting for F8...")
print("")

try:
    fishing_loop()

except KeyboardInterrupt:
    emergency_stop = True
    running = False
    print("\nStopped.")

except Exception as e:
    emergency_stop = True
    running = False

    print("\n==============================")
    print("ERROR:")
    print(e)
    print("==============================")
