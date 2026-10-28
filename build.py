#!/usr/bin/env python3
"""Builds the New Life Church livestream overlay pack (self-contained HTML files) into dist/.
Run: python build.py   (see AGENTS.md)"""
import base64, io, json, os, shutil
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / 'assets'
SRC = ROOT / 'src'
OUT = str(ROOT / 'dist') + os.sep
os.makedirs(OUT, exist_ok=True)

# ---------- embedded assets ----------
def b64img(img, fmt, **kw):
    buf = io.BytesIO(); img.save(buf, fmt, **kw)
    return f'data:image/{fmt.lower()};base64,' + base64.b64encode(buf.getvalue()).decode()

PHOTO = b64img(Image.open(ASSETS / 'church-photo.jpg').convert('L'), 'JPEG', quality=82)
LOGO = b64img(Image.open(ASSETS / 'logo-circle.png').resize((256, 256), Image.LANCZOS), 'PNG', optimize=True)
WORDMARK = (ASSETS / 'wordmark.svg').read_text(encoding='utf-8')

# ---------- shared CSS ----------
BASE_CSS = r"""
:root {
  --green: #8EC641; --white: #f7f7f7; --muted: rgba(247,247,247,.7); --ink: #000;
  --key: #FF00FF;
  --display: 'Oswald', 'Bebas Neue', 'Arial Narrow', Impact, sans-serif;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { width: 100%; height: 100%; background: transparent; overflow: hidden; }
#stage {
  position: absolute; left: 50%; top: 50%; width: 1920px; height: 1080px; overflow: hidden;
  color: var(--white); font-family: 'Inter', system-ui, sans-serif;
}
.display { font-family: var(--display); text-transform: uppercase; }
.green { color: var(--green); }
.muted { color: var(--muted); }
.hide { display: none !important; }

/* Keyable window: camera / slides go behind this in OBS */
.win { position: absolute; background: var(--key); }

/* Logo-style green bracket (top arm + right leg) */
.bracket { position: absolute; }
.bracket::before, .bracket::after { content: ""; position: absolute; background: var(--green); right: 0; top: 0; }
.bracket::before { width: 100%; height: var(--t, 20px); }
.bracket::after  { width: var(--t, 20px); height: 100%; }
.bracket.bl::before, .bracket.bl::after { right: auto; top: auto; left: 0; bottom: 0; }

/* Dark photo background used by full-screen layouts */
.bgphoto { position: absolute; inset: -40px; background: url("__PHOTO__") center 40% / cover no-repeat; animation: drift 70s ease-in-out infinite alternate; }
@keyframes drift { from { transform: scale(1.05); } to { transform: scale(1.15) translate(-24px,-12px); } }

.live {
  display: inline-flex; align-items: center; gap: 12px; padding: 10px 20px 10px 16px;
  background: #0b0b0b; font-family: var(--display); font-weight: 500; font-size: 26px; letter-spacing: 3px; text-transform: uppercase;
}
.live i { width: 14px; height: 14px; border-radius: 50%; background: #ff3b30; animation: livepulse 1.4s ease-in-out infinite; }
@keyframes livepulse { 0%,100% { opacity: 1; } 50% { opacity: .25; } }

.pulse { display: flex; gap: 16px; }
.pulse span { width: 18px; height: 18px; background: var(--green); animation: blink 1.6s ease-in-out infinite; }
.pulse span:nth-child(2) { animation-delay: .25s; } .pulse span:nth-child(3) { animation-delay: .5s; }
@keyframes blink { 0%,100% { opacity: .2; transform: scale(.8); } 50% { opacity: 1; transform: none; } }

@keyframes fade { from { opacity: 0; transform: translateY(18px); } to { opacity: 1; transform: none; } }
@keyframes grow { from { width: 0; } }
.in  { animation: fade .9s ease both; }
.tw tw-c { opacity: 0; }
.tw tw-c.on { opacity: 1; }

"""

# ---------- shared JS ----------
BASE_JS = r"""
const Q = new URLSearchParams(location.search);
const LANG = (Q.get('lang') || 'en').toLowerCase().startsWith('es') ? 'es' : 'en';
document.documentElement.lang = LANG;

/* Key colour for camera/slide windows: ?key=magenta (default) | green | blue | off (transparent) | any hex e.g. key=00b140 */
(function () {
  const k = (Q.get('key') || 'magenta').toLowerCase();
  const named = { magenta: '#FF00FF', pink: '#FF00FF', green: '#00FF00', blue: '#0000FF', off: 'transparent', none: 'transparent', transparent: 'transparent' };
  const v = named[k] || (/^[0-9a-f]{6}$/.test(k) ? '#' + k : '#FF00FF');
  document.documentElement.style.setProperty('--key', v);
})();

const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const isOff = v => v == null || v.trim() === '' || /^(null|none|off)$/i.test(v.trim());

/* Fixed labels (not URL options) */
function T(k) { return (I18N[LANG] && I18N[LANG][k] != null) ? I18N[LANG][k] : (I18N.en[k] || ''); }

/* URL options. Returns null when the option is set to null (or empty), or has no default.
   raw=true gives plain text; otherwise HTML-safe. */
function P(k, raw) {
  const spec = PARAMS[k] || {};
  for (const name of [k, ...(spec.alias || [])]) {
    if (Q.has(name)) { const v = Q.get(name); return isOff(v) ? null : (raw ? v.trim() : esc(v.trim())); }
  }
  const d = spec.def;
  if (d == null) return null;
  const v = typeof d === 'object' ? (d[LANG] != null ? d[LANG] : d.en) : d;
  return v === '' ? null : v;
}

/* Bible reference from ?book= ?chapter= ?verse= (e.g. John / 3 / 16-18 -> "John 3:16-18").
   ?reference=John+3:16 (or an old-style full reference in ?verse=) also works. */
function REF(raw) {
  const full = P('reference', raw) || ((P('verse', true) || '').match(/[a-z\u00c0-\u024f]/i) ? P('verse', raw) : null);
  if (full) return full;
  const b = P('book', raw), c = P('chapter', raw), v = P('verse', raw);
  if (!b || !c) return null;
  return b + ' ' + c.replace(/\s+/g, '') + (v ? ':' + v.replace(/\s+/g, '') : '');
}

/* Values built from several options */
const COMPUTED = {
  location: () => [P('city'), P('state')].filter(Boolean).join(', ') || null,
  verse_ref: () => { const v = REF(); if (!v) return null; const tr = P('translation'); return tr ? v + ' &middot; ' + tr : v; },
};
function V(k) {
  if (COMPUTED[k]) return COMPUTED[k]();
  if (k in PARAMS) return P(k);
  const t = T(k); return t === '' ? null : t;
}

/* Fill every [data-t]; hide what has no value. A [data-group] hides when all its text is hidden,
   or, if it names keys (data-group="message_title"), when all those keys are empty. */
document.querySelectorAll('[data-t]').forEach(el => {
  const v = V(el.dataset.t);
  if (v == null) { el.classList.add('hide'); el.dataset.empty = '1'; } else el.innerHTML = v;
});
document.querySelectorAll('[data-group]').forEach(g => {
  const keys = (g.dataset.group || '').trim();
  const empty = keys ? keys.split(/\s+/).every(k => V(k) == null)
                     : [...g.querySelectorAll('[data-t]')].every(e => e.dataset.empty);
  if (empty) g.classList.add('hide');
});

const stage = document.getElementById('stage');
function fit() { const s = Math.min(innerWidth / 1920, innerHeight / 1080); stage.style.transform = `translate(-50%, -50%) scale(${s})`; }
addEventListener('resize', fit); fit();

/* Typewriter: only the big headline (.title) types in; everything else fades in.
   Text marked .after-type fades in once the headline has finished. ?type=off turns typing off. */
(function () {
  if (Q.get('type') === 'off') return;
  const els = [...document.querySelectorAll('.title [data-t]')].filter(e => !e.closest('.hide') && e.textContent.trim());
  if (!els.length) return;
  const SPEED = 75;
  let start = 400;
  els.forEach(el => {
    const chars = [...el.textContent];
    el.textContent = ''; el.classList.add('tw');
    const spans = chars.map(ch => { const s = document.createElement('tw-c'); s.textContent = ch; el.appendChild(s); return s; });
    spans.forEach((s, j) => setTimeout(() => s.classList.add('on'), start + j * SPEED));
    start += spans.length * SPEED + 200;
  });
  document.querySelectorAll('.after-type').forEach(e => e.style.animationDelay = start + 'ms');
})();

/* ?hold=8 : slide/fade the overlay away after 8 seconds */
(function () {
  const hold = parseFloat(Q.get('hold'));
  const el = document.querySelector('[data-hold]');
  if (el && hold > 0) setTimeout(() => el.classList.add('out'), hold * 1000);
})();
"""

