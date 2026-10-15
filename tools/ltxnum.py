#!/usr/bin/env python3
"""Keep the LaTeX book's numbering in the PreTeXt web book.
  ltxnum.py extract chNN.ptx numbers/chNN.json   -- record ltx="..." numbers in document order, strip them
  ltxnum.py apply <web output dir> numbers/       -- rewrite numbers in the built HTML
PreTeXt numbers all blocks of a chapter with one counter; the LaTeX book (main.tex) has separate
counters (theorem+corollary, definition, example, proposition per chapter; lemma per section;
problem book-wide; remark/note unnumbered), and some sections are unnumbered (section*, chapter*)."""
import sys, os, re, json, glob
import lxml.etree as E

BLOCKS = ('theorem', 'lemma', 'corollary', 'proposition', 'definition', 'example', 'remark', 'note')
DIVS = ('exercises',)

def is_ai(el):
    return any(a.get('component') == 'ai' for a in el.iterancestors()) or el.get('component') == 'ai'

def inline_ex(el):
    return not any(a.tag in ('exercises', 'subexercises', 'exercisegroup') for a in el.iterancestors())

def extract(chap, out):
    t = E.parse(chap)
    blocks, secs = [], {}
    for el in t.iter():
        if not isinstance(el.tag, str):
            continue
        if el.tag in ('section', 'exercises') and el.get('ltx') is not None:
            secs[el.get('{http://www.w3.org/XML/1998/namespace}id')] = el.get('ltx')
        elif (el.tag in BLOCKS or (el.tag == 'exercise' and inline_ex(el))) and not is_ai(el):
            blocks.append([el.tag, el.get('ltx')])
        if 'ltx' in el.attrib:
            del el.attrib['ltx']
    t.write(chap, encoding='utf-8', xml_declaration=True)
    json.dump({'blocks': blocks, 'sections': secs}, open(out, 'w'), ensure_ascii=False)
    print(chap, len(blocks), 'blocks', len(secs), 'sections')

# ---------------------------------------------------------------- HTML side
import lxml.html as H
CLS = {'theorem', 'lemma', 'corollary', 'proposition', 'definition', 'example', 'remark', 'note', 'exercise'}

def art_type(a):
    c = (a.get('class') or '').split()
    return c[0] if c else ''

def heading_num(a):
    h = a.xpath('./*[contains(concat(" ",@class," ")," heading ")]')
    if not h:
        return None, None
    n = h[0].xpath('./span[@class="codenumber"]')
    return h[0], (n[0] if n else None)

