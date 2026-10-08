"""Builds the polished sprites in advance (behind the loading screen), so the first ninja,
bubble or star never makes the game stutter. Everything lands in gfx's cache."""
import gfx
from . import animals, bubbles, car, kungfu_master as kf, pizza
from .common import button_sprite, empty_star_sprite, icon_home, icon_of, icon_replay, star_sprite


def prewarm(games):
    for g in games:                                   # menu buttons + intro pictures
        icon_of(g.icon, 82 * 0.6)
        icon_of(g.icon, 150)
    icon_of(icon_home, 40 * 0.6)
    icon_of(icon_replay, 56 * 0.6)
    for r, rim in ((40, (255, 140, 90)), (56, (90, 210, 120)), (82, (255, 255, 255))):
        button_sprite(r, rim)
    for size in (20, 23, 24, 57):                     # star rows of the HUDs and the result screen
        star_sprite(size)
        empty_star_sprite(size * 0.5 / 0.6)
    for lv in kf.LEVELS.values():                     # every ninja animation frame
        for f in range(6):
            kf.ninja_sprite(lv["r"], "red", f)
            kf.ninja_sprite(lv["r"] * kf.BOSS_SIZE, "boss", f)
    for lv in kf.BOSS:                                # boss faces: every damage stage, + "ouch"
        for stage in range(5):
            for ouch in (False, True):
                kf.boss_face_sprite(kf.LEVELS[lv]["r"] * kf.BOSS_SIZE, stage, ouch)
    for col, power in kf.FIRE:                        # fire fist flames
        for r in range(3, 75):
            gfx.glow(r, col, power)
    gfx.glow(70, *kf.FIRE_CORE[0])
    gfx.glow(30, *kf.FIRE_CORE[1])
    kf.pow_sprite()
    kf.warning_sprite()
    kf.headband_sprite()
    for col in {c for _, c, _ in kf.BELTS}:
        kf.belt_sprite(col)
    for key, period in animals.ANIM_PERIOD.items():
        for f in range(animals.ANIM_FRAMES):
            animals.animal_sprite(key, (f + 0.5) / animals.ANIM_FRAMES * period)
    for key in animals.INFO:
        animals.animal_sprite(key, 0.0)
    sizes = {r for lv in bubbles.LEVELS.values() for r in range(int(lv["r"][0]) // 4 * 4, int(lv["r"][1]) + 4, 4)}
    sizes |= set(range(8, bubbles.TINY_R[1] + 4, 4)) | set(range(bubbles.GIANT_R[0] // 4 * 4, bubbles.GIANT_R[1] + 4, 4))
    for r in sorted(sizes):
        for hue in range(8):
            bubbles.make_sprite(r, hue, False)
    pizza.topping_sprite("cheese", 34)
    for kind in pizza.KINDS:
        pizza.topping_sprite(kind)
        pizza.whole_sprite(kind)
        pizza.whole_sprite(kind, 40)
    pizza.pizza_base()
    pizza.board_sprite()
    pizza.bowl_sprite()
    pizza.oven_sprite()
    pizza.oven_sprite(hole=True)
    for m in (0.0, 1.0):
        pizza.eater_sprite(m)
    pizza.eater_sprite(0.0, happy=True)
    for tool in ("knife", "blender", "grater"):
        pizza.tool_sprite(tool)
    pizza.whole_sprite("tomato", 30)
    pizza.whole_sprite("cheese", 34)
    pizza.pot_sprite(True)
    pizza.ladle_sprite()
    pizza.slice_sprite()
    pizza.cutter_wheel_sprite()
    pizza.melted_cheese_sprite(False)
    pizza.melted_cheese_sprite(True)
    pizza.cutter_handle_sprite()
    pizza.heart_sprite()
    for m in (0.25, 0.75, 0.5):
        pizza.eater_sprite(m)
    from main import DISPLAY_H, DISPLAY_W              # car: cockpit and the landscape
    car.car_frame(DISPLAY_W, DISPLAY_H, int(DISPLAY_H * car.DASH))
    for kind in car.SIZE:
        car.scenery_sprite(kind)
    car.rainbow_sprite()
    car.duck_sprite()
    for k in range(3):
        car.cloud_sprite(k)
    car.wheel_sprite()
    for size in range(3, 30):                         # star particles
        star_sprite(size * 1.3, (255, 230, 80), 2)
