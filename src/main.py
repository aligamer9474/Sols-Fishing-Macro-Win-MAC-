import pyautogui
import keyboard
import time
import ctypes
import ctypes.wintypes

# =========================
# SETTINGS
# =========================

FISH_X = 853
FISH_Y = 832

X_BUTTON_X = 1113
X_BUTTON_Y = 342

# Used to detect when the minigame appears/disappears
MINIGAME_CHECK_X = 1176
MINIGAME_CHECK_Y = 836

# Fishing bar
BAR_SCAN_LEFT = 757
BAR_SCAN_RIGHT = 1161
BAR_Y = 767

# Center of the fishing bar
CENTER_X = 959
CENTER_TOLERANCE = 12

# Rectangle detection
COLOR_TOLERANCE = 15
EDGE_TOLERANCE = 10

# Rectangle width limit
MAX_BAR_WIDTH = 25

# Prevent rapid clicking
NORMAL_CLICK_INTERVAL = 0.08

# How long to wait for a minigame
MINIGAME_WAIT_TIMEOUT = 30.0

# Maximum safety time for one minigame
MINIGAME_TIMEOUT = 12.0

# How long to wait after clicking X
AFTER_X_DELAY = 0.75


running = False
stop_requested = False

rectangle_center_clicked = False
last_normal_click = 0


# =========================
# WINDOWS MOUSE
# =========================

user32 = ctypes.windll.user32

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004


def get_mouse_pos():

    point = ctypes.wintypes.POINT()

    user32.GetCursorPos(
        ctypes.byref(point)
    )

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


def move_mouse_fast(x, y):

    while running:

        current_x, current_y = get_mouse_pos()

        dx = x - current_x
        dy = y - current_y

        if abs(dx) <= 2 and abs(dy) <= 2:
            break

        dx = max(-15, min(15, dx))
        dy = max(-15, min(15, dy))

        user32.mouse_event(
            MOUSEEVENTF_MOVE,
            dx,
            dy,
            0,
            0
        )

        time.sleep(0.001)


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

    return (
        r >= 240
        and g >= 240
        and b >= 240
    )


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

    global running
    global stop_requested

    stop_requested = True
    running = False

    print("\nEMERGENCY STOP")


keyboard.add_hotkey(
    "f8",
    toggle_macro
)

keyboard.add_hotkey(
    "f3",
    emergency_stop
)


# =========================
# MINIGAME CHECK
# =========================

def minigame_is_visible():

    pixel = get_pixel(
        MINIGAME_CHECK_X,
        MINIGAME_CHECK_Y
    )

    return is_white(pixel)


def wait_for_minigame():

    print("WAITING FOR MINIGAME...")

    start_time = time.monotonic()

    while running:

        if (
            time.monotonic() - start_time
            >= MINIGAME_WAIT_TIMEOUT
        ):

            print("MINIGAME WAIT TIMEOUT")

            return False

        if minigame_is_visible():

            time.sleep(0.05)

            if minigame_is_visible():

                print("MINIGAME DETECTED")

                return True

        time.sleep(0.05)

    return False


# =========================
# FIND BLUE FISH RECTANGLE
# =========================

def find_bar(bar_color):

    screenshot = pyautogui.screenshot()

    br, bg, bb = bar_color

    closest_x = None
    closest_distance = 999999

    # Find the closest matching pixel
    for x in range(
        BAR_SCAN_LEFT,
        BAR_SCAN_RIGHT + 1
    ):

        r, g, b = screenshot.getpixel(
            (x, BAR_Y)
        )

        distance = (
            abs(r - br)
            + abs(g - bg)
            + abs(b - bb)
        )

        if distance <= COLOR_TOLERANCE:

            if distance < closest_distance:

                closest_distance = distance
                closest_x = x

    if closest_x is None:
        return None

    left_x = closest_x
    right_x = closest_x

    # Expand to the right
    while right_x < BAR_SCAN_RIGHT:

        r, g, b = screenshot.getpixel(
            (right_x + 1, BAR_Y)
        )

        if (
            abs(r - br) <= EDGE_TOLERANCE
            and
            abs(g - bg) <= EDGE_TOLERANCE
            and
            abs(b - bb) <= EDGE_TOLERANCE
        ):

            right_x += 1

        else:
            break

    # Expand to the left
    while left_x > BAR_SCAN_LEFT:

        r, g, b = screenshot.getpixel(
            (left_x - 1, BAR_Y)
        )

        if (
            abs(r - br) <= EDGE_TOLERANCE
            and
            abs(g - bg) <= EDGE_TOLERANCE
            and
            abs(b - bb) <= EDGE_TOLERANCE
        ):

            left_x -= 1

        else:
            break

    return left_x, right_x


