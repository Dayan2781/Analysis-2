#!/usr/bin/env python3
"""LaTeX (Analysis2_16 weeks/*.tex) -> PreTeXt chapter converter.

Usage: tex2ptx.py weekNN.tex out.ptx NN
Heuristic converter tuned for Dayan's lecture files.  Prints warnings to stderr.
"""
import re, sys

WARN = []
def warn(msg):
    WARN.append(msg)

# ---------------------------------------------------------------- preprocess
def strip_comments(s):
    out = []
    for line in s.split('\n'):
        m = re.search(r'(?<!\\)%', line)
        if m:
            line = line[:m.start()]
            if not line.strip():
                line = '\x00'   # comment-only line: not a paragraph break
        out.append(line)
    s = '\n'.join(out)
    s = re.sub(r'\n\x00(?=\n)', '', s)
    s = s.replace('\x00', '')
    return s

def preprocess(s):
    s = strip_comments(s)
    s = re.sub(r'\\renewcommand\{\\(lectureno|topic)\}\{[^{}]*\}', '', s)
    s = re.sub(r'\\addcontentsline\{[^{}]*\}\{[^{}]*\}\{(?:[^{}]|\{[^{}]*\})*\}', '', s)
    s = re.sub(r'\\texorpdfstring\{((?:[^{}]|\{[^{}]*\})*)\}\{(?:[^{}]|\{[^{}]*\})*\}', r'\1', s)
    s = re.sub(r'\\(newpage|clearpage|noindent|medskip|smallskip|bigskip|centering|qed|par(?![a-z]))\b', '\n', s)
    s = re.sub(r'\\hfill\s*\$\\(square|blacksquare|Box)\$', '', s)
    s = re.sub(r'\\hfill\s*\\(square|blacksquare|qedsymbol)', '', s)
    s = re.sub(r'\\hfill\b', '', s)
    s = re.sub(r'\\renewcommand\{\\arraystretch\}\{[^{}]*\}', '', s)
    s = re.sub(r'\\vspace\*?\{[^{}]*\}', '', s)
    s = re.sub(r'\\hspace\*?\{[^{}]*\}', ' ', s)
    return s

# ---------------------------------------------------------------- parser
DISPLAY_MATH_ENVS = {'equation', 'equation*', 'align', 'align*', 'eqnarray', 'eqnarray*',
                     'gather', 'gather*', 'multline', 'multline*', 'displaymath'}
RAW_ENVS = {'tikzpicture', 'tabular'}

class Node:
    def __init__(self, kind, **kw):
        self.kind = kind
        self.__dict__.update(kw)
    def __repr__(self):
        return f'<{self.kind} {getattr(self, "name", "")}>'

def read_group(s, i, open_ch='{', close_ch='}'):
    """s[i] == open_ch; return (content, index after close)."""
    assert s[i] == open_ch, (s[i:i+20])
    depth = 0
    j = i
    while j < len(s):
        c = s[j]
        if c == '\\':
            j += 2
            continue
        if c == open_ch:
            depth += 1
        elif c == close_ch:
            depth -= 1
            if depth == 0:
                return s[i+1:j], j+1
        j += 1
    raise ValueError('unbalanced group at ' + s[i:i+60])

def skip_ws(s, i):
    while i < len(s) and s[i] in ' \t\n':
        i += 1
    return i

def find_inline_math_end(s, i):
    """s[i]=='$' opening (single). return index of closing $."""
    j = i + 1
    depth = 0
    while j < len(s):
        c = s[j]
        if c == '\\':
            j += 2
            continue
        if c == '{': depth += 1
        elif c == '}': depth -= 1
        elif c == '$' and depth <= 0:
            return j
        j += 1
    raise ValueError('unclosed $ at ' + s[i:i+60])

HEAD_RE = re.compile(r'\\(chapter|section|subsection|subsubsection|paragraph)(\*?)')

