"""Everything is generated procedurally in numpy every frame.

No mesh, no glTF, no Blender. Three rings are 3D circles projected to the
screen; the face is a handful of parametric curves. At these vertex counts
(~4k) rebuilding the buffers each frame costs nothing.

Emissive geometry becomes ribbons (screen-space quads with a brightness
profile across their width) and glow dots. Solid geometry — eye whites,
pupils, teeth — is plain triangles that deliberately never reach the bloom
threshold, so they read as objects inside the light rather than more light.
"""

from __future__ import annotations

import math
import numpy as np

TAU = math.tau


# ---------------------------------------------------------------------------
# small 3D helpers
# ---------------------------------------------------------------------------

def _rot(ax: float, ay: float, az: float) -> np.ndarray:
    ca, sa = math.cos(ax), math.sin(ax)
    cb, sb = math.cos(ay), math.sin(ay)
    cc, sc = math.cos(az), math.sin(az)
    rx = np.array([[1, 0, 0], [0, ca, -sa], [0, sa, ca]])
    ry = np.array([[cb, 0, sb], [0, 1, 0], [-sb, 0, cb]])
    rz = np.array([[cc, -sc, 0], [sc, cc, 0], [0, 0, 1]])
    return rz @ ry @ rx


def _circle3(n: int, radius: float) -> np.ndarray:
    t = np.linspace(0.0, TAU, n, endpoint=False)
    return np.stack([np.cos(t) * radius, np.sin(t) * radius, np.zeros(n)], 1)


class Projector:
    """Weak perspective. Returns screen points plus a depth brightness factor."""

    def __init__(self, cx: float, cy: float, scale: float, back_dim: float):
        self.c = np.array([cx, cy], dtype=np.float32)
        self.scale = scale
        self.back_dim = back_dim

    def __call__(self, pts3: np.ndarray):
        z = pts3[:, 2] / max(1e-6, self.scale)
        persp = 1.0 / (1.0 - np.clip(z, -0.95, 0.95) * 0.22)
        xy = pts3[:, :2] * persp[:, None]
        xy = xy * np.array([1.0, -1.0])          # y down in screen space
        screen = xy + self.c
        depth = self.back_dim + (1.0 - self.back_dim) * (z * 0.5 + 0.5)
        return screen.astype(np.float32), depth.astype(np.float32)


# ---------------------------------------------------------------------------
# frame buffers
# ---------------------------------------------------------------------------

