"""New-feature tests: modals, fixed top bar, Show wording, MIDI, item edit, positions,
watermark position, full-screen screens, scene previews, everything in profile export."""
import json, hashlib, base64, io, time
from PIL import Image
from playwright.sync_api import sync_playwright

from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
OUTDIR = ROOT / 'tests' / 'out'; OUTDIR.mkdir(exist_ok=True)
D = (ROOT / 'dist').as_uri() + '/'
PW = 'secret'; SALT = 'c2FsdHNhbHQ='; CHAL = 'Y2hhbGxlbmdl'
def py_auth(pw, salt, ch):
    s = base64.b64encode(hashlib.sha256((pw + salt).encode()).digest()).decode()
    return base64.b64encode(hashlib.sha256((s + ch).encode()).digest()).decode()
b = io.BytesIO(); Image.new('RGB', (160, 90), (200, 40, 40)).save(b, 'JPEG')
SHOT = 'data:image/jpg;base64,' + base64.b64encode(b.getvalue()).decode()
state = {'program': 'Sermon', 'scenes': ['Starting Soon', 'Sermon', 'Slides', 'Thank You'], 'shots': [], 'events': []}
clients = []

def broadcast(evtype, data, bit):
    for c in list(clients):
        if c['ok'] and c['subs'] & bit:
            try: c['ws'].send(json.dumps({'op': 5, 'd': {'eventType': evtype, 'eventIntent': bit, 'eventData': data}}))
            except Exception: pass

def handler(ws):
    c = {'ws': ws, 'subs': 0, 'ok': False}; clients.append(c)
    ws.send(json.dumps({'op': 0, 'd': {'rpcVersion': 1, 'authentication': {'challenge': CHAL, 'salt': SALT}}}))
    def on_msg(m):
        msg = json.loads(m); d = msg['d']
        if msg['op'] == 1:
            if d.get('authentication') != py_auth(PW, SALT, CHAL):
                clients.remove(c); ws.close(code=4009, reason='Authentication failed.'); return
            c['ok'] = True; c['subs'] = d.get('eventSubscriptions', 0)
            ws.send(json.dumps({'op': 2, 'd': {'negotiatedRpcVersion': 1}}))
        elif msg['op'] == 6:
            rt = d['requestType']; rd = d.get('requestData', {}); resp = {}
            if rt == 'BroadcastCustomEvent':
                state['events'].append(rd['eventData']); broadcast('CustomEvent', rd['eventData'], 1)
            elif rt == 'GetSceneList':
                n = len(state['scenes'])
                resp = {'currentProgramSceneName': state['program'], 'scenes': [{'sceneName': s, 'sceneIndex': n - 1 - i} for i, s in enumerate(state['scenes'])]}
            elif rt == 'GetSourceScreenshot':
                state['shots'].append(rd['sourceName']); resp = {'imageData': SHOT}
            elif rt == 'SetCurrentProgramScene':
                state['program'] = rd['sceneName']; broadcast('CurrentProgramSceneChanged', {'sceneName': rd['sceneName']}, 4)
            ws.send(json.dumps({'op': 7, 'd': {'requestType': rt, 'requestId': d['requestId'], 'requestStatus': {'result': True, 'code': 100}, 'responseData': resp}}))
    ws.on_message(on_msg)
    ws.on_close(lambda *a: c in clients and clients.remove(c))

def bolls(route):
    parts = route.request.url.rstrip('/').split('/'); tr, book, ch = parts[-3:]
    data = [{'pk': i, 'verse': i, 'text': f'Text of {tr} {book}:{ch}:{i}.'} for i in range(1, 30)]
    route.fulfill(status=200, headers={'Access-Control-Allow-Origin': '*'}, content_type='application/json', body=json.dumps(data))

FAKE_MIDI = """
window.__midi = [];
navigator.requestMIDIAccess = async () => {
  const out = { name: 'loopMIDI Port', send: (bytes) => window.__midi.push(Array.from(bytes)) };
  const outputs = new Map([['o1', out]]);
  return { outputs, inputs: new Map(), onstatechange: null };
};
"""

results = []
def check(label, cond): results.append(bool(cond)); print(('PASS ' if cond else 'FAIL ') + label)

