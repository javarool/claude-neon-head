---
name: neonhead-emotion-authoring
description: How to add or edit a neonhead emotion (or gesture) - rig channels, the "owned channel" gotcha, naming conventions, and the live test loop (restart, trigger, ask the user). Use whenever adding a new emotion/gesture file, tuning an existing PRESET, or adding a new rig param/geometry feature for an emotion.
---

# Authoring neonhead emotions

Distilled from the session that added `dead`, `sleep`, reworked `surprise`/
`anxiety`/`disgust`/`doubt`, and fixed several silently-dead preset keys.
Read this before touching `neonhead/emotions/*.py`, `neonhead/rig.py`, or
`neonhead/geometry.py` for an emotion.

## The shape of a change

1. **Preset-only tweak** (numbers already work): edit the `PRESET` dict in
   `neonhead/emotions/<name>.py`. Nothing else to touch — the file is
   auto-discovered by `neonhead/emotions/__init__.py` (`pkgutil.iter_modules`).
2. **New emotion**: copy the shape of an existing file — `NAME`, `ALIASES`
   (Russian aliases welcome, folded lowercase), `PRESET` (offsets from
   `rig.NEUTRAL`). Add a one-line comment above `PRESET` explaining *why*
   each unusual value is there (see any existing file for the density
   expected — this codebase explains why, not what).
3. **New visual capability** (e.g. an X-eye, a monocle, darting gaze) needs
   a new rig channel — see below, this is the part that's easy to get wrong.

## The "owned channel" gotcha — check this before adding any preset key

Some `rig.p` keys are **fully overwritten** every frame by prosody/idle
logic, *after* the emotion-offset loop runs:

```python
p = dict(NEUTRAL)
for k, v in emo.items():
    p[k] = p.get(k, 0.0) + v      # <- emotion offsets land here first
...
p["mouth_ap"] = ...                # <- then THIS overwrites it — dead code
```

If a preset sets one of these keys directly, it silently does **nothing** —
no error, no visual effect, just wasted numbers. Known owned keys in
`rig.Rig.update`:

| Owned key | Owned by | Use instead |
|---|---|---|
| `mouth_ap` | visemes (speech) | `mouth_open` (adds on top) |
| `mouth_w` | visemes (speech) | `mouth_narrow` (adds on top) |
| `core_glow` | prosody formula from `glow_gain` | `glow_gain` |
| `head_yaw` | idle sway | `head_tilt` (adds on top) |
| `eye_h` (final) | blink collapse | fine to set, but blink multiplies it — see `eye_h_base` below for anything that must NOT move on blink |

**Before wiring a new preset key to an existing rig param**, grep
`rig.py`'s `update()` for `p["your_key"] =` (plain `=`, not `+=`) appearing
*after* the `for k, v in emo.items()` loop. If you find one, don't reuse
that key from a preset — add a new `..._<verb>` channel to `NEUTRAL` that
the owning formula adds in (grep `emo.get("glow_gain"` for the pattern to
copy). Comment the channel's docstring/inline comment with *why* it needs
to be separate — future readers hit the same trap otherwise.

## Naming and value conventions

- Most `NEUTRAL` entries are **offset-from-zero**: `brow_y_l: 0.0`,
  `mouth_curve: 0.05`, `eye_slant: 0.0`. Preset deltas are typically
  0.1–0.6.
- A few are **baseline-around-1.0 multipliers**: `ring_spread`, `eye_h`,
  `eye_w`, `orbit_speed`, `blink_rate`. A preset offset of `+1.0` on
  `orbit_speed` doubles it (baseline 1.0 + 1.0 = 2.0×) — say what multiple
  you're aiming for in a comment, it's not obvious from the number alone.
- Left/right suffixes (`_l`/`_r`) always mean: `_l` = `sign == -1.0` in
  geometry's per-feature loop, `_r` = `sign == +1.0`. Established by the
  brow loop; eyes (`eye_h_l`/`eye_h_r`) follow the same mapping. Anything
  new with a left/right pair should match it.
- `eye_h_base` exists specifically for geometry that must ignore blink (the
  monocle ring) — it's `eye_h` captured *before* the blink collapse is
  applied, so use it instead of `eye_h` for anything anchored to the eye
  socket rather than the eyelid.

## Where things live

- `neonhead/rig.py` — `NEUTRAL` dict (declare every new param here or
  `set_params`/overrides/smoothing won't recognize it), `Rig.update()`
  (per-frame math, where "owned channel" formulas live), `CHANNEL_SPEED`/
  `OVERSHOOT_CHANNELS` (per-channel blend timing — optional, only if a
  feature needs to lead/lag/overshoot like brows do).
- `neonhead/geometry.py` — turns `rig.p` into vertex data. New shapes
  (crosses, rings, letters) are small helper functions near `_eye_outline`/
  `_brow`/`_mouth` (see `_cross`, `_ring`, `_letter_z` for the pattern),
  then drawn from inside `build()`.
- `neonhead/emotions/<name>.py` — the preset itself.
- `README.md` — has a hand-maintained list of emotion names in the
  "Emotions:" line; update it when adding a new one (the plugin scan picks
  it up automatically for the demo/hotkeys, but the README list is prose,
  not generated).

## Test loop — always live, never guess

There's no unit test for "does this look right" — visual judgement is the
user's, not something to assume from reading the numbers. Screenshotting
the window yourself is **not** the workflow here (the user asked for this
explicitly) — trigger the emotion and ask them to look and describe it.

1. Find and kill the running instance:
   ```bash
   ps aux | grep '[r]un\.py'        # bracket trick: doesn't match itself
   kill <pid>
   ```
   Don't use `pkill -f "python run.py"` — the pattern also matches this
   very shell invocation's own command-line text (it's substring-matched
   against `/proc/*/cmdline`), so it can kill the wrapper that's running
   your command and produce a confusing signal-based exit code.
2. Restart it detached so it survives the tool call returning:
   ```bash
   setsid env DISPLAY=:0 venv/bin/python /path/to/run.py \
     > /tmp/nh.log 2>&1 < /dev/null &
   disown
   sleep 2
   ps aux | grep '[r]un\.py'   # confirm the new pid came up
   cat /tmp/nh.log             # confirm no traceback on import
   ```
3. Trigger the emotion and say its name out loud in the reply:
   ```bash
   venv/bin/python client.py emotion <name>
   ```
   Then ask: "Включил эмоцию: **name**. Как выглядит?" — wait for the
   answer before iterating further. Re-sending `emotion neutral` then the
   target again forces a fresh blend if you want to see the transition
   replay rather than a static end state.
4. Iterate on the preset/geometry, restart, retrigger, ask again. Don't
   batch multiple unreviewed changes — the user is rating one visual
   change at a time.
