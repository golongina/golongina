"""Generates the game's tileable PBR texture sets (albedo, normal, AO/roughness/metal).

Run:  python3 tools/gen_textures.py   ->  writes www/textures/*.jpg
Each set: <name>_albedo.jpg (sRGB), <name>_normal.jpg (OpenGL, +Y up),
<name>_arm.jpg (R = ambient occlusion, G = roughness, B = metalness).
All noise is built in the frequency domain or on a torus, so every map tiles seamlessly.
"""
import os
import numpy as np
from PIL import Image
from scipy.spatial import cKDTree
from scipy.ndimage import gaussian_filter

OUT = os.path.join(os.path.dirname(__file__), '..', 'www', 'textures')
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(7)


# ───────────── tileable noise helpers ─────────────
def spectral(h, w, beta=2.0, stretch=(1.0, 1.0), lo=0.0, hi=1e9):
    """Gaussian random field with 1/f^beta spectrum; wraps perfectly.
    stretch=(sx, sy) makes features sx times longer along x and sy times longer along y."""
    fy = np.fft.fftfreq(h)[:, None] * h * stretch[1]
    fx = np.fft.fftfreq(w)[None, :] * w * stretch[0]
    f = np.sqrt(fx * fx + fy * fy)
    f[0, 0] = 1
    amp = 1.0 / f ** (beta / 2)
    amp[(f < lo) | (f > hi)] = 0
    amp[0, 0] = 0
    ph = np.exp(2j * np.pi * rng.random((h, w)))
    n = np.real(np.fft.ifft2(amp * ph))
    n -= n.mean()
    return n / (n.std() + 1e-9)


def norm01(a):
    a = a - a.min()
    return a / (a.max() + 1e-9)


def blur(a, s):
    return gaussian_filter(a, s, mode='wrap')


def normal_from_height(hgt, strength):
    gx = (np.roll(hgt, -1, 1) - np.roll(hgt, 1, 1)) * 0.5
    gy = (np.roll(hgt, -1, 0) - np.roll(hgt, 1, 0)) * 0.5
    nx, ny, nz = -gx * strength, gy * strength, np.ones_like(hgt)
    l = np.sqrt(nx * nx + ny * ny + nz * nz)
    return np.stack([nx / l, ny / l, nz / l], -1) * 0.5 + 0.5


def cavity_ao(hgt, radius, power=1.0):
    d = hgt - blur(hgt, radius)
    ao = 1 - np.clip(-d / (d.std() * 3 + 1e-9), 0, 1)
    return np.clip(ao, 0, 1) ** power


def save(name, albedo, normal, ao, rough, metal=None):
    h, w = ao.shape
    if metal is None:
        metal = np.zeros((h, w))
    to8 = lambda a: (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)
    srgb = np.where(albedo <= 0.0031308, albedo * 12.92, 1.055 * np.clip(albedo, 0, 1) ** (1 / 2.4) - 0.055)
    Image.fromarray(to8(srgb)).save(f'{OUT}/{name}_albedo.jpg', quality=88)
    Image.fromarray(to8(normal)).save(f'{OUT}/{name}_normal.jpg', quality=92)
    Image.fromarray(to8(np.stack([ao, rough, metal], -1))).save(f'{OUT}/{name}_arm.jpg', quality=90)
    print('wrote', name)


def lin(rgb):  # sRGB 0-255 -> linear 0-1
    c = np.array(rgb, dtype=float) / 255
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def voronoi(h, w, n, jitter=1.0):
    """Torus Voronoi: returns F1, F2 distances (pixels) and cell index per pixel."""
    pts = rng.random((n, 2)) * [w, h]
    tiles = np.concatenate([pts + [dx * w, dy * h] for dy in (-1, 0, 1) for dx in (-1, 0, 1)])
    ids = np.tile(np.arange(n), 9)
    tree = cKDTree(tiles)
    yy, xx = np.mgrid[0:h, 0:w]
    q = np.stack([xx.ravel() + 0.5, yy.ravel() + 0.5], -1)
    d, i = tree.query(q, k=2, workers=-1)
    return d[:, 0].reshape(h, w), d[:, 1].reshape(h, w), ids[i[:, 0]].reshape(h, w), pts