class Frame:
    """Accumulates one frame worth of vertices."""

    def __init__(self):
        self.ribbon: list = []   # pos2, side, arc, bright, rgb  -> 8 floats
        self.dots: list = []     # centre2, radius, bright, rgb  -> 7 floats
        self.solid: list = []    # pos2, rgba                    -> 6 floats

    # -- emissive ----------------------------------------------------------

    def add_ribbon(self, pts, width, bright, colour, closed=False, taper=True):
        """`pts` (N,2) screen px. `bright` scalar or (N,). Round-ish caps via taper."""
        pts = np.asarray(pts, dtype=np.float32)
        n = len(pts)
        if n < 2:
            return
        b = np.full(n, float(bright), np.float32) if np.isscalar(bright) \
            else np.asarray(bright, np.float32).copy()

        if closed:
            prev = np.roll(pts, 1, 0)
            nxt = np.roll(pts, -1, 0)
        else:
            if taper:
                # extend both ends and fade them out: a cheap round cap
                d0 = pts[1] - pts[0]
                d1 = pts[-1] - pts[-2]
                d0 = d0 / (np.linalg.norm(d0) + 1e-6)
                d1 = d1 / (np.linalg.norm(d1) + 1e-6)
                pts = np.vstack([pts[0] - d0 * width * 0.55, pts,
                                 pts[-1] + d1 * width * 0.55])
                b = np.concatenate([[0.0], b, [0.0]])
                n += 2
            prev = np.vstack([pts[0], pts[:-1]])
            nxt = np.vstack([pts[1:], pts[-1]])

        d = nxt - prev
        ln = np.linalg.norm(d, axis=1, keepdims=True)
        d = d / np.maximum(ln, 1e-6)
        nrm = np.stack([-d[:, 1], d[:, 0]], 1)
        hw = width * 0.5
        left = pts + nrm * hw
        right = pts - nrm * hw
        arc = np.linspace(0.0, 1.0, n, dtype=np.float32)

        # per-point vertex records for the two rails, then indexed into triangles
        col = np.tile(np.asarray(colour, np.float32), (n, 1))
        vl = np.concatenate([left, np.full((n, 1), -1.0, np.float32),
                             arc[:, None], b[:, None], col], 1)
        vr = np.concatenate([right, np.full((n, 1), 1.0, np.float32),
                             arc[:, None], b[:, None], col], 1)
        i = np.arange(n if closed else n - 1)
        j = (i + 1) % n
        tris = np.empty((len(i), 6, 8), np.float32)
        tris[:, 0] = vl[i]
        tris[:, 1] = vr[i]
        tris[:, 2] = vl[j]
        tris[:, 3] = vr[i]
        tris[:, 4] = vr[j]
        tris[:, 5] = vl[j]
        self.ribbon.append(tris.reshape(-1, 8))

    def add_dot(self, x, y, radius, bright, colour):
        self.dots.extend((x, y, radius, bright, colour[0], colour[1], colour[2]))

    # -- solid -------------------------------------------------------------

    def add_poly(self, pts, colour, alpha=1.0):
        """Convex-ish polygon as a triangle fan around its centroid."""
        pts = np.asarray(pts, dtype=np.float32)
        if len(pts) < 3:
            return
        n = len(pts)
        c = pts.mean(0)
        rgba = np.asarray((*colour, alpha), np.float32)
        verts = np.concatenate([pts, np.tile(rgba, (n, 1))], 1)
        centre = np.concatenate([c, rgba])
        i = np.arange(n)
        j = (i + 1) % n
        tris = np.empty((n, 3, 6), np.float32)
        tris[:, 0] = centre
        tris[:, 1] = verts[i]
        tris[:, 2] = verts[j]
        self.solid.append(tris.reshape(-1, 6))

    def add_strip(self, a, b, colour, alpha=1.0):
        """Quad strip between two equal-length polylines (fans fail on crescents)."""
        a = np.asarray(a, np.float32)
        b = np.asarray(b, np.float32)
        n = min(len(a), len(b))
        if n < 2:
            return
        rgba = np.asarray((*colour, alpha), np.float32)
        va = np.concatenate([a[:n], np.tile(rgba, (n, 1))], 1)
        vb = np.concatenate([b[:n], np.tile(rgba, (n, 1))], 1)
        i = np.arange(n - 1)
        tris = np.empty((n - 1, 6, 6), np.float32)
        tris[:, 0] = va[i]
        tris[:, 1] = vb[i]
        tris[:, 2] = va[i + 1]
        tris[:, 3] = vb[i]
        tris[:, 4] = vb[i + 1]
        tris[:, 5] = va[i + 1]
        self.solid.append(tris.reshape(-1, 6))

    def add_disc(self, x, y, radius, colour, alpha=1.0, segments=24):
        t = np.linspace(0, TAU, segments, endpoint=False)
        self.add_poly(np.stack([x + np.cos(t) * radius, y + np.sin(t) * radius], 1),
                      colour, alpha)

    def arrays(self):
        rib = np.concatenate(self.ribbon) if self.ribbon else np.zeros((0, 8), np.float32)
        sol = np.concatenate(self.solid) if self.solid else np.zeros((0, 6), np.float32)
        dots = np.asarray(self.dots, np.float32).reshape(-1, 7)
        return rib, dots, sol


# ---------------------------------------------------------------------------
# face parts
# ---------------------------------------------------------------------------

def _eye_outline(cx, cy, w, h, gaze, slant, n=26):
    """Flat lower lid, dome above. The apex slides sideways with gaze."""
    t = np.linspace(0.0, 1.0, n)
    x = cx + w * (2.0 * t - 1.0) + gaze * w * 0.30 * np.sin(np.pi * t)
    y = cy - h * np.sqrt(np.clip(1.0 - (2.0 * t - 1.0) ** 2, 0.0, 1.0))
    pts = np.stack([x, y], 1)
    if abs(slant) > 1e-3:
        a = math.radians(slant)
        ca, sa = math.cos(a), math.sin(a)
        rel = pts - np.array([cx, cy])
        pts = np.stack([rel[:, 0] * ca - rel[:, 1] * sa,
                        rel[:, 0] * sa + rel[:, 1] * ca], 1) + np.array([cx, cy])
    return pts.astype(np.float32)


