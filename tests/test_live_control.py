import json, hashlib, base64, time
from playwright.sync_api import sync_playwright
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
OUTDIR = ROOT / 'tests' / 'out'; OUTDIR.mkdir(exist_ok=True)
D=(ROOT / 'dist').as_uri() + '/'
PW='secret'; SALT='c2FsdHNhbHQ='; CHAL='Y2hhbGxlbmdl'
def py_auth(pw,salt,ch):
    s=base64.b64encode(hashlib.sha256((pw+salt).encode()).digest()).decode()
    return base64.b64encode(hashlib.sha256((s+ch).encode()).digest()).decode()
import io as _io
from PIL import Image as _Im
_b=_io.BytesIO(); _Im.new('RGB',(160,90),(200,40,40)).save(_b,'JPEG'); SHOT='data:image/jpg;base64,'+base64.b64encode(_b.getvalue()).decode()
state={'program':'Sermon','scenes':['Starting Soon','Sermon','Slides','Be Right Back'],'log':[]}
clients=[]
def broadcast(evtype, data, bit):
    for c in list(clients):
        if c['ok'] and c['subs'] & bit:
            try: c['ws'].send(json.dumps({'op':5,'d':{'eventType':evtype,'eventIntent':bit,'eventData':data}}))
            except Exception as e: pass
def handler(ws):
    c={'ws':ws,'subs':0,'ok':False}; clients.append(c)
    ws.send(json.dumps({'op':0,'d':{'obsWebSocketVersion':'5.5.0','rpcVersion':1,'authentication':{'challenge':CHAL,'salt':SALT}}}))
    def on_msg(m):
        msg=json.loads(m); op=msg['op']; d=msg['d']
        if op==1:
            if d.get('authentication')!=py_auth(PW,SALT,CHAL):
                state['log'].append('auth-fail'); clients.remove(c); ws.close(code=4009, reason='Authentication failed.'); return
            c['ok']=True; c['subs']=d.get('eventSubscriptions',0); ws.send(json.dumps({'op':2,'d':{'negotiatedRpcVersion':1}}))
        elif op==6:
            rt=d['requestType']; rd=d.get('requestData',{}); resp={}
            if rt=='BroadcastCustomEvent':
                state['log'].append(rd['eventData'].get('role')+':'+rd['eventData'].get('action'))
                broadcast('CustomEvent', rd['eventData'], 1)
            elif rt=='GetSceneList':
                n=len(state['scenes']); resp={'currentProgramSceneName':state['program'],'scenes':[{'sceneName':s,'sceneIndex':n-1-i} for i,s in enumerate(state['scenes'])]}
            elif rt=='GetSourceScreenshot':
                state.setdefault('shots',[]).append(rd['sourceName']); resp={'imageData':SHOT}
            elif rt=='SetCurrentProgramScene':
                state['program']=rd['sceneName']; broadcast('CurrentProgramSceneChanged',{'sceneName':rd['sceneName']},4)
            ws.send(json.dumps({'op':7,'d':{'requestType':rt,'requestId':d['requestId'],'requestStatus':{'result':True,'code':100},'responseData':resp}}))
    ws.on_message(on_msg)
    ws.on_close(lambda *a: c in clients and clients.remove(c))
def bolls(route):
    parts=route.request.url.rstrip('/').split('/'); tr,book,ch=parts[-3:]
    data=[{'pk':i,'verse':i,'text':f'<S>{i}</S>Text of {tr} {book}:{ch}:{i}.'} for i in range(1,30)]
    route.fulfill(status=200, headers={'Access-Control-Allow-Origin':'*'}, content_type='application/json', body=json.dumps(data))