# URL options shared by every overlay. 'def' = default (per language or single); no def = hidden unless set.
PARAMS = {
    'church_name':   {'alias': ['church'], 'def': {'en': 'New Life Church', 'es': 'Iglesia Nueva Vida'}},
    'city':          {'def': 'Atlantic'},
    'state':         {'def': 'Iowa'},
    'service_day':   {'def': {'en': 'Sunday', 'es': 'Domingo'}},
    'service_time':  {'alias': ['time'], 'def': '10:30 AM'},
    'service_name':  {'def': {'en': 'Worship Service', 'es': 'Servicio de adoración'}},
    'speaker_name':  {'alias': ['speaker', 'name']},
    'speaker_title': {'alias': ['role']},
    'message_title': {'alias': ['title']},
    'series_name':   {'alias': ['series']},
    'book':          {'alias': ['bible_book']},
    'chapter':       {},
    'verse':         {},
    'reference':     {'alias': ['scripture', 'bible_verse']},
    'translation':   {'alias': ['bible_translation'], 'def': {'en': 'KJV', 'es': 'RV1960'}},
    'verse_text':    {},
    'give_url':      {'alias': ['give']},
}

COMMON_I18N = {
    'en': {'live': 'Live', 'msglabel': "Today's Message"},
    'es': {'live': 'En vivo', 'msglabel': 'Mensaje de hoy'},
}

TIMES_HTML = """
<div class="times" data-group>
  <div><b class="display"><span data-t="service_day"></span> <em data-t="service_time"></em></b><span data-t="service_name"></span></div>
</div>"""

WHERE_INNER = '<div data-group><strong data-t="church_name"></strong><span data-t="location"></span></div>'

def page(fname, title, css, body, js='', i18n=None, stage_bg='transparent', note='', params=None, head_js=''):
    d = {l: dict(COMMON_I18N[l], **((i18n or {}).get(l, {}))) for l in ('en', 'es')}
    pp = dict(PARAMS, **(params or {}))
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<!-- New Life Church livestream overlay · 1920x1080 · {note} -->{head_js}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Oswald:wght@500;700&family=Inter:wght@400;600&display=swap" rel="stylesheet">
<style>{BASE_CSS}
#stage {{ background: {stage_bg}; }}
{css}</style>
</head>
<body>
<div id="stage">
{body}
</div>
<script>
const I18N = {json.dumps(d, ensure_ascii=False)};
const PARAMS = {json.dumps(pp, ensure_ascii=False)};
{BASE_JS}
{js}
</script>
</body>
</html>"""
    html = html.replace('__PHOTO__', PHOTO).replace('__LOGO__', LOGO).replace('__WORDMARK__', WORDMARK)
    assert '__' not in html.replace('__proto__', ''), fname
    open(OUT + fname, 'w', encoding='utf-8').write(html)


# ---------- Bible lookup library (used by 08, 09, 10) ----------
BIBLE_JS = r"""
const BIBLE = (() => {
  function norm(s) { return String(s).normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/^(i{1,3})\s+/, m => String(m.trim().length)).replace(/[^a-z0-9]/g, ''); }
  const BOOKS = "Genesis|Génesis|gen ge gn;Exodus|Éxodo|exod exo ex;Leviticus|Levítico|lev le lv;Numbers|Números|num nu nm nb;Deuteronomy|Deuteronomio|deut de dt;Joshua|Josué|josh jos;Judges|Jueces|judg jdg jue;Ruth|Rut|rth ru;1 Samuel|1 Samuel|1sam 1sa 1s;2 Samuel|2 Samuel|2sam 2sa 2s;1 Kings|1 Reyes|1kgs 1ki 1re 1r;2 Kings|2 Reyes|2kgs 2ki 2re 2r;1 Chronicles|1 Crónicas|1chr 1ch 1cr;2 Chronicles|2 Crónicas|2chr 2ch 2cr;Ezra|Esdras|ezr esd;Nehemiah|Nehemías|neh ne;Esther|Ester|esth est;Job|Job|jb;Psalms|Salmos|psalm ps psa pss sal salmo;Proverbs|Proverbios|prov pr prv;Ecclesiastes|Eclesiastés|eccl ecc qoh ec;Song of Solomon|Cantares|song sos songofsongs cant cnt;Isaiah|Isaías|isa is;Jeremiah|Jeremías|jer je;Lamentations|Lamentaciones|lam la;Ezekiel|Ezequiel|ezek eze ez;Daniel|Daniel|dan da dn;Hosea|Oseas|hos os;Joel|Joel|jl;Amos|Amós|am;Obadiah|Abdías|obad ob abd;Jonah|Jonás|jon;Micah|Miqueas|mic mi;Nahum|Nahúm|nah na;Habakkuk|Habacuc|hab;Zephaniah|Sofonías|zeph zep sof;Haggai|Hageo|hag;Zechariah|Zacarías|zech zec zac;Malachi|Malaquías|mal;Matthew|Mateo|matt mt mat;Mark|Marcos|mrk mk mr;Luke|Lucas|luk lk lc;John|Juan|jhn jn;Acts|Hechos|act ac hch;Romans|Romanos|rom ro rm;1 Corinthians|1 Corintios|1cor 1co;2 Corinthians|2 Corintios|2cor 2co;Galatians|Gálatas|gal ga;Ephesians|Efesios|eph ef;Philippians|Filipenses|phil php flp fil;Colossians|Colosenses|col;1 Thessalonians|1 Tesalonicenses|1thess 1th 1ts;2 Thessalonians|2 Tesalonicenses|2thess 2th 2ts;1 Timothy|1 Timoteo|1tim 1ti;2 Timothy|2 Timoteo|2tim 2ti;Titus|Tito|tit;Philemon|Filemón|phlm phm flm;Hebrews|Hebreos|heb he;James|Santiago|jas jm stg;1 Peter|1 Pedro|1pet 1pe 1p;2 Peter|2 Pedro|2pet 2pe 2p;1 John|1 Juan|1jn 1jo;2 John|2 Juan|2jn 2jo;3 John|3 Juan|3jn 3jo;Jude|Judas|jud;Revelation|Apocalipsis|rev re rv apoc ap revelations"
    .split(';').map((b, i) => { const [en, es, al] = b.split('|'); return { n: i + 1, en, keys: [en, es, ...al.split(' ')].map(norm) }; });

  function parse(r) {
    const m = String(r || '').trim().match(/^(.+?)\s*(\d+)\s*(?:[:.]\s*([\d\s,\-–—]+))?$/);
    if (!m) return null;
    const key = norm(m[1]);
    let book = BOOKS.find(b => b.keys.includes(key));
    if (!book && key.replace(/^\d/, '').length >= 3) book = BOOKS.find(b => b.keys.some(k => k.startsWith(key)));
    if (!book) return null;
    const verses = [];
    (m[3] || '').split(',').forEach(part => {
      const [a, b] = part.split(/[\-–—]/).map(x => parseInt(x, 10));
      if (!isNaN(a)) for (let v = a; v <= (isNaN(b) ? a : b) && v < a + 200; v++) verses.push(v);
    });
    return { book: book.n, en: book.en, ch: +m[2], verses, spec: (m[3] || '').replace(/\s+/g, '').replace(/[–—]/g, '-') };
  }

  const clean = s => { const d = document.createElement('div');
    d.innerHTML = String(s).replace(/<S>\s*\d+\s*<\/S>/gi, '').replace(/<sup[^>]*>.*?<\/sup>/gi, '').replace(/<br\s*\/?>/gi, ' ');
    return d.textContent.replace(/\s+/g, ' ').trim(); };

  async function getJSON(url) {
    const c = new AbortController(), t = setTimeout(() => c.abort(), 8000);
    try { const r = await fetch(url, { signal: c.signal }); if (!r.ok) throw new Error(r.status); return await r.json(); }
    finally { clearTimeout(t); }
  }

  async function fetchText(p, TR) {
    const codes = [...new Set([TR, TR.replace(/^RVR(?=\d)/, 'RV'), TR.replace(/^RV(?=\d)/, 'RVR')])];
    for (const code of codes) {
      try {
        const data = await getJSON(`https://bolls.life/get-text/${encodeURIComponent(code)}/${p.book}/${p.ch}/`);
        if (Array.isArray(data) && data.length) {
          const want = p.verses.length ? new Set(p.verses) : null;
          const txt = data.filter(v => !want || want.has(+v.verse)).sort((a, b) => a.verse - b.verse).map(v => clean(v.text)).join(' ');
          if (txt) return txt;
        }
      } catch (e) { console.warn('bolls.life lookup failed', code, e); }
    }
    if (['KJV', 'WEB', 'BBE'].includes(TR)) {
      try {
        const q = `${p.en} ${p.ch}${p.spec ? ':' + p.spec : ''}`;
        const data = await getJSON(`https://bible-api.com/${encodeURIComponent(q)}?translation=${TR.toLowerCase()}`);
        const txt = (data.verses || []).map(v => clean(v.text)).join(' ') || clean(data.text || '');
        if (txt) return txt;
      } catch (e) { console.warn('bible-api.com lookup failed', e); }
    }
    return null;
  }

  const defaultTr = lang => (lang === 'es' ? 'RV1960' : 'KJV');

  /* lookup("John 3:16", "NIV") -> verse text, or null. Remembers successful lookups for offline use. */
  async function lookup(ref, tr, lang) {
    const TR = String(tr || defaultTr(lang)).trim().toUpperCase();
    const key = 'verse:' + TR + ':' + String(ref).trim().toLowerCase();
    let cached = null; try { cached = localStorage.getItem(key); } catch (e) {}
    const p = parse(ref);
    if (!p) { console.warn('Could not read verse reference:', ref); return cached; }
    const txt = await fetchText(p, TR);
    if (txt) { try { localStorage.setItem(key, txt); } catch (e) {} }
    return txt || cached;
  }

  function buildRef(book, chapter, verse) {
    book = String(book || '').trim(); chapter = String(chapter || '').replace(/\s+/g, ''); verse = String(verse || '').replace(/\s+/g, '');
    if (!book || !chapter) return '';
    return book + ' ' + chapter + (verse ? ':' + verse : '');
  }

  /* Font size for the verse box, by text length */
  const sizeFor = n => (n < 160 ? 38 : n < 300 ? 34 : n < 450 ? 30 : 26);

  return { parse, lookup, buildRef, defaultTr, sizeFor };
})();
"""

VERSE_JS = r"""
/* Looks up the verse online (bolls.life, then bible-api.com for public-domain English).
   ?verse_text= skips the lookup. Last successful lookups are remembered for offline use. */
