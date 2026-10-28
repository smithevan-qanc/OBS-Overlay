NEW LIFE CHURCH · IGLESIA NUEVA VIDA — LIVESTREAM OVERLAY PACK
==============================================================

Open 00-preview-all.html in a browser to see every overlay (switch English / Español).
Every file is 1920x1080 and self-contained (photo and logos are built in).
Keep all the files together in one folder.


ADDING AN OVERLAY IN OBS
------------------------
1. Sources > + > Browser
2. To use options (below): untick "Local file" and paste a file:/// URL, e.g.
     file:///C:/Overlays/03-camera-sermon.html?speaker_name=Pastor+Juan
   With no options you can just tick "Local file" and pick the .html file.
3. Width 1920, Height 1080
4. Tick "Refresh browser when scene becomes active" (replays the animations and
   picks up any URL changes each time you switch to the scene)


THE FILES
---------
01-starting-soon            Full screen: logo, "Starting Soon", countdown.
02-camera-fullscreen        Camera fills the screen; church tag top-left, LIVE top-right.
03-camera-sermon            Camera window 1280x720 at x 70, y 70 + message panel.
04-camera-slides            Camera window 592x333 at x 70, y 70
                            Slides window 1148x646 at x 702, y 70
05-lower-third-speaker      Transparent. Speaker name + title, bottom-left.
06-be-right-back            Full screen.
07-thank-you                Full screen. Optional giving link.
08-lower-third-verse        Transparent. Looks up and shows the Bible verse text.
09-live-graphics            Transparent. Speaker / verse / message graphics that you
                            show and remove live from the control panel (10). Shows the
                            spinning church watermark in the corner when nothing else is up.
10-control-panel            The control panel. Open it in a normal browser, or dock it
                            inside OBS. NOT an overlay.


LIVE CONTROL PANEL (09 + 10)
----------------------------
Show and remove graphics live, control the full-screen screens, switch scenes and
send MIDI to ProPresenter, all through the WebSocket server built into OBS 28+.

1. In OBS: Tools > WebSocket Server Settings > tick "Enable WebSocket server".
   Click "Show Connect Info" to see the port (usually 4455) and the password.
2. Add 09-live-graphics.html as a Browser source (1920x1080) in every scene where
   graphics should be able to appear, at the top of the source list. Untick
   "Local file" and use this URL (with your password):
     file:///C:/Overlays/09-live-graphics.html?obs_password=YOURPASSWORD
   (Right-click > Copy, then Paste (Reference) to put the same source in other scenes.)
3. To control the full-screen screens from the panel, add ?obs_password=YOURPASSWORD
   to their browser-source URLs too:
     file:///C:/Overlays/01-starting-soon.html?obs_password=YOURPASSWORD
     file:///C:/Overlays/06-be-right-back.html?obs_password=YOURPASSWORD
     file:///C:/Overlays/07-thank-you.html?obs_password=YOURPASSWORD
4. Open 10-control-panel.html in Chrome or Edge (needed for MIDI), or as an OBS dock
   (Docks > Custom Browser Docks; no MIDI there). Click "Connection", enter the
   password and click Connect. The top shows "OBS: connected" and "Overlay: connected".
   If you used the old obs-watermark.html as its own source, remove it: the
   live-graphics overlay includes it (same picture, same 30-second spin).

Keep 09-live-graphics.html and the 01/06/07 files in the same folder as the panel
(the panel uses them for its previews). To run the panel on another computer or
tablet on the same network, copy the whole folder there and enter the streaming
computer's IP address (e.g. 192.168.1.20) instead of localhost in Connection.

THE PANEL
  Top bar      always at the top of the window: profile menu, Profiles, MIDI,
               OBS / overlay status, Connection (these open as pop-up windows).
  On screen    the bar under it shows what is on screen right now. The ring counts
               down the auto-remove time; a solid green circle = stays on.
               Remove all (or Esc) removes whatever is on screen.
  Speaker      name + title -> Show now / Remove
  Bible verse  book, chapter, verse, translation -> Look up shows the text first (you
               can edit it); Show now puts it on screen. The verse slides out from
               its green bar and slides back in when removed.
  Message      any line + optional small line. Style: Bottom (lower third) or
               Top (tag, like the church tag on 02-camera-fullscreen).
  Previews     each card shows the graphic itself on a checkerboard (not to scale).
  Position     every card (and the watermark) has Position: Top / Right / Bottom /
               Left in pixels from the edges of the 1920x1080 picture, like CSS.
               Blank = default. Setting Top replaces the default Bottom, etc.
  Saved lists  "Save to list" on each card. Each saved item: Edit (opens a window to
               change it and give it its own MIDI note; "Load into card" copies it
               to the card), Show, and x (delete).
  Full-screen  Starting Soon / Be Right Back / Thank You tabs: language, headline
  screens      (white + green), line under it, giving link, countdown (automatic,
               minutes, to the service time, or none) and service name/day/time.
               "Update screen" changes it in OBS; "Show" also switches OBS to the
               scene you picked for it. Your wording comes back even if OBS reloads.
  OBS scenes   side menu: live Program picture (Live / Off) and a thumbnail for each
               scene; click a scene to put it live (red = live now).
  Watermark    side menu: Auto = shows whenever nothing else is on screen; Off.