def check(label, cond): print(('PASS ' if cond else 'FAIL ')+label)
with sync_playwright() as p:
    b=p.chromium.launch(); ctx=b.new_context()
    ctx.route_web_socket('ws://localhost:4455/', handler); ctx.route('https://bolls.life/**', bolls)
    errs=[]
    CLOSE="document.querySelectorAll('dialog[open]').forEach(d=>d.close())"
    OPEN="document.getElementById('dlg-profiles').open||document.getElementById('dlg-profiles').showModal()"
    def newp(w,h):
        pg=ctx.new_page(); pg.set_viewport_size({'width':w,'height':h}); return pg
    ov=newp(1920,1080); ov.on('pageerror',lambda e: errs.append('ov '+str(e)))
    ov.goto(D+'09-live-graphics.html?obs_password=secret&debug=1'); ov.wait_for_timeout(800)
    check('overlay connected', 'connected' in ov.inner_text('#debug'))
    wm=lambda: ov.eval_on_selector('#wm','e=>e.classList.contains("show")')
    check('watermark shows when screen empty', wm())
    ov.screenshot(path=str(OUTDIR / f'e_wm.png'), omit_background=True)
    pn=newp(1400,1000); pn.on('pageerror',lambda e: errs.append('pn '+str(e)))
    pn.goto(D+'10-control-panel.html?obs_password=secret'); pn.wait_for_timeout(2200)
    check('panel OBS pill connected', 'connected' in pn.inner_text('#obsPill'))
    check('panel sees overlay', 'Overlay: connected' in pn.inner_text('#ovPill'))
    check('scenes listed in OBS order', pn.eval_on_selector_all('.scene','e=>e.map(x=>x.textContent.trim())')==state['scenes'])
    check('scenes are in right-side menu', pn.eval_on_selector('.side','e=>e.getBoundingClientRect().left')>900)
    check('program scene marked', pn.inner_text('.scene.pgm').strip()=='Sermon')
    # speaker
    pn.fill('#sp-name','Pastor Juan Pérez'); pn.fill('#sp-title','Lead Pastor'); pn.click('#sp-show'); pn.wait_for_timeout(1500)
    check('overlay shows speaker', ov.eval_on_selector('#g-speaker','e=>e.classList.contains("on")') and 'PASTOR JUAN' in ov.inner_text('#g-speaker').upper())
    check('panel on-air shows speaker', 'Speaker' in pn.inner_text('#onairWhat') and pn.eval_on_selector('#card-speaker','e=>e.classList.contains("showing")'))
    ov.screenshot(path=str(OUTDIR / f'e_speaker.png'), omit_background=True)
    check('watermark hidden while speaker shows', not wm())
    # verse replaces speaker
    pn.fill('#v-book','Juan'); pn.fill('#v-chapter','3'); pn.fill('#v-verse','16-17'); pn.fill('#v-tr','NIV'); pn.click('#v-show'); pn.wait_for_timeout(2200)
    check('overlay replaced speaker with verse', ov.eval_on_selector('#g-verse','e=>e.classList.contains("on")') and not ov.eval_on_selector('#g-speaker','e=>e.classList.contains("on")'))
    check('verse text looked up', ov.inner_text('#g-verse .verse')=='Text of NIV 43:3:16. Text of NIV 43:3:17.')
    check('verse reference', ov.inner_text('#g-verse .ref').upper()=='JUAN 3:16-17 · NIV')
    check('panel textarea filled', pn.input_value('#v-text').startswith('Text of NIV'))
    ov.screenshot(path=str(OUTDIR / f'e_verse.png'), omit_background=True)
    # save to list, then reload overlay -> restore state
    pn.click('#v-save'); pn.wait_for_timeout(300)
    check('verse saved to list', pn.locator('.item').count()==1)
    ov.reload(); ov.wait_for_timeout(2500)
    check('overlay restored verse after reload', ov.eval_on_selector('#g-verse','e=>e.classList.contains("on")'))
    pn.screenshot(path=str(OUTDIR / f'e_panel.png'), full_page=True)
    # remove
    pn.click('[data-remove="verse"]'); pn.wait_for_timeout(1200)
    check('remove hides verse', not ov.eval_on_selector('#g-verse','e=>e.classList.contains("on")'))
    check('panel shows nothing on screen', pn.inner_text('#onairWhat').startswith('Nothing'))
    check('watermark back after remove', wm())
    # message with auto-remove 5s
    pn.fill('#m-1','Welcome!'); pn.select_option('#m-hold','5'); pn.click('#m-show'); pn.wait_for_timeout(1500)
    check('message shown', ov.eval_on_selector('#g-message','e=>e.classList.contains("on")'))
    pn.wait_for_timeout(5000)
    check('message auto-removed', not ov.eval_on_selector('#g-message','e=>e.classList.contains("on")'))
    check('panel updated after auto-remove', pn.inner_text('#onairWhat').startswith('Nothing'))
    # display from saved list, then Esc
    pn.click('[data-show="0"]'); pn.wait_for_timeout(1500)
    check('list Display shows verse', ov.eval_on_selector('#g-verse','e=>e.classList.contains("on")'))
    pn.click('#card-speaker h2'); pn.keyboard.press('Escape'); pn.wait_for_timeout(1200)
    check('Esc removes all', not ov.eval_on_selector('#g-verse','e=>e.classList.contains("on")'))
    # top message
    pn.fill('#m-1','Welcome to New Life'); pn.fill('#m-2','Service starts at 10:30'); pn.select_option('#m-hold','0')
    pn.click('#m-pos button[data-v="top"]'); pn.wait_for_timeout(300)
    pn.screenshot(path=str(OUTDIR / f'e_panel2.png'))
    pn.click('#m-show'); pn.wait_for_timeout(1500)
    check('top message shown', ov.eval_on_selector('#g-message-top','e=>e.classList.contains("on")') and not ov.eval_on_selector('#g-message','e=>e.classList.contains("on")'))
    check('top message text', 'WELCOME TO NEW LIFE' in ov.inner_text('#g-message-top').upper())
    check('panel says top', '(top)' in pn.inner_text('#onairWhat'))
    ov.screenshot(path=str(OUTDIR / f'e_top.png'), omit_background=True)
    pn.click('#hideAll'); pn.wait_for_timeout(1200)
    # watermark off/on
    pn.click('#wm-mode button[data-v="off"]'); pn.wait_for_timeout(800)
    check('watermark off switch', not wm())
    pn.click('#wm-mode button[data-v="auto"]'); pn.wait_for_timeout(800)
    check('watermark auto switch', wm())
    # previews
    fr=pn.frame_locator('iframe[data-pv="message"]')
    check('message preview shows top tag', fr.locator('#g-message-top').get_attribute('class').find('on')>=0 and 'WELCOME TO NEW LIFE' in fr.locator('#g-message-top').inner_text().upper())
    pn.fill('#sp-name','Typed Live'); pn.wait_for_timeout(300)
    check('speaker preview updates as you type', 'TYPED LIVE' in pn.frame_locator('iframe[data-pv="speaker"]').locator('#g-speaker').inner_text().upper())
    check('verse preview shows text', 'Text of NIV' in pn.frame_locator('iframe[data-pv="verse"]').locator('#g-verse').inner_text())
    check('preview has no watermark', not pn.frame_locator('iframe[data-pv="speaker"]').locator('#wm').get_attribute('class'))
    # ---- countdown ring
    pn.fill('#sp-name','Timer Test'); pn.select_option('#sp-hold','10'); pn.click('#sp-show'); pn.wait_for_timeout(2500)
    num=pn.inner_text('#timerNum'); off=float(pn.eval_on_selector('#timerArc','e=>parseFloat(e.style.strokeDashoffset)'))
    check('countdown ring shows seconds left', num.isdigit() and 6<=int(num)<=9)
    check('ring is partly empty', off>5)
    check('not solid while counting', not pn.eval_on_selector('#timer','e=>e.classList.contains("solid")'))
    pn.screenshot(path=str(OUTDIR / f'e_timer.png'), clip={'x':0,'y':0,'width':1400,'height':150})
    pn.select_option('#sp-hold','0'); pn.click('#sp-show'); pn.wait_for_timeout(1800)
    check('solid circle when it stays on', pn.eval_on_selector('#timer','e=>e.classList.contains("solid") && getComputedStyle(e).display!=="none"'))
    pn.click('#hideAll'); pn.wait_for_timeout(1200)
    check('ring hidden when nothing on screen', pn.eval_on_selector('#timer','e=>getComputedStyle(e).display==="none"'))
    # ---- banner is separate, below the header
    hb=pn.eval_on_selector('header','e=>e.getBoundingClientRect().bottom'); bt=pn.eval_on_selector('#onair','e=>e.getBoundingClientRect().top')
    check('banner sits below the top bar', bt>=hb and not pn.eval_on_selector('header','e=>!!e.querySelector("#onair")'))
    # ---- preview is cropped to the graphic on a checkerboard
    h=pn.eval_on_selector('iframe[data-pv="speaker"]','e=>e.offsetHeight'); w=pn.eval_on_selector('iframe[data-pv="speaker"]','e=>e.offsetWidth')
    check('speaker preview is short (cropped, not 16:9)', 40<h<w*9/16*0.8)
    check('preview background is checkerboard', 'conic' in pn.eval_on_selector('.pv','e=>getComputedStyle(e).backgroundImage'))
    # ---- profiles
    pn.fill('#sp-name','Pastor Juan'); pn.fill('#sp-title','Pastor'); pn.click('#sp-save'); pn.wait_for_timeout(200)
    pn.fill('#m-1','Bienvenidos'); pn.click('#m-save'); pn.wait_for_timeout(200)
    check('speaker saved to list', pn.locator('#sp-list .item').count()==1)
    check('message saved to list', pn.locator('#m-list .item').count()==1)
    pn.locator('#sp-list [data-show="0"]').click(); pn.wait_for_timeout(1500)
    check('saved speaker displays', 'PASTOR JUAN' in ov.inner_text('#g-speaker').upper() and pn.locator('#sp-list .item.showing').count()==1)
    pn.click('#hideAll'); pn.wait_for_timeout(1000)
    names=pn.eval_on_selector_all('#profileSel option','e=>e.map(o=>o.textContent)')
    check('default profiles exist', names==['English service','Servicio en español'])
    pn.evaluate(CLOSE); pn.select_option('#profileSel', label='Servicio en español'); pn.wait_for_timeout(400)
    check('switching profile swaps lists', pn.locator('#sp-list .item').count()==0 and pn.input_value('#sp-name')=='')
    check('Spanish profile uses Spanish verse defaults', pn.input_value('#v-lang')=='es' and pn.get_attribute('#v-tr','placeholder')=='RV1960')
    pn.fill('#sp-name','Hermano Luis'); pn.click('#sp-save'); pn.wait_for_timeout(200)
    pn.evaluate(CLOSE); pn.select_option('#profileSel', label='English service'); pn.wait_for_timeout(400)
    check('switching back restores English lists', pn.locator('#sp-list .item').count()==1 and pn.input_value('#sp-name')=='Pastor Juan')
    pn.click('#profilesBtn'); pn.fill('#pf-new','Youth night'); pn.evaluate(OPEN); pn.click('#pf-create'); pn.wait_for_timeout(300)
    check('new profile created and selected', pn.eval_on_selector('#profileSel','e=>e.selectedOptions[0].textContent')=='Youth night')
    with pn.expect_download() as dl: pn.evaluate(OPEN); pn.click('#pf-exportall')
    path=dl.value.path(); data=json.load(open(path))
    check('export all writes every profile', [p['name'] for p in data['profiles']]==['English service','Servicio en español','Youth night'] and dl.value.suggested_filename=='nlc-profiles-all.json')
    pn.evaluate(CLOSE); pn.select_option('#profileSel', label='Servicio en español')
    with pn.expect_download() as dl2: pn.evaluate(OPEN); pn.click('#pf-export')
    one=json.load(open(dl2.value.path()))
    check('export one profile', len(one['profiles'])==1 and one['profiles'][0]['speakers'][0]['name']=='Hermano Luis')
    # delete Youth night (two clicks), then import file back on a clean panel
    pn.evaluate(CLOSE); pn.select_option('#profileSel', label='Youth night'); pn.evaluate(OPEN); pn.click('#pf-del'); pn.evaluate(OPEN); pn.click('#pf-del'); pn.wait_for_timeout(300)
    check('delete needs a second click and works', 'Youth night' not in pn.eval_on_selector_all('#profileSel option','e=>e.map(o=>o.textContent)'))
    fresh=ctx.new_page(); fresh.goto(D+'10-control-panel.html?obs_password=secret'); fresh.wait_for_timeout(500)
    fresh.evaluate("localStorage.clear()"); fresh.reload(); fresh.wait_for_timeout(800)
    check('clean panel starts with 2 default profiles', fresh.locator('#profileSel option').count()==2)
    fresh.click('#profilesBtn'); fresh.set_input_files('#pf-file', path); fresh.wait_for_timeout(600)
    opts=fresh.eval_on_selector_all('#profileSel option','e=>e.map(o=>o.textContent)')
    check('import adds profiles', 'Youth night' in opts and opts.count('English service')>=1)
    fresh.evaluate(CLOSE); fresh.select_option('#profileSel', label='Servicio en español'); fresh.wait_for_timeout(300)
    check('imported profile has its speakers', fresh.locator('#sp-list .item').count()==1)
    bad=str(OUTDIR / 'bad.json'); open(bad,'w').write('{"hello":1}')
    fresh.set_input_files('#pf-file', bad); fresh.wait_for_timeout(400)
    check('bad file shows an error', 'Could not import' in fresh.inner_text('#toast'))
    fresh.close()
    pn.evaluate(CLOSE); pn.select_option('#profileSel', label='English service'); pn.wait_for_timeout(300)
    pn.evaluate(CLOSE); pn.evaluate('window.scrollTo(0,0)'); pn.screenshot(path=str(OUTDIR / f'e_profiles.png'), full_page=True)
    # scenes
    pn.click('.scene[data-scene="Slides"]'); pn.wait_for_timeout(500)
    check('scene switched', state['program']=='Slides' and pn.inner_text('.scene.pgm').strip()=='Slides')
    # wrong password
    pn2=ctx.new_page(); pn2.goto(D+'10-control-panel.html?obs_password=wrong'); pn2.wait_for_timeout(1500)
    check('wrong password reported', 'wrong password' in pn2.inner_text('#obsPill'))
    # channel isolation
    ov2=newp(1920,1080); ov2.goto(D+'09-live-graphics.html?obs_password=secret&channel=side'); ov2.wait_for_timeout(800)
    pn.fill('#sp-name','Only main'); pn.click('#sp-show'); pn.wait_for_timeout(1500)
    check('other channel ignores main', not ov2.eval_on_selector('#g-speaker','e=>e.classList.contains("on")'))
    pn.screenshot(path=str(OUTDIR / f'e_panel_scrolled.png')) if pn.evaluate('window.scrollTo(0,600)') is None else None
    check('on-screen bar stays at top when scrolled', 60<pn.eval_on_selector('#onair','e=>e.getBoundingClientRect().top')<130)
    pn.evaluate('window.scrollTo(0,0)')
    pn.set_viewport_size({'width':390,'height':900}); pn.wait_for_timeout(300)
    pn.screenshot(path=str(OUTDIR / f'e_phone.png'), full_page=True)
    check('no horizontal scroll on phone', pn.evaluate('document.documentElement.scrollWidth<=390'))
    print('overflow:', pn.evaluate("""[...document.querySelectorAll('body *')].filter(e=>e.getBoundingClientRect().right>391 && getComputedStyle(e).position!=='fixed').slice(0,8).map(e=>e.tagName+'.'+e.className+'#'+e.id+' '+Math.round(e.getBoundingClientRect().right))"""))
    print('log tail', state['log'][-6:]); print('errors', errs)
    b.close()