def parse(s, i=0, end_env=None):
    nodes = []
    buf = []
    def flush():
        if buf:
            nodes.append(Node('text', text=''.join(buf)))
            buf.clear()
    n = len(s)
    while i < n:
        c = s[i]
        if c == '\n':
            m = re.match(r'\n[ \t]*\n\s*', s[i:])
            if m:
                flush(); nodes.append(Node('par')); i += m.end(); continue
            buf.append(' '); i += 1; continue
        if s.startswith('$$', i):
            j = s.index('$$', i + 2)
            flush(); nodes.append(Node('dmath', body=s[i+2:j], env=None)); i = j + 2; continue
        if c == '$':
            j = find_inline_math_end(s, i)
            buf.append(s[i:j+1]); i = j + 1; continue
        if s.startswith('\\[', i):
            j = s.index('\\]', i + 2)
            flush(); nodes.append(Node('dmath', body=s[i+2:j], env=None)); i = j + 2; continue
        if s.startswith('\\(', i):
            j = s.index('\\)', i + 2)
            buf.append('$' + s[i+2:j] + '$'); i = j + 2; continue
        if s.startswith('\\begin{', i):
            name, k = read_group(s, i + 6)
            if name in DISPLAY_MATH_ENVS:
                endtag = '\\end{' + name + '}'
                j = s.index(endtag, k)
                flush(); nodes.append(Node('dmath', body=s[k:j], env=name)); i = j + len(endtag); continue
            if name in RAW_ENVS:
                endtag = '\\end{' + name + '}'
                j = s.index(endtag, k)
                flush(); nodes.append(Node('raw', name=name, body=s[k:j])); i = j + len(endtag); continue
            # optional / mandatory args
            opt = None; args = []
            kk = k
            if kk < n and s[kk] == '[':
                opt, kk = read_group(s, kk, '[', ']')
            if name in ('multicols',) and s[kk] == '{':
                a, kk = read_group(s, kk); args.append(a)
            if name in ('problem',) and opt is None:
                pass
            flush()
            children, i = parse(s, kk, name)
            nodes.append(Node('env', name=name, opt=opt, args=args, children=children))
            continue
        if s.startswith('\\end{', i):
            name, k = read_group(s, i + 4)
            if name != end_env:
                warn(f'unexpected \\end{{{name}}} while in {end_env}')
                if end_env is not None and name not in ('problem', 'solution'):
                    i = k; continue
            flush(); return nodes, k
        if s.startswith('\\item', i) and not s[i+5:i+6].isalpha():
            k = i + 5
            lab = None
            k2 = skip_ws(s, k)
            if k2 < n and s[k2] == '[':
                lab, k = read_group(s, k2, '[', ']')
            flush(); nodes.append(Node('item', label=lab)); i = k; continue
        m = HEAD_RE.match(s, i)
        if m:
            level, star = m.group(1), m.group(2)
            k = m.end()
            k = skip_ws(s, k)
            short = None
            if s[k] == '[':
                short, k = read_group(s, k, '[', ']')
            title, k = read_group(s, k)
            flush(); nodes.append(Node('head', level=level, star=bool(star), title=title)); i = k; continue
        if s.startswith('\\label{', i):
            lab, k = read_group(s, i + 6)
            flush(); nodes.append(Node('label', label=lab)); i = k; continue
        if c == '\\':
            buf.append(s[i:i+2]); i += 2; continue
        buf.append(c); i += 1
    flush()
    if end_env is not None:
        warn(f'unclosed environment {end_env}')
    return nodes, i

# ---------------------------------------------------------------- inline
def esc(t):
    return t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

LABELS = {}
def xmlid(label):
    i = re.sub(r'[^A-Za-z0-9_-]', '-', label)
    if not i[0].isalpha():
        i = 'x' + i
    return i

def math_clean(m):
    m = m.strip()
    m = m.replace('\\dfrac', '\\dfrac')
    return esc(m)

SIMPLE = {
    '\\ldots': '…', '\\dots': '…', '\\quad': ' ', '\\qquad': ' ', '\\,': ' ', '\\;': ' ',
    '\\!': '', '\\ ': ' ', '\\%': '%', '\\&': '&amp;', '\\$': '$', '\\_': '_', '\\#': '#',
    '\\S': '§', '\\\\': ' ', '\\-': '', '\\LaTeX': 'LaTeX', '\\TeX': 'TeX', '\\textbackslash': '\\',
    '\\displaystyle': '', '\\small': '', '\\large': '', '\\Large': '', '\\footnotesize': '',
    '\\normalsize': '', '\\bf': '', '\\it': '', '\\em': '', '\\rm': '', '\\hline': '',
}
WRAP = {'textbf': 'term', 'emph': 'em', 'textit': 'em', 'itcol': 'em', 'underline': 'em',
        'textsl': 'em', 'textsc': None, 'text': None, 'mbox': None, 'textrm': None,
        'textup': None, 'textnormal': None, 'footnote': 'fn', 'texttt': 'c'}