(function () {
  const box = document.getElementById('sc'), textEl = document.getElementById('vtext');
  const ref = REF(true);
  const override = P('verse_text', true);
  if (!ref && !override) return;
  const trQ = Q.has('translation') ? Q.get('translation') : Q.get('bible_translation');
  function show(text) {
    if (text) { textEl.textContent = text; textEl.style.fontSize = BIBLE.sizeFor(text.length) + 'px'; }
    else textEl.classList.add('hide');
    box.classList.add('ready');
  }
  if (override) return show(override);
  BIBLE.lookup(ref, isOff(trQ) ? null : trQ, LANG).then(show);
})();
"""

# ---------- OBS WebSocket (v5) client, used by 09 and 10 ----------
OBS_JS = r"""
const OBSWS = (() => {
  /* SHA-256 (for the OBS password handshake) */
  function sha256(bytes) {
    const K = new Uint32Array([0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2]);
    const H = new Uint32Array([0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19]);
    const l = bytes.length, n = ((l + 9 + 63) >> 6) << 6, m = new Uint8Array(n);
    m.set(bytes); m[l] = 0x80;
    const dv = new DataView(m.buffer);
    dv.setUint32(n - 4, (l * 8) >>> 0); dv.setUint32(n - 8, Math.floor(l / 0x20000000));
    const W = new Uint32Array(64), r = (x, k) => (x >>> k) | (x << (32 - k));
    for (let o = 0; o < n; o += 64) {
      for (let i = 0; i < 16; i++) W[i] = dv.getUint32(o + i * 4);
      for (let i = 16; i < 64; i++) { const a = W[i - 15], b = W[i - 2];
        W[i] = (W[i - 16] + (r(a, 7) ^ r(a, 18) ^ (a >>> 3)) + W[i - 7] + (r(b, 17) ^ r(b, 19) ^ (b >>> 10))) >>> 0; }
      let [a, b, c, d, e, f, g, h] = H;
      for (let i = 0; i < 64; i++) {
        const t1 = (h + (r(e, 6) ^ r(e, 11) ^ r(e, 25)) + ((e & f) ^ (~e & g)) + K[i] + W[i]) >>> 0;
        const t2 = ((r(a, 2) ^ r(a, 13) ^ r(a, 22)) + ((a & b) ^ (a & c) ^ (b & c))) >>> 0;
        h = g; g = f; f = e; e = (d + t1) >>> 0; d = c; c = b; b = a; a = (t1 + t2) >>> 0;
      }
      H[0] += a; H[1] += b; H[2] += c; H[3] += d; H[4] += e; H[5] += f; H[6] += g; H[7] += h;
    }
    const out = new Uint8Array(32), ov = new DataView(out.buffer);
    for (let i = 0; i < 8; i++) ov.setUint32(i * 4, H[i]);
    return out;
  }
  const enc = s => new TextEncoder().encode(s);
  const b64 = u => btoa(String.fromCharCode(...u));
  const authString = (pw, salt, challenge) => b64(sha256(enc(b64(sha256(enc(pw + salt))) + challenge)));

  /* create({host, port, password, subs, onStatus(status), onEvent(type, data), onReady()})
     status: connecting | connected | disconnected | auth-failed */
  function create(o) {
    let ws = null, ready = false, stopped = true, retry = null, delay = 1000, seq = 0;
    const pending = new Map();
    const status = s => o.onStatus && o.onStatus(s);
    function schedule(ms) { clearTimeout(retry); if (stopped) return; retry = setTimeout(open, ms || delay); delay = Math.min(delay * 2, 10000); }
    function open() {
      clearTimeout(retry);
      try { ws = new WebSocket(`ws://${o.host || 'localhost'}:${o.port || 4455}`); }
      catch (e) { status('disconnected'); return schedule(); }
      status('connecting');
      const sock = ws;
      sock.onmessage = ev => {
        let m; try { m = JSON.parse(ev.data); } catch (e) { return; }
        if (m.op === 0) {
          const ident = { op: 1, d: { rpcVersion: 1, eventSubscriptions: o.subs == null ? 1 : o.subs } };
          if (m.d && m.d.authentication) ident.d.authentication = authString(o.password || '', m.d.authentication.salt, m.d.authentication.challenge);
          sock.send(JSON.stringify(ident));
        } else if (m.op === 2) {
          ready = true; delay = 1000; status('connected'); o.onReady && o.onReady();
        } else if (m.op === 5) {
          o.onEvent && o.onEvent(m.d.eventType, m.d.eventData || {});
        } else if (m.op === 7) {
          const p = pending.get(m.d.requestId); if (!p) return;
          pending.delete(m.d.requestId);
          const st = m.d.requestStatus || {};
          st.result ? p.res(m.d.responseData || {}) : p.rej(new Error(st.comment || ('OBS error ' + st.code)));
        }
      };
      sock.onclose = ev => {
        if (sock !== ws) return;
        ready = false;
        pending.forEach(p => p.rej(new Error('disconnected'))); pending.clear();
        status(ev.code === 4009 ? 'auth-failed' : 'disconnected');
        schedule(ev.code === 4009 ? 10000 : null);
      };
    }
    function request(type, data) {
      return new Promise((res, rej) => {
        if (!ready) return rej(new Error('not connected'));
        const id = 'r' + (++seq); pending.set(id, { res, rej });
        ws.send(JSON.stringify({ op: 6, d: { requestType: type, requestId: id, requestData: data || {} } }));
        setTimeout(() => { if (pending.has(id)) { pending.delete(id); rej(new Error('timeout')); } }, 5000);
      });
    }
    return {
      connect() { stopped = false; delay = 1000; if (ws) { const old = ws; ws = null; try { old.close(); } catch (e) {} } open(); },
      close() { stopped = true; clearTimeout(retry); ready = false; if (ws) { const old = ws; ws = null; try { old.close(); } catch (e) {} } status('disconnected'); },
      request,
      broadcast: data => request('BroadcastCustomEvent', { eventData: data }),
      get ready() { return ready; },
    };
  }
  return { create, sha256, authString };
})();
const NLC_APP = 'nlc-overlays';
"""

# ---------- Full-screen screens controlled from the panel (01, 06, 07) ----------
SCREEN_HEAD = r"""
<script>
/* Rebuild this page's URL with settings sent from the control panel (keeps the OBS connection options). */
window.nlcScreenURL = function (Q, c) {
  var out = new URLSearchParams();
  ['obs_host', 'obs_port', 'obs_password', 'channel', 'key'].forEach(function (k) { if (Q.has(k)) out.set(k, Q.get(k)); });
  var s = (c && c.settings) || {};
  Object.keys(s).forEach(function (k) { if (s[k] !== '' && s[k] != null) out.set(k, String(s[k])); });
  out.set('rev', c.rev);
  return location.pathname + '?' + out.toString();
};
/* If OBS reloads this page with its plain URL, go straight back to the last settings from the panel. */
(function () {
  var Q = new URLSearchParams(location.search);
  if (Q.get('obs') === 'off' || Q.has('rev')) return;
  var c = null;
  try { c = JSON.parse(localStorage.getItem('nlc-screen:__SCREEN__:' + (Q.get('channel') || 'main')) || 'null'); } catch (e) {}
  if (c && c.rev) location.replace(window.nlcScreenURL(Q, c));
})();
</script>"""

SCREEN_JS = r"""
/* Live control from 10-control-panel: ?obs_password=...  (?obs=off = preview, no connection) */
(function () {
  const SCREEN = '__SCREEN__', CH = Q.get('channel') || 'main', REV = Q.get('rev') || '';
  if (Q.get('obs') === 'off') return;
  const ME = 'screen-' + Math.random().toString(36).slice(2, 8);
  const KEY = 'nlc-screen:' + SCREEN + ':' + CH;
  function apply(settings, rev) {
    if (!rev || rev === REV) return;
    const c = { settings: settings || {}, rev };
    try { localStorage.setItem(KEY, JSON.stringify(c)); } catch (e) {}
    location.replace(window.nlcScreenURL(Q, c));
  }
  const say = (action, extra) => client.broadcast(Object.assign({ app: NLC_APP, channel: CH, role: 'screen', screen: SCREEN, from: ME, action, rev: REV }, extra || {})).catch(() => {});
  const client = OBSWS.create({
    host: Q.get('obs_host') || 'localhost', port: Q.get('obs_port') || 4455, password: Q.get('obs_password') || '', subs: 1,
    onReady: () => say('hello'),
    onEvent: (type, d) => {
      if (type !== 'CustomEvent' || !d || d.app !== NLC_APP || d.channel !== CH || d.role !== 'panel') return;
      if (d.action === 'screen' && d.screen === SCREEN && (!d.to || d.to === ME)) apply(d.settings, d.rev);
      else if (d.action === 'ping') say('status');
    },
  });
  client.connect();
})();
"""

def screen_js(name):
    return OBS_JS + SCREEN_JS.replace('__SCREEN__', name)
def screen_head(name):
    return SCREEN_HEAD.replace('__SCREEN__', name)

# =====================================================================
# Countdown (01)
# =====================================================================
COUNTDOWN_JS = r"""
/* Countdown target:
   ?minutes=10      -> 10 minutes from when the scene loads
   ?service_time=.. -> that time today (when it is still ahead)
   otherwise        -> the default service (Sunday 10:30 AM), only during the hour before it
   ?countdown=off   -> never */