MIDI (to ProPresenter or anything else)
  Needs Chrome or Edge, plus a virtual MIDI port: loopMIDI (free, Windows) or the
  IAC Driver (Mac: Audio MIDI Setup > MIDI Studio > IAC Driver > "Device is online").
  In ProPresenter add that port as a MIDI input (Settings > Devices / MIDI map).
  In the panel: MIDI > Turn on MIDI > pick the output.
  ProPresenter uses the NOTE to pick the action and the VELOCITY to pick which item
  (1 = first, 2 = second...). Example: saved verse A = note G-1 velocity 1,
  saved verse B = note G-1 velocity 5.
  - Each action (Show / Remove for each card, Remove all, each full-screen Show)
    can have a note + velocity in the MIDI window. Each saved item can have its own
    note in its Edit window; items without one use their card's Show note.
  - Notes can be names (G-1, C#2) or numbers (0-127). Apps disagree on octave
    numbering: pick "C-1 = note 0" or "C-2 = note 0" so the names match
    ProPresenter (G-1 = 7 or 19). Use Test to check, or just type numbers.
  - Leave a note blank to send nothing.

PROFILES (top bar menu + "Profiles")
  A profile keeps everything you set up: saved speakers, messages and verses (with
  their MIDI notes), what is typed in each card, positions, watermark, full-screen
  screen wording and scene choices, MIDI action notes and panel settings. It starts
  with "English service" and "Servicio en español".
  Export this profile / Export all profiles saves a .json file, which also carries
  this computer's connection and MIDI port (the OBS password only if you tick the
  box). Import… loads files: a profile with the same name is updated, new ones are
  added. Use it to back up, or to set up another computer in one step.
  (Exporting downloads a file, so do it from Chrome/Edge rather than the OBS dock.)

Options for 09-live-graphics:
  obs_password=...   the OBS WebSocket password (leave off if authentication is off)
  obs_port=4455      only if you changed the port in OBS
  obs_host=localhost only if OBS runs on a different computer than the overlay
  channel=main       only needed for two separately controlled setups;
                     set the same channel in the panel's Connection
  watermark=off      start with the watermark off (the panel can switch it)
  debug=1            shows a small connection status box (for setup only)
The same obs_password / obs_port / obs_host / channel options work on 01, 06, 07.

Verse lookups need internet on the computer running the panel. If a lookup fails,
type the verse into the text box and press Show now.


HOW OPTIONS WORK
----------------
Add options to the end of the file URL: start with ? and join more with &.
Use + (or %20) for spaces.   Example:  ?speaker_name=Pastor+Juan&verse=John+3:16

  - Set any option to  null  to hide it:          ?city=null
  - Options marked "hidden unless set" only appear when you give them a value.
  - Options with a default show the default unless you change it or set it to null.


ALL OPTIONS
-----------
Option          Example                     Default                 Used on
--------------  --------------------------  ----------------------  -----------------
GENERAL
lang            es                          en (English)            all
key             off                         magenta                 02 03 04
                (off = transparent windows, or green / blue / any hex like 00b140)
type            off                         on                      01 06 07
                (off = headline appears instantly instead of typing in)

CHURCH
church_name     New+Life+Church             New Life Church /       02 04 06 07
                                            Iglesia Nueva Vida
city            Atlantic                    Atlantic                02 03 04 06 07
state           Iowa                        Iowa                    02 03 04 06 07

SERVICE
service_day     Sunday                      Sunday / Domingo        01 03 04 06 07
service_time    10:30+AM                    10:30 AM                01 03 04 06 07
                (also accepts 24-hour, e.g. 18:30)
