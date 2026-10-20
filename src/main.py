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

# Ignore the fake line that sometimes appears behind the timer
IGNORE_LINE_LEFT = 765
IGNORE_LINE_RIGHT = 800

# Only used when the rectangle is NOT detected
CENTER_FALLBACK_CLICK_INTERVAL = 0.20

MINIGAME_TIMEOUT = 9.0


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

        # Small relative movements so Roblox recognizes the mouse
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
    if not running or emergency_stop:
        return

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
        print("\n[F8] MACRO STARTED")
    else:
        print("\n[F8] MACRO PAUSED")


def emergency_stop_macro():
    global running, emergency_stop

    emergency_stop = True
    running = False

    print("\n[F3] EMERGENCY STOP")


keyboard.add_hotkey("f8", toggle_macro)
keyboard.add_hotkey("f3", emergency_stop_macro)


# =========================
# COLOR FUNCTIONS
# =========================

def get_pixel(x, y):
    image = pyautogui.screenshot(region=(x, y, 1, 1))
    return image.getpixel((0, 0))


def is_white(color):
    r, g, b = color
    return r >= 240 and g >= 240 and b >= 240


def color_matches(color1, color2, tolerance):
    r1, g1, b1 = color1
    r2, g2, b2 = color2

    return (
        abs(r1 - r2) <= tolerance and
        abs(g1 - g2) <= tolerance and
        abs(b1 - b2) <= tolerance
    )


# =========================
# FIND FISHING RECTANGLE
# =========================

