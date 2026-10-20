import time
import threading
import ctypes
import pyautogui
import keyboard


# ============================================================
# SETTINGS
# ============================================================

FISH_X = 853
FISH_Y = 832

RESULT_X = 1113
RESULT_Y = 342

CENTER_X = 959
CENTER_TOLERANCE = 8

BAR_LEFT = 757
BAR_RIGHT = 1161
BAR_Y = 767

MAX_BAR_WIDTH = 25

LINE_BRIGHTNESS = 215
LINE_MIN_HEIGHT = 5

IGNORE_LINE_LEFT = 765
IGNORE_LINE_RIGHT = 800

FAKE_LINE_LEFT = 1100
FAKE_LINE_RIGHT = 1161

CENTER_CLICK_INTERVAL = 0.20
FALLBACK_CLICK_INTERVAL = 0.20

MINIGAME_WAIT_TIMEOUT = 15.0
MINIGAME_TIMEOUT = 30.0

BAR_HIDDEN_GRACE = 0.08

# How long BOTH the bar and player line must stay gone
# before we assume the minigame has finished.
FINISH_HIDDEN_TIME = 1.0

AFTER_FISH_DELAY = 0.50


# ============================================================
# WINDOWS MOUSE
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

    running = not running

    if running:
        print("\n[STATUS] RUNNING")
    else:
        print("\n[STATUS] PAUSED")


def emergency_stop():
    global running
    global stop_requested

    stop_requested = True
    running = False

    print("\n[EMERGENCY STOP]")


# ============================================================
# BAR COLOR
# ============================================================

def looks_like_bar_color(color):
    if color is None:
        return False

    r, g, b = color

    return (
        r >= 70 and
        g >= 35 and
        b >= 70 and
        r > g + 20 and
        b > g + 20
    )


def get_bar_color(timeout=5.0):
    start = time.time()

    while time.time() - start < timeout:

        if not running:
            return None

        color = pyautogui.pixel(955, BAR_Y)

        if looks_like_bar_color(color):
            return color

        time.sleep(0.03)

    return None


# ============================================================
# BAR DETECTION
# ============================================================

def color_matches(c1, c2, tolerance=10):
    return (
        abs(c1[0] - c2[0]) <= tolerance and
        abs(c1[1] - c2[1]) <= tolerance and
        abs(c1[2] - c2[2]) <= tolerance
    )


def find_rectangle(bar_color):

    left_x = None
    right_x = None

    for x in range(BAR_LEFT, BAR_RIGHT + 1):

        color = pyautogui.pixel(x, BAR_Y)

        if color_matches(color, bar_color, 5):
            left_x = x
            break

    if left_x is None:
        return None

    right_x = left_x

    for x in range(left_x + 1, BAR_RIGHT + 1):

        color = pyautogui.pixel(x, BAR_Y)

        if color_matches(color, bar_color, 10):
            right_x = x
        else:
            break

    width = right_x - left_x
    center = (left_x + right_x) // 2

    return left_x, right_x, width, center


# ============================================================
# PLAYER LINE DETECTION
# ============================================================

def find_player_line():

    screenshot = pyautogui.screenshot()

    for x in range(BAR_LEFT, BAR_RIGHT + 1):

        if IGNORE_LINE_LEFT <= x <= IGNORE_LINE_RIGHT:
            continue

        if FAKE_LINE_LEFT <= x <= FAKE_LINE_RIGHT:
            continue

        bright_pixels = 0

        for y in range(BAR_Y - 10, BAR_Y + 11):

            r, g, b = screenshot.getpixel((x, y))

            if (
                r >= LINE_BRIGHTNESS and
                g >= LINE_BRIGHTNESS and
                b >= LINE_BRIGHTNESS
            ):
                bright_pixels += 1

        if bright_pixels >= LINE_MIN_HEIGHT:
            return x

    return None


# ============================================================
# LINE FALLBACK
# ============================================================

def line_fallback(last_fallback_click):

    line_x = find_player_line()

    if line_x is None:
        print("LINE HIDDEN -> NO CLICK")
        return last_fallback_click, False

    distance = line_x - CENTER_X

    print(f"LINE FOUND: {line_x} (distance {distance})")

    # LEFT OF CENTER
    if distance < -CENTER_TOLERANCE:

        if time.time() - last_fallback_click >= FALLBACK_CLICK_INTERVAL:
            print("LINE LEFT -> CLICK")
            click_native()
            last_fallback_click = time.time()
        else:
            print("LINE LEFT -> WAIT")

        return last_fallback_click, False

    # RIGHT OF CENTER
    if distance > CENTER_TOLERANCE:
        print("LINE RIGHT -> NO CLICK")
        return last_fallback_click, False

    # CENTER
    if time.time() - last_fallback_click >= CENTER_CLICK_INTERVAL:

        print(
            f"LINE CENTER: {line_x} "
            f"(distance {distance}) -> CLICK"
        )

        click_native()
        last_fallback_click = time.time()

    else:
        print("LINE CENTER -> WAIT")

    return last_fallback_click, False


# ============================================================
# WAIT FOR MINIGAME
# ============================================================

def wait_for_minigame():

    print("WAITING FOR MINIGAME...")

    start = time.time()

    while running and not stop_requested:

        # White indicator used by the original macro
        color = pyautogui.pixel(1176, 836)

        r, g, b = color

        if r >= 230 and g >= 230 and b >= 230:

            print("MINIGAME DETECTED")

            # Original macro moves here before sampling bar color.
            move_mouse_native(950, 880)

            time.sleep(0.05)

            return True

        if time.time() - start >= MINIGAME_WAIT_TIMEOUT:
            print("MINIGAME NOT FOUND")
            return False

        time.sleep(0.03)

    return False