service_name    Worship+Service             Worship Service /       03 04 06 07
                                            Servicio de adoración

MESSAGE  (hidden unless set)
speaker_name    Pastor+John+Smith           —                       03 04 05
speaker_title   Lead+Pastor                 —                       03 04 05
message_title   Grace+Upon+Grace            —                       03 04
series_name     The+Gospel+of+John          —                       03 04
book            John                        —                       03 04 08
                (English or Spanish names and abbreviations: Juan, 1+Cor, Ps)
chapter         3                           —                       03 04 08
verse           16   or  16-18  or  16,18   —                       03 04 08
                (leave verse off to show the whole chapter)
                book + chapter are both needed; 03/04 show the reference,
                08 also looks up the verse text
reference       John+3:16                   —                       03 04 08
                (shortcut: the whole reference in one option instead of
                book / chapter / verse)
translation     NIV                         KJV  (Spanish: RV1960)  03 04 08
verse_text      For+God+so+loved...         —                       08
                (your own verse text; skips the online lookup)

SCREEN TEXT  (override the built-in wording)
headline        Merry                       Starting / Be Right /   01 06 07
                                            Thanks for
headline2       Christmas                   Soon / Back /           01 06 07
                                            Joining Us
subtitle        See+you+soon                (line under headline)   06 07
give_url        yourwebsite.org/give        — (hidden unless set)   07

COUNTDOWN (01)
minutes         10                          —                       01
                (counts down 10 minutes from when the scene loads)
countdown       off                         auto                    01
                Auto: if you set service_time, it counts down to that time today.
                If not, it only appears during the hour before Sunday 10:30 AM.
                With no countdown, three pulsing dots show instead.

SHOW / HIDE PIECES
hold            8                           stays on                05 08
                (slides away after 8 seconds)
church_tag      off                         on                      02
live_tag        off                         on                      02
corner          off                         on                      02

Older option names still work: name, role, title, series, scripture, time, give,
church, bug, livetag. An old-style full reference in verse (verse=John+3:16) also
still works.


BIBLE VERSE LOOKUP (08-lower-third-verse)
-----------------------------------------
Needs internet. The verse text is fetched from bolls.life; for KJV, WEB and BBE it
falls back to bible-api.com if bolls.life is unavailable.

Books: English or Spanish names and common abbreviations all work:
  book=John   book=Juan   book=1+Cor   book=Ps   book=Romans   book=Jhn

Translation codes are the ones bolls.life uses. Common ones:
  English: KJV, NKJV, NIV, ESV, NLT, NASB, CSB, WEB
  Spanish: RV1960, NVI, LBLA, NTV
If a translation doesn't load, try another code or use verse_text.

The last verse that loaded successfully is remembered, so it still shows if the
internet drops later. If a lookup fails with nothing remembered, the box shows the
reference only.

Note on copyright: KJV, WEB and RV1909 are public domain. Most modern translations
(NIV, ESV, NLT, RV1960...) allow use in church services and livestreams within limits.
Check the publisher's terms if you show a lot of scripture.


CAMERA WINDOWS — TWO WAYS TO USE THEM
-------------------------------------
The windows are filled with MAGENTA (#FF00FF). Magenta is used instead of green
so the church's green never gets keyed out.

A) OBS (easiest): add  key=off  to the URL. The windows become truly transparent,
   no chroma key filter needed. Put the overlay ABOVE your camera / slides in the
   source list and size the camera to fit the window.

B) Chroma key (vMix, ATEM, ProPresenter, OBS etc.): leave it magenta, put the
   overlay ABOVE the camera, add a Chroma Key filter to the overlay,
   Key Color Type = Magenta (or Custom #FF00FF).


EXAMPLES
--------
Spanish sermon layout, transparent windows:
  03-camera-sermon.html?lang=es&key=off&speaker_name=Pastor+Juan&message_title=Gracia+sobre+gracia&book=Juan&chapter=1&verse=16

Speaker lower third that leaves after 8 seconds:
  05-lower-third-speaker.html?speaker_name=Pastor+John+Smith&speaker_title=Lead+Pastor&hold=8

Verse lower third in the NIV:
  08-lower-third-verse.html?book=Romans&chapter=8&verse=28&translation=NIV

Starting Soon counting down to a 6:00 PM special service:
  01-starting-soon.html?service_time=6:00+PM


FONTS
-----
Headlines use Oswald from Google Fonts (needs internet). Without internet the
pages fall back to a similar condensed font.
