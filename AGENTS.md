# AGENTS.md: New Life Church livestream overlays

OBS livestream graphics for **New Life Church / Iglesia Nueva Vida** (Atlantic, Iowa). The project is bilingual (EN/ES).
It produces self-contained HTML files that run as OBS **Browser sources** (1920×1080) from `file://`.
It also produces a **control panel** web page that drives them live through the **OBS WebSocket (v5, OBS 28+)**.
The panel can send **MIDI** (e.g. to ProPresenter).

## Golden rules

1. **Never hand-edit `dist/`.** It is generated. Edit `build.py`, `src/` or `assets/`, then run `python build.py`.
2. After any change: **build, then run the tests** (see Testing). Keep them passing, and add a test for new behaviour.
3. **Every user customization made in the control panel must live in the active profile.** That way it survives export/import. Exception: per-computer settings go in `DEV`.
   - When you add a setting, add it to `cleanProfile()` (with a default) and make sure `switchProfile()` re-renders it.
   - Check that it appears in the exported JSON.
4. Every output file stays **one self-contained HTML file**:
   - Images are embedded as data URIs, with no build-time dependencies at runtime.
   - The only network use is Google Fonts (with a fallback font) and the Bible APIs.
5. Keep **English and Spanish** working for every user-facing string on overlays. The panel UI itself is English.
6. User-facing wording: buttons say **"Show"**, never "Display". Keep plain, non-technical language in the panel and README; the user is a church volunteer.

## Layout

```
build.py                    # the whole generator (CSS/JS/HTML as Python strings) -> dist/
src/panel_template.html     # control panel source (placeholders filled by build.py)
src/static/README.txt       # end-user guide (copied to dist/ as-is) - keep it in sync with features
src/static/00-preview-all.html  # gallery page of all overlays (copied as-is)
assets/                     # church-photo.jpg, logo-circle.png, wordmark.svg (from wordmark-original.svg),
                            # watermark-parts.json (img/mask/svg pulled from obs-watermark-original.html),
                            # logo-bracket.png (reference only)
tests/                      # Playwright tests (mock OBS, mock Bible API, fake Web MIDI); screenshots -> tests/out/
dist/                       # GENERATED: what the user puts on the streaming PC (zip it for delivery)
```

Setup: `pip install pillow playwright && python -m playwright install chromium`.
Build: `python build.py`. Release: zip `dist/` as `New-Life-Church-Overlays.zip` (folder name `New-Life-Church-Overlays/`).

## Output files (dist/)

| File | What | Built in `build.py` section |
|---|---|---|
| 01-starting-soon | Full screen: wordmark, typed "Starting Soon", countdown or pulsing dots | `# 01 Starting Soon` (+ `COUNTDOWN_JS`, `screen_js('starting')`) |
| 02-camera-fullscreen | Magenta key window full frame; church tag (top-left), LIVE tag, corner bracket | `# 02 Full-screen camera` |
| 03-camera-sermon | Camera window 1280×720 @ (70,70) + message panel | `# 03 Sermon / 04 Camera + Slides` |
| 04-camera-slides | Camera 592×333 @ (70,70) + slides 1148×646 @ (702,70) | same |
| 05-lower-third-speaker | Static speaker lower third (URL options) | `# 05 Lower third – speaker` |
| 06-be-right-back / 07-thank-you | Side layout + service bar; live-controllable | `# 06 … / 07 …` (`SIDE_CSS`, `side_body`) |
| 08-lower-third-verse | Static verse lower third; looks the verse up online | `# 08 Lower third – Bible verse` |
| 09-live-graphics | Transparent overlay driven by the panel: speaker, verse, message (bottom lower third or top tag), watermark | `# 09 Live graphics` (`LIVE_CSS`, `LIVE_JS`, `LIVE_BODY`) |
| 10-control-panel | The control panel (normal page / OBS dock), not an overlay | `src/panel_template.html` |

## How `build.py` works

- `page(fname, title, css, body, js, i18n, stage_bg, note, params, head_js)` writes one overlay.
  - It wraps `BASE_CSS` + page CSS, `body` inside `<div id="stage">` (fixed 1920×1080 and scaled to the window by `fit()`), then `I18N`, `PARAMS`, `BASE_JS` and page JS.
  - The placeholders `__PHOTO__`, `__LOGO__` and `__WORDMARK__` are replaced with data URIs or SVG.
  - It **asserts that no `__` remains** in the output. Don't introduce `__` in content; embedded base64 must not contain it.
- **Text system (`BASE_JS`):**
  - `[data-t="key"]` is filled from the URL option `?key=` (via `PARAMS`: aliases and EN/ES defaults), from `COMPUTED` (`location`, `verse_ref`), or from fixed `I18N` labels.
  - A value of `null` or empty hides the element. A `[data-group]` hides when all its text is hidden, or when the keys it lists in `data-group="a b"` are all empty.
  - Message details (speaker, title, series, verse…) are hidden unless set. Church and service details have defaults.
