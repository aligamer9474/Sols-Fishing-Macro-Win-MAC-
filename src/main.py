import time
import threading
import ctypes
import keyboard
import pyautogui

running = False

# ============================================================
# COORDINATES
# ============================================================

# Confirmed working Fish button
FISH_BUTTON = (853, 832)

# These will be calibrated later
FISH_CAUGHT_X = None
COLLECTIONS_BUTTON = None
COLLECTIONS_CLOSE_X = None
SELL_BUTTON = None
SELL_ALL_BUTTON = None
SHOP_CLOSE_X = None

# ============================================================
# FISHING MINIGAME COORDINATES
# ============================================================

# Based on the old macro.
# These are screen coordinates at 1080p.

MINIGAME_START_PIXEL = (1176, 836)

BAR_SAMPLE_POINT = (955, 767)

BAR_SCAN_LEFT = 757
BAR_SCAN_RIGHT = 1161
BAR_SCAN_Y = 767

# How wide the detected bar must be before we consider
# ourselves inside the target area.
ADVANCED_FISHING_THRESHOLD = 25

# Small delay between pixel checks
MINIGAME_SCAN_DELAY = 0.01

# Maximum amount of time to wait for the minigame
MINIGAME_TIMEOUT = 10

# ============================================================
# SETTINGS
# ============================================================

MAX_FISHING_CYCLES = 15

CLICK_DELAY = 0.25

# ============================================================
# WINDOWS MOUSE INPUT
# ============================================================

user32 = ctypes.windll.user32

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004


class POINT(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_long),
        ("y", ctypes.c_long),
    ]


def get_mouse_position():
    point = POINT()
    user32.GetCursorPos(ctypes.byref(point))
    return point.x, point.y


def native_move_to(x, y):

    start_x, start_y = get_mouse_position()

    distance = max(
        abs(x - start_x),
        abs(y - start_y)
    )

    if distance == 0:
        return

    steps = max(20, int(distance / 8))

    for i in range(1, steps + 1):

        if not running:
            return

        target_x = int(
            start_x + (x - start_x) * i / steps
        )

        target_y = int(
            start_y + (y - start_y) * i / steps
        )

        current_x, current_y = get_mouse_position()

        move_x = target_x - current_x
        move_y = target_y - current_y

        if move_x != 0 or move_y != 0:

            user32.mouse_event(
                MOUSEEVENTF_MOVE,
                move_x,
                move_y,
                0,
                0
            )

        time.sleep(0.008)


def native_click():

    user32.mouse_event(
        MOUSEEVENTF_LEFTDOWN,
        0,
        0,
        0,
        0
    )

    time.sleep(0.05)

    user32.mouse_event(
        MOUSEEVENTF_LEFTUP,
        0,
        0,
        0,
        0
    )


def click_position(position, name="button"):

    if position is None:
        print(f"[!] {name} coordinate has not been set yet.")
        return False

    print(f"Moving to {name}: {position}")

    native_move_to(
        position[0],
        position[1]
    )

    if not running:
        return False

    time.sleep(CLICK_DELAY)

    native_click()

    print(f"Clicked {name}.")

    time.sleep(CLICK_DELAY)

    return True


# ============================================================
# PIXEL FUNCTIONS
# ============================================================

def get_pixel(x, y):

    try:
        return pyautogui.pixel(x, y)
    except Exception:
        return None


def colors_match(color1, color2, tolerance=5):

    if color1 is None or color2 is None:
        return False

    return all(
        abs(color1[i] - color2[i]) <= tolerance
        for i in range(3)
    )


def is_white_pixel(x, y):

    color = get_pixel(x, y)

    if color is None:
        return False

    return (
        color[0] >= 245
        and color[1] >= 245
        and color[2] >= 245
    )


# ============================================================
# FISHING
# ============================================================

def start_fishing():

    print()
    print("=== START FISHING ===")

    return click_position(
        FISH_BUTTON,
        "Fish button"
    )


def wait_for_minigame():

    print("Waiting for fishing minigame...")

    start_time = time.time()

    while running:

        if time.time() - start_time >= MINIGAME_TIMEOUT:
            print("[!] Timed out waiting for minigame.")
            return False

        if is_white_pixel(
            MINIGAME_START_PIXEL[0],
            MINIGAME_START_PIXEL[1]
        ):
            print("Fishing minigame detected!")
            return True

        time.sleep(MINIGAME_SCAN_DELAY)

    return False


def find_bar_color():

    """
    The fishing bar color is randomized.

    The old macro sampled a pixel around the middle
    of the fishing bar to determine the current color.
    """

    color = get_pixel(
        BAR_SAMPLE_POINT[0],
        BAR_SAMPLE_POINT[1]
    )

    if color is None:
        return None

    # Ignore almost-white pixels.
    if (
        color[0] > 240
        and color[1] > 240
        and color[2] > 240
    ):
        return None

    # Ignore nearly-black pixels.
    if (
        color[0] < 15
        and color[1] < 15
        and color[2] < 15
    ):
        return None

    return color


