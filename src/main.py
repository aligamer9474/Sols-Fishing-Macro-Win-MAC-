import time
import ctypes
import ctypes.wintypes
import pyautogui
import keyboard


# ============================================================
# SETTINGS
# ============================================================

FISH_BUTTON_X = 853
FISH_BUTTON_Y = 832

RESULT_X = 1113
RESULT_Y = 342

MINIGAME_CHECK_X = 1176
MINIGAME_CHECK_Y = 836

BAR_Y = 767
BAR_LEFT = 757
BAR_RIGHT = 1161

CENTER_X = (BAR_LEFT + BAR_RIGHT) // 2

BAR_SAMPLE_X = 955
BAR_SAMPLE_Y = 767

MINIGAME_WAIT_TIMEOUT = 30.0
MINIGAME_TIMEOUT = 15.0

FINISH_HIDDEN_TIME = 1.0

CENTER_CLICK_DELAY = 0.20
FALLBACK_CLICK_DELAY = 0.20

ADVANCED_THRESHOLD = 25

# Ignore fake line detections around these areas
IGNORE_LINE_LEFT = 765
IGNORE_LINE_RIGHT = 800

IGNORE_LINE_RIGHT_START = 1100
IGNORE_LINE_RIGHT_END = 1161


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


def move_mouse_native(target_x, target_y):
    """
    Moves using relative mouse_event movement.
    This is the method that Roblox actually recognized.
    """

    while True:
        current_x, current_y = get_mouse_position()

        dx = target_x - current_x
        dy = target_y - current_y

        if abs(dx) <= 1 and abs(dy) <= 1:
            break

        if dx > 3:
            move_x = 3
        elif dx < -3:
            move_x = -3
        else:
            move_x = dx

        if dy > 3:
            move_y = 3
        elif dy < -3:
            move_y = -3
        else:
            move_y = dy

        user32.mouse_event(
            MOUSEEVENTF_MOVE,
            move_x,
            move_y,
            0,
            0
        )

        time.sleep(0.004)


def click_native():
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
stop_requested = False


# ============================================================
# HOTKEYS
# ============================================================

def toggle_macro():
    global running

    if stop_requested:
        return

    running = not running

    if running:
        print("\n[STATUS] RUNNING")
    else:
        print("\n[STATUS] PAUSED")


def emergency_stop():
    global running, stop_requested

    running = False
    stop_requested = True

    print("\n[EMERGENCY STOP]")


keyboard.add_hotkey("f8", toggle_macro)
keyboard.add_hotkey("f3", emergency_stop)


# ============================================================
# COLOR FUNCTIONS
# ============================================================

def get_pixel(x, y):
    try:
        return pyautogui.pixel(x, y)
    except Exception:
        return None


def color_matches(color1, color2, tolerance=10):
    if color1 is None or color2 is None:
        return False

    return (
        abs(color1[0] - color2[0]) <= tolerance
        and
        abs(color1[1] - color2[1]) <= tolerance
        and
        abs(color1[2] - color2[2]) <= tolerance
    )


# ============================================================
# BAR COLOR
# ============================================================

def get_bar_color():
    """
    IMPORTANT:
    We do NOT wait for a special purple color anymore.

    The old working behavior samples the bar immediately
    after the minigame starts.
    """

    color = get_pixel(BAR_SAMPLE_X, BAR_SAMPLE_Y)

    if color is not None:
        print(
            f"BAR COLOR: "
            f"({color[0]}, {color[1]}, {color[2]})"
        )

        return color

    return None


# ============================================================
# RECTANGLE DETECTION
# ============================================================

def find_rectangle(bar_color):
    if bar_color is None:
        return None

    left_x = None
    right_x = None

    # Find left edge
    for x in range(BAR_LEFT, BAR_RIGHT + 1):

        color = get_pixel(x, BAR_Y)

        if color_matches(color, bar_color, 5):
            left_x = x
            break

    if left_x is None:
        return None

    # Find right edge
    right_x = left_x

    for x in range(left_x + 1, BAR_RIGHT + 1):

        color = get_pixel(x, BAR_Y)

        if color_matches(color, bar_color, 10):
            right_x = x
        else:
            break

    width = right_x - left_x

    return left_x, right_x, width


# ============================================================
# PLAYER LINE DETECTION
# ============================================================

def find_player_line():
    """
    Looks for the player's vertical line.

    The fake detections near the extreme left/right
    sides are ignored.
    """

    for x in range(BAR_LEFT, BAR_RIGHT + 1):

        if IGNORE_LINE_LEFT <= x <= IGNORE_LINE_RIGHT:
            continue

        if IGNORE_LINE_RIGHT_START <= x <= IGNORE_LINE_RIGHT_END:
            continue

        # Look at a few pixels vertically around the bar
        for y in range(BAR_Y - 5, BAR_Y + 6):

            color = get_pixel(x, y)

            if color is None:
                continue

            r, g, b = color

            # Player line is generally bright/white
            if r >= 210 and g >= 210 and b >= 210:
                return x

    return None


# ============================================================
# MINIGAME START DETECTION
# ============================================================

def wait_for_minigame():
    print("WAITING FOR MINIGAME...")

    start_time = time.time()

    while running and not stop_requested:

        color = get_pixel(
            MINIGAME_CHECK_X,
            MINIGAME_CHECK_Y
        )

        if color is not None:

            r, g, b = color

            if r >= 230 and g >= 230 and b >= 230:

                print("MINIGAME DETECTED")

                # Put cursor where the old macro expected it.
                move_mouse_native(950, 880)

                time.sleep(0.05)

                return True

        if time.time() - start_time >= MINIGAME_WAIT_TIMEOUT:

            print(
                f"MINIGAME NOT FOUND AFTER "
                f"{MINIGAME_WAIT_TIMEOUT:.0f} SECONDS"
            )

            return False

        time.sleep(0.05)

    return False