with sync_playwright() as p:
    br = p.chromium.launch(); ctx = br.new_context(accept_downloads=True)
    ctx.route_web_socket('ws://localhost:4455/', handler); ctx.route('https://bolls.life/**', bolls)
    ctx.add_init_script(FAKE_MIDI)
    errs = []
    def newp(w, h):
        pg = ctx.new_page(); pg.set_viewport_size({'width': w, 'height': h}); pg.on('pageerror', lambda e: errs.append(str(e))); return pg
    ov = newp(1920, 1080); ov.goto(D + '09-live-graphics.html?obs_password=secret'); ov.wait_for_timeout(600)
    ty = newp(1920, 1080); ty.goto(D + '07-thank-you.html?obs_password=secret'); ty.wait_for_timeout(600)
    pn = newp(1440, 1000); pn.goto(D + '10-control-panel.html?obs_password=secret'); pn.wait_for_timeout(2500)

    # ---- top bar: fixed, modals, wording
    check('top bar is position:fixed at 0/0/0', pn.eval_on_selector('#top', 'e=>{const s=getComputedStyle(e);return s.position==="fixed"&&s.top==="0px"&&s.left==="0px"&&s.right==="0px"}'))
    pn.click('#settingsBtn'); pn.wait_for_timeout(200)
    check('Connection opens as a modal', pn.eval_on_selector('#dlg-connection', 'e=>e.open && e.matches(":modal")'))
    check('modal is centered on screen', pn.eval_on_selector('#dlg-connection', 'e=>{const r=e.getBoundingClientRect();return Math.abs((r.left+r.right)/2-innerWidth/2)<2&&Math.abs((r.top+r.bottom)/2-innerHeight/2)<2}'))
    check('page scroll locked while modal open', pn.evaluate('getComputedStyle(document.documentElement).overflow==="hidden"&&getComputedStyle(document.body).overflow==="hidden"'))
    pn.keyboard.press('Escape'); pn.wait_for_timeout(200)
    check('modal closes with Esc', not pn.eval_on_selector('#dlg-connection', 'e=>e.open'))
    check('page scroll unlocked after modal closes', pn.evaluate('getComputedStyle(document.documentElement).overflow!=="hidden"'))
    check('no "Display" wording left', 'Display' not in pn.inner_text('main') and pn.inner_text('#sp-show') == 'Show now')

    # ---- scene previews
    pn.wait_for_timeout(1500)
    check('program preview image shown', (pn.get_attribute('#pgmImg', 'src') or '').startswith('data:image/jpg'))
    check('scene thumbnails requested for every scene', all(s in state['shots'] for s in state['scenes']))
    check('scene thumbnail painted', 'data:image' in pn.eval_on_selector('.scene .thumb', 'e=>e.style.backgroundImage'))
    pn.click('#pgm-toggle button[data-v="off"]'); pn.wait_for_timeout(200)
    check('live preview can be turned off', pn.eval_on_selector('#program', 'e=>getComputedStyle(e).display==="none"'))
    pn.click('#pgm-toggle button[data-v="on"]')

    # ---- MIDI
    pn.click('#midiBtn'); pn.wait_for_timeout(200)
    check('MIDI opens as a modal', pn.eval_on_selector('#dlg-midi', 'e=>e.open'))
    pn.click('#midiEnable'); pn.wait_for_timeout(300)
    pn.select_option('#midiOut', 'loopMIDI Port')
    check('MIDI output listed', 'loopMIDI Port' in pn.inner_text('#midiOut'))
    check('note names: G-1 = 7 (C-1 = 0)', pn.evaluate("NLC_PANEL.noteNum('G-1')") == 7)
    pn.select_option('#midiNaming', 'c-2')
    check('note names: G-1 = 19 (C-2 = 0)', pn.evaluate("NLC_PANEL.noteNum('G-1')") == 19)
    pn.select_option('#midiNaming', 'c-1')
    row = pn.locator('#midiMap tr[data-k="show:verse"]')
    row.locator('input[data-f="note"]').fill('G-1'); row.locator('input[data-f="vel"]').fill('9')
    rem = pn.locator('#midiMap tr[data-k="remove:all"]'); rem.locator('input[data-f="note"]').fill('A-1'); rem.locator('input[data-f="vel"]').fill('1')
    pn.evaluate('window.__midi.length=0'); row.locator('[data-test]').click(); pn.wait_for_timeout(300)
    check('Test sends note on + note off', pn.evaluate('window.__midi') == [[0x90, 7, 9], [0x80, 7, 0]])
    pn.keyboard.press('Escape')

    # saved verse with its own note
    pn.fill('#v-book', 'John'); pn.fill('#v-chapter', '3'); pn.fill('#v-verse', '16'); pn.fill('#v-tr', 'NIV'); pn.click('#v-lookup'); pn.wait_for_timeout(600)
    pn.click('#v-save'); pn.wait_for_timeout(300)
    pn.fill('#v-verse', '17'); pn.click('#v-lookup'); pn.wait_for_timeout(600); pn.click('#v-save'); pn.wait_for_timeout(300)
    pn.locator('#v-list [data-edit="0"]').click(); pn.wait_for_timeout(200)
    check('Edit opens a modal', pn.eval_on_selector('#dlg-item', 'e=>e.open'))
    pn.fill('#it-note', 'G-1'); pn.fill('#it-vel', '1'); pn.click('#it-save'); pn.wait_for_timeout(200)
    pn.locator('#v-list [data-edit="1"]').click(); pn.wait_for_timeout(200)
    pn.fill('#it-note', 'G-1'); pn.fill('#it-vel', '5'); pn.click('#it-save'); pn.wait_for_timeout(200)
    check('saved verses show their MIDI chip', pn.locator('#v-list .chip.midi').count() == 2 and 'G-1 · 5' in pn.inner_text('#v-list'))
    pn.evaluate('window.__midi.length=0'); pn.locator('#v-list [data-show="1"]').click(); pn.wait_for_timeout(1500)
    check('Show on saved verse sends its own note (G-1 vel 5)', pn.evaluate('window.__midi')[0] == [0x90, 7, 5])
    check('verse shows on overlay', ov.eval_on_selector('#g-verse', 'e=>e.classList.contains("on")') and '3:17' in ov.inner_text('#g-verse .ref'))
    pn.evaluate('window.__midi.length=0'); pn.click('#hideAll'); pn.wait_for_timeout(1200)
    check('Remove all sends its note (A-1 = 9)', pn.evaluate('window.__midi')[0] == [0x90, 9, 1])
    pn.evaluate('window.__midi.length=0'); pn.fill('#v-verse', '18'); pn.click('#v-show'); pn.wait_for_timeout(1500)
    check('card Show uses the action note (G-1 vel 9)', pn.evaluate('window.__midi')[0] == [0x90, 7, 9])
    pn.click('#hideAll'); pn.wait_for_timeout(1000)

    # ---- positions
    pn.locator('details.posbox[data-pos="speaker"] summary').click()
    pn.locator('details.posbox[data-pos="speaker"] input[data-side="top"]').fill('40')
    pn.locator('details.posbox[data-pos="speaker"] input[data-side="right"]').fill('60')
    check('position summary updates', 'top 40' in pn.inner_text('details.posbox[data-pos="speaker"] .possum'))
    pn.fill('#sp-name', 'Pastor Juan'); pn.click('#sp-show'); pn.wait_for_timeout(1500)
    st = ov.eval_on_selector('#g-speaker', 'e=>[e.style.top,e.style.bottom,e.style.left,e.style.right]')
    check('speaker placed top 40 / right 60 on the overlay', st == ['40px', 'auto', 'auto', '60px'])
    r = ov.eval_on_selector('#g-speaker', 'e=>e.getBoundingClientRect()')
    check('speaker really is top-right', abs(r['y'] - 40) < 2 and abs(1920 - (r['x'] + r['width']) - 60) < 2)
    pn.click('#hideAll'); pn.wait_for_timeout(1000)
    pn.locator('details.posbox[data-pos="watermark"] summary').click()
    pn.locator('details.posbox[data-pos="watermark"] input[data-side="top"]').fill('20'); pn.wait_for_timeout(500)
    check('watermark moved to the top', ov.eval_on_selector('#wm', 'e=>e.style.top') == '20px')
    pn.locator('details.posbox[data-pos="watermark"] [data-reset]').click(); pn.wait_for_timeout(500)
    check('watermark position reset', ov.eval_on_selector('#wm', 'e=>e.style.top') == '')

    # ---- full-screen screens
    pn.click('#scTabs button[data-s="thanks"]'); pn.wait_for_timeout(300)
    pn.fill('#sc-h1', 'Thank you'); pn.fill('#sc-h2', 'for watching'); pn.fill('#sc-give', 'nlc.org/give')
    pn.select_option('#sc-scene', 'Thank You'); pn.wait_for_timeout(900)
    check('screen preview loads the Thank You page with settings', 'headline=Thank+you' in pn.eval_on_selector('#scPreview', 'e=>e.src') and 'obs=off' in pn.eval_on_selector('#scPreview', 'e=>e.src'))
    check('Thank You page found in OBS', 'connected in OBS' in pn.inner_text('#scFound'))
    pn.click('#sc-show'); pn.wait_for_timeout(3500)
    check('Show switched OBS to the Thank You scene', state['program'] == 'Thank You')
    check('Thank You page now shows the new wording', 'headline=Thank+you' in ty.url and 'nlc.org/give' in ty.inner_text('#stage'))
    ty.goto(D + '07-thank-you.html?obs_password=secret'); ty.wait_for_timeout(2500)
    check('wording survives an OBS refresh', 'nlc.org/give' in ty.inner_text('#stage'))
    pn.click('#scTabs button[data-s="starting"]'); pn.select_option('#sc-cd', 'minutes'); pn.fill('#sc-min', '7'); pn.wait_for_timeout(800)
    check('starting-soon preview counts down 7 min', 'minutes=7' in pn.eval_on_selector('#scPreview', 'e=>e.src'))

    # ---- everything is in the exported profile
    pn.click('#profilesBtn'); pn.wait_for_timeout(200)
    check('Profiles opens as a modal', pn.eval_on_selector('#dlg-profiles', 'e=>e.open'))
    with pn.expect_download() as dl: pn.click('#pf-export')
    data = json.load(open(dl.value.path())); pr = data['profiles'][0]
    check('export: positions', pr['positions'].get('speaker') == {'top': 40, 'right': 60})
    check('export: MIDI actions + item notes', pr['midi']['actions']['show:verse']['note'] == 'G-1' and pr['verses'][1]['midi']['vel'] == '5')
    check('export: screens + scene link', pr['screens']['thanks']['h1'] == 'Thank you' and pr['screens']['thanks']['scene'] == 'Thank You' and pr['screens']['starting']['minutes'] == '7')
    check('export: watermark + UI', pr['watermark'] == 'auto' and 'programPreview' in pr['ui'])
    check('export: device settings without password by default', data['device']['midiOut'] == 'loopMIDI Port' and 'pw' not in data['device'])
    pn.check('#pf-incpw')
    with pn.expect_download() as dl2: pn.click('#pf-export')
    check('export: password only when ticked', json.load(open(dl2.value.path()))['device'].get('pw') == 'secret')
    # import into a clean panel
    fresh = newp(1440, 1000); fresh.goto(D + '10-control-panel.html'); fresh.evaluate('localStorage.clear()'); fresh.reload(); fresh.wait_for_timeout(800)
    fresh.set_input_files('#pf-file', dl2.value.path()); fresh.wait_for_timeout(800)
    db = fresh.evaluate('NLC_PANEL.DB'); act = [x for x in db['list'] if x['id'] == db['active']][0]
    check('import restores positions, MIDI, screens', act['positions'].get('speaker', {}).get('top') == 40 and act['midi']['actions'].get('show:verse') and act['screens']['thanks'].get('h1') == 'Thank you')
    check('import restores connection password', fresh.input_value('#pw') == 'secret')
    fresh.close()
    pn.keyboard.press('Escape')

    pn.screenshot(path=str(OUTDIR / f'v8_panel.png'), full_page=True)
    pn.set_viewport_size({'width': 390, 'height': 900}); pn.wait_for_timeout(400)
    check('no horizontal scroll on phone', pn.evaluate('document.documentElement.scrollWidth<=390'))
    pn.screenshot(path=str(OUTDIR / f'v8_phone.png'), full_page=True)
    print('errors', errs)
    print(f'{sum(results)}/{len(results)} passed')
    br.close()
