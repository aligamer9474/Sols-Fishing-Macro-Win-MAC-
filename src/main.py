import time
import threading
import ctypes
import keyboard

running = False

# ============================================================
# COORDINATES
# ============================================================

# Already tested and confirmed working
FISH_BUTTON = (853, 832)

# We will fill these in after testing/calibrating them
FISH_CAUGHT_X = None
COLLECTIONS_BUTTON = None
COLLECTIONS_CLOSE_X = None
SELL_BUTTON = None
SELL_ALL_BUTTON = None
SHOP_CLOSE_X = None

# ============================================================
# SETTINGS
# ============================================================

# How many fishing cycles before going to sell
MAX_FISHING_CYCLES = 15

# Time between actions
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
    """
    Move the mouse using Windows mouse movement events.

    This is the method that successfully made Roblox
    recognize the Fish button hover.
    """

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
# FISHING
# ============================================================

def start_fishing():

    print()
    print("=== START FISHING ===")

    return click_position(
        FISH_BUTTON,
        "Fish button"
    )


def play_fishing_minigame():

    print("Fishing minigame started.")

    # --------------------------------------------------------
    # THIS IS THE PART WE WILL BUILD NEXT.
    #
    # The old macro used pixel/color detection to watch the
    # fishing bar and determine when to click.
    #
    # We are NOT guessing the colors yet.
    # --------------------------------------------------------

    print("[!] Fishing minigame detection is not coded yet.")

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

    # Slowly press Escape
    print("Pressing ESC...")
    keyboard.press("esc")
    time.sleep(0.5)
    keyboard.release("esc")

    time.sleep(1)

    if not running:
        return

    # Restart character
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

    # Zoom all the way in
    print("Zooming in...")

    keyboard.press("o")
    time.sleep(3)
    keyboard.release("o")

    time.sleep(0.5)

    if not running:
        return

    # Zoom all the way back out
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

    # Move toward the wall
    print("Moving toward wall...")

    keyboard.keyDown("w")
    time.sleep(2)
    keyboard.keyUp("w")

    if not running:
        return

    # Align for jump sequence
    print("Aligning for jump sequence...")

    # Placeholder for the actual path.
    #
    # We will replace this with the exact movement sequence
    # once we test the route in-game.

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

        # ----------------------------------------------------
        # 1. Start fishing
        # ----------------------------------------------------

        if not start_fishing():
            break

        if not running:
            break

        # ----------------------------------------------------
        # 2. Fishing minigame
        # ----------------------------------------------------

        if not play_fishing_minigame():
            print()
            print("[STOPPED]")
            print("Fishing minigame detection needs to be added.")
            running = False
            break

        if not running:
            break

        # ----------------------------------------------------
        # 3. Close Fish Caught popup
        # ----------------------------------------------------

        close_fish_caught_popup()

        fishing_cycles += 1

        print()
        print(f"Fishing cycle: {fishing_cycles}/{MAX_FISHING_CYCLES}")

        # ----------------------------------------------------
        # 4. Check whether it's time to sell
        # ----------------------------------------------------

        if fishing_cycles >= MAX_FISHING_CYCLES:

            print()
            print("Maximum fishing cycles reached.")

            # ------------------------------------------------
            # 5. Reset character
            # ------------------------------------------------

            reset_character()

            if not running:
                break

            # ------------------------------------------------
            # 6. Open Collections
            # ------------------------------------------------

            open_collections()

            if not running:
                break

            # ------------------------------------------------
            # 7. Close Collections
            # ------------------------------------------------

            close_collections()

            if not running:
                break

            # ------------------------------------------------
            # 8. Face beach
            # ------------------------------------------------

            face_beach()

            # ------------------------------------------------
            # 9. Reset camera
            # ------------------------------------------------

            reset_camera()

            if not running:
                break

            # ------------------------------------------------
            # 10. Walk to fish shop
            # ------------------------------------------------

            path_to_fish_shop()

            if not running:
                break

            # ------------------------------------------------
            # 11. Open shop
            # ------------------------------------------------

            open_fish_shop()

            if not running:
                break

            # ------------------------------------------------
            # 12. Sell fish
            # ------------------------------------------------

            sell_fish()

            if not running:
                break

            # ------------------------------------------------
            # 13. Close shop
            # ------------------------------------------------

            close_fish_shop()

            if not running:
                break

            # ------------------------------------------------
            # 14. Return to beach
            # ------------------------------------------------

            return_to_beach()

            # Start fishing again
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