def _chevron(cx, cy, w, h, inward):
    """A sharp '<'/'>' angle in place of the eye dome — disgust's tell.
    `inward` is +1/-1 for the direction the apex points (toward the nose):
    apex sits at cx + inward*w, the two arms open back out to the socket
    edge. One open polyline (not two crossing strokes like `_cross`) so
    the vertex reads as a single sharp corner."""
    apex = [cx + inward * w, cy]
    top = [cx - inward * w * 0.5, cy - h]
    bot = [cx - inward * w * 0.5, cy + h]
    return np.array([top, apex, bot], np.float32)


def _cross(cx, cy, half):
    """Two crossing strokes — the `eye_dead` X, drawn over the collapsed lid."""
    return (
        np.array([[cx - half, cy - half], [cx + half, cy + half]], np.float32),
        np.array([[cx - half, cy + half], [cx + half, cy - half]], np.float32),
    )


def _letter_z(cx, cy, half):
    """A single 'Z' as one open polyline: top bar, diagonal, bottom bar."""
    return np.array([[cx - half, cy - half], [cx + half, cy - half],
                     [cx - half, cy + half], [cx + half, cy + half]], np.float32)


def _drop(cx, cy, size, n=20):
    """Teardrop via cardioid r = a(1 - cos t): cusp at the top, round bulb
    below — the manga "sweat drop" anxiety tell."""
    t = np.linspace(0.0, TAU, n, endpoint=False)
    r = size * 0.5 * (1.0 - np.cos(t))
    x = cx + r * np.cos(t - math.pi / 2)
    y = cy + r * np.sin(t - math.pi / 2)
    return np.stack([x, y], 1).astype(np.float32)


def _tongue(cx, cy, w, h, tilt, n=14):
    """Half an oval — the "blep" tongue poking out of a mouth corner,
    independent of aperture (works on a closed, smiling mouth). Only the
    curved half is traced (t in [0, pi]); `add_poly` closes the polygon
    with a straight chord back to the start, which becomes the flat cut
    edge that sits flush against the lip line."""
    t = np.linspace(0.0, math.pi, n)
    x, y = np.cos(t) * w, np.sin(t) * h
    ca, sa = math.cos(tilt), math.sin(tilt)
    return np.stack([cx + x * ca - y * sa, cy + x * sa + y * ca], 1).astype(np.float32)


def _ring(cx, cy, r, n=32):
    """A thin circle — the `monocle` ring around one eye."""
    t = np.linspace(0.0, TAU, n, endpoint=False)
    return np.stack([cx + np.cos(t) * r, cy + np.sin(t) * r], 1).astype(np.float32)


