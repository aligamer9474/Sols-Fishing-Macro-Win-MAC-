import pyautogui
import keyboard
import time
import ctypes

# =========================
# SETTINGS
# =========================

FISH_X = 853
FISH_Y = 832

X_BUTTON_X = 1113
X_BUTTON_Y = 342

MINIGAME_CHECK_X = 1176
MINIGAME_CHECK_Y = 836

BAR_SCAN_LEFT = 757
BAR_SCAN_RIGHT = 1161
BAR_Y = 767

CENTER_X = 959
CENTER_TOLERANCE = 12

LINE_BRIGHTNESS = 215
LINE_MIN_HEIGHT = 5

IGNORE_LINE_LEFT = 765
IGNORE_LINE_RIGHT = 800

CENTER_FALLBACK_CLICK_INTERVAL = 0.20

MINIGAME_WAIT_TIMEOUT = 15.0
MINIGAME_TIMEOUT = 15.0

running = False
stop_requested = False

rectangle_center_clicked = False
last_fallback_click = 0


# =========================
# WINDOWS MOUSE
# =========================

user32 = ctypes.windll.user32

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004


def get_mouse_pos():
    point = ctypes.wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(point))
    return point.x, point.y


def move_mouse(x, y):
    while running:
        current_x, current_y = get_mouse_pos()

        dx = x - current_x
        dy = y - current_y

        if abs(dx) <= 1 and abs(dy) <= 1:
            break

        dx = max(-3, min(3, dx))
        dy = max(-3, min(3, dy))

        user32.mouse_event(
            MOUSEEVENTF_MOVE,
            dx,
            dy,
            0,
            0
        )

        time.sleep(0.004)


def click_mouse():
    if not running:
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
# PIXEL HELPERS
# =========================

def get_pixel(x, y):
    try:
        return pyautogui.pixel(x, y)
    except:
        return None


def is_white(pixel):
    if pixel is None:
        return False

    r, g, b = pixel
    return r >= 240 and g >= 240 and b >= 240


# =========================
# HOTKEYS
# =========================

def toggle_macro():
    global running

    running = not running

    if running:
        print("\nMACRO STARTED")
    else:
        print("\nMACRO PAUSED")


def emergency_stop():
    global running, stop_requested

    stop_requested = True
    running = False

    print("\nEMERGENCY STOP")


keyboard.add_hotkey("f8", toggle_macro)
keyboard.add_hotkey("f3", emergency_stop)


# =========================
# MINIGAME DETECTION
# =========================

def wait_for_minigame():
    print("WAITING FOR MINIGAME...")

    start = time.monotonic()

    while running:
        if time.monotonic() - start >= MINIGAME_WAIT_TIMEOUT:
            print("MINIGAME WAIT TIMEOUT")
            return False

        pixel = get_pixel(
            MINIGAME_CHECK_X,
            MINIGAME_CHECK_Y
        )

        if is_white(pixel):
            time.sleep(0.05)

            pixel2 = get_pixel(
                MINIGAME_CHECK_X,
                MINIGAME_CHECK_Y
            )

            if is_white(pixel2):
                print("MINIGAME DETECTED")
                return True

        time.sleep(0.05)

    return False


# =========================
# FIND FISHING BAR
# =========================

def find_bar(bar_color):
    screenshot = pyautogui.screenshot()

    closest_match = None
    closest_distance = 999999

    br, bg, bb = bar_color

    for x in range(BAR_SCAN_LEFT, BAR_SCAN_RIGHT + 1):
        r, g, b = screenshot.getpixel((x, BAR_Y))

        distance = (
            abs(r - br) +
            abs(g - bg) +
            abs(b - bb)
        )

        if distance <= 15:
            if distance < closest_distance:
                closest_distance = distance
                closest_match = x

    if closest_match is None:
        return None

    left_x = closest_match
    right_x = closest_match

    while right_x < BAR_SCAN_RIGHT:
        r, g, b = screenshot.getpixel((right_x + 1, BAR_Y))

        if (
            abs(r - br) <= 10
            and abs(g - bg) <= 10
            and abs(b - bb) <= 10
        ):
            right_x += 1
        else:
            break

    return left_x, right_x


# =========================
# LINE FALLBACK
# =========================

