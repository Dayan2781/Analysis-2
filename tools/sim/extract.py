"""Extract each <exercise> statement (math as $..$) with a stable key -> sim/gen/exNN.json"""
import lxml.etree as E, glob, json, hashlib, re, os
def txt(el):
    out=[]
    def walk(e):
        if not isinstance(e.tag,str): 
            if e.tail: out.append(e.tail); 
            return
        if e.tag=='m': out.append('$'+(e.text or '')+'$')
        elif e.tag in ('md','me','men'):
            rows=e.findall('mrow')
            out.append(' $$'+(' \\\\ '.join((r.text or '') for r in rows) if rows else (e.text or ''))+'$$ ')
        else:
            if e.text: out.append(e.text)
            for c in e: walk(c)
            if e.tag in ('p','li'): out.append(' ')
        if e.tail: out.append(e.tail)
    for c in el: walk(c)
    if el.text: out.insert(0,el.text)
    return re.sub(r'\s+',' ',''.join(out)).strip()
def key(st): return hashlib.sha1(txt(st).encode()).hexdigest()[:10]
if __name__=='__main__':
    for f in sorted(glob.glob('book/source/chapters/ch*.ptx')):
        n=os.path.basename(f)[2:4]; d={}
        for x in E.parse(f).iter('exercise'):
            st=x.find('statement')
            if st is not None: d[key(st)]=txt(st)[:1200]
        json.dump(d,open(f'sim/gen/ex{n}.json','w'),ensure_ascii=False,indent=0)
        print(n,len(d))
