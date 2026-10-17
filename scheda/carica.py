#!/usr/bin/env python3
"""Fills Giocapensa's App Store listing through the App Store Connect API.

For every language in testi.json it sets name, subtitle and privacy policy URL (app information),
description, keywords, promotional text and support URL (the version being prepared), and the
6.9-inch screenshots; it also sets categories and copyright. Price, countries, age rating, app
privacy, review contact and the submission stay manual in App Store Connect.
It can run again at any time: texts are rewritten, screenshots are replaced only where they differ.

Environment: APPSTORE_KEY_ID, APPSTORE_ISSUER_ID, APPSTORE_P8 (text of the .p8 key);
optional VERSIONE (version to fill, e.g. 1.1; default: the one being prepared), ASC_API (tests only).
usage: python3 carica.py [folder with testi.json and schermate/]
Messages for the parent are in Italian and go out as GitHub annotations, readable from the API.
"""
import glob, hashlib, http.client, json, os, sys, time, urllib.error, urllib.parse, urllib.request

API = os.environ.get('ASC_API', 'https://api.appstoreconnect.apple.com').rstrip('/')
DIR = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__)))
EDITABLE = {'PREPARE_FOR_SUBMISSION', 'DEVELOPER_REJECTED', 'REJECTED', 'METADATA_REJECTED', 'INVALID_BINARY'}
DISPLAY = 'APP_IPHONE_67'            # the 6.9-inch slot of App Store Connect (1320 x 2868)
SUMMARY = []                          # rows for the run page


class Apple(Exception):
    pass


def _esc(s, prop=False):
    s = str(s).replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
    return s.replace(':', '%3A').replace(',', '%2C') if prop else s


def note(kind, title, msg):
    print('::%s title=%s::%s' % (kind, _esc(title, True), _esc(msg)), flush=True)


def fail(msg):
    note('error', 'Scheda App Store', msg)
    sys.exit(1)


_tok = {'t': None, 'at': 0}


def token():
    now = int(time.time())
    if not _tok['t'] or now - _tok['at'] > 600:
        import jwt                    # PyJWT, with cryptography for ES256
        key = os.environ['APPSTORE_P8'].strip().replace('\\n', '\n')
        _tok['t'] = jwt.encode({'iss': os.environ['APPSTORE_ISSUER_ID'].strip(), 'iat': now, 'exp': now + 1080, 'aud': 'appstoreconnect-v1'},
                               key, algorithm='ES256', headers={'kid': os.environ['APPSTORE_KEY_ID'].strip(), 'typ': 'JWT'})
        _tok['at'] = now
    return _tok['t']


def describe(method, path, status, raw):
    try:
        errs = json.loads(raw).get('errors') or []
    except ValueError:
        errs = []
    parts = []
    for e in errs[:4]:
        where = (e.get('source') or {}).get('pointer') or (e.get('source') or {}).get('parameter') or ''
        parts.append(' '.join(x for x in (e.get('code', ''), '-', e.get('detail') or e.get('title') or '', ('(' + where + ')') if where else '') if x))
    text = '%s %s → %d: %s' % (method, urllib.parse.unquote(path.replace(API, '')), status, '; '.join(parts) or raw[:300])
    if status == 401:
        text += '. Apple non accetta la chiave: controlla i segreti APPSTORE_KEY_ID, APPSTORE_ISSUER_ID e APPSTORE_P8 (passo C1), senza spazi in più.'
    elif status == 403:
        text += '. Apple rifiuta l\'operazione: la chiave deve avere accesso Admin, e in App Store Connect → Business gli accordi devono essere accettati.'
    return text


