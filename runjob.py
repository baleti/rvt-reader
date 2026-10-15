import sys, os, json, time, ssl, urllib.request
port, f = sys.argv[1], sys.argv[2]
tok = open(os.path.expandvars(r'%APPDATA%\revit-ballet\runtime\network\token')).read().strip()
ctx = ssl._create_unverified_context()
def api(m, path, body=None):
    r = urllib.request.Request(f'https://127.0.0.1:{port}{path}', method=m, headers={'X-Auth-Token': tok, 'Content-Type': 'application/json'}, data=json.dumps(body).encode() if body is not None else None)
    try: return json.load(urllib.request.urlopen(r, context=ctx, timeout=60))
    except urllib.error.HTTPError as e: return {'http': e.code, 'body': e.read().decode()[:300]}
code = open(f, encoding='utf-8').read(); dialogs = []
for attempt in range(8):
    j = api('POST', '/v1/jobs', {'engine': 'roslyn', 'code': code, 'timeoutMs': 280000, 'wait': 0})
    t0 = time.time(); blocked = False
    while time.time() - t0 < 300:
        j = api('GET', '/v1/jobs/' + j['id'])
        if j.get('state') in ('done', 'failed', 'cancelled', 'timeout', 'timedout', 'error'): break
        d = api('GET', '/v1/dialog').get('dialog')
        if d and time.time() - t0 > 2:
            dialogs.append((d.get('title'), (d.get('text') or '')[:100], d.get('buttons')))
            btn = (d.get('buttons') or ['OK'])[0]
            for b in (d.get('buttons') or []):
                if b.lower() in ('ok', 'close', 'yes', 'continue'): btn = b; break
            api('POST', '/v1/dialog/respond', {'button': btn}); time.sleep(1)
        time.sleep(1)
    if (j.get('error') or {}).get('kind') == 'blocked_by_dialog' and attempt < 7:
        continue
    break
print(j.get('state')); print((j.get('output') or '')[-6000:])
if j.get('error'): print('ERROR', json.dumps(j['error'])[:1200])
if dialogs: print('DIALOGS answered:', dialogs)
