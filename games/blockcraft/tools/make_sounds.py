"""Generate original, code-made sound effects for Blockcraft.

Every sound here is synthesized from scratch (noise, tones, envelopes).
Output: sounds/sounds00.js in the same format the game already loads.
"""
import base64, io, json, os, subprocess, sys, wave
import numpy as np

SR = 22050
rng = np.random.default_rng(7)
OUT = sys.argv[1] if len(sys.argv) > 1 else "sounds00.js"


def t(dur):
    return np.arange(int(SR * dur)) / SR


def env(n, attack=0.005, decay=0.15):
    x = np.arange(n) / SR
    a = np.clip(x / max(attack, 1e-4), 0, 1)
    return a * np.exp(-x / max(decay, 1e-4))


def lowpass(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


def highpass(x, cutoff):
    return x - lowpass(x, cutoff)


def noise(dur):
    return rng.uniform(-1, 1, int(SR * dur))


def tone(freq, dur, kind="sine"):
    ph = 2 * np.pi * np.cumsum(np.broadcast_to(freq, t(dur).shape)) / SR
    if kind == "square":
        return np.sign(np.sin(ph))
    if kind == "tri":
        return 2 / np.pi * np.arcsin(np.sin(ph))
    return np.sin(ph)


def norm(x, peak=0.8):
    m = np.max(np.abs(x)) or 1
    return x / m * peak


# ---- material sounds (dig = break/place, step = footstep) ----
MATERIALS = {
    #          lowpass, highpass, decay, extra tone
    "stone":     (2500, 300, 0.08, 180),
    "wood":      (1400, 150, 0.10, 220),
    "grass":     (3000, 800, 0.07, None),
    "wet_grass": (1800, 500, 0.08, None),
    "gravel":    (4000, 600, 0.09, None),
    "sand":      (5000, 1500, 0.08, None),
    "snow":      (2200, 900, 0.10, None),
    "cloth":     (900, 100, 0.07, None),
    "coral":     (2600, 400, 0.08, 300),
}


def material(name, step=False, seed=0):
    lp, hp, dec, tn = MATERIALS[name]
    dur = 0.12 if step else 0.22
    x = noise(dur)
    x = highpass(lowpass(x, lp * (1 + 0.1 * seed)), hp)
    if tn:
        x = x + 0.6 * tone(tn * (1 + 0.07 * seed), dur, "tri")
    x *= env(len(x), 0.002, dec * (0.6 if step else 1))
    return norm(x, 0.5 if step else 0.75)


SOUNDS = {}
for m in MATERIALS:
    for v in range(1, 5):
        SOUNDS[f"dig/{m}{v}"] = material(m, False, v)
        SOUNDS[f"step/{m}{v}"] = material(m, True, v)
for v in range(1, 5):
    SOUNDS[f"step/ladder{v}"] = material("wood", True, v)


def sweep(f0, f1, dur, kind="sine", decay=None):
    f = np.linspace(f0, f1, int(SR * dur))
    x = tone(f, dur, kind)
    return x * env(len(x), 0.003, decay or dur / 2)


# ---- UI and general ----
SOUNDS["random/click"] = norm(tone(1800, 0.04, "square") * env(int(SR*.04), .001, .01), .5)
SOUNDS["random/wood_click"] = norm(tone(900, 0.05, "tri") * env(int(SR*.05), .001, .015), .5)
SOUNDS["random/pop"] = norm(sweep(400, 1400, 0.08), .6)
SOUNDS["random/orb"] = norm(sweep(1500, 2200, 0.12, "sine", .08) + .4*sweep(3000, 4400, .12, "sine", .05), .5)
SOUNDS["random/levelup"] = norm(np.concatenate([tone(f, .1, "tri") * env(int(SR*.1), .003, .2) for f in (523, 659, 784, 1047)]), .6)
SOUNDS["random/break"] = norm(highpass(noise(.25), 1500) * env(int(SR*.25), .001, .06) + .5*sweep(900, 300, .25, "square", .05), .6)
SOUNDS["random/glass"] = norm(sum(tone(f, .4) * env(int(SR*.4), .001, .12) for f in (2100, 3170, 4400)) + .5*highpass(noise(.4), 4000) * env(int(SR*.4), .001, .05), .6)
SOUNDS["random/fizz"] = norm(highpass(noise(.5), 3000) * env(int(SR*.5), .02, .2), .5)
SOUNDS["random/fuse"] = norm(highpass(noise(1.2), 2500) * np.linspace(.6, 1, int(SR*1.2)), .4)
boom = lowpass(noise(1.6), 300) * env(int(SR*1.6), .002, .5)
SOUNDS["random/explode"] = norm(boom + .3 * lowpass(noise(1.6), 1500) * env(int(SR*1.6), .001, .15), .9)
for v in range(1, 5):
    SOUNDS[f"random/explode{v}"] = norm(lowpass(noise(1.5), 250 + 40*v) * env(int(SR*1.5), .002, .45), .9)
SOUNDS["random/bow"] = norm(sweep(300, 900, .25, "tri", .1) + .3*highpass(noise(.25), 2000) * env(int(SR*.25), .001, .06), .5)
SOUNDS["random/bowhit"] = norm(lowpass(noise(.12), 1200) * env(int(SR*.12), .001, .03), .6)
SOUNDS["random/successful_hit"] = norm(tone(1600, .08) * env(int(SR*.08), .001, .03), .4)
SOUNDS["random/eat"] = norm(lowpass(noise(.15), 1500) * env(int(SR*.15), .005, .04), .5)
for v in range(1, 4):
    SOUNDS[f"random/eat{v}"] = norm(lowpass(noise(.14), 1200 + 300*v) * env(int(SR*.14), .005, .04), .5)
SOUNDS["random/burp"] = norm(lowpass(tone(110, .3, "square") * (1 + .5*noise(.3)), 600) * env(int(SR*.3), .02, .12), .6)
SOUNDS["random/drink"] = norm(sweep(300, 500, .12, "sine", .05), .4)
for name, f0, f1 in [("door_open", 160, 120), ("door_close", 140, 90), ("chestopen", 200, 150), ("chestclosed", 150, 90)]:
    SOUNDS[f"random/{name}"] = norm(lowpass(noise(.3), 900) * env(int(SR*.3), .003, .08) + .6*sweep(f0, f1, .3, "tri", .1), .6)
SOUNDS["tile/piston/out"] = norm(sweep(120, 260, .2, "square", .08) + .4*lowpass(noise(.2), 800)*env(int(SR*.2), .002, .05), .5)
SOUNDS["tile/piston/in"] = norm(sweep(260, 120, .2, "square", .08) + .4*lowpass(noise(.2), 800)*env(int(SR*.2), .002, .05), .5)

# ---- damage ----
for v in range(1, 4):
    SOUNDS[f"damage/hit{v}"] = norm(lowpass(noise(.18), 900 + 200*v) * env(int(SR*.18), .001, .05) + .5*sweep(300, 150, .18, "square", .05), .7)
SOUNDS["damage/fallsmall"] = norm(lowpass(noise(.15), 500) * env(int(SR*.15), .001, .05), .6)
SOUNDS["damage/fallbig"] = norm(lowpass(noise(.3), 350) * env(int(SR*.3), .001, .1), .8)

# ---- liquids, fire, portal ----
SOUNDS["liquid/splash"] = norm(highpass(lowpass(noise(.6), 4000), 300) * env(int(SR*.6), .005, .18), .6)
for v in range(1, 4):
    SOUNDS[f"liquid/swim{v}"] = norm(highpass(lowpass(noise(.35), 2500 + 300*v), 400) * env(int(SR*.35), .03, .12), .4)
SOUNDS["fire/ignite"] = norm(highpass(noise(.35), 1200) * env(int(SR*.35), .002, .1) + .4*sweep(2000, 600, .35, "sine", .1), .5)
SOUNDS["portal/trigger"] = norm(sum(sweep(f, f*1.5, 2.0, "sine", 1.2) for f in (110, 165, 220)), .5)
SOUNDS["portal/travel"] = norm(sum(sweep(f*1.5, f, 2.5, "sine", 1.5) for f in (110, 165, 220)) + .2*lowpass(noise(2.5), 600)*env(int(SR*2.5), .2, 1.5), .5)

# ---- note block (harp-like pluck at F#3; the game pitches it) ----
pl = sum(tone(185 * k, .8) / k for k in (1, 2, 3, 4)) * env(int(SR*.8), .002, .25)
SOUNDS["note/harp"] = norm(pl, .6)

# ---- weather / ambience ----
SOUNDS["ambient/weather/rain1"] = norm(highpass(lowpass(noise(3.0), 6000), 800) * .5, .25)
SOUNDS["ambient/weather/thunder1"] = norm(lowpass(noise(3.0), 180) * env(int(SR*3), .05, 1.0), .9)
SOUNDS["ambient/cave/cave1"] = norm(sweep(70, 55, 3.0, "sine", 1.5) + .3*lowpass(noise(3.0), 200)*env(int(SR*3), .5, 1.5), .3)


# ---- mobs: simple voice-ish tones ----
def voice(f0, f1, dur, grit=0.3, kind="square", lp=1200):
    x = sweep(f0, f1, dur, kind, dur * .6) + grit * noise(dur) * env(int(SR*dur), .01, dur*.5)
    return norm(lowpass(x, lp), .6)


MOBS = {
    "zombie":   (140, 90, .6, .4, 900),
    "skeleton": (500, 400, .25, .6, 3000),
    "spider":   (300, 220, .3, .8, 2500),
    "creeper":  (200, 200, .3, .9, 1500),
    "cow":      (180, 120, .7, .2, 900),
    "pig":      (400, 300, .25, .5, 1600),
    "sheep":    (450, 380, .5, .2, 1800),
    "wolf":     (500, 300, .2, .4, 2000),
    "endermen": (90, 140, .8, .5, 700),
    "ghast":    (700, 350, 1.0, .3, 2500),
}
for mob, (f0, f1, dur, grit, lp) in MOBS.items():
    for v in range(1, 4):
        k = 1 + .08 * v
        SOUNDS[f"mob/{mob}/say{v}"] = voice(f0*k, f1*k, dur, grit, "square", lp)
        SOUNDS[f"mob/{mob}/hurt{v}"] = voice(f0*1.3*k, f0*.8*k, .2, grit, "square", lp)
        SOUNDS[f"mob/{mob}/step{v}"] = material("cloth" if mob in ("spider", "wolf") else "gravel", True, v)
    SOUNDS[f"mob/{mob}/death"] = voice(f0*1.1, f1*.5, dur*1.4, grit, "square", lp)
SOUNDS["mob/wolf/bark1"] = voice(600, 350, .15, .3, "square", 2200)
SOUNDS["mob/endermen/idle1"] = voice(80, 120, 1.0, .5, "sine", 600)
SOUNDS["mob/endermen/hit1"] = voice(160, 90, .3, .5, "square", 900)
SOUNDS["mob/endermen/portal"] = norm(sweep(200, 1200, .4, "sine", .3) + .3*highpass(noise(.4), 2000)*env(int(SR*.4), .01, .2), .5)
SOUNDS["mob/ghast/moan1"] = voice(300, 220, 1.5, .2, "sine", 1500)
SOUNDS["mob/ghast/scream1"] = voice(900, 500, .7, .4, "square", 3000)
SOUNDS["mob/ghast/charge"] = voice(300, 900, .6, .3, "sine", 2000)
SOUNDS["mob/ghast/fireball4"] = SOUNDS["random/explode1"] * .6
SOUNDS["mob/slime/big1"] = norm(lowpass(sweep(200, 90, .2, "sine", .08) + .3*noise(.2)*env(int(SR*.2), .001, .05), 800), .6)
SOUNDS["mob/slime/small1"] = norm(lowpass(sweep(400, 200, .15, "sine", .06) + .3*noise(.15)*env(int(SR*.15), .001, .04), 1500), .5)
SOUNDS["mob/sheep/shear"] = norm(highpass(noise(.12), 3000) * env(int(SR*.12), .001, .03), .5)
SOUNDS["mob/zombiepig/zpig1"] = voice(220, 160, .5, .4, "square", 1000)
SOUNDS["mob/zombiepig/zpighurt1"] = voice(300, 200, .2, .4, "square", 1000)
SOUNDS["mob/zombiepig/zpigdeath"] = voice(260, 100, .8, .4, "square", 1000)

# ---- items ----
for k, src in {"item/bucket/fill1": "liquid/splash", "item/bucket/empty1": "liquid/splash",
               "item/bucket/fill_lava1": "fire/ignite", "item/bucket/empty_lava1": "fire/ignite",
               "item/hoe/till1": "dig/grass1", "item/shovel/flatten1": "dig/gravel1",
               "item/axe/strip1": "dig/wood1", "item/bonemeal/bonemeal1": "dig/grass2"}.items():
    SOUNDS[k] = SOUNDS[src] * .8


def to_ogg_b64(x):
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2").tobytes()
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm)
    ogg = subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "wav", "-i", "pipe:0",
                          "-c:a", "libvorbis", "-q:a", "2", "-f", "ogg", "pipe:1"],
                         input=buf.getvalue(), capture_output=True, check=True).stdout
    return base64.b64encode(ogg).decode()


data = {k: to_ogg_b64(v) for k, v in SOUNDS.items()}
with open(OUT, "w") as f:
    f.write("(window.EMBED_SOUND_PARTS=window.EMBED_SOUND_PARTS||[]).push(")
    f.write(json.dumps(data, separators=(",", ":")))
    f.write(");\n")
print(len(data), "sounds,", os.path.getsize(OUT) // 1024, "KB")