def inline(t):
    out = []
    i = 0
    n = len(t)
    while i < n:
        c = t[i]
        if c == '$':
            j = find_inline_math_end(t, i)
            out.append('<m>' + math_clean(t[i+1:j]) + '</m>'); i = j + 1; continue
        if c == '\\':
            m = re.match(r'\\([A-Za-z]+)\*?', t[i:])
            if m:
                cmd = m.group(1)
                k = i + m.end()
                if cmd in WRAP:
                    k2 = skip_ws(t, k)
                    if k2 < n and t[k2] == '{':
                        body, k3 = read_group(t, k2)
                        tag = WRAP[cmd]
                        inner = inline(body)
                        out.append(f'<{tag}>{inner}</{tag}>' if tag else inner)
                        i = k3; continue
                if cmd == 'textcolor':
                    _, k2 = read_group(t, k)
                    body, k3 = read_group(t, k2)
                    out.append(inline(body)); i = k3; continue
                if cmd in ('ref', 'eqref', 'autoref', 'cref', 'Cref'):
                    lab, k2 = read_group(t, k)
                    if cmd == 'eqref':
                        out.append(f'<xref ref="{xmlid(lab)}"/>')
                    else:
                        out.append(f'<xref ref="{xmlid(lab)}" text="global"/>')
                    i = k2; continue
                if cmd == 'cite':
                    _, k2 = read_group(t, k); i = k2; continue
                if cmd in ('href',):
                    url, k2 = read_group(t, k)
                    body, k3 = read_group(t, k2)
                    out.append(f'<url href="{esc(url)}">{inline(body)}</url>'); i = k3; continue
                if cmd == 'url':
                    url, k2 = read_group(t, k)
                    out.append(f'<url href="{esc(url)}"/>'); i = k2; continue
                key = '\\' + cmd
                if key in SIMPLE:
                    out.append(SIMPLE[key]); i = k
                    if i < n and t[i] == ' ' and cmd.isalpha() and SIMPLE[key] == '': i += 1
                    continue
                if cmd in ('item',):
                    i = k; continue
                warn(f'unknown inline command \\{cmd}')
                i = k; continue
            two = t[i:i+2]
            if two in SIMPLE:
                out.append(SIMPLE[two]); i += 2; continue
            out.append(esc(t[i+1:i+2])); i += 2; continue
        if c == '{' or c == '}':
            i += 1; continue
        if c == '~':
            out.append('\u00a0'); i += 1; continue
        if t.startswith('---', i):
            out.append('—'); i += 3; continue
        if t.startswith('--', i):
            out.append('–'); i += 2; continue
        if t.startswith('``', i):
            out.append('“'); i += 2; continue
        if t.startswith("''", i):
            out.append('”'); i += 2; continue
        out.append(esc(c)); i += 1
    s = ''.join(out)
    s = re.sub(r'[ \t\n]+', ' ', s)
    return s

# ---------------------------------------------------------------- display math
def dmath(node):
    body = node.body
    labels = re.findall(r'\\label\{([^{}]*)\}', body)
    body = re.sub(r'\\label\{[^{}]*\}', '', body)
    body = re.sub(r'\\(nonumber|notag)\b', '', body)
    env = node.env or ''
    if env.startswith('eqnarray'):
        body = body.replace('&=&', '&=').replace('& = &', '&=').replace('&\\le&', '&\\le').replace('&\\ge&', '&\\ge')
        body = re.sub(r'&\s*([<>=]|\\[a-z]+)\s*&', r'&\1 ', body)
    numbered = env in ('equation', 'align', 'eqnarray', 'gather', 'multline')
    idattr = ''
    if labels:
        idattr = f' xml:id="{xmlid(labels[0])}"'
        numbered = True
    if env.startswith(('align', 'eqnarray', 'gather', 'multline')):
        rows = [r for r in re.split(r'\\\\(?:\[[^\]]*\])?', body) if r.strip()]
        if env.startswith('multline') or len(rows) == 1:
            b = body if not env.startswith('multline') else '\\begin{gathered}' + body + '\\end{gathered}'
            b = b.replace('&', '') if len(rows) == 1 and not env.startswith('multline') else b
            num = ' number="yes"' if numbered else ''
            return f'<md{idattr}{num}>{math_clean(b)}</md>'
        al = ' alignment="gather"' if env.startswith('gather') else ''
        num = ' number="yes"' if numbered else ''
        mrows = ''.join(f'<mrow>{math_clean(r)}</mrow>' for r in rows)
        return f'<md{num}{al}>{mrows}</md>'
    b = body.strip()
    if not b:
        return ''
    num = ' number="yes"' if numbered else ''
    return f'<md{idattr}{num}>{math_clean(b)}</md>'

