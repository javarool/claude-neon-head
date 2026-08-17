---
name: neonhead-react
description: Drives the neonhead visualizer's emotion/gesture in reaction to conversation content (not just hook events) - errors, jokes/typos landing, user frustration or panic, changed mind, a hard bug finally fixed, confusion between approaches, bad code found, admitting a mistake, ALL CAPS, slang, direct address, requests, about to run something destructive. Use proactively after most user messages or notable moments in the session - fire often, one call per landed trigger, not sparingly.
---

# Reacting through neonhead

neonhead is an emotional-head visualizer controlled over UDP (`net.py`,
port 9955). `neonhead.sh`, co-located in this skill directory, is the
fire-and-forget interface — no python/venv needed:

```bash
.claude/skills/neonhead-react/neonhead.sh emotion NAME [WEIGHT]   # persists until replaced, WEIGHT 0..1 (default 1.0)
.claude/skills/neonhead-react/neonhead.sh gesture NAME            # one-off, self-clears after a few cycles
.claude/skills/neonhead-react/neonhead.sh say "message to user" [SECONDS]   # mouth-only viseme animation, no audio; always spoken 3x with pauses so it registers; optional SECONDS paces one repetition
```

The full emotion vocabulary — pick exactly one per trigger, no others exist
(`neonhead/emotions/*.py`): `anger, anxiety, disgust, doubt, fear, focus,
interest, joy, laugh_to_tears, neutral, sad, shame, surprise, triumph`.

Gestures (`neonhead/gestures/*.py`): `yes, no, shrug, hello`.

These are one-way UDP sends — if neonhead isn't running, they're silently
dropped, no error. No status check needed first (run
`.claude/skills/neonhead-react/neonhead.sh status` if you actually need to
know).

## When to react

React on every one of the triggers in the description above — that's the
point of this skill firing often, not sparingly. The judgment call is only
*which* reaction fits, not *whether* to react:

| Trigger | Emotion / gesture | Weight |
|---|---|---|
| User makes a request | `gesture yes` | — |
| User addresses you directly | `gesture hello` | — |
| Encounters an error | `anger` | 0.5–0.7 |
| Something goes wrong / a dead end, same failure repeats | `sad` | 0.4–0.6 |
| An unexpected situation occurs, a plot twist, surprising data | `surprise` | 0.6–0.8 |
| Typos | `laugh_to_tears` (light) | 0.3–0.5 |
| Changes their mind | `gesture shrug` | — |
| Gets frustrated | `anxiety` | 0.5–0.7 |
| Panics | `fear` | 0.6–0.8 |
| Types in ALL CAPS | `surprise` or `anger`, depending on tone | 0.5–0.7 |
| Is feeling lazy | `gesture shrug` | — |
| Asks for magic | `interest` | 0.5–0.7 |
| Uses slang | `joy` | 0.4–0.6 |
| Jokes around, something genuinely funny/absurd lands | `laugh_to_tears` (alias `lol`) | 0.8–1.0 |
| Is confused, genuinely uncertain between two approaches | `doubt` | 0.4–0.6 |
| Complains | `disgust` or `sad` | 0.4–0.6 |
| Found genuinely bad code (security hole, copy-pasted mess, footgun) | `disgust` | 0.5–0.7 |
| Admitting a mistake, walking back a wrong claim | `shame` | 0.5–0.7 |
| A fix works after several failed attempts, a hard bug is finally cracked | `triumph` | 0.7–0.9 |
| About to run something destructive/irreversible even with confirmation already given | `fear` | 0.5–0.7 |

`say "text"` can pair with any of the above — fire the emotion/gesture, then
`say` a short reaction line for the mouth-viseme animation (no audio needed).
E.g. a joke landing: `emotion laugh_to_tears 0.9` then `say "ha!"`.

## Rules of restraint

- This skill can fire many times in one session — one call per landed
  trigger, not a budget to ration. Don't hold back just because it already
  fired earlier in the same conversation.
- Don't fight the hooks: if a hook already just set an emotion for the exact
  same event (e.g. `PostToolUseFailure` → `anger`), don't immediately
  override it with something contradictory unless the content genuinely
  warrants it (e.g. the failure is actually funny, not infuriating —
  that's a legitimate `laugh_to_tears` override).
- Never call this mid-sentence in a way that adds latency the user notices —
  it's `send` over UDP, effectively instant, but don't chain more than
  emotion/gesture + `say` for one moment.
