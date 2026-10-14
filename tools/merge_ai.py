#!/usr/bin/env python3
"""Insert AI-generated content (ai/chNN.xml) into a converted chapter (chNN.ptx).

ai/chNN.xml format:
<ai>
  <preview> <exploration>...</exploration> </preview>
  <section ref="wNN-sK"> <exercise>...</exercise> ... </section>
  <homework> <exercise>...</exercise> ... </homework>
</ai>
Every inserted top element gets component="ai" so it can be switched off in
publication.ptx (<version include="..."/>).
"""
import re, sys
import lxml.etree as E

chap_path, ai_path, out_path = sys.argv[1:4]
chap = open(chap_path, encoding='utf-8').read()
ai = E.parse(ai_path).getroot()

def ser(el):
    return E.tostring(el, encoding='unicode', with_tail=False)

def inner(el):
    return ''.join(ser(c) for c in el if isinstance(c.tag, str))

def tag_ai(xml):
    # add component="ai" to the first element of each top-level child
    return re.sub(r'^<(\w+)', r'<\1 component="ai"', xml, count=1)

wk = re.search(r'xml:id="ch-(w\d\d)"', chap).group(1)

# preview
pv = ai.find('preview')
if pv is not None:
    blocks = ''.join(tag_ai(ser(c)) for c in pv if isinstance(c.tag, str))
    if '<introduction>' in chap.split('<section', 1)[0]:
        chap = chap.replace('<!--AI-PREVIEW-->', blocks, 1)
    else:
        chap = chap.replace('<!--AI-PREVIEW-->', '<introduction>' + blocks + '</introduction>', 1)
chap = chap.replace('<!--AI-PREVIEW-->', '')

# sections
used = set()
for sec in ai.findall('section'):
    ref = sec.get('ref')
    marker = f'<!--AI-SECTION {ref}-->'
    if marker not in chap:
        print(f'WARNING: no section marker {ref}', file=sys.stderr)
        continue
    title = sec.get('title', 'Шалгах дасгал (AI)')
    xml = (f'<exercises component="ai" xml:id="{ref}-ai"><title>{title}</title>'
           + inner(sec) + '</exercises>')
    chap = chap.replace(marker, xml)
    used.add(ref)
chap = re.sub(r'<!--AI-SECTION [^>]*-->', '', chap)

# homework
hw = ai.find('homework')
if hw is not None:
    title = hw.get('title', 'Нэмэлт бодлого (AI)')
    intro = hw.find('introduction')
    exs = ''.join(ser(c) for c in hw if isinstance(c.tag, str) and c.tag != 'introduction')
    intro_xml = ser(intro) if intro is not None else '<introduction><p>Доорх бодлогуудыг хиймэл оюун ухаанаар үүсгэсэн. Заавар, хариу, бодолтыг гарчиг дээр нь дарж нээнэ.</p></introduction>'
    hwblock = chap[chap.index(f'<exercises xml:id="{wk}-hw"'):]
    hwblock = hwblock[:hwblock.index('</exercises>')]
    if '<subexercises' in hwblock:
        xml = f'<subexercises component="ai" xml:id="{wk}-hw-ai"><title>{title}</title>{intro_xml}{exs}</subexercises>'
    elif '<exercise' in hwblock:
        xml = f'<exercisegroup component="ai"><title>{title}</title>{intro_xml}{exs}</exercisegroup>'
    else:
        xml = intro_xml.replace('<introduction>', '<introduction component="ai">') + exs.replace('<exercise>', '<exercise component="ai">')
    chap = chap.replace('<!--AI-HOMEWORK-->', xml, 1)
chap = chap.replace('<!--AI-HOMEWORK-->', '')
open(out_path, 'w', encoding='utf-8').write(chap)