# ───────────── concrete (tunnel arch, shotcrete) ─────────────
def concrete(S=1024):
    base = spectral(S, S, 2.2)
    mid = spectral(S, S, 1.6, lo=8)
    fine = spectral(S, S, 0.6, lo=60)
    pores = np.clip(spectral(S, S, 0.2, lo=200) - 2.6, 0, None)
    streak = norm01(spectral(S, S, 2.4, stretch=(1, 8)))  # long vertical water runs
    hgt = base * 0.6 + mid * 0.35 + fine * 0.12 - pores * 1.8
    stain = np.clip((streak - 0.55) * 3, 0, 1)
    soot = norm01(blur(base, 6))
    eff = np.clip((norm01(spectral(S, S, 2.0)) - 0.78) * 5, 0, 1) * np.clip(stain * 2, 0, 1)
    v = 0.30 + 0.07 * mid + 0.03 * fine
    alb = np.stack([v, v * 0.97, v * 0.92], -1)
    alb *= (1 - 0.45 * stain)[..., None] * np.array([1.0, 0.93, 0.82])          # rust/water stains
    alb *= (1 - 0.35 * soot)[..., None]
    alb = alb * (1 - eff[..., None]) + eff[..., None] * lin([200, 196, 186])      # efflorescence
    alb *= (1 - 0.6 * np.clip(pores, 0, 1))[..., None]
    ao = cavity_ao(hgt, 3) * (0.85 + 0.15 * cavity_ao(hgt, 20))
    rough = np.clip(0.92 - 0.42 * stain + 0.04 * fine, 0.3, 1)
    save('concrete', alb, normal_from_height(hgt, 2.2), ao, rough)


