import time
import ctypes
import ctypes.wintypes
import keyboard
import pyautogui


# =========================
# SETTINGS
# =========================

FISH_BUTTON_X = 853
FISH_BUTTON_Y = 832

RESULT_X = 1113
RESULT_Y = 342

MINIGAME_CHECK_X = 1176
MINIGAME_CHECK_Y = 836

BAR_SAMPLE_X = 955
BAR_SAMPLE_Y = 767

BAR_LEFT = 757
BAR_RIGHT = 1161
BAR_Y = 767

BAR_COLOR_TOLERANCE = 5
BAR_EDGE_TOLERANCE = 10
ADVANCED_THRESHOLD = 25

CENTER_X = 959
CENTER_TOLERANCE = 12

LINE_BRIGHTNESS = 215
LINE_MIN_HEIGHT = 5

IGNORE_LINE_LEFT = 765
IGNORE_LINE_RIGHT = 800

CENTER_FALLBACK_CLICK_INTERVAL = 0.20

MINIGAME_WAIT_TIMEOUT = 15.0
MINIGAME_TIMEOUT = 12.0


# =========================
# WINDOWS MOUSE
# =========================

user32 = ctypes.windll.user32

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004


def get_mouse_position():
    point = ctypes.wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(point))
    return point.x, point.y