# ---------------------------------------------------------------- blocks
THM = {'theorem': 'theorem', 'proposition': 'proposition', 'lemma': 'lemma', 'corollary': 'corollary',
       'cor': 'corollary', 'definition': 'definition', 'remark': 'remark', 'note': 'note',
       'example': 'example', 'problem': 'exercise'}
STATEMENT_ENVS = {'theorem', 'proposition', 'lemma', 'corollary', 'definition'}

class Ctx:
    def __init__(self, exercise_mode=False):
        self.exercise_mode = exercise_mode

def split_items(children):
    """flatten multicols, split by item markers. returns (cols, [ [nodes], ...], pre)"""
    cols = None
    flat = []
    for ch in children:
        if ch.kind == 'env' and ch.name == 'multicols':
            cols = ch.args[0] if ch.args else '2'
            flat.extend(ch.children)
        else:
            flat.append(ch)
    items = []
    pre = []
    cur = None
    labels = []
    for ch in flat:
        if ch.kind == 'item':
            cur = []
            items.append(cur)
            labels.append(ch.label)
        elif cur is None:
            pre.append(ch)
        else:
            cur.append(ch)
    return cols, items, pre, labels

def tabular_xml(node):
    body = node.body
    spec, k = read_group(body, 0) if body.startswith('{') else ('', 0)
    body = body[k:]
    rows = [r for r in re.split(r'\\\\', body) if r.replace('\\hline', '').strip()]
    hasrules = '|' in spec or '\\hline' in body
    halign = {'c': 'center', 'l': 'left', 'r': 'right'}
    cols = [c for c in spec if c in 'lcrp']
    out = ['<tabular' + (' top="minor" bottom="minor" left="minor" right="minor"' if hasrules else '') + '>']
    for c in cols:
        out.append(f'<col halign="{halign.get(c, "left")}"' + (' right="minor"' if hasrules else '') + '/>')
    for r in rows:
        r = r.replace('\\hline', '')
        cells = split_amp(r)
        out.append('<row' + (' bottom="minor"' if hasrules else '') + '>' + ''.join(f'<cell>{inline(cl.strip())}</cell>' for cl in cells) + '</row>')
    out.append('</tabular>')
    return ''.join(out)

def split_amp(r):
    cells, cur, i, depth = [], [], 0, 0
    inmath = False
    while i < len(r):
        c = r[i]
        if c == '\\':
            cur.append(r[i:i+2]); i += 2; continue
        if c == '$': inmath = not inmath
        if c == '{': depth += 1
        if c == '}': depth -= 1
        if c == '&' and depth == 0 and not inmath:
            cells.append(''.join(cur)); cur = []; i += 1; continue
        cur.append(c); i += 1
    cells.append(''.join(cur))
    return cells