def _brow(cx, cy, hw, tilt, bend, mirror, n=16):
    """Quadratic arc. `tilt` > 0 drops the inner end — the anger tell."""
    inner_dx = hw if not mirror else -hw
    x0, y0 = cx - inner_dx, cy - tilt * 0.35 * hw      # outer end
    x1, y1 = cx + inner_dx, cy + tilt * 0.75 * hw      # inner end
    mx, my = (x0 + x1) * 0.5, (y0 + y1) * 0.5 - hw * (0.30 + bend * 0.45)
    t = np.linspace(0.0, 1.0, n)[:, None]
    p0 = np.array([[x0, y0]])
    p1 = np.array([[mx, my]])
    p2 = np.array([[x1, y1]])
    return ((1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t ** 2 * p2).astype(np.float32)


def _mouth(cx, cy, half_w, aperture, curve, tilt=0.0, n=22):
    """Lens: upper and lower curve around a bent, optionally skewed centreline.

    `tilt` adds a linear skew across the width — one corner down, the other
    up — for a one-sided smirk/doubt, layered on top of `curve`'s symmetric
    bend.
    """
    t = np.linspace(0.0, 1.0, n)
    x = cx + half_w * (2.0 * t - 1.0)
    bend = -curve * half_w * 0.45
    centre = (cy - bend * np.sqrt(np.clip(1.0 - (2.0 * t - 1.0) ** 2, 0.0, 1.0))
              + tilt * half_w * (2.0 * t - 1.0) * 0.5)
    lift = np.sqrt(np.clip(1.0 - (2.0 * t - 1.0) ** 2, 0.0, 1.0)) * aperture * 0.5
    upper = np.stack([x, centre - lift], 1)
    lower = np.stack([x, centre + lift], 1)
    return upper.astype(np.float32), lower.astype(np.float32)


# ---------------------------------------------------------------------------
# the whole head
# ---------------------------------------------------------------------------

def build(cfg, rig, width_px: int, height_px: int) -> Frame:
    f = Frame()
    p = rig.p
    H = cfg["head"]
    B = cfg["brightness"]
    W = cfg["widths"]
    rgb = cfg.rgb

    R = min(width_px, height_px) * H["radius_frac"]
    ws = R / 246.0            # line widths are authored for a 820 px window
    W = {k: v * ws for k, v in W.items()}
    cx = width_px * 0.5 + p["head_yaw"] * R
    cy = height_px * 0.5 + p["head_pitch"] * R
    proj = Projector(cx, cy, R, B["depth_back"])
    gain = 1.0 + p["glow_gain"]
    spread = max(0.5, p["ring_spread"])
    tilt = math.radians(p["ring_tilt"])

    # ambient spill so the black reads as air rather than emptiness
    f.add_dot(cx, cy, R * 2.6, B["spill"] * gain, rgb["spill"])

    # ---- inner rings: thin and dim, they must never fight the contour ----
    seg = int(H["ring_segments"])
    orientations = (
        (0.20, rig.spin[0], tilt),
        (math.pi / 2 + 0.15, rig.spin[1] * 0.7, tilt),
        (0.75, rig.spin[2], tilt + 0.5),
    )
    for i, (ax, ay, az) in enumerate(orientations):
        pts3 = _circle3(seg, R * spread * (0.98 - i * 0.015)) @ _rot(ax, ay, az).T
        pts, depth = proj(pts3)
        f.add_ribbon(pts, W["rings"], depth * B["rings"] * gain,
                     rgb["rings"], closed=True)

    # ---- outer contour: the only thing allowed to be loud ----
    t = np.linspace(0, TAU, 96, endpoint=False)
    ring = np.stack([cx + np.cos(t) * R * spread, cy + np.sin(t) * R * spread], 1)
    f.add_ribbon(ring, W["contour"], B["contour"] * gain, rgb["contour"], closed=True)

    # ---- orbit and planet: the nose ----
    orb_r = R * max(0.12, H["orbit_r"] + p["orbit_r"])
    orb_y = H["orbit_y"] * R
    orb_m = _rot(math.radians(H["orbit_tilt"]), rig.precession, tilt)
    orbit3 = _circle3(72, orb_r) @ orb_m.T + np.array([0.0, orb_y, 0.0])
    opts, odepth = proj(orbit3)
    f.add_ribbon(opts, W["orbit"], odepth * B["orbit"] * gain, rgb["orbit"], closed=True)

    trail_n = int(cfg["idle"]["trail_points"])
    for k in range(trail_n, -1, -1):
        ph = rig.orbit_phase - k * 0.055
        pt3 = np.array([[math.cos(ph) * orb_r, math.sin(ph) * orb_r, 0.0]]) @ orb_m.T
        pt3 = pt3 + np.array([0.0, orb_y, 0.0])
        (sp,), (dp,) = proj(pt3)
        fade = (1.0 - k / (trail_n + 1.0)) ** 2.2
        if k == 0:
            f.add_dot(sp[0], sp[1], R * 0.055, B["planet"] * dp * gain, rgb["planet"])
            f.add_dot(sp[0], sp[1], R * 0.020, B["planet"] * 1.6 * dp * gain, rgb["core"])
        else:
            f.add_dot(sp[0], sp[1], R * 0.030 * fade,
                      B["trail"] * fade * dp * gain, rgb["planet"])

    # faint core at the centre of the orbit
    f.add_dot(cx, cy * 1.22 + orb_y, R * H["core_r"] * 2,
              B["core"] * p["core_glow"] * gain * 0.35, rgb["core"])

    # ---- eyes ----
    ew = R * H["eye_w"] * p["eye_w"]
    ey = cy + R * H["eye_y"] + p["eye_gaze_y"] * R * 0.02
    sep = R * H["eye_sep"]
    dead = max(0.0, min(1.0, p["eye_dead"]))
    angry = max(0.0, min(1.0, p["eye_angry"]))
    hide = min(1.0, dead + angry)   # either tell replaces the normal eye
    # eye_h_l/_r stack on the shared eye_h, same asymmetry pattern as the
    # brows — one eye can go wide while the other squints (e.g. doubt)
    for sign, side in ((-1.0, "eye_h_l"), (1.0, "eye_h_r")):
        ex = cx + sign * sep
        eh = R * H["eye_dome"] * max(0.02, p["eye_h"] + p[side])
        slant = p["eye_slant"] * (-sign)
        outline = _eye_outline(ex, ey, ew, eh, p["eye_gaze_x"], slant)
        # white sclera first, then the pupil, then the glowing rim — all
        # fade out as eye_dead/eye_angry come in, so a dead/angry eye is
        # X-only or chevron-only, not layered over a closed lid (that's
        # what `sleep` is for)
        if hide < 0.99:
            f.add_poly(outline, rgb["sclera"], 1.0 - hide)
            pr = min(R * H["pupil_r"], eh * 0.42, ew * 0.55)
            if eh > R * H["eye_dome"] * 0.18 and pr > 0.6:
                px = ex + p["eye_gaze_x"] * ew * 0.34
                py = ey - eh * 0.46
                f.add_disc(px, py, pr, rgb["pupil"], 1.0 - hide)
            f.add_ribbon(outline, W["features"], B["features"] * gain * (1.0 - hide),
                         rgb["features"], closed=True)
        # dead: an X fades in in its place, sized off the base eye radius
        # so it doesn't shrink along with the (now-irrelevant) eye_h dome
        if dead > 0.01:
            half = R * H["eye_w"] * 0.42
            for stroke in _cross(ex, ey, half):
                f.add_ribbon(stroke, W["features"], B["features"] * gain * dead,
                             rgb["features"])
        # angry: a sharp '>'/'<' chevron, apex pointing at the nose —
        # disgust's tell. Same off-the-base sizing as the X above.
        if angry > 0.01:
            half = R * H["eye_w"] * 0.42
            chevron = _chevron(ex, ey, half, half * 1.1, -sign)
            f.add_ribbon(chevron, W["features"], B["features"] * gain * angry,
                         rgb["features"], taper=False)
        # monocle: a thin ring on the wide eye only (eye_h_l), the classic
        # "well, I never" gag — doubt's raised-brow side. Centred on the
        # pupil using eye_h_base (pre-blink) rather than eh, so it sits on
        # the socket and doesn't bob with every blink.
        if side == "eye_h_l" and p["monocle"] > 0.01:
            eh_base = R * H["eye_dome"] * max(0.02, p["eye_h_base"] + p[side])
            mx = ex + p["eye_gaze_x"] * ew * 0.34
            my = ey - eh_base * 0.46
            mr = ew * 1.35
            ring = _ring(mx, my, mr)
            f.add_ribbon(ring, W["features"] * 0.5,
                         B["features"] * gain * 0.6 * p["monocle"],
                         rgb["features"], closed=True)
            # dangling chain: hangs from the outer edge of the ring (away
            # from the nose), two ring diameters long
            ox = mx + sign * mr
            chain = np.array([[ox, my], [ox, my + mr * 4.0]], np.float32)
            f.add_ribbon(chain, W["features"] * 0.4,
                         B["features"] * gain * 0.5 * p["monocle"],
                         rgb["features"])

    # ---- brows ----
    bw = R * H["brow_w"]
    by = cy + R * H["brow_y"]
    for sign, suffix, mirror in ((-1.0, "_l", False), (1.0, "_r", True)):
        b = _brow(cx + sign * sep, by - p["brow_y" + suffix] * R * 0.10, bw,
                  p["brow_tilt" + suffix], p["brow_bend" + suffix], mirror)
        f.add_ribbon(b, W["features"], B["features"] * gain, rgb["features"])

    # ---- mouth ----
    mw = R * H["mouth_w"] * (0.60 + 0.80 * p["mouth_w"])
    ap = R * H["mouth_w"] * 1.15 * max(0.0, p["mouth_ap"])
    my = cy + R * H["mouth_y"]
    upper, lower = _mouth(cx, my, mw, ap, p["mouth_curve"], p["mouth_tilt"])
    saw = p["mouth_saw"]
    if saw > 0.01:
        # triangle wave via arcsin(sin(x)): cheap, no extra teeth-shape
        # geometry needed — just ripple the existing lip lines into points,
        # upper biting down and lower biting up. disgust's "bared teeth"
        # tell without an actual teeth mesh. Both use the SAME wave at the
        # SAME x-positions (in phase, not one shifted like sin vs cos) so
        # the two rows of teeth face each other rather than interleaving.
        n = len(upper)
        teeth_n = 4
        wave = np.abs(np.arcsin(np.sin(np.linspace(0.0, teeth_n * math.pi, n))) * (2.0 / math.pi))
        # tooth amplitude pegged to half the eye-chevron size, so the two
        # "sharp tell" shapes on the face read at a matched scale
        chevron_half = R * H["eye_w"] * 0.42
        jag = wave * (chevron_half * 0.75) * saw
        # both rows ride the SAME sign of the wave — teeth pointing one
        # direction, like two parallel saw blades — with a small constant
        # gap between the rows so they don't collapse onto each other
        gap = chevron_half * 0.35 * saw
        upper[:, 1] = upper[:, 1] - gap * 0.5 - jag
        lower[:, 1] = lower[:, 1] + gap * 0.5 - jag
        # drawn as two independent open strokes, not one closed loop
        # stitching top to bottom — a mitered ribbon can't take a sharp
        # zigzag's near-180-degree turns cleanly and braids the two rows
        # together instead of keeping them as parallel lines
        f.add_ribbon(upper, W["features"], B["features"] * gain,
                     rgb["features"], taper=False)
        f.add_ribbon(lower, W["features"], B["features"] * gain,
                     rgb["features"], taper=False)
    else:
        loop = np.vstack([upper, lower[::-1]])

        if ap > R * 0.012:
            f.add_poly(loop, rgb["mouth_dark"], 1.0)
            teeth = p["mouth_smile"]
            alpha = max(0.0, min(1.0, (teeth - 0.45) / 0.35))
            if alpha > 0.01:
                depth_px = min(ap * 0.42, mw * 0.16)
                inner = upper[2:-2]
                if len(inner) > 3:
                    band = inner + np.array([0.0, depth_px], np.float32)
                    f.add_strip(inner, band, rgb["teeth"], alpha)
                    step = max(1, len(inner) // 4)
                    for k in range(step, len(inner) - 1, step):
                        a = inner[k]
                        f.add_poly(np.array([[a[0] - 0.9, a[1]], [a[0] + 0.9, a[1]],
                                             [a[0] + 0.9, a[1] + depth_px],
                                             [a[0] - 0.9, a[1] + depth_px]], np.float32),
                                   rgb["mouth_dark"], alpha)

        f.add_ribbon(loop, W["features"], B["features"] * gain,
                     rgb["features"], closed=True)

    # ---- tongue: a "blep" poking from the right mouth corner, independent
    # of aperture so it reads on a closed, goofy-grin mouth too (dead's
    # tell) rather than requiring the jaw to hang open ----
    tongue = p["tongue"]
    if tongue > 0.01:
        corner = (upper[-1] + lower[-1]) * 0.5
        tw, th = mw * 0.26, mw * 0.40
        # nudge down by one mouth-stroke width so the flat cut edge tucks
        # under the lip line instead of its corner poking through it, and
        # left by one tongue-width so it sits inboard of the mouth corner
        # rather than hanging off the very edge
        shape = _tongue(corner[0] - tw, corner[1] + W["features"] * 3.0, tw, th, -0.35)
        f.add_poly(shape, rgb["tongue"], min(1.0, tongue))
        f.add_ribbon(shape, W["features"] * 0.35,
                     B["features"] * gain * 0.35 * tongue,
                     rgb["features"], closed=True)

    # ---- sweat: a droplet sliding down the temple, anxiety's tell. One
    # cycle = one drip; solid + a faint glowing rim, same "object inside
    # the light" treatment as the teeth/sclera rather than another light
    # source.
    sweat = p["sweat"]
    if sweat > 0.01:
        ph = (rig.t * 0.55) % 1.0
        dx = cx + R * 0.80
        dy = cy - R * 0.60 + ph * R * 1.05
        size = R * 0.075 * (1.0 - 0.2 * ph)
        fade = sweat * min(1.0, ph * 8.0) * min(1.0, (1.0 - ph) * 4.0)
        drop = _drop(dx, dy, size)
        f.add_poly(drop, rgb["core"], fade * 0.85)
        f.add_ribbon(drop, W["features"] * 0.35, B["features"] * gain * fade * 0.4,
                     rgb["features"], closed=True)

    # ---- zzz: three drifting "Z"s, sleep's tell ----
    zzz = p["zzz"]
    if zzz > 0.01:
        for i in range(3):
            ph = (rig.t * 0.35 + i / 3.0) % 1.0
            size = R * (0.045 + 0.02 * i)
            zx = cx + R * 0.40 + ph * R * 0.22
            zy = cy - R * 0.55 - ph * R * 0.30 - i * R * 0.02
            fade = zzz * min(1.0, ph * 6.0) * min(1.0, (1.0 - ph) * 3.0)
            f.add_ribbon(_letter_z(zx, zy, size), W["features"] * 0.75,
                         B["features"] * gain * fade, rgb["features"])
    return f