(function () {
  function parseTime(s) {
    const m = String(s || '').trim().match(/^(\d{1,2})(?::(\d{2}))?\s*(a|p)?\.?\s*m?\.?$/i);
    if (!m) return null;
    let h = +m[1]; const min = +(m[2] || 0), ap = (m[3] || '').toLowerCase();
    if (ap === 'p' && h < 12) h += 12; if (ap === 'a' && h === 12) h = 0;
    return h < 24 && min < 60 ? [h, min] : null;
  }
  function dayIndex(s) {
    const n = String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();
    const names = [['sunday','domingo'],['monday','lunes'],['tuesday','martes'],['wednesday','miercoles'],['thursday','jueves'],['friday','viernes'],['saturday','sabado']];
    const i = names.findIndex(p => p.some(x => n && x.startsWith(n.slice(0, 3)))); return i < 0 ? null : i;
  }
  if (Q.get('countdown') === 'off') return;
  const now = new Date(); let target = null;
  const mins = parseFloat(Q.get('minutes')), until = parseFloat(Q.get('until'));
  if (until > now.getTime()) target = new Date(until);
  else if (mins > 0) target = new Date(now.getTime() + mins * 60000);
  else {
    const hm = parseTime(P('service_time', true));
    if (hm) {
      const t = new Date(now); t.setHours(hm[0], hm[1], 0, 0);
      const explicit = (Q.has('service_time') || Q.has('time')) && Q.get('countdown') !== 'auto';
      const day = dayIndex(P('service_day', true));
      const diff = (t - now) / 60000;
      if (explicit ? diff > 0 : (diff > 0 && diff <= 60 && (day == null || day === now.getDay()))) target = t;
    }
  }
  if (!target) return;
  document.getElementById('countdown').classList.remove('hide');
  document.getElementById('pulse').classList.add('hide');
  const start = Date.now(), clock = document.getElementById('clock'), bar = document.getElementById('progress');
  function tick() {
    const left = Math.max(0, Math.round((target - Date.now()) / 1000));
    const h = Math.floor(left / 3600), m = Math.floor(left % 3600 / 60), s = left % 60;
    clock.textContent = (h ? h + ':' + String(m).padStart(2, '0') : String(m).padStart(2, '0')) + ':' + String(s).padStart(2, '0');
    const total = (target - start) / 1000; bar.style.width = (total > 0 ? Math.min(100, (1 - left / total) * 100) : 100) + '%';
  }
  tick(); setInterval(tick, 1000);
})();
"""

PULSE = '<div class="pulse" id="pulse"><span></span><span></span><span></span></div>'
HEADLINE = '<h1 class="title" data-group><span data-t="headline"></span><br><span class="t2" data-t="headline2"></span></h1>'

def headline_params(en1, en2, es1, es2, sub_en=None, sub_es=None):
    d = {'headline': {'def': {'en': en1, 'es': es1}}, 'headline2': {'def': {'en': en2, 'es': es2}}}
    if sub_en is not None: d['subtitle'] = {'def': {'en': sub_en, 'es': sub_es}}
    return d

# =====================================================================
# 01 Starting Soon (simple)
# =====================================================================
SIMPLE_CSS = r"""
.photo { position: absolute; top: -40px; bottom: -40px; left: 600px; right: -40px;
  background: url("__PHOTO__") center 40% / cover no-repeat; filter: contrast(1.05) brightness(.82);
  animation: drift 60s ease-in-out infinite alternate; }