def emit_blocks(nodes, ctx):
    """Return list of xml block strings."""
    blocks = []
    para = []   # inline xml pieces / me / lists

    def flush():
        if para:
            content = ''.join(para).strip()
            if content and re.sub(r'<[^>]+>', '', content).strip() or '<m' in content or '<md' in content or '<ol' in content or '<ul' in content or '<xref' in content:
                if content:
                    blocks.append('<p>' + content + '</p>')
            para.clear()

    i = 0
    nodes = list(nodes)
    while i < len(nodes):
        nd = nodes[i]
        k = nd.kind
        if k == 'text':
            para.append(inline(nd.text))
        elif k == 'par':
            flush()
        elif k == 'dmath':
            para.append(dmath(nd))
        elif k == 'label':
            warn(f'stray label {nd.label}')
        elif k == 'item':
            warn('stray \\item')
        elif k == 'head':
            flush()
            blocks.append(('HEAD', nd))
        elif k == 'raw':
            flush()
            if nd.name == 'tabular':
                blocks.append(tabular_xml(nd))
            else:
                opt = ''
                body = nd.body
                blocks.append('<image width="60%"><latex-image>\n\\begin{tikzpicture}' + esc(body) + '\\end{tikzpicture}\n</latex-image></image>')
        elif k == 'env':
            name = nd.name
            if name in ('enumerate', 'itemize'):
                cols, items, pre, labels = split_items(nd.children)
                if pre and any(p.kind != 'par' and not (p.kind == 'text' and not p.text.strip()) for p in pre):
                    para.append(''.join(inline(p.text) for p in pre if p.kind == 'text'))
                if ctx.exercise_mode and name == 'enumerate':
                    flush()
                    for it in items:
                        blocks.append(('EXERCISE', it, None))
                    if cols and not items:
                        pass
                else:
                    tag = 'ol' if name == 'enumerate' else 'ul'
                    attrs = f' cols="{cols}"' if cols in ('2', '3', '4') else ''
                    lis = []
                    sub = Ctx(False)
                    for it in items:
                        lis.append('<li>' + li_content(it, sub) + '</li>')
                    para.append(f'<{tag}{attrs}>' + ''.join(lis) + f'</{tag}>')
            elif name in ('multicols', 'center', 'table', 'flushleft', 'flushright', 'minipage', 'figure', 'small', 'footnotesize', 'quote'):
                # transparent
                inner = emit_blocks(nd.children, ctx)
                flush()
                blocks.extend(inner)
            elif name in THM or name in ('prof', 'proof', 'solution'):
                flush()
                blocks.append(('ENV', nd))
            else:
                warn(f'unknown env {name}; treated transparently')
                flush()
                blocks.extend(emit_blocks(nd.children, ctx))
        i += 1
    flush()
    return blocks

def li_content(nodes, ctx):
    bl = assemble(emit_blocks(nodes, ctx), ctx)
    if len(bl) == 1 and bl[0].startswith('<p>') and bl[0].endswith('</p>'):
        return bl[0][3:-4]
    return ''.join(bl)

def get_label(nodes):
    labs = [n.label for n in nodes if n.kind == 'label']
    rest = [n for n in nodes if n.kind != 'label']
    # labels directly at start as text?
    return (labs[0] if labs else None), rest, labs[1:]

def body_blocks(nodes, ctx):
    bl = assemble(emit_blocks(nodes, ctx), ctx)
    if not bl:
        bl = ['<p/>']
    return ''.join(bl)

def title_xml(opt):
    if opt is None:
        return ''
    t = inline(opt).strip()
    return f'<title>{t}</title>' if t else ''

def env_xml(nd, ctx, attach=None):
    """attach: list of following solution/proof nodes"""
    name = nd.name
    lab, rest, extra = get_label(nd.children)
    for e in extra:
        warn(f'extra label {e} in {name}')
    idattr = f' xml:id="{xmlid(lab)}"' if lab else ''
    if hasattr(nd, 'ltx'):
        idattr += f' ltx="{nd.ltx}"'   # LaTeX number, used by tools/renumber.py, stripped before build
    tag = THM.get(name)
    attach = attach or []
    if name in ('prof', 'proof'):
        return f'<proof{idattr}>' + body_blocks(rest, Ctx(False)) + '</proof>'
    if name == 'solution':
        return f'<solution{idattr}>' + body_blocks(rest, Ctx(False)) + '</solution>'
    if tag in STATEMENT_ENVS:
        s = f'<{tag}{idattr}>' + title_xml(nd.opt) + '<statement>' + body_blocks(rest, Ctx(False)) + '</statement>'
        for a in attach:
            s += env_xml(a, ctx)
        return s + f'</{tag}>'
    if tag in ('remark', 'note'):
        return f'<{tag}{idattr}>' + title_xml(nd.opt) + body_blocks(rest, Ctx(False)) + f'</{tag}>'
    if tag in ('example', 'exercise'):
        sols = [a for a in attach if a.name == 'solution']
        # nested solution envs inside the problem/example body
        inner_sols = [c for c in rest if c.kind == 'env' and c.name == 'solution']
        rest = [c for c in rest if not (c.kind == 'env' and c.name == 'solution')]
        sols = inner_sols + sols
        s = f'<{tag}{idattr}>' + title_xml(nd.opt)
        if sols or tag == 'exercise' or any(a.name in ('prof', 'proof') for a in attach):
            s += '<statement>' + body_blocks(rest, Ctx(False)) + '</statement>'
            for so in sols:
                s += env_xml(so, ctx)
        else:
            s += body_blocks(rest, Ctx(False))
        for a in attach:
            if a.name in ('prof', 'proof'):
                warn('proof attached to example/exercise -> solution')
                s += '<solution>' + body_blocks(a.children, Ctx(False)) + '</solution>'
        return s + f'</{tag}>'
    raise ValueError(name)