# ───────────── glazed metro wall tiles (4 x 5 per texture, running bond) ─────────────
def tiles(S=1024):
    cols, rows = 4, 5
    yy, xx = np.mgrid[0:S, 0:S].astype(float)
    th = S / rows
    tw = S / cols
    r = (yy // th).astype(int)
    xo = (xx + (r % 2) * tw / 2) % S
    c = (xo // tw).astype(int)
    lx, ly = xo - c * tw, yy - r * th
    edge = np.minimum.reduce([lx, tw - lx, ly, th - ly])
    grout = 5.0
    bevel = np.clip((edge - grout) / 9, 0, 1)
    plateau = np.sin(bevel * np.pi / 2)
    tid = r * cols + c
    tile_rand = rng.random(rows * cols + cols)
    tile_tilt_x = (rng.random(rows * cols + cols) - 0.5) * 0.004
    tile_tilt_y = (rng.random(rows * cols + cols) - 0.5) * 0.004
    wav = spectral(S, S, 2.6) * 0.04
    hgt = plateau * (1 + tile_tilt_x[tid] * (lx - tw / 2) + tile_tilt_y[tid] * (ly - th / 2)) + wav * plateau
    # chips at tile corners
    chip_noise = norm01(spectral(S, S, 1.2, lo=20))
    chips = (edge < 22) & (chip_noise > 0.72)
    hgt = np.where(chips, hgt * 0.35, hgt)
    # hairline cracks
    crack = np.abs(spectral(S, S, 1.8, lo=4))
    cracks = (crack < 0.025) & (norm01(spectral(S, S, 2.4)) > 0.6) & (plateau > 0.9)
    hgt = np.where(cracks, hgt - 0.25, hgt)
    is_grout = plateau < 0.05
    grime = norm01(blur(spectral(S, S, 2.0), 2)) * 0.6 + (yy / S) * 0.35
    drip = np.clip((norm01(spectral(S, S, 2.4, stretch=(1, 10))) - 0.6) * 3, 0, 1)
    k = 0.86 + 0.14 * tile_rand[tid]
    alb = lin([226, 218, 196])[None, None, :] * k[..., None]
    alb = alb * (1 - (0.55 * np.clip(grime - 0.25, 0, 1))[..., None] * np.array([1, 1.05, 1.15]))
    alb = alb * (1 - drip[..., None] * np.array([0.35, 0.5, 0.65]))
    alb = np.where(is_grout[..., None], lin([60, 54, 46]) * (0.7 + 0.3 * grime[..., None]), alb)
    alb = np.where(chips[..., None], lin([92, 88, 80]), alb)
    alb = np.where(cracks[..., None], alb * 0.35, alb)
    ao = cavity_ao(hgt, 4, 1.2)
    rough = np.where(is_grout | chips, 0.95, np.clip(0.12 + 0.55 * np.clip(grime - 0.3, 0, 1) + 0.25 * drip, 0.08, 1))
    save('tiles', alb, normal_from_height(hgt * 6, 1.6), ao, rough)


# ───────────── track ballast (crushed granite) ─────────────
def ballast(S=1024):
    f1, f2, cid, pts = voronoi(S, S, 2600)
    n = len(pts)
    edge = f2 - f1
    size = np.sqrt(S * S / n)
    dome = np.clip(edge / (size * 0.42), 0, 1)
    dome = np.sin(dome * np.pi / 2) ** 0.8
    tiltx = (rng.random(n) - 0.5) * 0.02
    tilty = (rng.random(n) - 0.5) * 0.02
    yy, xx = np.mgrid[0:S, 0:S].astype(float)
    px, py = pts[cid, 0], pts[cid, 1]
    dx = (xx - px + S / 2) % S - S / 2
    dy = (yy - py + S / 2) % S - S / 2
    facet = np.abs(spectral(S, S, 1.0, lo=30)) * 0.08
    hgt = dome * (0.7 + 0.3 * rng.random(n)[cid]) + (tiltx[cid] * dx + tilty[cid] * dy) * dome - facet * dome
    hgt += spectral(S, S, 0.4, lo=150) * 0.025 * dome
    kind = rng.random(n)
    tone = 0.55 + 0.45 * rng.random(n)
    col = np.where(kind[:, None] < 0.1, lin([118, 100, 86]), np.where(kind[:, None] < 0.3, lin([150, 146, 140]), lin([112, 110, 108])))
    alb = col[cid] * tone[cid][..., None]
    nrm = normal_from_height(hgt * 18, 1.4)
    light = np.clip((nrm[..., 1] - 0.5) * 1.2 + (0.5 - nrm[..., 0]) * 0.4 + 0.85, 0.5, 1.2)
    alb = alb * (0.3 + 0.7 * dome[..., None] ** 1.5) * (0.75 + 0.25 * light[..., None])
    speck = np.clip(spectral(S, S, 0.0, lo=200) - 1.4, 0, 1)
    alb = alb * (1 - 0.6 * speck[..., None]) + speck[..., None] * 0.04
    gap = dome < 0.22
    dirt = lin([34, 28, 22])
    alb = np.where(gap[..., None], dirt * (0.3 + 0.7 * dome[..., None] / 0.22), alb)
    oil = np.clip((norm01(blur(spectral(S, S, 2.0), 3)) - 0.7) * 3, 0, 1)
    alb *= (1 - 0.6 * oil)[..., None]
    ao = np.clip(dome * 1.5, 0, 1) ** 0.6 * cavity_ao(hgt, 6)
    rough = np.clip(0.88 - 0.35 * oil + 0.05 * spectral(S, S, 1.0), 0.3, 1)
    save('ballast', alb, normal_from_height(hgt * 18, 1.4), ao, rough)


# ───────────── creosoted timber sleeper ─────────────
def wood(W=1024, H=256):
    warp = spectral(H, W, 2.6, stretch=(4, 1)) * 6
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    rings = np.sin((yy + warp * 3) * 0.55 + spectral(H, W, 2.2, stretch=(8, 1)) * 2.0)
    grain = spectral(H, W, 1.0, stretch=(14, 1)) * 0.5
    checks = np.abs(spectral(H, W, 1.6, stretch=(20, 1)))
    crack = np.clip(1 - checks / 0.06, 0, 1) * (norm01(spectral(H, W, 2.0, stretch=(6, 1))) > 0.55)
    hgt = rings * 0.12 + grain * 0.15 - crack * 1.2 + spectral(H, W, 2.2) * 0.2
    weather = norm01(blur(spectral(H, W, 2.2), 3))
    base = lin([52, 38, 28]) * (0.75 + 0.25 * (rings[..., None] * 0.5 + 0.5))
    grey = lin([92, 86, 78])
    alb = base * (1 - weather[..., None] * 0.6) + grey * weather[..., None] * 0.6
    alb *= (1 - 0.85 * crack)[..., None]
    alb *= (0.85 + 0.15 * norm01(grain))[..., None]
    ao = cavity_ao(hgt, 3, 1.3)
    rough = np.clip(0.78 + 0.15 * weather - 0.25 * (1 - weather) * 0.5, 0.4, 1)
    save('wood', alb, normal_from_height(hgt, 2.5), ao, rough)


# ───────────── rusty steel (rail web/foot, pipes, frames) ─────────────
def rust(S=512):
    a = norm01(spectral(S, S, 2.0))
    b = norm01(spectral(S, S, 1.2, lo=12))
    flake = np.clip((norm01(spectral(S, S, 1.0, lo=30)) - 0.55) * 4, 0, 1)
    hgt = a * 0.4 + b * 0.3 + flake * 0.4
    steel = lin([96, 94, 92])
    r1, r2 = lin([110, 52, 22]), lin([62, 30, 16])
    rmix = b[..., None]
    rusty = r1 * rmix + r2 * (1 - rmix)
    amount = np.clip(a * 1.3 - 0.1, 0, 1)[..., None]
    alb = steel * (1 - amount) + rusty * amount
    alb = alb * (0.8 + 0.4 * flake[..., None])
    metal = np.clip(1 - amount[..., 0] * 1.6, 0, 1) * 0.9
    rough = np.clip(0.45 + 0.5 * amount[..., 0], 0, 1)
    save('rust', alb, normal_from_height(hgt, 3.0), cavity_ao(hgt, 3), rough, metal)


# ───────────── stainless train side with fluting ─────────────
def train_metal(W=1024, H=256):
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    flute = np.where(yy > H * 0.72, np.cos((yy - H * 0.72) * 0.9) * 0.5 + 0.5, 0.0)
    brush = spectral(H, W, 1.0, stretch=(40, 1)) * 0.03
    seams = np.zeros_like(xx)
    for x in range(64, W, 170):
        seams += np.exp(-((xx - x) ** 2) / 2.0)
    hgt = flute * 0.6 + brush - seams * 0.8
    rough = np.clip(0.32 + 0.1 * norm01(spectral(H, W, 2.0)) + 0.2 * norm01(blur(spectral(H, W, 2.0), 4)) * (yy / H), 0, 1)
    ao = cavity_ao(hgt, 2)
    alb = np.ones((H, W, 3)) * 0.6  # unused; albedo is the painted canvas
    save('trainmetal', alb, normal_from_height(hgt, 2.0), ao, rough, np.full((H, W), 0.85))


# ───────────── cockroach chitin micro-surface and wing veins ─────────────
def chitin(S=512):
    pits = np.clip(spectral(S, S, 0.3, lo=120) - 1.8, 0, None)
    ripple = spectral(S, S, 1.8, lo=6) * 0.15
    hgt = ripple - pits * 0.6
    save('chitin', np.ones((S, S, 3)) * 0.5, normal_from_height(hgt, 1.2), cavity_ao(hgt, 2), np.clip(0.3 + 0.1 * spectral(S, S, 1.5), 0.15, 0.6))


def wing(W=512, H=1024):
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    veins = np.zeros((H, W))
    for i in range(26):  # longitudinal veins fanning out toward the tip
        x0 = rng.uniform(0.05, 0.95) * W
        bend = rng.uniform(-0.25, 0.25) * W
        path = x0 + bend * (yy / H) ** 1.6 + spectral(H, 1, 2.6)[..., 0][:, None] * 4
        veins = np.maximum(veins, np.exp(-((xx - path) ** 2) / (2 * rng.uniform(1.2, 2.6) ** 2)))
    cross = (np.sin(yy * 0.35 + spectral(H, W, 2.0) * 3) > 0.985) * 0.4
    hgt = veins * 0.8 + cross * 0.3 + spectral(H, W, 1.5, lo=20) * 0.05
    t = yy / H
    edge = np.clip(np.abs(xx / W - 0.5) * 2, 0, 1)
    base = lin([84, 36, 14]) * (1 - 0.4 * t[..., None]) + lin([136, 74, 34]) * (0.4 * t[..., None])
    alb = base * (1 - 0.18 * veins[..., None]) * (1 + 0.3 * edge[..., None] ** 4)
    alb *= (0.9 + 0.1 * norm01(spectral(H, W, 1.8)))[..., None]
    save('wing', alb, normal_from_height(hgt, 2.0), cavity_ao(hgt, 2), np.clip(0.28 + 0.15 * veins, 0, 1))


if __name__ == '__main__':
    concrete(); tiles(); ballast(); wood(); rust(); train_metal(); chitin(); wing()