def find_contiguous_bar_width(bar_color):

    """
    Scan across the fishing bar and determine how many
    matching pixels are next to each other.

    This follows the basic detection idea from the old macro.
    """

    if bar_color is None:
        return 0

    width = 0
    best_width = 0

    screenshot = pyautogui.screenshot(
        region=(
            BAR_SCAN_LEFT,
            BAR_SCAN_Y,
            BAR_SCAN_RIGHT - BAR_SCAN_LEFT + 1,
            1
        )
    )

    for x in range(
        BAR_SCAN_RIGHT - BAR_SCAN_LEFT + 1
    ):

        pixel = screenshot.getpixel((x, 0))

        if colors_match(
            pixel,
            bar_color,
            tolerance=10
        ):

            width += 1

            if width > best_width:
                best_width = width

        else:

            width = 0

    return best_width


def play_fishing_minigame():

    print()
    print("=== FISHING MINIGAME ===")

    if not wait_for_minigame():
        return False

    print("Reading fishing bar color...")

    bar_color = None

    # Give the game a moment to fully render the bar.
    time.sleep(0.1)

    # Try several times to find the randomized color.
    for _ in range(20):

        if not running:
            return False

        bar_color = find_bar_color()

        if bar_color is not None:
            break

        time.sleep(0.02)

    if bar_color is None:

        print("[!] Could not detect fishing bar color.")
        print("[!] Stopping so we don't randomly click.")

        return False

    print(f"Detected bar color: {bar_color}")

    print("Watching fishing bar...")

    start_time = time.time()

    while running:

        if time.time() - start_time >= MINIGAME_TIMEOUT:

            print("[!] Fishing minigame timed out.")
            return False

        width = find_contiguous_bar_width(
            bar_color
        )

        # ----------------------------------------------------
        # If the colored bar is narrow or missing, click.
        #
        # This follows the old macro's advanced detection:
        # when the detected width falls below the threshold,
        # the macro clicks.
        # ----------------------------------------------------

        if width == 0:

            print("Target lost - clicking!")

            native_click()

            time.sleep(0.15)

        elif width < ADVANCED_FISHING_THRESHOLD:

            print(
                f"Target width: {width} "
                f"- clicking!"
            )

            native_click()

            time.sleep(0.15)

        else:

            time.sleep(
                MINIGAME_SCAN_DELAY
            )

        # ----------------------------------------------------
        # Check whether the minigame has disappeared.
        # ----------------------------------------------------

        if not is_white_pixel(
            MINIGAME_START_PIXEL[0],
            MINIGAME_START_PIXEL[1]
        ):

            # Give the game a moment to transition.
            time.sleep(0.2)

            print("Fishing minigame finished.")

            return True

    return False


def close_fish_caught_popup():

    if FISH_CAUGHT_X is None:
        print("[!] Fish Caught X coordinate not set yet.")
        return False

    return click_position(
        FISH_CAUGHT_X,
        "Fish Caught X"
    )


# ============================================================
# RESET CHARACTER
# ============================================================

def reset_character():

    print()
    print("=== RESET CHARACTER ===")

    if not running:
        return

    print("Pressing ESC...")

    keyboard.press("esc")
    time.sleep(0.5)
    keyboard.release("esc")

    time.sleep(1)

    if not running:
        return

    print("Pressing R...")

    keyboard.press("r")
    time.sleep(0.5)
    keyboard.release("r")

    time.sleep(1)

    if not running:
        return

    print("Pressing Enter...")

    keyboard.press("enter")
    time.sleep(0.5)
    keyboard.release("enter")

    time.sleep(3)

    print("Character reset sequence finished.")


# ============================================================
# COLLECTIONS / BEACH ALIGNMENT
# ============================================================

def open_collections():

    print()
    print("=== OPEN COLLECTIONS ===")

    if COLLECTIONS_BUTTON is None:
        print("[!] Collections coordinate not set yet.")
        return False

    return click_position(
        COLLECTIONS_BUTTON,
        "Collections"
    )


def close_collections():

    print("Closing Collections...")

    if COLLECTIONS_CLOSE_X is None:
        print("[!] Collections close X coordinate not set yet.")
        return False

    return click_position(
        COLLECTIONS_CLOSE_X,
        "Collections X"
    )


def face_beach():

    print("Player should now be facing the beach.")


# ============================================================
# CAMERA
# ============================================================