def find_line():
    screenshot = pyautogui.screenshot()

    for x in range(BAR_SCAN_LEFT, BAR_SCAN_RIGHT + 1):
        if IGNORE_LINE_LEFT <= x <= IGNORE_LINE_RIGHT:
            continue

        found = False

        for y in range(BAR_Y - LINE_MIN_HEIGHT, BAR_Y + LINE_MIN_HEIGHT + 1):
            r, g, b = screenshot.getpixel((x, y))

            if (
                r >= LINE_BRIGHTNESS
                and g >= LINE_BRIGHTNESS
                and b >= LINE_BRIGHTNESS
            ):
                found = True
                break

        if found:
            return x

    return None


# =========================
# FISHING MINIGAME
# =========================

def play_minigame():
    global rectangle_center_clicked
    global last_fallback_click

    print("STARTING MINIGAME")

    # Move to the fishing bar once.
    move_mouse(950, 880)

    time.sleep(0.05)

    bar_color = get_pixel(955, BAR_Y)

    if bar_color is None:
        print("COULD NOT READ BAR COLOR")
        return

    print(f"BAR COLOR: {bar_color}")

    rectangle_center_clicked = False
    last_fallback_click = 0

    start_time = time.monotonic()

    while running:

        if time.monotonic() - start_time >= MINIGAME_TIMEOUT:
            print("MINIGAME TIMEOUT")
            break

        bar = find_bar(bar_color)

        # =====================
        # RECTANGLE FOUND
        # =====================

        if bar is not None:
            left_x, right_x = bar
            width = right_x - left_x
            center = (left_x + right_x) // 2

            print(
                f"BAR FOUND: {left_x}-{right_x} "
                f"Width={width} Center={center}"
            )

            if width < 25:

                # Rectangle overlaps center.
                if (
                    left_x <= CENTER_X
                    and right_x >= CENTER_X
                ):
                    if not rectangle_center_clicked:
                        print("RECTANGLE CENTER -> CLICK ONCE")
                        click_mouse()
                        rectangle_center_clicked = True
                    else:
                        print("RECTANGLE CENTER -> HOLD NO CLICK")

                else:
                    rectangle_center_clicked = False

                    print("NORMAL CLICK")
                    click_mouse()

            else:
                rectangle_center_clicked = False
                print("TOO WIDE -> NO CLICK")

        # =====================
        # BAR HIDDEN
        # =====================

        else:
            rectangle_center_clicked = False

            print("BAR HIDDEN -> LINE FALLBACK")

            line_x = find_line()

            if line_x is not None:
                print(f"LINE FOUND: {line_x}")

                if line_x < CENTER_X - CENTER_TOLERANCE:
                    print("LINE LEFT -> CLICK")

                    now = time.monotonic()

                    if now - last_fallback_click >= 0.20:
                        click_mouse()
                        last_fallback_click = now

                elif line_x > CENTER_X + CENTER_TOLERANCE:
                    print("LINE RIGHT -> NO CLICK")

                else:
                    print("LINE CENTER -> CONTROLLED CLICK")

                    now = time.monotonic()

                    if now - last_fallback_click >= CENTER_FALLBACK_CLICK_INTERVAL:
                        click_mouse()
                        last_fallback_click = now

            else:
                print("LINE HIDDEN")

        time.sleep(0.01)


# =========================
# FISHING CYCLE
# =========================

def fishing_cycle():
    global running

    print("\nFISH BUTTON CLICK")

    move_mouse(FISH_X, FISH_Y)
    click_mouse()

    time.sleep(0.35)

    if not wait_for_minigame():
        print("MINIGAME DID NOT START")
        running = False
        print("MACRO PAUSED")
        return

    play_minigame()

    if not running:
        return

    # =========================
    # FAST X CLICK
    # =========================

    # The minigame is finished.
    # Don't wait around for the X.
    time.sleep(0.10)

    move_mouse(X_BUTTON_X, X_BUTTON_Y)

    time.sleep(0.15)

    click_mouse()

    print("X CLICKED")

    # Short delay before starting next fish.
    time.sleep(0.20)


# =========================
# MAIN LOOP
# =========================

def fishing_loop():
    global running

    cycle = 0

    print("SOLS FISHING MACRO")
    print("F8 = START / PAUSE")
    print("F3 = EMERGENCY STOP")

    while not stop_requested:

        if not running:
            time.sleep(0.1)
            continue

        cycle += 1

        print(f"\n========== CYCLE {cycle} ==========")

        fishing_cycle()

        time.sleep(0.05)


# =========================
# START
# =========================

if __name__ == "__main__":
    fishing_loop()