def assemble(blocks, ctx):
    """Turn ('ENV', node) / ('EXERCISE', items) entries into xml, attaching proofs/solutions."""
    out = []
    i = 0
    while i < len(blocks):
        b = blocks[i]
        if isinstance(b, tuple) and b[0] == 'ENV':
            nd = b[1]
            attach = []
            j = i + 1
            if nd.name in STATEMENT_ENVS or nd.name in ('example', 'problem'):
                want = ('prof', 'proof') if nd.name in STATEMENT_ENVS else ('solution', 'prof', 'proof')
                while j < len(blocks) and isinstance(blocks[j], tuple) and blocks[j][0] == 'ENV' and blocks[j][1].name in want:
                    attach.append(blocks[j][1]); j += 1
            if nd.name == 'solution' and not attach:
                # orphan solution: attach to previous example/exercise if possible
                if out and re.search(r'</(example|exercise)>$', out[-1]):
                    t = re.search(r'</(example|exercise)>$', out[-1]).group(1)
                    prev = out[-1][:-len(f'</{t}>')]
                    if '<statement>' not in prev:
                        # wrap existing content into statement
                        m = re.match(rf'(<{t}[^>]*>(?:<title>.*?</title>)?)(.*)$', prev, re.S)
                        prev = m.group(1) + '<statement>' + m.group(2) + '</statement>'
                    out[-1] = prev + env_xml(nd, ctx) + f'</{t}>'
                    i += 1; continue
                warn('orphan solution -> remark')
                out.append('<remark><title>Бодолт</title>' + body_blocks(nd.children, Ctx(False)) + '</remark>')
                i += 1; continue
            if nd.name in ('prof', 'proof') and out and re.search(r'</(theorem|lemma|corollary|proposition)>$', out[-1]) and '<proof' not in out[-1][-200:]:
                t = re.search(r'</(theorem|lemma|corollary|proposition)>$', out[-1]).group(1)
                out[-1] = out[-1][:-len(f'</{t}>')] + env_xml(nd, ctx) + f'</{t}>'
                i += 1; continue
            out.append(env_xml(nd, ctx, attach))
            i = j
            continue
        if isinstance(b, tuple) and b[0] == 'EXERCISE':
            it = b[1]
            # subitem solutions?
            sols = [c for c in it if c.kind == 'env' and c.name == 'solution']
            rest = [c for c in it if not (c.kind == 'env' and c.name == 'solution')]
            s = '<exercise><statement>' + body_blocks(rest, Ctx(False)) + '</statement>'
            for so in sols:
                s += env_xml(so, ctx)
            out.append(s + '</exercise>')
            i += 1; continue
        out.append(b)
        i += 1
    return out

# ---------------------------------------------------------------- structure
def is_exercise_title(t):
    return bool(re.search(r'Семинар|Гэрийн даалгавар|бодлого|Бодлого|Хэсэг [IVX]|Хариу|Санамж|Онолын хүнд', t))

def split_by(nodes, level_names):
    """split node list into (pre, [(headnode, nodes)])"""
    pre, secs = [], []
    cur = None
    for nd in nodes:
        if nd.kind == 'head' and nd.level in level_names:
            cur = (nd, [])
            secs.append(cur)
        elif cur is None:
            pre.append(nd)
        else:
            cur[1].append(nd)
    return pre, secs

def pop_label(nodes):
    # label directly following a heading
    for idx, nd in enumerate(nodes):
        if nd.kind == 'label':
            return nd.label, nodes[:idx] + nodes[idx+1:]
        if nd.kind == 'par' or (nd.kind == 'text' and not nd.text.strip()):
            continue
        break
    return None, nodes

def content(nodes, exmode):
    return '\n'.join(content_blocks(nodes, exmode))