# ============================================================
# FISHING MINIGAME
# ============================================================

def run_fishing_minigame():

    print("GETTING BAR COLOR...")

    # Immediately sample the bar.
    bar_color = get_bar_color()

    if bar_color is None:
        print("COULD NOT GET BAR COLOR")
        return False

    print("BAR COLOR READY")

    start_time = time.time()

    bar_hidden_since = None

    rectangle_center_clicked = False

    last_fallback_click = 0

    while running and not stop_requested:

        # ----------------------------------------------------
        # TIMEOUT
        # ----------------------------------------------------

        if time.time() - start_time >= MINIGAME_TIMEOUT:

            print("MINIGAME TIMEOUT")

            return False

        # ----------------------------------------------------
        # FIND RECTANGLE
        # ----------------------------------------------------

        rectangle = find_rectangle(bar_color)

        if rectangle is not None:

            left_x, right_x, width = rectangle

            # Rectangle exists, so it is NOT hidden.
            bar_hidden_since = None

            # -----------------------------------------------
            # RECTANGLE IS CENTERED
            # -----------------------------------------------

            if left_x <= CENTER_X <= right_x:

                if not rectangle_center_clicked:

                    click_native()

                    print(
                        f"RECTANGLE CENTERED "
                        f"({left_x}-{right_x}) -> CLICK"
                    )

                    rectangle_center_clicked = True

                # IMPORTANT:
                # Do NOT keep clicking while centered.

                time.sleep(0.01)

                continue

            # -----------------------------------------------
            # RECTANGLE MOVED AWAY FROM CENTER
            # -----------------------------------------------

            rectangle_center_clicked = False

            # -----------------------------------------------
            # NORMAL ADVANCED DETECTION
            # -----------------------------------------------

            if width < ADVANCED_THRESHOLD:

                click_native()

                print(
                    f"RECTANGLE WIDTH {width} "
                    f"-> CLICK"
                )

                time.sleep(0.025)

            # Wide rectangle:
            # do not click.

            time.sleep(0.01)

            continue

        # ====================================================
        # RECTANGLE NOT FOUND
        # ====================================================

        if bar_hidden_since is None:
            bar_hidden_since = time.time()

        # Find player line
        line_x = find_player_line()

        # ----------------------------------------------------
        # BOTH BAR AND LINE HIDDEN
        # ----------------------------------------------------

        if line_x is None:

            if (
                time.time() - bar_hidden_since
                >= FINISH_HIDDEN_TIME
            ):

                print(
                    "BAR + LINE HIDDEN "
                    "-> MINIGAME FINISHED"
                )

                return True

            time.sleep(0.01)

            continue

        # ----------------------------------------------------
        # LINE FOUND
        # ----------------------------------------------------

        # LINE IS FAR LEFT
        if line_x < CENTER_X - 15:

            now = time.time()

            if now - last_fallback_click >= FALLBACK_CLICK_DELAY:

                click_native()

                last_fallback_click = now

                print(
                    f"FALLBACK LINE LEFT "
                    f"x={line_x} -> CLICK"
                )

        # LINE IS FAR RIGHT
        elif line_x > CENTER_X + 15:

            # Do NOT click.
            pass

        # LINE IS IN THE CENTER
        else:

            now = time.time()

            if now - last_fallback_click >= CENTER_CLICK_DELAY:

                click_native()

                last_fallback_click = now

                print(
                    f"FALLBACK LINE CENTER "
                    f"x={line_x} -> CLICK"
                )

        time.sleep(0.01)

    return False


# ============================================================
# FISHING LOOP
# ============================================================

def fishing_loop():

    cycle = 0

    while running and not stop_requested:

        cycle += 1

        print()
        print(
            f"========== CYCLE {cycle} =========="
        )

        # ----------------------------------------------------
        # MOVE TO FISH BUTTON
        # ----------------------------------------------------

        move_mouse_native(
            FISH_BUTTON_X,
            FISH_BUTTON_Y
        )

        time.sleep(0.05)

        click_native()

        print("FISH BUTTON CLICKED")

        # ----------------------------------------------------
        # WAIT FOR MINIGAME
        # ----------------------------------------------------

        if not wait_for_minigame():

            if stop_requested:
                break

            print("MINIGAME DID NOT START.")
            running = False
            break

        # ----------------------------------------------------
        # RUN MINIGAME
        # ----------------------------------------------------

        caught = run_fishing_minigame()

        if stop_requested:
            break

        if not caught:

            print("MINIGAME FAILED.")
            running = False
            break

        # ----------------------------------------------------
        # FISH CAUGHT
        # ----------------------------------------------------

        print("FISH CAUGHT")

        time.sleep(0.50)

        # Move to result X
        move_mouse_native(
            RESULT_X,
            RESULT_Y
        )

        time.sleep(0.05)

        click_native()

        print("RESULT X CLICKED")

        time.sleep(0.30)


# ============================================================
# MAIN
# ============================================================

print("================================")
print(" SOL'S RNG FISHING MACRO")
print("================================")
print("F8 = Start / Pause")
print("F3 = Emergency Stop")
print("================================")

try:

    while not stop_requested:

        if running:
            fishing_loop()

        time.sleep(0.05)

except KeyboardInterrupt:

    print("\n[STOPPED]")

finally:

    running = False

    print("\nMACRO CLOSED")