def call(method, path, body=None, query=None):
    url = path if path.startswith('http') else API + path
    if query:
        url += ('&' if '?' in url else '?') + urllib.parse.urlencode(query)
    data = None if body is None else json.dumps(body).encode()
    for attempt in range(5):
        req = urllib.request.Request(url, data=data, method=method, headers={'Authorization': 'Bearer ' + token(), 'Content-Type': 'application/json', 'Accept': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                raw = r.read()
            return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            raw = e.read().decode('utf-8', 'replace')
            if e.code in (429, 500, 502, 503, 504) and attempt < 4:
                time.sleep(5 * (attempt + 1))
                continue
            raise Apple(describe(method, url, e.code, raw))
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if attempt < 4:
                time.sleep(5 * (attempt + 1))
                continue
            raise Apple('%s %s: Apple non risponde (%s)' % (method, path, e))


def items(path, query=None):
    q = dict(query or {})
    q.setdefault('limit', 50)
    res, out = call('GET', path, query=q), []
    while True:
        out += res.get('data') or []
        nxt = (res.get('links') or {}).get('next')
        if not nxt:
            return out
        res = call('GET', nxt)


def state(x):
    a = x.get('attributes') or {}
    return a.get('appVersionState') or a.get('state') or a.get('appStoreState') or ''


def rel(kind, id_):
    return {'data': {'type': kind, 'id': id_}}


def upsert(kind, have, locale, attrs, parent_rel, parent_kind, parent_id):
    """PATCH the localization of this locale if it exists, else create it."""
    if locale in have:
        call('PATCH', '/v1/%s/%s' % (kind, have[locale]), {'data': {'type': kind, 'id': have[locale], 'attributes': attrs}})
        return have[locale], 'aggiornata'
    a = dict(attrs, locale=locale)
    res = call('POST', '/v1/' + kind, {'data': {'type': kind, 'attributes': a, 'relationships': {parent_rel: rel(parent_kind, parent_id)}}})
    return res['data']['id'], 'aggiunta'


def md5(path):
    return hashlib.md5(open(path, 'rb').read()).hexdigest()


def put_part(op, data):
    """Sends one part of a file to the address Apple gives, with exactly the headers Apple asks for."""
    u = urllib.parse.urlsplit(op['url'])
    chunk = data[op['offset']:op['offset'] + op['length']]
    headers = {h['name']: h['value'] for h in op.get('requestHeaders') or []}
    headers['Content-Length'] = str(len(chunk))
    target = u.path + ('?' + u.query if u.query else '')
    for attempt in range(5):
        conn = (http.client.HTTPSConnection if u.scheme == 'https' else http.client.HTTPConnection)(u.netloc, timeout=120)
        try:
            conn.request(op.get('method') or 'PUT', target, body=chunk, headers=headers)
            r = conn.getresponse()
            r.read()
            if r.status < 300:
                return
            err = 'HTTP %d' % r.status
        except (OSError, http.client.HTTPException) as e:
            err = str(e)
        finally:
            conn.close()
        if attempt < 4:
            time.sleep(4 * (attempt + 1))
    raise Apple('invio di una schermata non riuscito (%s)' % err)


def upload(set_id, path, checksum):
    data = open(path, 'rb').read()
    res = call('POST', '/v1/appScreenshots', {'data': {'type': 'appScreenshots', 'attributes': {'fileName': os.path.basename(path), 'fileSize': len(data)},
                                                       'relationships': {'appScreenshotSet': rel('appScreenshotSets', set_id)}}})['data']
    for op in res['attributes'].get('uploadOperations') or []:
        put_part(op, data)
    call('PATCH', '/v1/appScreenshots/' + res['id'], {'data': {'type': 'appScreenshots', 'id': res['id'], 'attributes': {'uploaded': True, 'sourceFileChecksum': checksum}}})
    return res['id']


def main():
    for k in ('APPSTORE_KEY_ID', 'APPSTORE_ISSUER_ID', 'APPSTORE_P8'):
        if not os.environ.get(k, '').strip():
            fail('Manca il segreto %s: aggiungilo in Settings → Secrets and variables → Actions del repository (passo C1).' % k)
    T = json.load(open(os.path.join(DIR, 'testi.json'), encoding='utf-8'))
    shots = {}
    for loc, L in T['lingue'].items():
        files = sorted(glob.glob(os.path.join(DIR, 'schermate', L['schermate'], '*.png')))
        if not files:
            fail('Mancano le schermate nella cartella scheda/schermate/%s.' % L['schermate'])
        shots[loc] = files

    apps = call('GET', '/v1/apps', query={'filter[bundleId]': T['bundle']}).get('data') or []
    if not apps:
        fail('In App Store Connect non c\'è ancora un\'app con identificativo %s: creala prima (passo B6), poi rilancia.' % T['bundle'])
    app = apps[0]['id']
    print('App:', apps[0]['attributes'].get('name'), app, flush=True)

    # app information: categories, then name, subtitle, privacy URL in every language
    infos = [x for x in items('/v1/apps/%s/appInfos' % app) if state(x) in EDITABLE]
    if not infos:
        fail('Le informazioni dell\'app adesso non si possono modificare (app in revisione o già pubblicata senza una versione nuova).')
    info = infos[0]['id']
    call('PATCH', '/v1/appInfos/' + info, {'data': {'type': 'appInfos', 'id': info, 'relationships': {k: rel('appCategories', v) for k, v in T['categorie'].items()}}})
    print('Categorie:', ', '.join(T['categorie'].values()), flush=True)
    have = {x['attributes']['locale']: x['id'] for x in items('/v1/appInfos/%s/appInfoLocalizations' % info)}
    for loc, L in T['lingue'].items():
        _, what = upsert('appInfoLocalizations', have, loc, {'name': L['name'], 'subtitle': L['subtitle'], 'privacyPolicyUrl': T['url']['privacy']}, 'appInfo', 'appInfos', info)
        print('%-8s nome e sottotitolo: %s' % (loc, what), flush=True)

    # the version being prepared: copyright, texts, screenshots
    want = os.environ.get('VERSIONE', '').strip()
    vers = [v for v in items('/v1/apps/%s/appStoreVersions' % app, {'filter[platform]': 'IOS'}) if state(v) in EDITABLE and (not want or v['attributes'].get('versionString') == want)]
    if not vers:
        fail('Non c\'è nessuna versione %sin preparazione per iPhone: in App Store Connect crea la versione (+ accanto a «App iOS»), poi rilancia.' % (want + ' ' if want else ''))
    ver = vers[0]
    print('Versione:', ver['attributes'].get('versionString'), state(ver), flush=True)
    call('PATCH', '/v1/appStoreVersions/' + ver['id'], {'data': {'type': 'appStoreVersions', 'id': ver['id'], 'attributes': {'copyright': T['copyright']}}})
    have = {x['attributes']['locale']: x['id'] for x in items('/v1/appStoreVersions/%s/appStoreVersionLocalizations' % ver['id'])}
    vloc = {}
    for loc, L in T['lingue'].items():
        attrs = {'description': L['description'], 'keywords': L['keywords'], 'promotionalText': L['promotionalText'], 'supportUrl': T['url']['support']}
        vloc[loc], what = upsert('appStoreVersionLocalizations', have, loc, attrs, 'appStoreVersion', 'appStoreVersions', ver['id'])
        print('%-8s descrizione e parole chiave: %s' % (loc, what), flush=True)

    sent, same, pending = 0, 0, []
    for loc, files in shots.items():
        sets = items('/v1/appStoreVersionLocalizations/%s/appScreenshotSets' % vloc[loc])
        s = next((x for x in sets if x['attributes'].get('screenshotDisplayType') == DISPLAY), None)
        if s is None:
            s = call('POST', '/v1/appScreenshotSets', {'data': {'type': 'appScreenshotSets', 'attributes': {'screenshotDisplayType': DISPLAY},
                                                                 'relationships': {'appStoreVersionLocalization': rel('appStoreVersionLocalizations', vloc[loc])}}})['data']
        old = items('/v1/appScreenshotSets/%s/appScreenshots' % s['id'])
        sums = [md5(f) for f in files]
        if [x['attributes'].get('sourceFileChecksum') for x in old] == sums and all(((x['attributes'].get('assetDeliveryState') or {}).get('state')) == 'COMPLETE' for x in old):
            same += len(files)
            print('%-8s schermate: già queste' % loc, flush=True)
            continue
        for x in old:
            call('DELETE', '/v1/appScreenshots/' + x['id'])
        ids = [upload(s['id'], f, h) for f, h in zip(files, sums)]
        sent += len(ids)
        pending.append((loc, s['id'], ids))
        print('%-8s schermate: %d inviate' % (loc, len(ids)), flush=True)

    # Apple checks every image: wait for the verdict, then fix the order
    deadline, late = time.time() + 900, []
    for loc, set_id, ids in pending:
        while True:
            now = {x['id']: x for x in items('/v1/appScreenshotSets/%s/appScreenshots' % set_id)}
            st = {i: ((now.get(i, {}).get('attributes') or {}).get('assetDeliveryState') or {}) for i in ids}
            bad = [(i, v) for i, v in st.items() if v.get('state') == 'FAILED']
            if bad:
                why = '; '.join(' '.join(filter(None, (e.get('code'), e.get('description') or e.get('detail')))) for _, v in bad for e in (v.get('errors') or [])) or 'motivo non indicato'
                fail('Apple ha scartato %s di %s: %s' % ('1 schermata' if len(bad) == 1 else '%d schermate' % len(bad), loc, why))
            if all(v.get('state') == 'COMPLETE' for v in st.values()):
                break
            if time.time() > deadline:
                late.append(loc)
                break
            time.sleep(float(os.environ.get('ASC_POLL', 8)))
        if [x for x in now if x in ids] != ids:
            call('PATCH', '/v1/appScreenshotSets/%s/relationships/appScreenshots' % set_id, {'data': [{'type': 'appScreenshots', 'id': i} for i in ids]})
    if late:
        note('warning', 'Schermate', 'Apple sta ancora controllando le schermate di: %s. Di solito finisce da sola; se in App Store Connect restano vuote, rilancia il flusso.' % ', '.join(late))

    langs = len(T['lingue'])
    note('notice', 'Scheda compilata', '%d lingue: testi, categorie e copyright a posto; schermate inviate %d, già presenti %d.' % (langs, sent, same))
    out = os.environ.get('GITHUB_STEP_SUMMARY')
    if out:
        with open(out, 'a', encoding='utf-8') as f:
            f.write('## Scheda App Store compilata\n\n| Lingua | Nome | Sottotitolo | Schermate |\n| --- | --- | --- | --- |\n')
            for loc, L in T['lingue'].items():
                f.write('| %s | %s | %s | %d |\n' % (loc, L['name'], L['subtitle'], len(shots[loc])))
            f.write('\nRestano a mano in App Store Connect: classificazione per età, diritti sui contenuti, prezzo e disponibilità, privacy dell\'app, dati per la revisione, build e invio.\n')


if __name__ == '__main__':
    try:
        main()
    except Apple as e:
        fail(str(e))