def exercises_body(nodes, exmode=True):
    """blocks for an exercises/subexercises container: leading prose -> introduction,
    trailing prose -> conclusion, prose in the middle -> folded into an exercisegroup intro"""
    bl = content_blocks(nodes, exmode)
    isex = [b.startswith('<exercise') for b in bl]
    if not any(isex):
        return '\n'.join(bl), False
    first = isex.index(True)
    last = len(isex) - 1 - isex[::-1].index(True)
    out = []
    if first > 0:
        out.append('<introduction>' + ''.join(bl[:first]) + '</introduction>')
    mid = bl[first:last+1]
    # prose in the middle: start an exercisegroup with that prose as introduction
    groups, cur_intro, cur = [], None, []
    for b in mid:
        if b.startswith('<exercise'):
            cur.append(b)
        else:
            groups.append((cur_intro, cur)); cur_intro, cur = b, []
    groups.append((cur_intro, cur))
    for intro, exs in groups:
        if intro is None:
            out.extend(exs)
        else:
            if exs:
                out.append('<exercisegroup><introduction>' + intro + '</introduction>' + ''.join(exs) + '</exercisegroup>')
    tail = bl[last+1:]
    if tail:
        out.append('<conclusion>' + ''.join(tail) + '</conclusion>')
    return '\n'.join(out), True

def content_blocks(nodes, exmode):
    ctx = Ctx(exmode)
    bl = assemble(emit_blocks(nodes, ctx), ctx)
    out, grp = [], None
    for b in bl:
        if isinstance(b, tuple) and b[0] == 'HEAD':
            if grp is not None:
                out.append(grp + '</paragraphs>')
            grp = '<paragraphs><title>' + inline(b[1].title).strip() + '</title>'
            continue
        if grp is not None:
            grp += b
        else:
            out.append(b)
    if grp is not None:
        out.append(grp + '</paragraphs>')
    return out

def subdiv_xml(tag, head, nodes, exmode, idbase):
    lab, nodes = pop_label(nodes)
    idattr = f' xml:id="{xmlid(lab)}"' if lab else f' xml:id="{idbase}"'
    title = inline(head.title).strip()
    return f'<{tag}{idattr}>\n<title>{title}</title>\n' + content(nodes, exmode) + f'\n</{tag}>'

def section_xml(head, nodes, idbase, exmode):
    lab, nodes = pop_label(nodes)
    idattr = f' xml:id="{xmlid(lab)}"' if lab else f' xml:id="{idbase}"'
    title = inline(head.title).strip()
    first = next((n.level for n in nodes if n.kind == 'head' and n.level in ('subsection', 'subsubsection')), None)
    pre, subs = split_by(nodes, (first,)) if first else (nodes, [])
    ltx = f' ltx="{head.ltx}"' if hasattr(head, 'ltx') else ''
    out = [f'<section{idattr}{ltx}>', f'<title>{title}</title>']
    if subs:
        intro = content(pre, exmode)
        if intro.strip():
            out.append('<introduction>\n' + intro + '\n</introduction>')
        for k, (h, ns) in enumerate(subs, 1):
            ex = exmode or is_exercise_title(h.title)
            out.append(subdiv_xml('subsection', h, ns, ex, f'{idbase}-{k}'))
    else:
        out.append(content(pre, exmode))
    out.append('</section>')
    return '\n'.join(out)

def homework_xml(title, nodes, idbase, ltx=''):
    """chapter-level <exercises>; section*/subsection* -> subexercises"""
    pre, subs = split_by(nodes, ('section', 'subsection'))
    out = [f'<exercises xml:id="{idbase}" ltx="{ltx}">', f'<title>{inline(title).strip()}</title>']
    pre_body, has_ex = exercises_body(pre)
    if subs:
        if pre_body.strip():
            if has_ex:
                out.append(f'<subexercises xml:id="{idbase}-0">' + pre_body + '</subexercises>')
            else:
                out.append('<introduction>\n' + pre_body + '\n</introduction>')
        tail = []
        for k, (h, ns) in enumerate(subs, 1):
            t = inline(h.title).strip()
            body, has = exercises_body(ns, not re.search(r'[Сс]анамж|Хариу', t))
            if not has:
                tail.append('<p><term>' + t + '</term></p>\n' + body)
            else:
                out.append(f'<subexercises xml:id="{idbase}-{k}">\n<title>{t}</title>\n' + body + '\n</subexercises>')
        out.append('<!--AI-HOMEWORK-->')
        if tail:
            out.append('<conclusion>' + ''.join(tail) + '</conclusion>')
    else:
        out.append(pre_body)
        out.append('<!--AI-HOMEWORK-->')
    out.append('</exercises>')
    return '\n'.join(out)

