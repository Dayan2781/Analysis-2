"""Append a pre-generated similar problem to each <exercise> of a chapter.
usage: add_similar.py chNN.ptx simNN.json   (edits chNN.ptx in place)
Keys come from extract.py (hash of the statement text), so they survive reordering."""
import sys, json, re, lxml.etree as E
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract import key
chap, simf = sys.argv[1:3]
sim = json.load(open(simf, encoding='utf-8'))
def esc(s): return s.replace('&', '&amp;').replace('<', '\\lt ').replace('>', '\\gt ')
def para(s):
    out = []
    for i, part in enumerate(re.split(r'(\$\$.*?\$\$|\$.*?\$)', s)):
        if part.startswith('$$'): out.append('<md>' + esc(part[2:-2]) + '</md>')
        elif part.startswith('$'): out.append('<m>' + esc(part[1:-1]) + '</m>')
        else: out.append(part.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))
    x = '<p>' + ''.join(out) + '</p>'
    return x.replace('<p></p>', '').replace('<p> </p>', '')
t = E.parse(chap); n = 0
for x in t.iter('exercise'):
    st = x.find('statement')
    if st is None or any((s.findtext('title') or '').startswith('Төстэй') for s in x.findall('solution')): continue
    it = sim.get(key(st))
    if not it: continue
    xml = ('<solution component="ai"><title>Төстэй бодлого (AI)</title>' + para(it['p'])
           + para('Заавар: ' + it['h']).replace('<p>Заавар: ', '<p><em>Заавар:</em> ', 1)
           + para('Хариу: ' + it['a']).replace('<p>Хариу: ', '<p><em>Хариу:</em> ', 1) + '</solution>')
    x.append(E.fromstring(xml)); n += 1
t.write(chap, encoding='utf-8', xml_declaration=True)
print(chap, n, 'similar problems added')