- **Headline typing:** only `.title [data-t]` types in, at 75 ms per character with no cursor. `.after-type` elements fade in once typing finishes. `?type=off` turns typing off.
- **Shared JS strings:**
  - `BIBLE_JS`: book parser (EN/ES names and abbreviations), `BIBLE.lookup(ref, tr, lang)` and `buildRef`/`sizeFor`. Lookups use bolls.life first, then bible-api.com for KJV/WEB/BBE, and are cached in localStorage.
  - `OBS_JS`: `OBSWS.create({...})` is a minimal obs-websocket v5 client with a pure-JS SHA-256 for auth, reconnect with backoff, `request` and `broadcast`. It also defines `NLC_APP = 'nlc-overlays'`.
  - `SCREEN_HEAD`/`SCREEN_JS`: live control for 01/06/07.
  - `COUNTDOWN_JS`, `VERSE_JS` and `LIVE_JS` are page-specific.
- **Key colour:** camera/slide windows are `.win` with `--key` (magenta `#FF00FF` by default; `?key=off|green|blue|hex`). Magenta is used because the brand is green.

## Live control protocol (panel ⇄ overlay ⇄ screens)

Everything travels as **OBS `BroadcastCustomEvent`** (`CustomEvent`, event subscription bit 1).

- **Message envelope:** every message carries `{app:'nlc-overlays', channel, role, from, action, …}`.
  - `role` is `panel`, `overlay` (09) or `screen` (01/06/07). OBS echoes broadcasts back to the sender, so always filter by `role`/`from`.
  - `channel` (default `main`) separates independent setups.
- **Panel → overlay:**
  - `show` `{graphic: speaker|verse|message, data, hold}`. `data.pos` = `{top,right,bottom,left}` px. `data.position` = `bottom|top` for message.
  - `hide` `{graphic?}` (no graphic = all)
  - `watermark` `{mode: auto|off, pos}`
  - `ping`
  - `state` `{to, showing:{graphic,data,remaining}, watermark, watermarkPos}`, sent in reply to the overlay's `hello`
- **Overlay → panel:**
  - `hello` on connect
  - `status` `{showing:{graphic,data,hold,remaining}|null, watermark}` after every change and on `ping`
- **Panel → screen:** `screen` `{screen: starting|brb|thanks, settings, rev, to?}`.
  - The screen page **reloads itself** with `location.replace(nlcScreenURL(Q, {settings, rev}))`. It keeps `obs_*`, `channel` and `key`, and adds the settings as URL options plus `rev`.
  - It caches `{settings, rev}` in localStorage (`nlc-screen:<screen>:<channel>`). The `<head>` script redirects to the cached settings when OBS reloads the plain URL.
  - `?obs=off` = preview mode (no connection, no redirect).
- **Screen → panel:** `hello` and `status` `{screen, rev}`. On `hello` the panel re-sends the last *applied* settings if the `rev` differs.
- **Countdown options on 01:**
  - `until=<epoch ms>` comes from the panel's "minutes" mode.
  - `minutes=`
  - `service_time=` (explicit = always count down unless `countdown=auto`)
  - `countdown=off|auto`
- Only one graphic is on screen at a time; `show` swaps. The overlay keeps `hold` timers and reports `remaining`, so the panel's countdown ring and a reloaded overlay stay in sync.
- The watermark shows only when nothing is on screen and the mode is `auto`.

## Control panel (`src/panel_template.html`)

- **Top bar** (`.top`, `position: fixed; top:0; left:0; right:0`): profile menu, Profiles, MIDI, OBS/overlay status pills, Connection. These open **`<dialog>` modals**.
  - Under it sits the separate **On screen** banner with a countdown ring: it drains for auto-remove and is a solid circle for "stay on".
  - `--stick` (set by a ResizeObserver) offsets the layout below the fixed area.
- **Cards:**
  - Speaker, Message (style Bottom/Top + saved list) and Bible verse (lookup, editable text, saved list).
  - Each card has a cropped **preview**. The iframe loads `09-live-graphics.html?preview=1`, the content arrives by `postMessage('nlc-preview')`, and the iframe reports its height with `nlc-preview-size`. The background is a checkerboard.
  - Each card also has a **Position** box: Top/Right/Bottom/Left px, with defaults in `DEFPOS`.
    - `DEFPOS` must match the overlay CSS defaults: speaker L90/B110, verse L180/B90, message L90/B110, messageTop L60/T56, watermark R15/B15.
    - Setting one side of an axis clears the default opposite side (`place()` in `LIVE_JS`).
- **Full-screen screens card:** tabs for starting/brb/thanks.
  - It has a 16:9 preview iframe of the real page with `obs=off`, wording, countdown, service info and the OBS scene to switch to.
  - **Update screen** applies the settings; **Show** applies them and runs `SetCurrentProgramScene`.
- **Side menu:**
  - Program preview: `GetSourceScreenshot` every 1 s, toggleable.
  - Scene thumbnails: every 10 s.
  - Scene buttons: `SetCurrentProgramScene`.
  - Watermark mode and position.