def move_mouse_native(target_x, target_y):
    while running and not emergency_stop:
        current_x, current_y = get_mouse_position()

        dx = target_x - current_x
        dy = target_y - current_y

        if abs(dx) <= 1 and abs(dy) <= 1:
            break

        move_x = max(-3, min(3, dx))
        move_y = max(-3, min(3, dy))

        user32.mouse_event(
            MOUSEEVENTF_MOVE,
            move_x,
            move_y,
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


# =========================
# GLOBAL STATE
# =========================

running = False
emergency_stop = False
cycle_count = 0


# =========================
# HOTKEYS
# =========================

def toggle_macro():
    global running

    if emergency_stop:
        return

    running = not running

    if running:
        print("\n[STATUS] RUNNING")
    else:
        print("\n[STATUS] PAUSED")


def emergency_stop_macro():
    global running
    global emergency_stop

    emergency_stop = True
    running = False

    print("\n[EMERGENCY STOP]")


keyboard.add_hotkey("f8", toggle_macro)
keyboard.add_hotkey("f3", emergency_stop_macro)


# =========================
# COLOR FUNCTIONS
# =========================

def get_pixel(x, y):
    screenshot = pyautogui.screenshot()
    return screenshot.getpixel((x, y))


def is_white(color):
    r, g, b = color

    return (
        r >= 240 and
        g >= 240 and
        b >= 240
    )


def color_matches(color, target, tolerance):
    r1, g1, b1 = color
    r2, g2, b2 = target

    return (
        abs(r1 - r2) <= tolerance and
        abs(g1 - g2) <= tolerance and
        abs(b1 - b2) <= tolerance
    )


# =========================
# FIND RECTANGLE
# =========================

def find_bar(bar_color):
    screenshot = pyautogui.screenshot()

    left_x = None

    for x in range(BAR_LEFT, BAR_RIGHT + 1):
        color = screenshot.getpixel(
            (x, BAR_Y)
        )

        if color_matches(
            color,
            bar_color,
            BAR_COLOR_TOLERANCE
        ):
            left_x = x
            break

    if left_x is None:
        return None

    right_x = left_x

    while right_x < BAR_RIGHT:
        test_x = right_x + 1

        color = screenshot.getpixel(
            (test_x, BAR_Y)
        )

        if color_matches(
            color,
            bar_color,
            BAR_EDGE_TOLERANCE
        ):
            right_x = test_x
        else:
            break

    return left_x, right_x


# =========================
# FIND PLAYER LINE
# =========================

def find_player_line():
    screenshot = pyautogui.screenshot()

    candidates = []

    for x in range(BAR_LEFT, BAR_RIGHT + 1):

        if IGNORE_LINE_LEFT <= x <= IGNORE_LINE_RIGHT:
            continue

        bright_count = 0

        for y in range(750, 785):
            r, g, b = screenshot.getpixel(
                (x, y)
            )

            if (
                r >= LINE_BRIGHTNESS and
                g >= LINE_BRIGHTNESS and
                b >= LINE_BRIGHTNESS
            ):
                bright_count += 1

        if bright_count >= LINE_MIN_HEIGHT:
            candidates.append(x)

    if not candidates:
        return None

    groups = []
    current_group = [candidates[0]]

    for x in candidates[1:]:
        if x <= current_group[-1] + 2:
            current_group.append(x)
        else:
            groups.append(current_group)
            current_group = [x]

    groups.append(current_group)

    strongest = max(
        groups,
        key=len
    )

    return (
        strongest[0] +
        strongest[-1]
    ) // 2


# =========================
# FALLBACK LINE CONTROL
# =========================

def center_fallback(line_x, last_click):

    if line_x is None:
        return last_click

    distance = line_x - CENTER_X

    # LEFT
    if distance < -CENTER_TOLERANCE:
        native_click()

        print(
            f"LINE LEFT: {line_x} "
            f"(distance {distance}) -> CLICK"
        )

        return time.monotonic()

    # RIGHT
    if distance > CENTER_TOLERANCE:
        print(
            f"LINE RIGHT: {line_x} "
            f"(distance +{distance}) -> NO CLICK"
        )

        return last_click

    # CENTER
    now = time.monotonic()

    if now - last_click >= CENTER_FALLBACK_CLICK_INTERVAL:
        native_click()

        print(
            f"LINE CENTER: {line_x} "
            f"(distance {distance}) -> CLICK"
        )

        return now

    return last_click


# =========================
# WAIT FOR MINIGAME
# =========================

def wait_for_minigame():

    print("WAITING FOR MINIGAME...")

    start = time.monotonic()

    while running and not emergency_stop:

        color = get_pixel(
            MINIGAME_CHECK_X,
            MINIGAME_CHECK_Y
        )

        if is_white(color):
            print("MINIGAME DETECTED")
            return True

        if time.monotonic() - start >= MINIGAME_WAIT_TIMEOUT:
            print("MINIGAME WAIT TIMEOUT")
            return False

        time.sleep(0.05)

    return False


# =========================
# FISHING MINIGAME
# =========================

def run_fishing_minigame():

    if not wait_for_minigame():
        return False

    # Move to bar once
    move_mouse_native(
        950,
        880
    )

    time.sleep(0.05)

    bar_color = get_pixel(
        BAR_SAMPLE_X,
        BAR_SAMPLE_Y
    )

    print(
        f"BAR COLOR: {bar_color}"
    )

    start = time.monotonic()

    last_fallback_click = 0.0

    # Prevents repeated clicks while
    # the rectangle remains centered.
    rectangle_center_clicked = False

    while running and not emergency_stop:

        if time.monotonic() - start >= MINIGAME_TIMEOUT:
            print("MINIGAME TIMEOUT")
            break

        bar = find_bar(bar_color)

        # =========================
        # RECTANGLE DETECTED
        # =========================

        if bar is not None:

            left_x, right_x = bar

            width = right_x - left_x

            center = (
                left_x + right_x
            ) // 2

            print(
                f"BAR FOUND: "
                f"{left_x}-{right_x} "
                f"Width={width} "
                f"Center={center}"
            )

            if width < ADVANCED_THRESHOLD:

                # Rectangle is touching
                # the center position.
                if left_x <= CENTER_X <= right_x:

                    if not rectangle_center_clicked:

                        native_click()

                        print(
                            "RECTANGLE CENTER "
                            "-> CLICK ONCE"
                        )

                        rectangle_center_clicked = True

                    else:

                        print(
                            "RECTANGLE CENTER "
                            "-> NO CLICK"
                        )

                else:

                    # Rectangle moved away,
                    # so allow another center click
                    # the next time it reaches center.
                    rectangle_center_clicked = False

                    native_click()

                    print(
                        "RECTANGLE NOT CENTER "
                        "-> NORMAL CLICK"
                    )

            else:

                rectangle_center_clicked = False

                # Do nothing when the rectangle
                # is too wide.
                print(
                    "RECTANGLE TOO WIDE "
                    "-> NO CLICK"
                )

        # =========================
        # RECTANGLE HIDDEN
        # =========================

        else:

            print(
                "BAR HIDDEN -> LINE FALLBACK"
            )

            line_x = find_player_line()

            if line_x is None:

                print(
                    "LINE HIDDEN -> NO CLICK"
                )

            else:

                print(
                    f"LINE FOUND: {line_x}"
                )

                last_fallback_click = (
                    center_fallback(
                        line_x,
                        last_fallback_click
                    )
                )

        time.sleep(0.01)

    # =========================
    # FISH RESULT
    # =========================

    if running and not emergency_stop:

        time.sleep(0.30)

        move_mouse_native(
            RESULT_X,
            RESULT_Y
        )

        time.sleep(0.70)

        native_click()

        time.sleep(0.30)

    return True


# =========================
# MAIN LOOP
# =========================

def fishing_loop():

    global cycle_count
    global running

    while not emergency_stop:

        if not running:
            time.sleep(0.1)
            continue

        cycle_count += 1

        print(
            f"\n========== CYCLE "
            f"{cycle_count} =========="
        )

        # Go to Fish button
        move_mouse_native(
            FISH_BUTTON_X,
            FISH_BUTTON_Y
        )

        time.sleep(0.05)

        # Click Fish ONCE
        native_click()

        print(
            "FISH BUTTON CLICKED"
        )

        # Give Roblox time to react
        time.sleep(0.50)

        # Wait for minigame
        success = run_fishing_minigame()

        if not success:

            print(
                "MINIGAME DID NOT START."
            )

            print(
                "MACRO PAUSED."
            )

            running = False

            continue

        time.sleep(0.20)


# =========================
# START
# =========================

print("================================")
print(" SOL'S RNG FISHING MACRO")
print("================================")
print("F8 = Start / Pause")
print("F3 = Emergency Stop")
print("================================")


try:

    fishing_loop()

except KeyboardInterrupt:

    running = False
    print("\nMacro stopped.")

except Exception as e:

    running = False
    print(f"\nERROR: {e}")