# =========================
# FISHING MINIGAME
# =========================

def play_minigame():

    global rectangle_center_clicked
    global last_normal_click

    print("STARTING MINIGAME")

    # Move mouse into the fishing area.
    # This does NOT control the fishing line.
    move_mouse(
        950,
        880
    )

    time.sleep(0.05)

    # Get THIS minigame's rectangle color.
    bar_color = get_pixel(
        955,
        BAR_Y
    )

    if bar_color is None:

        print("COULD NOT READ BAR COLOR")

        return

    print(
        f"BAR COLOR: {bar_color}"
    )

    rectangle_center_clicked = False
    last_normal_click = 0

    start_time = time.monotonic()

    while running:

        # Safety timeout only.
        # This is NOT the normal way the minigame ends.
        if (
            time.monotonic() - start_time
            >= MINIGAME_TIMEOUT
        ):

            print(
                "MINIGAME SAFETY TIMEOUT"
            )

            break

        # Look for the blue-ish rectangle.
        bar = find_bar(
            bar_color
        )

        if bar is not None:

            left_x, right_x = bar

            width = right_x - left_x

            center = (
                left_x + right_x
            ) // 2

            # =====================
            # TARGET TOO WIDE
            # =====================

            if width >= MAX_BAR_WIDTH:

                rectangle_center_clicked = False

            # =====================
            # TARGET IS USABLE
            # =====================

            else:

                # The rectangle overlaps
                # our center position.
                if (
                    left_x
                    <= CENTER_X
                    and
                    right_x
                    >= CENTER_X
                ):

                    # Only click ONCE while
                    # the rectangle remains
                    # centered.
                    if not rectangle_center_clicked:

                        click_mouse()

                        rectangle_center_clicked = True

                        print(
                            "RECTANGLE CENTER -> CLICK ONCE"
                        )

                else:

                    # Rectangle moved away.
                    # Allow another click when
                    # it comes back.
                    rectangle_center_clicked = False

                    now = time.monotonic()

                    if (
                        now - last_normal_click
                        >= NORMAL_CLICK_INTERVAL
                    ):

                        click_mouse()

                        last_normal_click = now

        else:

            # Rectangle temporarily disappeared.
            # Do NOT use the white progress
            # line to control anything.
            rectangle_center_clicked = False

        time.sleep(0.01)


# =========================
# FISHING CYCLE
# =========================

def fishing_cycle():

    global running

    print("\nFISH BUTTON CLICK")

    # Move to Fish button
    move_mouse(
        FISH_X,
        FISH_Y
    )

    # Click Fish once
    click_mouse()

    print("FISH CLICKED")

    # Give Roblox time to open
    time.sleep(0.50)

    # Wait for actual minigame
    if not wait_for_minigame():

        print(
            "MINIGAME DID NOT START"
        )

        running = False

        print(
            "MACRO PAUSED"
        )

        return

    # Play minigame
    play_minigame()

    if not running:
        return

    # =========================
    # CLICK X
    # =========================

    print("GOING TO X")

    move_mouse_fast(
        X_BUTTON_X,
        X_BUTTON_Y
    )

    time.sleep(0.05)

    click_mouse()

    print("X CLICKED")

    # Let Roblox reset
    time.sleep(
        AFTER_X_DELAY
    )


# =========================
# MAIN LOOP
# =========================

def fishing_loop():

    global running

    cycle = 0

    print(
        "SOLS FISHING MACRO"
    )

    print(
        "F8 = START / PAUSE"
    )

    print(
        "F3 = EMERGENCY STOP"
    )

    while not stop_requested:

        if not running:

            time.sleep(0.1)

            continue

        cycle += 1

        print(
            f"\n========== CYCLE {cycle} =========="
        )

        fishing_cycle()

        time.sleep(0.05)


# =========================
# START
# =========================

if __name__ == "__main__":

    fishing_loop()