- **Keyboard:** Esc removes everything, unless a dialog is open or an input is focused.
- **Storage** (all access wrapped in try/catch):
  - `nlc-panel:profiles`: `{active, list:[profile]}`
  - `nlc-panel:device`: this computer's `DEV`: `host, port, pw, channel, midiOn, midiOut, naming`
  - Legacy keys `form`, `verses`, `lookedUp` and `conn` are migrated on first load.
- **Profile shape:** see `cleanProfile()`. It has:
  - `form` (card inputs + `m-pos`), `speakers[]`, `messages[]`, `verses[]` (each item may have `midi:{note,vel,ch}`), `lookedUp`
  - `positions{}`, `watermark`, `midi{channel, actions{}}`
  - `screens{starting,brb,thanks,service}` (each has `applied:{settings,rev}`, `scene`)
  - `ui{programPreview, screenTab}`
  - Defaults are "English service" and "Servicio en español".
- **Export file:** `{app:'nlc-live-graphics', type:'profiles', version:2, device, profiles[]}`. The OBS password is included only when the checkbox is ticked.
- **Import:** matches profiles by `id`, then by name (case-insensitive) and replaces the match; otherwise it adds. It also applies `device`.
- **MIDI** (Web MIDI; Chrome/Edge only, not available in the OBS dock):
  - Each send is note-on then note-off after 120 ms.
  - `ACTIONS` keys: `show:<graphic>`, `remove:<graphic>`, `remove:all`, `screen:<name>`.
  - A saved item's own `midi` overrides the card's `show:` mapping.
  - Note names honour `DEV.naming`: `c-1` means C-1 = 0, so G-1 = 7; `c-2` means G-1 = 19. Plain numbers are accepted too.
  - ProPresenter convention: the note picks the action, the velocity picks the item (1-based). Velocity 0 means note-off in MIDI, so default to 1.

## Design system

- Colours: black `#000`/`#0b0b0b`, white `#f7f7f7`, muted `rgba(247,247,247,.7)`, brand green **`#8EC641`**.
  - The panel uses a dark UI (`--bg #0c0c0c`, `--panel #151515`), red `#ff5b4f` for live/remove and amber for warnings.
- Type: **Oswald** 500/700 uppercase for display text, with fallbacks `Bebas Neue`, `Arial Narrow`, `Impact`. **Inter** for body text.
- Motifs: the green "bracket" (the 1 of the N logo: top arm + right leg), a thin green rule, and the circular N logo.
- The B&W photo of the Atlantic theatre (the church building) is used on full screens.
- Motion:
  - Lower thirds: the logo block fades in, then the text wipes out from behind the green edge.
  - Verse: the green bar grows, then the text wipes out of it, and the reverse on exit.
  - Top tag: drops in.
  - Watermark: photo-in-N with a spin+flip every 30 s (user's original animation, keep it).

## Testing

Run from `tests/`. Each script prints PASS/FAIL lines and `errors [...]` (page JS errors; must be empty).

- `python test_live_control.py`: about 60 checks against a **mock OBS** (`context.route_web_socket`, real v5 handshake + auth, CustomEvent fan-out, scenes, screenshots) and a **mocked bolls.life**.
  - Covers overlay ⇄ panel show/hide/hold/restore-after-reload, profiles, saved lists, previews, the countdown ring, scene switching, wrong password, channel isolation and phone width.
- `python test_panel_features.py`: about 40 checks.
  - Covers the fixed top bar, modals, "Show" wording and scene previews.
  - Covers **MIDI** (fake `navigator.requestMIDIAccess`: note names, per-item vs action notes, Remove all), positions on the real overlay and watermark position.
  - Covers full-screen screen control (apply, scene switch, survives reload) and that export/import carries everything, plus password opt-in.
- `python test_static_overlays.py`: smoke test of 08/03/05/07 URL options and the verse lookup fallbacks. It prints what is visible; read the output.

Known noise: Playwright may print `KeyError: 'code'` tracebacks when mocked sockets close. Ignore them.

Full-page screenshots can show blank iframes that are off-screen (throttled); check with viewport screenshots instead.

## Gotchas

- **OBS browser sources** reload on scene activation if "Refresh browser when scene becomes active" is ticked. The design relies on `hello` → `state`, or on cached screen settings, to restore.
- **`file://`:** use `postMessage(..., '*')` between the panel and its preview iframes. localStorage is per-origin; all `file://` pages share it in Chrome, and OBS keeps its own.
- **Auth failure** closes with code `4009`. The client retries every 10 s and the panel opens the Connection dialog.
- **Bible APIs** are third-party with no key; always keep the typed-text fallback (`verse_text` / editable textarea).
  - Translation codes are bolls.life codes. Spanish `RV1960` also tries `RVR1960`.
- **Changing a default position or size** in overlay CSS means updating `DEFPOS` in the panel and the README too.
- **New panel controls** must be added to the profile (rule 3), the README "THE PANEL" section, and a test.
- **Watermark source:** `assets/obs-watermark-original.html` is the user's original. `assets/watermark-parts.json` holds its `img` (JPEG data URI), `mask` (SVG data URI) and `svg` (outline markup). If the user sends a new watermark, re-extract those three parts.