def apply(root, numdir):
    toc = H.parse(os.path.join(root, 'w01-s1.html'))
    blockmap, secmap = {}, {}   # id -> (old, new)
    for f in sorted(glob.glob(os.path.join(numdir, 'ch*.json'))):
        nn = int(os.path.basename(f)[2:4]); data = json.load(open(f))
        for sid, num in data['sections'].items():
            secmap[sid] = num
        # chapter pages in TOC order
        li = toc.xpath(f'//nav[contains(@class,"toc")]//li[contains(@class,"toc-chapter")][.//a[starts-with(@href,"ch-w{nn:02d}")]]')[0]
        pages = []
        for a in li.xpath('.//a[@href]'):
            p = a.get('href').split('#')[0]
            if p not in pages:
                pages.append(p)
        web = []
        for p in pages:
            d = H.parse(os.path.join(root, p))
            for a in d.xpath('//article[@id]'):
                t = art_type(a)
                if t not in CLS:
                    continue
                h, n = heading_num(a)
                if t == 'exercise':
                    if any('exercises' in (x.get('class') or '').split() or 'exercisegroup' in (x.get('class') or '')
                           for x in a.iterancestors()):
                        continue
                elif n is None:
                    continue
                web.append((t, a.get('id'), n.text if n is not None else None))
        src = data['blocks']
        if len(web) != len(src) or any(w[0] != s[0] for w, s in zip(web, src)):
            for i, (w, s) in enumerate(zip(web, src)):
                if w[0] != s[0]:
                    print('  first type mismatch at', i, w, s); break
            sys.exit(f'chapter {nn}: web {len(web)} blocks vs source {len(src)}')
        for (t, i, old), (_, new) in zip(web, src):
            if old is not None:
                blockmap[i] = (old, new if new is not None else '')
    n_files = 0
    for f in glob.glob(os.path.join(root, '**', '*.html'), recursive=True):
        s = open(f, encoding='utf-8').read()
        d = H.document_fromstring(s)
        changed = False
        # block headings
        for a in d.xpath('//article[@id]'):
            i = a.get('id')
            if i in blockmap:
                h, n = heading_num(a)
                if n is not None:
                    changed |= set_num(n, blockmap[i][1])
        # sections and exercises divisions
        for sec in d.xpath('//section[@id]'):
            i = sec.get('id')
            ai = i.endswith('-ai')
            if i in secmap or ai:
                h = sec.xpath('./*[contains(concat(" ",@class," ")," heading ")]')
                if h:
                    n = h[0].xpath('./span[@class="codenumber"]')
                    if n:
                        changed |= set_num(n[0], '' if ai else secmap[i])
        # TOC entries and xrefs
        for a in d.xpath('//a[@href]'):
            href = a.get('href'); frag = href.split('#')[-1] if '#' in href else None
            page = href.split('#')[0].split('/')[-1].replace('.html', '')
            tgt = frag or page
            cls = a.get('class') or ''
            if 'xref' in cls and a.get('data-knowl'):
                tgt = a.get('data-knowl').split('/')[-1].replace('.html', '')
            nspan = a.xpath('./span[@class="codenumber"]')
            if nspan and (tgt in secmap or tgt.endswith('-ai')):
                changed |= set_num(nspan[0], '' if tgt.endswith('-ai') else secmap[tgt])
            elif 'xref' in cls and tgt in blockmap:
                old, new = blockmap[tgt]
                changed |= replace_text(a, old, new)
                if a.get('title'):
                    t2 = re.sub(rf'\s*(?<![\d.]){re.escape(old)}(?!\d)', (' ' + new) if new else '', a.get('title'))
                    if t2 != a.get('title'):
                        a.set('title', t2); changed = True
            elif 'xref' in cls and tgt in secmap and secmap[tgt]:
                pass  # section xrefs: number differs only in ch4-5; handled below
        if changed:
            n_files += 1
            out = H.tostring(d, encoding='unicode', doctype='<!DOCTYPE html>')
            if 'charset' not in out[:3000]:   # lxml drops the http-equiv charset meta
                out = re.sub(r'(<head\b[^>]*>)', r'\1\n<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">', out, count=1)
            open(f, 'w', encoding='utf-8').write(out)
    print('rewrote', n_files, 'files;', len(blockmap), 'blocks,', len(secmap), 'sections')

def set_num(span, new):
    if span.text == new:
        return False
    if new == '':
        prev = span.getprevious()
        if prev is not None and prev.get('class') == 'space':
            prev.drop_tree()
        span.drop_tree()
    else:
        span.text = new
    return True

def replace_text(a, old, new):
    done = False
    for el in a.iter():
        for attr in ('text', 'tail'):
            if el is a and attr == 'tail':
                continue
            v = getattr(el, attr)
            if v and re.search(rf'(?<![\d.]){re.escape(old)}(?![\d])', v):
                setattr(el, attr, re.sub(rf'\s*(?<![\d.]){re.escape(old)}(?![\d])', (' ' + new) if new else '', v) if not v.strip() == old else new)
                done = True
    return done

if __name__ == '__main__':
    if sys.argv[1] == 'extract':
        extract(sys.argv[2], sys.argv[3])
    else:
        apply(sys.argv[2], sys.argv[3])
