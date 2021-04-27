import yaml
import markdown
import re
import os
from sys import argv, stderr, stdin

def eprint(*args, **kwargs):
    kwargs['file'] = stderr
    print(*args, **kwargs)

class Entry:
    def __init__(self, id, data):
        self.id = id
        self.title = data['title']
        self.text = data.get('text')
        self.tags = data.get('tags', [])
        self.bulat = data.get('bulat')
        self.colloq = data.get('colloq', False)
        self.references = []
        self.referenced_by = []

class Missing:
    def __init__(self, id):
        self.id = id

def what_letter(x):
    superscript_map = {
            '⁰': '0', '¹': '1', '²': '2', '³': '3', '⁴': '4', '⁵': '5', '⁻': '-', '⁺': '+',
            'ⁱ': 'i', 'ʲ': 'j', 'ⁿ': 'n'}
    subscript_map = {
            '₀': '0', '₁': '1', '₂': '2', '₃': '3', '₄': '4', '₅': '5', '₋': '-', '₊': '+',
            'ᵢ': 'i', 'ⱼ': 'j', 'ₖ': 'k', 'ₙ': 'n', 'ₘ': 'm', 'ₚ': 'p', 'ᵣ': 'r', 'ₛ': 's',
            'ₐ': 'a'}
    if x in superscript_map:
        return 'super', superscript_map[x]
    if x in subscript_map:
        return 'sub', subscript_map[x]
    return None, x

def clean_text(text_id, text):
    # Find subscripts and group them
    new_text = ''
    last_group = None
    for i in text:
        g, x = what_letter(i)
        if last_group != g:
            if last_group is not None:
                new_text += '}'
            if g == 'super':
                new_text += '^{'
            if g == 'sub':
                new_text += '_{'
            last_group = g
        new_text += x
    if last_group is not None:
        new_text += '}'
    text = new_text

    line_starts = [0]
    for n, i in enumerate(text):
        if i == '\n':
            line_starts.append(n)

    def get_pos(pos):
        line = 0
        while line_starts[line + 1] < pos:
            line += 1
        col = pos - line_starts[line]
        return (line+1, col+1)

    for math in re.finditer(r'(?s)\$(.*?)\$', text):
        span = math.start()
        math = math.group(1)
        if math[0] != '`' or math[-1] != '`':
            line, col = get_pos(span)
            eprint(f'::warning line={line},col={col}::[{text_id}] Looks like non-gitlab math syntax: {repr(math)}')

    return text

def load(src):
    if isinstance(src, str):
        with open(src, 'r') as f:
            data = yaml.load(f, Loader=yaml.CLoader)
    else:
        data = yaml.load(src, Loader=yaml.CLoader)
    data = {k: Entry(k, v) for k, v in data.items() if not k.startswith('_')}

    missing = set()
    for k, v in data.items():
        for tag in v.tags:
            other = data.get(tag)
            if other is None:
                missing.add(tag)
            else:
                data[tag].referenced_by.append(v)
                v.references.append(data[tag])
    for i in missing:
        eprint(f'::warning ::Missing tag: {i}')
    return data

def toposort(data):
    marks = {}
    ids = [i.id for i in data]

    result = []
    def visit(node):
        mark = marks.get(node.id)
        if mark == 2:  # Perm
            return
        if mark == 1:  # Temp
            raise Exception(f'not a DAG: {node.id} visited twice')
        marks[node.id] = 1

        children = sorted(node.references, key=lambda x: ids.index(x.id))
        for child in children:
            visit(child)

        marks[node.id] = 2
        result.append(node)
    for i in data:
        if not marks.get(i.id):
            visit(i)
    return result

def add_more(prefix, src):
    for more in src:
        if more.text is not None:
            yield f'<a class="more" href="#{more.id}">{prefix} {more.title}</a><br/>'
        else:
            yield f'{prefix} {more.title} <code>[WIP]</code><br/>'

def render(i):
    bulat = f'<small>(<a target="_blank" href="{i.bulat}">Конспект</a>)</small>' if i.bulat else ''
    colloq = 'colloq' if i.colloq else ''
    yield f'<div class="entry">'
    yield f'<h1 id={i.id}><a class="tag more {colloq}" href="#{i.id}">#</a>{i.title} {bulat}</h1>'
    yield (markdown.Markdown(
            extensions=['mdx_math'],
            extension_configs={
                'mdx_math': {'use_gitlab_delimiters': True}
            }
        ).convert(clean_text(i.id, i.text)))

    yield '<hr/>'
    yield from add_more('←', i.references)
    yield from add_more('→', i.referenced_by)
    yield '</div>'

def graph(data, outfile, root=None):
    root = '' if root is None else root
    import graphviz
    dot = graphviz.Digraph()
    dot.attr('graph', rankdir='LR')
    js = 'const nodes={};'
    for k, v in data.items():
        dot.node(v.id, v.title, target="_blank", href=f"{root}#{v.id}", id=v.id)
        for i in v.referenced_by:
            dot.edge(v.id, i.id, id=f"{v.id}___{i.id}")
        arrows = [f'"{v.id}___{i.id}"' for i in v.referenced_by]
        others = ([f'"{i.id}"' for i in v.referenced_by + v.references + [v]]
                + [f'"{i.id}___{v.id}"' for i in v.references]
                + arrows)
        js += f'''
            {{
                let node = document.getElementById("{v.id}");
                let others = [{','.join(others)}];
                let arrows = [{','.join(arrows)}];
                nodes["{v.id}"] = node;
                for (let i of arrows)
                    nodes[i] = document.getElementById(i);
                node.onmouseover = function() {{
                    for (let other of others)
                        nodes[other].classList.add("hovered");
                }};
                node.onmouseout = function() {{
                    for (let other of others)
                        nodes[other].classList.remove("hovered");
                }};
            }}
        '''

    dot = dot.unflatten()
    outfile = dot.render(outfile, format='svg', cleanup=True)
    with open(outfile, 'r') as f:
        rendered = list(f.readlines())

    js = ''.join(i.strip() for i in js.split('\n'))
    rendered.insert(-1, f'''
        <script type="text/javascript">{js}</script>
        <style>
            .hovered.node ellipse {{
                fill: beige;
            }}
            .hovered.edge path {{
                stroke: red;
            }}
            .hovered.edge polygon {{
                stroke: red;
                fill: red;
            }}
        </style>
    ''')
    with open(outfile, 'w') as f:
        f.write(''.join(rendered))

def print_html(data):
    with open('template.html', 'r') as f:
        before, after = f.read().split('<!-- PUT CARDS HERE -->')
    print(before)
    for i in data:
        if i.text is not None:
            for ln in render(i):
                print(ln)
    print(after)

if __name__ == "__main__":
    data = load(stdin)
    eprint(f'Loaded {len(data)} cards')
    print_html(toposort(data.values()))
    if len(argv) > 1:
        graph(data, argv[1], root=os.path.basename(argv[1]) + '.html')