def find_bar(bar_color):
    screenshot = pyautogui.screenshot()

    left_x = None

    for x in range(BAR_LEFT, BAR_RIGHT + 1):
        color = screenshot.getpixel((x, BAR_Y))

        if color_matches(color, bar_color, BAR_COLOR_TOLERANCE):
            left_x = x
            break

    if left_x is None:
        return None

    right_x = left_x

    while right_x < BAR_RIGHT:
        test_x = right_x + 1
        test_color = screenshot.getpixel((test_x, BAR_Y))

        if color_matches(
            test_color,
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

        # Ignore false detection behind timer
        if IGNORE_LINE_LEFT <= x <= IGNORE_LINE_RIGHT:
            continue

        bright_count = 0

        for y in range(750, 785):

            r, g, b = screenshot.getpixel((x, y))

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

    # Group nearby pixels
    groups = []
    current_group = [candidates[0]]

    for x in candidates[1:]:

        if x - current_group[-1] <= 2:
            current_group.append(x)
        else:
            groups.append(current_group)
            current_group = [x]

    groups.append(current_group)

    # Strongest group
    strongest = max(groups, key=len)

    return int((strongest[0] + strongest[-1]) / 2)


# =========================
# CENTER FALLBACK
# =========================

def center_fallback(line_x, last_fallback_click):
    if line_x is None:
        return last_fallback_click

    distance = line_x - CENTER_X

    # Line is too far LEFT
    if distance < -CENTER_TOLERANCE:
        native_click()
        print(
            f"LINE FOUND: {line_x} "
            f"(distance {distance}) -> LINE LEFT - CLICK"
        )

        return time.monotonic()

    # Line is too far RIGHT
    if distance > CENTER_TOLERANCE:
        print(
            f"LINE FOUND: {line_x} "
            f"(distance +{distance}) -> LINE RIGHT - STOP"
        )

        return last_fallback_click

    # Line is CENTERED
    now = time.monotonic()

    if now - last_fallback_click >= CENTER_FALLBACK_CLICK_INTERVAL:
        native_click()

        print(
            f"LINE FOUND: {line_x} "
            f"(distance {distance}) -> "
            f"LINE CENTER - CLICK"
        )

        return now

    return last_fallback_click


# =========================
# WAIT FOR MINIGAME
# =========================

def wait_for_minigame():
    start_time = time.monotonic()

    while running and not emergency_stop:

        color = get_pixel(
            MINIGAME_CHECK_X,
            MINIGAME_CHECK_Y
        )

        if is_white(color):
            return True

        if time.monotonic() - start_time > 5:
            return False

        time.sleep(0.02)

    return False


# =========================
# FISHING MINIGAME
# =========================

def run_fishing_minigame():

    global running

    print("Waiting for minigame...")

    if not wait_for_minigame():
        print("Minigame not detected.")
        return

    print("MINIGAME DETECTED")

    # Move mouse into fishing area
    move_mouse_native(950, 880)

    time.sleep(0.05)

    # Sample rectangle color
    bar_color = get_pixel(
        BAR_SAMPLE_X,
        BAR_SAMPLE_Y
    )

    print(f"Sampled bar color: {bar_color}")

    start_time = time.monotonic()

    last_fallback_click = 0.0

    # Prevents repeated clicking while rectangle stays centered
    rectangle_center_clicked = False

    while running and not emergency_stop:

        # Timeout
        if time.monotonic() - start_time > MINIGAME_TIMEOUT:
            print("Minigame timeout.")
            break

        # =========================
        # TRY RECTANGLE FIRST
        # =========================

        bar = find_bar(bar_color)

        if bar is not None:

            left_x, right_x = bar

            width = right_x - left_x
            bar_center = int((left_x + right_x) / 2)

            print(
                f"BAR FOUND: {left_x}-{right_x} "
                f"Width={width} Center={bar_center}"
            )

            # Rectangle is wide enough
            if width >= ADVANCED_THRESHOLD:

                rectangle_center_clicked = False

                print("RECTANGLE WIDE - NO CLICK")

            else:

                # =========================
                # RECTANGLE IS AT CENTER
                # =========================

                if left_x <= CENTER_X <= right_x:

                    if not rectangle_center_clicked:

                        native_click()

                        rectangle_center_clicked = True

                        print(
                            "RECTANGLE CENTER - "
                            "CLICK ONCE"
                        )

                    else:

                        print(
                            "RECTANGLE CENTER - "
                            "HOLD NO CLICK"
                        )

                # =========================
                # RECTANGLE IS NOT CENTER
                # =========================

                else:

                    rectangle_center_clicked = False

                    native_click()

                    print(
                        "RECTANGLE NOT CENTER - CLICK"
                    )

            # Rectangle is detected,
            # so fallback line detection is ignored.
            last_fallback_click = time.monotonic()

            time.sleep(0.01)
            continue

        # =========================
        # RECTANGLE NOT DETECTED
        # =========================

        rectangle_center_clicked = False

        line_x = find_player_line()

        if line_x is None:

            print("LINE HIDDEN - NO CLICK")

            time.sleep(0.01)
            continue

        # =========================
        # LINE FALLBACK
        # =========================

        last_fallback_click = center_fallback(
            line_x,
            last_fallback_click
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

        print("Fish result clicked.")


# =========================
# FISHING LOOP
# =========================

def fishing_loop():

    global cycle_count

    while running and not emergency_stop:

        cycle_count += 1

        print(
            f"\n========== CYCLE {cycle_count} =========="
        )

        # Move to Fish button
        move_mouse_native(
            FISH_BUTTON_X,
            FISH_BUTTON_Y
        )

        time.sleep(0.05)

        # Click Fish
        native_click()

        print("Fish button clicked.")

        time.sleep(0.05)

        # Run minigame
        run_fishing_minigame()

        time.sleep(0.10)


# =========================
# MAIN
# =========================

print("===================================")
print("   SOL'S RNG FISHING MACRO")
print("===================================")
print("F8 = Start / Pause")
print("F3 = Emergency Stop")
print()
print("Waiting for F8...")


try:

    while not emergency_stop:

        if running:
            fishing_loop()

        time.sleep(0.05)

except KeyboardInterrupt:

    print("\nProgram stopped.")

except Exception as e:

    print(f"\nERROR: {e}")

finally:

    running = False

    print("Macro closed.")
