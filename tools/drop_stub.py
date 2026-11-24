"""Remove placeholder chapter(s) kept only to preserve LaTeX chapter numbering (e.g. ch-w05).
Usage: drop_stub.py <web-dir> 05 [..]"""
import sys, os, re, glob, json
import lxml.html as H
root = sys.argv[1]; stubs = [f'ch-w{n}' for n in sys.argv[2:]]
pages = [os.path.basename(p) for p in sorted(glob.glob(os.path.join(root, 'ch-w*.html')))]
# neighbours in reading order for prev/next buttons
def neighbour(stub, d):
    toc = H.parse(os.path.join(root, 'w01-s1.html'))
    hrefs = []
    for a in toc.xpath('//nav[contains(@class,"toc")]//a[@href]'):
        h = a.get('href').split('#')[0]
        if h not in hrefs: hrefs.append(h)
    if stub + '.html' not in hrefs: return None
    i = hrefs.index(stub + '.html')
    return hrefs[i - 1] if d < 0 else hrefs[i + 1]
repl = {s: (neighbour(s, -1), neighbour(s, +1)) for s in stubs}
n = 0
for f in glob.glob(os.path.join(root, '**', '*.html'), recursive=True):
    s = open(f, encoding='utf-8').read()
    if not any(st in s for st in stubs): continue
    d = H.document_fromstring(s)
    for st in stubs:
        prev, nxt = repl[st]
        for li in d.xpath(f'//li[contains(@class,"toc-chapter")][.//a[starts-with(@href,"{st}.html")]]'):
            li.drop_tree()
        for li in d.xpath(f'//main//li[a[@href="{st}.html"]]'):
            li.drop_tree()
        for a in d.xpath(f'//a[starts-with(@href,"{st}.html")]'):
            c = a.get('class') or ''
            if 'previous-button' in c and prev: a.set('href', prev)
            elif 'next-button' in c and nxt: a.set('href', nxt)
    out = H.tostring(d, encoding='unicode', doctype='<!DOCTYPE html>')
    if 'charset' not in out[:3000]:
        out = re.sub(r'(<head\b[^>]*>)', r'\1\n<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">', out, count=1)
    open(f, 'w', encoding='utf-8').write(out); n += 1
for st in stubs:
    p = os.path.join(root, st + '.html')
    if os.path.exists(p): os.remove(p)
idx = os.path.join(root, 'lunr-pretext-search-index.js')
if os.path.exists(idx):
    s = open(idx, encoding='utf-8').read()
    for st in stubs:
        s = re.sub(r'\{\s*"id": "' + st + r'".*?\n\},?\n', '', s, flags=re.S)
    open(idx, 'w', encoding='utf-8').write(s)
print('drop_stub:', n, 'files rewritten; removed', stubs)
