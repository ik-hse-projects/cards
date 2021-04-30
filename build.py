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
        self.source = data.get('source')
        self.colloq = data.get('colloq', [])
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
    source = f'<small>(<a target="_blank" href="{i.source}">Конспект</a>)</small>' if i.source else ''
    colloq = 'colloq' if i.colloq else ''
    yield f'<div class="entry">'
    yield f'<h1 id={i.id}><a class="tag more {colloq}" href="#{i.id}">#</a>{i.title} {source}</h1>'
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
    dot = graphviz.Digraph(engine='neato')
    dot.attr('graph', rankdir='LR', overlap="false", splines="true", epsilon=".0000001")
    js = '''
        function setup(id, others) {
            let node = document.getElementById(id);
            node.onmouseover = function() {{
                for (let other of others)
                    document.getElementById(other).classList.add("hovered");
            }};
            node.onmouseout = function() {{
                for (let other of others)
                    document.getElementById(other).classList.remove("hovered");
            }};
        }
    '''
    for k, v in data.items():
        dot.node(v.id, v.title, target="_blank", href=f"{root}#{v.id}", id=v.id)
        for i in v.referenced_by:
            dot.edge(v.id, i.id, id=f"{v.id}___{i.id}")
        others = ','.join(
            [f'"{i.id}"' for i in v.referenced_by + v.references + [v]]
            + [f'"{i.id}___{v.id}"' for i in v.references]
            + [f'"{v.id}___{i.id}"' for i in v.referenced_by]
        )
        js += f'setup("{v.id}", [{others}]);'

    outfile = dot.render(outfile, format='svg', cleanup=True)
    with open(outfile, 'r') as f:
        rendered = list(f.readlines())

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

def check_colloq(data):
    total = set()
    for card in data.values():
        for i in card.colloq:
            total.add(i)
    total = list(sorted(total))
    missing = []
    for n in range(1, int(total[-1]) + 1):
        group = [i for i in total if int(i) == n]
        step = min(group[i+1] - group[i] for i in range(len(group)-1))
        group = [int(i / step) for i in group]
        for i in range(group[0], group[-1], 1):
            if i not in group:
                missing.append(round(i * step, 4))
    eprint(f"Colloq: {len(total)}, but {len(missing)}: {repr(missing)}")

if __name__ == "__main__":
    data = load(stdin)
    eprint(f'Loaded {len(data)} cards')
    check_colloq(data)
    print_html(toposort(data.values()))
    eprint("\tHTML done")
    if len(argv) > 1:
        graph(data, argv[1], root=os.path.basename(argv[1]) + '.html')
        eprint("\tGraphivz done")
    eprint("Done")