# ============================================================
# FISHING MINIGAME
# ============================================================

def run_fishing_minigame():

    print("WAITING FOR BAR COLOR...")

    bar_color = get_bar_color()

    if bar_color is None:
        print("BAR COLOR NOT FOUND")
        return False

    print(f"BAR COLOR FOUND: {bar_color}")

    rectangle_center_clicked = False

    last_fallback_click = 0.0

    bar_hidden_since = None

    start_time = time.time()

    while running and not stop_requested:

        # ----------------------------------------------------
        # SAFETY TIMEOUT
        # ----------------------------------------------------

        if time.time() - start_time >= MINIGAME_TIMEOUT:
            print("MINIGAME TIMEOUT")
            return False

        # ----------------------------------------------------
        # FIND RECTANGLE
        # ----------------------------------------------------

        rectangle = find_rectangle(bar_color)

        if rectangle is not None:

            bar_hidden_since = None

            left_x, right_x, width, center = rectangle

            print(
                f"BAR FOUND: {left_x}-{right_x} "
                f"Width={width} Center={center}"
            )

            # ------------------------------------------------
            # RECTANGLE IS CENTERED
            # ------------------------------------------------

            if (
                left_x <= CENTER_X <= right_x
            ):

                if not rectangle_center_clicked:

                    print("RECTANGLE CENTER -> CLICK ONCE")

                    click_native()

                    rectangle_center_clicked = True

                else:

                    print(
                        "RECTANGLE CENTER -> "
                        "HOLD NO CLICK"
                    )

            # ------------------------------------------------
            # RECTANGLE MOVED AWAY
            # ------------------------------------------------

            else:

                rectangle_center_clicked = False

                if width < MAX_BAR_WIDTH:

                    print(
                        "RECTANGLE NOT CENTER "
                        "-> NORMAL CLICK"
                    )

                    click_native()

                else:

                    print(
                        "RECTANGLE TOO WIDE "
                        "-> NO CLICK"
                    )

            time.sleep(0.01)
            continue

        # ====================================================
        # RECTANGLE HIDDEN
        # ====================================================

        print("BAR HIDDEN -> LINE FALLBACK")

        # Start tracking how long the bar has been gone.
        if bar_hidden_since is None:
            bar_hidden_since = time.time()

        line_x = find_player_line()

        # ----------------------------------------------------
        # LINE EXISTS
        # ----------------------------------------------------

        if line_x is not None:

            bar_hidden_since = time.time()

            distance = line_x - CENTER_X

            print(
                f"LINE FOUND: {line_x} "
                f"(distance {distance})"
            )

            # LEFT
            if distance < -CENTER_TOLERANCE:

                if (
                    time.time() - last_fallback_click
                    >= FALLBACK_CLICK_INTERVAL
                ):

                    print("LINE LEFT -> CLICK")

                    click_native()

                    last_fallback_click = time.time()

                else:

                    print("LINE LEFT -> WAIT")

            # RIGHT
            elif distance > CENTER_TOLERANCE:

                print("LINE RIGHT -> NO CLICK")

            # CENTER
            else:

                if (
                    time.time() - last_fallback_click
                    >= CENTER_CLICK_INTERVAL
                ):

                    print(
                        f"LINE CENTER: {line_x} "
                        f"(distance {distance}) -> CLICK"
                    )

                    click_native()

                    last_fallback_click = time.time()

                else:

                    print("LINE CENTER -> WAIT")

        # ----------------------------------------------------
        # NOTHING FOUND
        # ----------------------------------------------------

        else:

            print("LINE HIDDEN -> NO CLICK")

            # If both the rectangle and player line have
            # disappeared for long enough, the minigame
            # has almost certainly ended.
            if (
                time.time() - bar_hidden_since
                >= FINISH_HIDDEN_TIME
            ):

                print(
                    "BAR + LINE HIDDEN -> "
                    "MINIGAME FINISHED"
                )

                return True

        time.sleep(0.03)

    return False


# ============================================================
# FISHING LOOP
# ============================================================

def fishing_loop():

    global running

    cycle = 0

    while running and not stop_requested:

        cycle += 1

        print(f"\n========== CYCLE {cycle} ==========")

        # ----------------------------------------------------
        # CLICK FISH BUTTON
        # ----------------------------------------------------

        move_mouse_native(FISH_X, FISH_Y)

        time.sleep(0.05)

        click_native()

        print("FISH BUTTON CLICKED")

        time.sleep(0.10)

        # ----------------------------------------------------
        # WAIT FOR MINIGAME
        # ----------------------------------------------------

        if not wait_for_minigame():

            print("MINIGAME DID NOT START.")
            print("MACRO PAUSED.")

            running = False
            break

        # ----------------------------------------------------
        # RUN MINIGAME
        # ----------------------------------------------------

        finished = run_fishing_minigame()

        if not finished:

            print("MINIGAME DID NOT FINISH.")
            print("MACRO PAUSED.")

            running = False
            break

        # ----------------------------------------------------
        # FISH CAUGHT
        # ----------------------------------------------------

        print("FISH CAUGHT")

        time.sleep(AFTER_FISH_DELAY)

        # Click the X to close the caught-fish result.
        move_mouse_native(RESULT_X, RESULT_Y)

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

keyboard.add_hotkey("f8", toggle_macro)
keyboard.add_hotkey("f3", emergency_stop)

while not stop_requested:

    if running:

        fishing_loop()

    time.sleep(0.05)

print("\nMACRO CLOSED.")