.shade { position: absolute; inset: 0; background: linear-gradient(90deg, #000 0%, #000 31%, rgba(0,0,0,.55) 46%, rgba(0,0,0,.18) 70%, rgba(0,0,0,.45) 100%); }
.side-bracket { right: 90px; top: 90px; width: 200px; height: 560px; --t: 62px; animation: fade 1.4s cubic-bezier(.2,.8,.2,1) both .3s; }
.content { position: absolute; left: 150px; top: 0; bottom: 0; width: 1000px; display: flex; flex-direction: column; justify-content: center; }
.wordmark { width: 230px; margin-bottom: 70px; } .wordmark svg { width: 100%; height: auto; display: block; }
.title { font-family: var(--display); font-weight: 700; text-transform: uppercase; font-size: 160px; line-height: .95; letter-spacing: 2px; }
html[lang=es] .title { font-size: 136px; }
.title .t2 { color: var(--green); }
.extra { margin-top: 56px; min-height: 84px; }
.clock { font-family: var(--display); font-weight: 500; font-size: 84px; line-height: 1; font-variant-numeric: tabular-nums; }
.progress { position: absolute; left: 0; bottom: 0; height: 8px; width: 0; background: var(--green); transition: width 1s linear; }
"""
page('01-starting-soon.html', 'Starting Soon', SIMPLE_CSS, f"""
<div class="photo"></div><div class="shade"></div>
<div class="bracket side-bracket"></div>
<div class="content">
  <div class="wordmark in">__WORDMARK__</div>
  {HEADLINE}
  <div class="extra in after-type" style="animation-delay:1.6s">
    <div class="countdown hide" id="countdown"><div class="clock" id="clock">00:00</div></div>
    {PULSE}
  </div>
</div>
<div class="progress" id="progress"></div>
""", COUNTDOWN_JS + screen_js('starting'), stage_bg='#000', note='full screen · controllable from 10-control-panel',
     params=headline_params('Starting', 'Soon', 'Comenzamos', 'Pronto'), head_js=screen_head('starting'))

# =====================================================================
# 06 Be Right Back / 07 Thank You (side layout with service bar)
# =====================================================================
SIDE_CSS = r"""
.photo { position: absolute; top: -40px; bottom: -40px; left: 600px; right: -40px;
  background: url("__PHOTO__") center 40% / cover no-repeat; filter: contrast(1.05) brightness(.82);
  animation: drift 60s ease-in-out infinite alternate; }
.shade { position: absolute; inset: 0; background:
  linear-gradient(90deg, #000 0%, #000 31%, rgba(0,0,0,.55) 46%, rgba(0,0,0,.18) 70%, rgba(0,0,0,.45) 100%),
  linear-gradient(0deg, rgba(0,0,0,.85) 0%, rgba(0,0,0,0) 32%); }
.side-bracket { right: 90px; top: 90px; width: 200px; height: 560px; --t: 62px; animation: fade 1.4s cubic-bezier(.2,.8,.2,1) both .3s; }
.content { position: absolute; left: 150px; top: 110px; width: 900px; }
.wordmark { width: 250px; animation-delay: .1s; } .wordmark svg { width: 100%; height: auto; display: block; }
.rule { width: 140px; height: 6px; background: var(--green); margin: 46px 0 30px; animation: grow 1s cubic-bezier(.2,.8,.2,1) both .6s; }
.title { font-family: var(--display); font-weight: 700; text-transform: uppercase; font-size: 150px; line-height: .95; letter-spacing: 2px; }
html[lang=es] .title { font-size: 128px; }
.title .t2 { color: var(--green); }
.subtitle { margin-top: 22px; font-family: var(--display); font-weight: 500; font-size: 32px; letter-spacing: 5px; text-transform: uppercase; color: var(--muted); animation-delay: .8s; }
.extra { margin-top: 40px; animation-delay: 1s; }
.bar { position: absolute; left: 0; right: 0; bottom: 0; height: 128px; display: flex; align-items: center; justify-content: space-between;
  padding: 0 150px; border-top: 1px solid rgba(255,255,255,.12); background: rgba(0,0,0,.55); backdrop-filter: blur(6px); animation-delay: 1.2s; }
.times div { font-size: 26px; color: var(--muted); }
.times b { display: block; font-weight: 500; font-size: 30px; color: var(--white); letter-spacing: 1px; }
.times em { font-style: normal; color: var(--green); }
.where { display: flex; align-items: center; gap: 22px; margin-left: auto; }
.where img { width: 76px; height: 76px; border-radius: 50%; background: #000; box-shadow: 0 0 0 2px rgba(255,255,255,.18); }
.where div { text-align: right; font-size: 24px; color: var(--muted); line-height: 1.35; }
.where strong { display: block; color: var(--white); font-weight: 600; font-size: 26px; }
.barlabel { position: absolute; left: 150px; top: -46px; font-family: var(--display); font-size: 24px; letter-spacing: 4px; text-transform: uppercase; color: var(--green); }
"""

def side_body(extra, barlabel=False):
    return f"""
<div class="photo"></div><div class="shade"></div>
<div class="bracket side-bracket"></div>
<div class="content">
  <div class="wordmark in">__WORDMARK__</div>
  <div class="rule"></div>
  {HEADLINE}
  <p class="subtitle in after-type" data-t="subtitle"></p>
  <div class="extra in after-type">{extra}</div>
</div>
<div class="bar in">
  {'<div class="barlabel" data-t="barlabel" data-group="service_day service_time service_name"></div>' if barlabel else ''}
  {TIMES_HTML}
  <div class="where">{WHERE_INNER}<img src="__LOGO__" alt=""></div>
</div>"""

page('06-be-right-back.html', 'Be Right Back', SIDE_CSS, side_body(PULSE), screen_js('brb'), stage_bg='#000', note='full screen · controllable from 10-control-panel', head_js=screen_head('brb'),
     params=headline_params('Be Right', 'Back', 'Volvemos', 'Enseguida',
                            'Stay with us &mdash; back in a moment', 'Quédate con nosotros'))

page('07-thank-you.html', 'Thank You', SIDE_CSS + r"""
.give { display: flex; align-items: baseline; gap: 18px; }
.givelabel { font-family: var(--display); font-size: 28px; letter-spacing: 4px; text-transform: uppercase; color: var(--green); }
.giveurl { font-size: 40px; font-weight: 600; }
.title { font-size: 124px; white-space: nowrap; } html[lang=es] .title { font-size: 118px; }
""", side_body('<div class="give" data-group="give_url"><span class="givelabel" data-t="givelabel"></span><span class="giveurl" data-t="give_url"></span></div>', barlabel=True), screen_js('thanks'),
     stage_bg='#000', note='full screen · controllable from 10-control-panel', head_js=screen_head('thanks'),
     i18n={'en': {'barlabel': 'Join us again', 'givelabel': 'Give online'},
           'es': {'barlabel': 'Acompáñanos de nuevo', 'givelabel': 'Ofrenda en línea'}},
     params=headline_params('Thanks for', 'Joining Us', 'Gracias por', 'Estar Aquí',
                            'God bless you &mdash; see you next time', 'Dios te bendiga &mdash; nos vemos pronto'))

# =====================================================================
# 02 Full-screen camera
# =====================================================================
page('02-camera-fullscreen.html', 'Camera – Full Screen', r"""
.bug { position: absolute; left: 60px; top: 56px; display: flex; align-items: center; gap: 18px;
  padding: 12px 28px 12px 12px; background: #0b0b0b; border-left: 8px solid var(--green); }
.bug img { width: 84px; height: 84px; border-radius: 50%; display: block; }
.bug strong { display: block; font-family: var(--display); font-weight: 500; font-size: 30px; letter-spacing: 2px; text-transform: uppercase; }
.bug span { font-size: 20px; color: var(--muted); }
.livewrap { position: absolute; right: 60px; top: 70px; }
.c1 { right: 40px; bottom: 40px; width: 110px; height: 110px; --t: 16px; transform: rotate(90deg); }
""", r"""
<div class="win" style="inset:0"></div>
<div class="bug in" id="church_tag"><img src="__LOGO__" alt="">""" + WHERE_INNER + r"""</div>
<div class="livewrap in" id="live_tag"><div class="live"><i></i><span data-t="live"></span></div></div>
<div class="bracket c1 in" id="corner"></div>
""", r"""
/* ?church_tag=off  ?live_tag=off  ?corner=off  (old names bug / livetag also work) */
[['church_tag','bug'],['live_tag','livetag'],['corner','corner']].forEach(([id, old]) => {
  if (Q.get(id) === 'off' || Q.get(old) === 'off') document.getElementById(id).classList.add('hide');
});
""", note='camera window = key colour')

# =====================================================================
# 03 Sermon / 04 Camera + Slides
# =====================================================================
DARK_BG = '<div class="bgphoto" style="filter: blur(6px) brightness(.28)"></div><div style="position:absolute;inset:0;background:linear-gradient(90deg,rgba(0,0,0,.6),rgba(0,0,0,.2))"></div>'

PANEL_CSS = r"""
.label { font-family: var(--display); font-weight: 500; font-size: 24px; letter-spacing: 5px; text-transform: uppercase; color: var(--green); }
.msgtitle { margin-top: 18px; font-family: var(--display); font-weight: 700; text-transform: uppercase; line-height: 1.02; letter-spacing: 1px; }
.series { margin-top: 18px; font-size: 26px; color: var(--muted); }
.prule { width: 90px; height: 5px; background: var(--green); margin: 34px 0 26px; }
.scripture { font-family: var(--display); font-weight: 500; font-size: 34px; letter-spacing: 1px; display: flex; align-items: center; gap: 14px; }
.scripture::before { content: ""; flex: none; width: 14px; height: 34px; background: var(--green); }
.speaker strong { display: block; font-family: var(--display); font-weight: 700; font-size: 50px; text-transform: uppercase; letter-spacing: 1px; line-height: 1.05; }
.speaker span { font-family: var(--display); font-weight: 500; font-size: 26px; letter-spacing: 3px; text-transform: uppercase; color: var(--green); }
"""
MESSAGE_HTML = """
  <div data-group="message_title series_name"><div class="label" data-t="msglabel"></div>
  <div class="msgtitle" data-t="message_title"></div>
  <div class="series" data-t="series_name"></div></div>
  <div data-group="verse_ref"><div class="prule"></div><div class="scripture" data-t="verse_ref"></div></div>"""
SPEAKER_HTML = '<div class="speaker in" data-group><strong data-t="speaker_name"></strong><span data-t="speaker_title"></span></div>'

page('03-camera-sermon.html', 'Camera – Sermon', PANEL_CSS + r"""
.cam { left: 70px; top: 70px; width: 1280px; height: 720px; }
.camb { left: 1310px; top: 50px; width: 60px; height: 60px; --t: 14px; }
.panel { position: absolute; left: 1420px; top: 90px; width: 430px; }
.panel .wm { width: 190px; margin-bottom: 70px; } .panel .wm svg { width: 100%; height: auto; display: block; }
.msgtitle { font-size: 60px; }
.speaker { position: absolute; left: 70px; top: 845px; }
.foot { position: absolute; left: 1420px; right: 70px; top: 860px; font-size: 22px; color: var(--muted); line-height: 1.6; }
.foot b { font-family: var(--display); font-weight: 500; color: var(--white); text-transform: uppercase; letter-spacing: 1px; margin-right: 8px; }
.foot em { font-style: normal; color: var(--green); }
""", DARK_BG + r"""
<div class="win cam"></div>
<div class="bracket camb"></div>
<div class="panel in">
  <div class="wm">__WORDMARK__</div>""" + MESSAGE_HTML + r"""
</div>
""" + SPEAKER_HTML + r"""
<div class="foot in" data-group>
  <div><b data-t="service_day"></b><em data-t="service_time"></em></div>
  <div data-t="service_name"></div>
  <div data-t="location"></div>
</div>
""", stage_bg='#000', note='camera window 1280x720 at x70 y70 = key colour')

page('04-camera-slides.html', 'Camera + Slides', PANEL_CSS + r"""
.cam { left: 70px; top: 70px; width: 592px; height: 333px; }
.slides { left: 702px; top: 70px; width: 1148px; height: 646px; }
.slb { left: 1810px; top: 50px; width: 60px; height: 60px; --t: 14px; }
.info { position: absolute; left: 70px; top: 448px; width: 592px; }
.msgtitle { font-size: 48px; }
.speaker { position: absolute; left: 702px; top: 760px; }
.speaker strong { font-size: 44px; }
.bar { position: absolute; left: 0; right: 0; bottom: 0; height: 116px; display: flex; align-items: center; justify-content: space-between;
  padding: 0 70px; background: rgba(0,0,0,.7); border-top: 1px solid rgba(255,255,255,.12); }
.times { font-size: 22px; color: var(--muted); }
.times b { font-weight: 500; font-size: 26px; color: var(--white); letter-spacing: 1px; margin-right: 10px; }
.times em { font-style: normal; color: var(--green); }
.where { display: flex; align-items: center; gap: 18px; margin-left: auto; }
.where div { text-align: right; font-size: 20px; color: var(--muted); line-height: 1.3; }
.where strong { display: block; font-family: var(--display); font-weight: 500; font-size: 26px; letter-spacing: 2px; text-transform: uppercase; color: var(--white); }
.where img { width: 64px; height: 64px; border-radius: 50%; }
""", DARK_BG + f"""
<div class="win cam"></div>
<div class="win slides"></div>
<div class="bracket slb"></div>
<div class="info in">{MESSAGE_HTML}
</div>
{SPEAKER_HTML}
<div class="bar in">{TIMES_HTML}<div class="where">{WHERE_INNER}<img src="__LOGO__" alt=""></div></div>
""", stage_bg='#000', note='camera 592x333 at x70 y70, slides 1148x646 at x702 y70 = key colour')

# =====================================================================
# 05 Lower third – speaker (transparent)
# =====================================================================
page('05-lower-third-speaker.html', 'Lower Third – Speaker', r"""
.lt { position: absolute; left: 90px; bottom: 110px; display: flex; align-items: stretch; }
.lt .mark { width: 136px; background: #000; display: grid; place-items: center; position: relative; z-index: 2; animation: fade .6s ease both; }
.lt .mark img { width: 104px; height: 104px; border-radius: 50%; }
.lt .mark::after { content: ""; position: absolute; right: 0; top: 0; bottom: 0; width: 8px; background: var(--green); }
.lt .body { overflow: hidden; }
.lt .slide { animation: wipe .8s cubic-bezier(.2,.8,.2,1) both .35s; }
@keyframes wipe { from { transform: translateX(-100%); } to { transform: none; } }
.lt .name { background: rgba(0,0,0,.88); padding: 18px 44px 14px 30px; font-family: var(--display); font-weight: 700; font-size: 56px; line-height: 1.05; text-transform: uppercase; letter-spacing: 1px; white-space: nowrap; }
.lt .role { display: inline-block; background: var(--green); color: #000; padding: 8px 30px; font-family: var(--display); font-weight: 500; font-size: 26px; letter-spacing: 4px; text-transform: uppercase; white-space: nowrap; }
.lt.out .slide { animation: wipeout .6s ease both; } .lt.out .mark { animation: fadeout .4s ease both .4s; }
@keyframes wipeout { to { transform: translateX(-100%); } } @keyframes fadeout { to { opacity: 0; } }
""", r"""
<div class="lt" id="lt" data-hold data-group="speaker_name">
  <div class="mark"><img src="__LOGO__" alt=""></div>
  <div class="body"><div class="slide"><div class="name" data-t="speaker_name"></div><div data-group><span class="role" data-t="speaker_title"></span></div></div></div>
</div>
""", note='transparent background')

# =====================================================================
# 08 Lower third – Bible verse (transparent, looks up verse text online)
# =====================================================================


page('08-lower-third-verse.html', 'Lower Third – Verse', r"""
/* verse box: green bar appears, then the verse slides out from it (like the speaker lower third) */
.sc { position: absolute; left: 180px; bottom: 90px; width: 1560px; align-items: stretch; }
.sc .vbar { flex: none; width: 10px; background: var(--green); transform-origin: 50% 100%; position: relative; z-index: 2; }
.sc .vbody { flex: 1; min-width: 0; overflow: hidden; }
.sc .vslide { height: 100%; background: rgba(0,0,0,.86); padding: 40px 60px 36px 60px; }
.sc .verse { font-size: 36px; line-height: 1.42; font-weight: 400; display: -webkit-box; -webkit-line-clamp: 6; -webkit-box-orient: vertical; overflow: hidden; }
.sc .ref { margin-top: 18px; font-family: var(--display); font-weight: 500; font-size: 30px; letter-spacing: 4px; text-transform: uppercase; color: var(--green); }
.sc .verse.hide + .ref { margin-top: 0; }
.sc.on .vbar, .sc.ready .vbar { animation: barin .45s cubic-bezier(.2,.8,.2,1) both; }
.sc.on .vslide, .sc.ready .vslide { animation: vwipe .8s cubic-bezier(.2,.8,.2,1) both .3s; }
.sc.out .vslide { animation: vwipeout .55s ease both; }
.sc.out .vbar { animation: barout .3s ease both .45s; }
@keyframes barin { from { transform: scaleY(0); } to { transform: none; } }
@keyframes barout { from { transform: none; } to { transform: scaleY(0); } }
@keyframes vwipe { from { transform: translateX(-100%); } to { transform: none; } }
@keyframes vwipeout { from { transform: none; } to { transform: translateX(-100%); } }
.sc { display: flex; visibility: hidden; }
.sc.ready { visibility: visible; }
""", r"""
<div class="sc" id="sc" data-hold><div class="vbar"></div><div class="vbody"><div class="vslide"><div class="verse" id="vtext"></div><div class="ref" data-t="verse_ref"></div></div></div></div>
""", BIBLE_JS + VERSE_JS, note='transparent background · needs internet for verse lookup')


# =====================================================================
# 09 Live graphics – controlled from 10-control-panel through OBS WebSocket
# =====================================================================
WM = json.loads((ASSETS / 'watermark-parts.json').read_text(encoding='utf-8'))   # user's watermark: photo masked into the N + outline

LIVE_CSS = r"""
.g { display: none; }
.g.on { display: flex; }
/* speaker + bottom message lower third (same look as 05) */
.lt { position: absolute; left: 90px; bottom: 110px; align-items: stretch; }
.lt .mark { width: 136px; background: #000; display: grid; place-items: center; position: relative; z-index: 2; }
.lt .mark img { width: 104px; height: 104px; border-radius: 50%; }
.lt .mark::after { content: ""; position: absolute; right: 0; top: 0; bottom: 0; width: 8px; background: var(--green); }
.lt .body { overflow: hidden; }
.lt .name { background: rgba(0,0,0,.88); padding: 18px 44px 14px 30px; font-family: var(--display); font-weight: 700; font-size: 56px; line-height: 1.05; text-transform: uppercase; letter-spacing: 1px; white-space: nowrap; }
.lt .role { display: inline-block; background: var(--green); color: #000; padding: 8px 30px; font-family: var(--display); font-weight: 500; font-size: 26px; letter-spacing: 4px; text-transform: uppercase; white-space: nowrap; }
.lt.on .mark { animation: fade .6s ease both; }
.lt.on .slide { animation: wipe .8s cubic-bezier(.2,.8,.2,1) both .35s; }
.lt.out .slide { animation: wipeout .6s ease both; } .lt.out .mark { animation: fadeout .4s ease both .3s; }
@keyframes wipe { from { transform: translateX(-100%); } to { transform: none; } }
@keyframes wipeout { from { transform: none; } to { transform: translateX(-100%); } }
@keyframes fadeout { from { opacity: 1; } to { opacity: 0; } }
/* top message (same look as the church tag on 02-camera-fullscreen) */
.tag { position: absolute; left: 60px; top: 56px; align-items: center; gap: 18px; max-width: 1500px;
  padding: 12px 28px 12px 12px; background: #0b0b0b; border-left: 8px solid var(--green); }
.tag img { width: 84px; height: 84px; border-radius: 50%; display: block; flex: none; }
.tag strong { display: block; font-family: var(--display); font-weight: 500; font-size: 30px; letter-spacing: 2px; text-transform: uppercase; }
.tag span { display: block; font-size: 20px; color: var(--muted); }
.tag.on { animation: dropin .7s cubic-bezier(.2,.8,.2,1) both; }
.tag.out { animation: dropout .5s ease both; }
@keyframes dropin { from { opacity: 0; transform: translateY(-24px); } to { opacity: 1; transform: none; } }
@keyframes dropout { from { opacity: 1; transform: none; } to { opacity: 0; transform: translateY(-24px); } }
/* verse box: green bar appears, then the verse slides out from it (like the speaker lower third) */
.sc { position: absolute; left: 180px; bottom: 90px; width: 1560px; align-items: stretch; }
.sc .vbar { flex: none; width: 10px; background: var(--green); transform-origin: 50% 100%; position: relative; z-index: 2; }
.sc .vbody { flex: 1; min-width: 0; overflow: hidden; }
.sc .vslide { height: 100%; background: rgba(0,0,0,.86); padding: 40px 60px 36px 60px; }
.sc .verse { font-size: 36px; line-height: 1.42; font-weight: 400; display: -webkit-box; -webkit-line-clamp: 6; -webkit-box-orient: vertical; overflow: hidden; }
.sc .ref { margin-top: 18px; font-family: var(--display); font-weight: 500; font-size: 30px; letter-spacing: 4px; text-transform: uppercase; color: var(--green); }
.sc .verse.hide + .ref { margin-top: 0; }
.sc.on .vbar, .sc.ready .vbar { animation: barin .45s cubic-bezier(.2,.8,.2,1) both; }
.sc.on .vslide, .sc.ready .vslide { animation: vwipe .8s cubic-bezier(.2,.8,.2,1) both .3s; }
.sc.out .vslide { animation: vwipeout .55s ease both; }
.sc.out .vbar { animation: barout .3s ease both .45s; }
@keyframes barin { from { transform: scaleY(0); } to { transform: none; } }
@keyframes barout { from { transform: none; } to { transform: scaleY(0); } }
@keyframes vwipe { from { transform: translateX(-100%); } to { transform: none; } }
@keyframes vwipeout { from { transform: none; } to { transform: translateX(-100%); } }

/* Watermark (shown when nothing else is on screen). Spin + flip every 30 s, as in obs-watermark.html */
#wm { position: absolute; right: 15px; bottom: 15px; width: 80px; height: 80px; padding: 20px; box-sizing: content-box;
  opacity: 0; transition: opacity .6s ease; }
#wm.show { opacity: 1; }
#wm .size { width: 80px; height: 80px; }
#wm img { opacity: .9; z-index: 9; }
#wm svg { z-index: 10; }
#wm img, #wm svg { position: absolute; animation: wmrotate 30s ease-in-out 5s infinite; }
@keyframes wmrotate { 0% { transform: rotate(0deg) rotateY(0deg); } 10% { transform: rotate(360deg) rotateY(360deg); } 100% { transform: rotate(360deg) rotateY(360deg); } }
#wm .mask { -webkit-mask-image: url("__WMMASK__"); mask-image: url("__WMMASK__"); -webkit-mask-size: 100% 100%; mask-size: 100% 100%; }

/* Preview mode (inside the control panel): fake camera background, no animations */
.preview .g, .preview .g * { animation: none !important; }
#debug { position: absolute; left: 20px; top: 20px; padding: 8px 14px; background: #000; color: #fff; font: 600 20px Inter, sans-serif; }
"""

LIVE_JS = r"""
/* Options: ?obs_host=localhost ?obs_port=4455 ?obs_password=... ?channel=main ?watermark=off ?debug=1
   ?preview=1 is used by the control panel (no OBS connection; content arrives by postMessage). */
(function () {
  const CH = Q.get('channel') || 'main';
  const ME = 'overlay-' + Math.random().toString(36).slice(2, 8);
  const PREVIEW = Q.get('preview') === '1';
  const ids = { speaker: 'g-speaker', verse: 'g-verse', message: 'g-message', messageTop: 'g-message-top' };
  const elFor = (g, d) => document.getElementById(g === 'message' && d && d.position === 'top' ? ids.messageTop : ids[g]);
  const dbg = document.getElementById('debug'), wm = document.getElementById('wm');
  if (Q.get('debug') !== '1') dbg.remove();
  let current = null, holdTimer = null, busy = Promise.resolve();
  let wmMode = Q.get('watermark') === 'off' ? 'off' : 'auto';

  function updateWM() { wm.classList.toggle('show', !PREVIEW && wmMode === 'auto' && !current); }

  function setText(el, v) { v = v == null ? '' : String(v).trim(); el.textContent = v; el.classList.toggle('hide', !v); }
  function fill(g, d, el) {
    if (g === 'speaker') { setText(el.querySelector('.name'), d.name); setText(el.querySelector('.role'), d.title); }
    if (g === 'message') {
      if (d.position === 'top') { setText(el.querySelector('strong'), d.line1); setText(el.querySelector('span'), d.line2); }
      else { setText(el.querySelector('.name'), d.line1); setText(el.querySelector('.role'), d.line2); }
    }
    if (g === 'verse') {
      const tx = el.querySelector('.verse'); setText(tx, d.text);
      if (d.text) tx.style.fontSize = BIBLE.sizeFor(String(d.text).length) + 'px';
      setText(el.querySelector('.ref'), d.reference);
    }
  }
  /* pos = {top,right,bottom,left} in px (blank = default). Setting one side of an axis clears the default other side. */
  function place(el, pos) {
    ['top', 'right', 'bottom', 'left'].forEach(k => el.style[k] = '');
    if (!pos) return;
    const n = v => v !== '' && v != null && !isNaN(+v);
    if (n(pos.top) || n(pos.bottom)) { el.style.top = n(pos.top) ? +pos.top + 'px' : 'auto'; el.style.bottom = n(pos.bottom) ? +pos.bottom + 'px' : 'auto'; }
    if (n(pos.left) || n(pos.right)) { el.style.left = n(pos.left) ? +pos.left + 'px' : 'auto'; el.style.right = n(pos.right) ? +pos.right + 'px' : 'auto'; }
  }
  function animateOut(el) {
    return new Promise(res => {
      if (!el.classList.contains('on')) return res();
      el.classList.add('out');
      setTimeout(() => { el.classList.remove('on', 'out'); res(); }, el.classList.contains('sc') ? 820 : 700);
    });
  }
  function report() {
    if (PREVIEW) return;
    client.broadcast({ app: NLC_APP, channel: CH, role: 'overlay', from: ME, action: 'status',
      showing: current ? { graphic: current.graphic, data: current.data, hold: current.hold || 0,
        remaining: current.endAt ? Math.max(0, (current.endAt - Date.now()) / 1000) : 0 } : null, watermark: wmMode }).catch(() => {});
  }
  function show(g, d, hold) {
    if (!ids[g]) return;
    busy = busy.then(async () => {
      clearTimeout(holdTimer);
      d = d || {};
      const el = elFor(g, d);
      if (current) await animateOut(current.el);
      current = { graphic: g, data: d, el, hold: hold > 0 ? hold : 0, endAt: hold > 0 ? Date.now() + hold * 1000 : 0 };
      updateWM();
      if (g === 'verse' && !d.text && d.reference) {             // panel couldn't look it up: try here
        const ref = String(d.reference).split('·')[0].trim();
        d.text = await BIBLE.lookup(ref, d.translation, d.lang);
      }
      fill(g, d, el); place(el, d.pos);
      el.classList.remove('out'); void el.offsetWidth; el.classList.add('on');
      if (hold > 0) holdTimer = setTimeout(() => hide(), Math.max(0, current.endAt - Date.now()));
      report();
    });
  }
  function hide(g) {
    busy = busy.then(async () => {
      if (!current || (g && current.graphic !== g)) return report();
      clearTimeout(holdTimer);
      const c = current; current = null;
      await animateOut(c.el);
      updateWM();
      report();
    });
  }
  function setWatermark(mode, pos) { wmMode = mode === 'off' ? 'off' : 'auto'; if (pos !== undefined) place(wm, pos); updateWM(); report(); }

  if (PREVIEW) {
    /* Control-panel preview: draw just the graphic, zoomed to fit the preview box (not to scale).
       Reports the height it needs so the panel can size the box. */
    document.body.classList.add('preview');
    removeEventListener('resize', fit);
    let shown = null;
    function frame() {
      if (!shown) return;
      const PAD = 16, MAXS = 0.42, W = innerWidth;
      const bx = shown.offsetLeft, by = shown.offsetTop, bw = shown.offsetWidth, bh = shown.offsetHeight;
      if (!bw || !bh) return;
      const s = Math.min((W - PAD * 2) / bw, MAXS);
      stage.style.left = '0'; stage.style.top = '0'; stage.style.transformOrigin = '0 0';
      stage.style.transform = `translate(${(W - bw * s) / 2 - bx * s}px, ${PAD - by * s}px) scale(${s})`;
      parent.postMessage({ type: 'nlc-preview-size', height: Math.ceil(bh * s + PAD * 2) }, '*');
    }
    addEventListener('resize', frame);
    document.fonts && document.fonts.ready.then(frame);
    window.addEventListener('message', e => {
      const m = e.data || {};
      if (m.type !== 'nlc-preview') return;
      document.querySelectorAll('.g').forEach(x => x.classList.remove('on', 'out'));
      shown = null;
      if (!m.graphic) return;
      const el = elFor(m.graphic, m.data || {});
      fill(m.graphic, m.data || {}, el); el.classList.add('on');
      shown = el; frame();
    });
    window.parent !== window && window.parent.postMessage({ type: 'nlc-preview-ready' }, '*');
    return;
  }

  const client = OBSWS.create({
    host: Q.get('obs_host') || 'localhost', port: Q.get('obs_port') || 4455, password: Q.get('obs_password') || '', subs: 1,
    onStatus: s => { if (dbg.isConnected) dbg.textContent = 'OBS: ' + s + ' · channel ' + CH; },
    onReady: () => client.broadcast({ app: NLC_APP, channel: CH, role: 'overlay', from: ME, action: 'hello' }).catch(() => {}),
    onEvent: (type, d) => {
      if (type !== 'CustomEvent' || !d || d.app !== NLC_APP || d.channel !== CH || d.role !== 'panel') return;
      if (d.action === 'show') show(d.graphic, d.data, +d.hold || 0);
      else if (d.action === 'hide') hide(d.graphic);
      else if (d.action === 'ping') report();
      else if (d.action === 'watermark') setWatermark(d.mode, d.pos);
      else if (d.action === 'state' && d.to === ME) {
        if (d.watermark) setWatermark(d.watermark, d.watermarkPos);
        if (d.showing && !current) show(d.showing.graphic, d.showing.data, +d.showing.remaining || 0);
      }
    },
  });
  updateWM();
  client.connect();
  window.NLC_LIVE = { show, hide, setWatermark, get current() { return current; } };   // for testing
})();
"""

LIVE_BODY = r"""
<div class="g lt" id="g-speaker">
  <div class="mark"><img src="__LOGO__" alt=""></div>
  <div class="body"><div class="slide"><div class="name"></div><div><span class="role"></span></div></div></div>
</div>
<div class="g lt" id="g-message">
  <div class="mark"><img src="__LOGO__" alt=""></div>
  <div class="body"><div class="slide"><div class="name"></div><div><span class="role"></span></div></div></div>
</div>
<div class="g tag" id="g-message-top"><img src="__LOGO__" alt=""><div><strong></strong><span></span></div></div>
<div class="g sc" id="g-verse"><div class="vbar"></div><div class="vbody"><div class="vslide"><div class="verse"></div><div class="ref"></div></div></div></div>
<div id="wm">__WMSVG__<img class="size mask" src="__WMIMG__" alt=""></div>
<div id="debug">OBS: starting…</div>
"""

def live_page():
    css = LIVE_CSS.replace('__WMMASK__', WM['mask'])
    body = LIVE_BODY.replace('__WMSVG__', WM['svg']).replace('__WMIMG__', WM['img'])
    page('09-live-graphics.html', 'Live Graphics', css, body, BIBLE_JS + OBS_JS + LIVE_JS,
         note='transparent background · controlled by 10-control-panel via OBS WebSocket')
live_page()

# =====================================================================
# 10 Control panel (normal web page, not an OBS overlay)
# =====================================================================
panel = (SRC / 'panel_template.html').read_text(encoding='utf-8')
panel = panel.replace('__BIBLE_JS__', BIBLE_JS).replace('__OBS_JS__', OBS_JS).replace('__LOGO__', LOGO)
assert '__' not in panel.replace('__proto__', '')
open(OUT + '10-control-panel.html', 'w', encoding='utf-8').write(panel)

# Hand-written files (user guide + preview page) are copied as-is
for f in (SRC / 'static').iterdir():
    shutil.copy(f, OUT + f.name)

print('built', sorted(os.listdir(OUT)))