def reset_camera():

    print()
    print("=== CAMERA RESET ===")

    if not running:
        return

    print("Zooming in...")

    keyboard.press("o")
    time.sleep(3)
    keyboard.release("o")

    time.sleep(0.5)

    if not running:
        return

    print("Zooming out...")

    keyboard.press("i")
    time.sleep(3)
    keyboard.release("i")

    print("Camera reset finished.")


# ============================================================
# PATH TO FISH SHOP
# ============================================================

def path_to_fish_shop():

    print()
    print("=== PATH TO FISH SHOP ===")

    if not running:
        return

    print("Moving toward wall...")

    keyboard.keyDown("w")
    time.sleep(2)
    keyboard.keyUp("w")

    if not running:
        return

    print("Aligning for jump sequence...")

    print("[!] Exact shop path still needs calibration.")


# ============================================================
# FISH SHOP
# ============================================================

def open_fish_shop():

    print()
    print("=== OPEN FISH SHOP ===")

    if not running:
        return False

    print("Pressing E...")

    keyboard.press("e")
    time.sleep(0.5)
    keyboard.release("e")

    time.sleep(1)

    return True


def sell_fish():

    print()
    print("=== SELL FISH ===")

    if SELL_BUTTON is None:
        print("[!] Sell button coordinate not set yet.")
        return False

    click_position(
        SELL_BUTTON,
        "Sell"
    )

    if not running:
        return False

    if SELL_ALL_BUTTON is None:
        print("[!] Sell All coordinate not set yet.")
        return False

    click_position(
        SELL_ALL_BUTTON,
        "Sell All"
    )

    return True


def close_fish_shop():

    print("Closing fish shop...")

    if SHOP_CLOSE_X is None:
        print("[!] Shop X coordinate not set yet.")
        return False

    return click_position(
        SHOP_CLOSE_X,
        "Shop X"
    )


# ============================================================
# RETURN TO BEACH
# ============================================================

def return_to_beach():

    print()
    print("=== RETURN TO BEACH ===")

    if not running:
        return

    print("Moving away from shop...")

    keyboard.keyDown("a")
    time.sleep(0.5)
    keyboard.keyUp("a")

    if not running:
        return

    print("Moving toward beach...")

    keyboard.keyDown("s")
    time.sleep(3)
    keyboard.keyUp("s")

    print("Returned toward beach.")


# ============================================================
# MAIN MACRO
# ============================================================

def macro():

    global running

    print()
    print("================================")
    print("Sol's Fishing Macro")
    print("================================")
    print()

    fishing_cycles = 0

    while running:

        # 1. Start fishing
        if not start_fishing():
            break

        if not running:
            break

        # 2. Play fishing minigame
        if not play_fishing_minigame():

            print()
            print("[STOPPED]")
            print("Fishing minigame could not be completed.")

            running = False
            break

        if not running:
            break

        # 3. Fish Caught popup
        if FISH_CAUGHT_X is not None:
            close_fish_caught_popup()
        else:
            print("[!] Fish Caught X not calibrated yet.")

        fishing_cycles += 1

        print()
        print(
            f"Fishing cycle: "
            f"{fishing_cycles}/{MAX_FISHING_CYCLES}"
        )

        # 4. Check whether it is time to sell
        if fishing_cycles >= MAX_FISHING_CYCLES:

            print()
            print("Maximum fishing cycles reached.")

            # 5. Reset character
            reset_character()

            if not running:
                break

            # 6. Open Collections
            open_collections()

            if not running:
                break

            # 7. Close Collections
            close_collections()

            if not running:
                break

            # 8. Face beach
            face_beach()

            # 9. Reset camera
            reset_camera()

            if not running:
                break

            # 10. Walk to fish shop
            path_to_fish_shop()

            if not running:
                break

            # 11. Open shop
            open_fish_shop()

            if not running:
                break

            # 12. Sell fish
            sell_fish()

            if not running:
                break

            # 13. Close shop
            close_fish_shop()

            if not running:
                break

            # 14. Return to beach
            return_to_beach()

            fishing_cycles = 0

            print()
            print("================================")
            print("Back to fishing.")
            print("================================")

        time.sleep(0.5)

    print()
    print("Macro stopped.")


# ============================================================
# HOTKEYS
# ============================================================

def toggle_macro():

    global running

    if running:

        running = False

        print()
        print("Macro stopped!")

    else:

        running = True

        threading.Thread(
            target=macro,
            daemon=True
        ).start()


def emergency_stop():

    global running

    running = False

    print()
    print("!!! EMERGENCY STOP !!!")


keyboard.add_hotkey("f8", toggle_macro)
keyboard.add_hotkey("f3", emergency_stop)


# ============================================================
# START
# ============================================================

print("Sol's Fishing Macro")
print()
print("Fish button: (853, 832)")
print()
print("F8 = Start / Stop")
print("F3 = Emergency Stop")
print()
print("Ready.")

keyboard.wait()
