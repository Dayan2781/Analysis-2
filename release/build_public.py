#!/usr/bin/env python3
"""Make the public site from the full site: homework solutions (hints, answers, solutions,
similar problems) of week N stay hidden until the end of week N + delay_weeks.

usage: python3 release/build_public.py site _public [YYYY-MM-DD]
Settings: release/release.json  (week1_monday, delay_weeks, utc_offset_hours)."""
import sys, os, re, json, shutil, datetime
import lxml.html as H

src, out = sys.argv[1], sys.argv[2]
cfg = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'release.json')))
tz = datetime.timezone(datetime.timedelta(hours=cfg.get('utc_offset_hours', 8)))
today = (datetime.date.fromisoformat(sys.argv[3]) if len(sys.argv) > 3
         else datetime.datetime.now(tz).date())
start = datetime.date.fromisoformat(cfg['week1_monday'])
week = (today - start).days // 7 + 1          # current teaching week
released = week - 1 - cfg['delay_weeks']       # homework of weeks <= released is fully shown
print(f'{today}: week {week}; homework solutions shown for weeks 1..{max(released, 0)}')

if os.path.exists(out):
    shutil.rmtree(out)
shutil.copytree(src, out)

NOTE = ('<p class="hw-hidden-note"><em>Гэрийн даалгаврын заавар, хариу, бодолт '
        '{d} нээгдэнэ.</em></p>')
hidden_text = {}
for n in range(1, 17):
    if n <= released:
        continue
    f = os.path.join(out, f'w{n:02d}-hw.html')
    if not os.path.exists(f):
        continue
    opens = start + datetime.timedelta(weeks=n + cfg['delay_weeks'])   # Monday after week n+delay
    s = open(f, encoding='utf-8').read()
    d = H.document_fromstring(s)
    k = 0
    for sol in d.xpath('//*[contains(concat(" ",@class," ")," solutions ")]'):
        sol.drop_tree(); k += 1
    for art in d.xpath('//article[@id]'):
        hidden_text[art.get('id')] = re.sub(r'\\\(.*?\\\)|\s+', ' ', art.text_content()).strip()
    sec = d.xpath('//section[contains(concat(" ",@class," ")," exercises ")]')
    if sec:
        h = sec[0].xpath('./*[contains(concat(" ",@class," ")," heading ")]')
        note = H.fragment_fromstring(NOTE.format(d=opens.strftime('%Y-%m-%d')))
        (h[0].addnext(note) if h else sec[0].insert(0, note))
    html = H.tostring(d, encoding='unicode', doctype='<!DOCTYPE html>')
    if 'charset' not in html[:3000]:
        html = re.sub(r'(<head\b[^>]*>)', r'\1\n<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">', html, count=1)
    open(f, 'w', encoding='utf-8').write(html)
    print(f'  week {n}: hid {k} solution blocks (opens {opens})')

# search index: hidden homework entries keep only the statement text
idx = os.path.join(out, 'lunr-pretext-search-index.js')
if os.path.exists(idx) and hidden_text:
    s = open(idx, encoding='utf-8').read()
    def fix(m):
        e = json.loads(m.group(0))
        if e.get('id') in hidden_text:
            e['body'] = hidden_text[e['id']]
        return json.dumps(e, ensure_ascii=False, indent=2)
    s = re.sub(r'\{\s*"id": "w\d\d-hw[^"]*".*?\n\}', fix, s, flags=re.S)
    open(idx, 'w', encoding='utf-8').write(s)