# LaTeX numbering as in Analysis2_16/main.tex: theorem+corollary, proposition, definition,
# example per chapter; lemma per section; problem book-wide; remark/note/cor unnumbered.
LTX_COUNTER = {'theorem': 'thm', 'corollary': 'thm', 'proposition': 'prop', 'definition': 'def',
               'example': 'ex', 'lemma': 'lem', 'problem': 'prob', 'cor': None, 'remark': None, 'note': None}

def number_ltx(nodes, week, prob0):
    st = {'sec': 0, 'prob': prob0, 'thm': 0, 'prop': 0, 'def': 0, 'ex': 0, 'lem': 0}
    def walk(ns):
        for nd in ns:
            if nd.kind == 'head' and nd.level == 'section':
                if not nd.star:
                    st['sec'] += 1; st['lem'] = 0
                nd.ltx = '' if nd.star else f"{week}.{st['sec']}"
            if nd.kind == 'env' and nd.name in LTX_COUNTER:
                c = LTX_COUNTER[nd.name]
                if c is None:
                    nd.ltx = ''
                else:
                    st[c] += 1
                    nd.ltx = (str(st[c]) if c == 'prob' else
                              f"{week}.{st['sec']}.{st[c]}" if c == 'lem' else f'{week}.{st[c]}')
            for ch in getattr(nd, 'children', None) or []:
                if isinstance(ch, Node):
                    walk([ch])
    walk(nodes)
    return st['prob']

def problems_before(path, week):
    import glob, os
    n = 0
    for f in sorted(glob.glob(os.path.join(os.path.dirname(path), 'week*.tex'))):
        w = int(re.search(r'week(\d+)', os.path.basename(f)).group(1))
        if w < week:
            nd, _ = parse(preprocess(open(f, encoding='utf-8').read()))
            n = number_ltx(nd, w, n)
    return n

def convert(src, week, prob0=0):
    s = preprocess(src)
    nodes, _ = parse(s)
    number_ltx(nodes, week, prob0)
    idb = f'w{week:02d}'
    # chapter heading
    pre, chaps = split_by(nodes, ('chapter',))
    main_head, main_nodes = chaps[0]
    hw = chaps[1] if len(chaps) > 1 else None
    lab, main_nodes = pop_label(main_nodes)
    title = inline(main_head.title).strip()
    out = [f'<chapter xml:id="ch-{idb}" xmlns:xi="http://www.w3.org/2001/XInclude">', f'<title>{title}</title>']
    intro_nodes, secs = split_by(main_nodes, ('section',))
    intro = content(intro_nodes, False)
    out.append('<introduction>\n' + intro + '\n<!--AI-PREVIEW-->\n</introduction>' if intro.strip() else '<!--AI-PREVIEW-->')
    hw_inline = None
    k = 0
    for h, ns in secs:
        t = h.title
        if hw is None and 'Гэрийн даалгавар' in t and not h.star:
            hw_inline = (t, ns, getattr(h, 'ltx', '')); continue
        k += 1
        ex = is_exercise_title(t)
        sx = section_xml(h, ns, f'{idb}-s{k}', ex)
        if not ex:
            sx = sx[:-len('</section>')] + f'<!--AI-SECTION {idb}-s{k}-->\n</section>'
        out.append(sx)
    if hw is not None:
        out.append(homework_xml(hw[0].title, hw[1], f'{idb}-hw'))
    elif hw_inline is not None:
        out.append(homework_xml(hw_inline[0], hw_inline[1], f'{idb}-hw', hw_inline[2]))
    else:
        out.append(f'<exercises xml:id="{idb}-hw" ltx=""><title>Гэрийн даалгавар</title>\n<!--AI-HOMEWORK-->\n</exercises>')
    out.append('</chapter>')
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + '\n'.join(out) + '\n'

if __name__ == '__main__':
    src = open(sys.argv[1], encoding='utf-8').read()
    week = int(sys.argv[3])
    xml = convert(src, week, problems_before(sys.argv[1], week))
    open(sys.argv[2], 'w', encoding='utf-8').write(xml)
    for w in sorted(set(WARN)):
        print(f'[w{week:02d}] {w}', file=sys.stderr)
