import json
from playwright.sync_api import sync_playwright
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
OUTDIR = ROOT / 'tests' / 'out'; OUTDIR.mkdir(exist_ok=True)
D=(ROOT / 'dist').as_uri() + '/'
calls=[]
def bolls(route):
    url=route.request.url; calls.append(url)
    parts=url.rstrip('/').split('/')   # .../get-text/TR/book/ch
    tr,book,ch=parts[-3],parts[-2],parts[-1]
    if tr in ('NIV','RV1960','KJV') and book=='43' and ch=='3':
        data=[{'pk':i,'verse':i,'text':f'<S>{1000+i}</S>Verse {i} of John 3 ({tr}) <i>word</i>&amp;more<br/>'} for i in range(1,37)]
        route.fulfill(status=200, headers={'Access-Control-Allow-Origin':'*','Content-Type':'application/json'}, body=json.dumps(data))
    elif tr=='DOWN':
        route.abort()
    else:
        route.fulfill(status=404, body='[]')
def bibleapi(route):
    calls.append(route.request.url)
    route.fulfill(status=200, headers={'Access-Control-Allow-Origin':'*','Content-Type':'application/json'},
      body=json.dumps({'verses':[{'text':'Fallback text for Psalm 23:1.\n'}],'text':'x'}))
cases=[
 ('08-lower-third-verse.html?book=John&chapter=3&verse=16-17&translation=NIV', '#sc'),
 ('08-lower-third-verse.html?lang=es&book=Juan&chapter=3&verse=16', '#sc'),
 ('08-lower-third-verse.html?book=Psalm&chapter=23&verse=1', '#sc'),
 ('08-lower-third-verse.html?book=John&chapter=3', '#sc'),
 ('08-lower-third-verse.html?book=John&verse=16', '#sc'),
 ('08-lower-third-verse.html?verse=John+3:16', '#sc'),
 ('08-lower-third-verse.html?reference=John+3:18&verse=null', '#sc'),
 ('03-camera-sermon.html?message_title=Grace&book=1+Corinthians&chapter=13&verse=4-7&translation=ESV', '#stage'),
 ('03-camera-sermon.html?message_title=Grace&book=John&chapter=null&verse=16', '#stage'),
]
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':1920,'height':1080}); errs=[]
    pg.on('pageerror',lambda e: errs.append(str(e)))
    pg.route('https://bolls.life/**', bolls); pg.route('https://bible-api.com/**', bibleapi)
    for i,(u,sel) in enumerate(cases):
        calls.clear(); pg.goto(D+u); pg.wait_for_timeout(2500)
        vis = pg.evaluate("""() => [...document.querySelectorAll('[data-t], #vtext')].filter(e => e.offsetParent && e.textContent.trim()).map(e => e.textContent.trim().slice(0,80))""")
        print(f'\n[{i}] {u}\n   calls={[c.split("/",3)[-1] for c in calls]}\n   visible={vis}')
        pg.screenshot(path=str(OUTDIR / f'v{i}.png'), omit_background=True)
    b.close(); print('\nerrors', errs)
