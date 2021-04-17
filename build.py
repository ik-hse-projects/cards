import yaml
import markdown
from sys import argv, stderr

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
        self.collok = data.get('collok', False)
        self.references = []
        self.referenced_by = []

class Missing:
    def __init__(self, id):
        self.id = id

def what_letter(x):
    superscript_map = {'¹': '1', '²': '2', '³': '3', '⁴': '4', '⁵': 5, '⁻': '-', '⁺': '+'}
    subscript_map = {
            '₁': '1', '₂': '2', '₃': '3', '₄': '4', '₅': '5', '₋': '-', '₊': '+',
            'ᵢ': 'i', 'ⱼ': 'j', 'ₖ': 'k', 'ₙ': 'n', 'ₘ': 'm', 'ₛ': 's'}
    if x in superscript_map:
        return 'super', superscript_map[x]
    if x in subscript_map:
        return 'sub', subscript_map[x]
    return None, x


def clean_text(text):
    text = text.replace('≠', '\u2260')  # For some reason KaTeX does not display it well

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
    return text


def load(path):
    with open(path, 'r') as f:
        data = yaml.load(f, Loader=yaml.CLoader)
    data = {k: Entry(k, v) for k, v in data.items() if not k.startswith('_')}

    for k, v in data.items():
        for tag in v.tags:
            data[tag].referenced_by.append(v)
            v.references.append(data[tag])
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
            raise Exception('not a DAG')
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
    collok = 'collok' if i.collok else ''
    yield f'<div class="entry">'
    yield f'<h1 id={i.id}><a class="tag more {collok}" href="#{i.id}">#</a>{i.title} {bulat}</h1>'
    yield (markdown.Markdown(
            extensions=['mdx_math'],
            extension_configs={
                'mdx_math': {'use_gitlab_delimiters': True}
            }
        ).convert(clean_text(i.text)))

    yield '<hr/>'
    yield from add_more('←', i.references)
    yield from add_more('→', i.referenced_by)
    yield '</div>'

HEADER='''<!DOCTYPE html>
<html>
  <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.13.2/dist/katex.min.css" integrity="sha384-Cqd8ihRLum0CCg8rz0hYKPoLZ3uw+gES2rXQXycqnL5pgVQIflxAUDS7ZSjITLb5" crossorigin="anonymous">
    <script src="https://cdn.jsdelivr.net/npm/katex@0.13.2/dist/katex.min.js" integrity="sha384-1Or6BdeNQb0ezrmtGeqQHFpppNd7a/gw29xeiSikBbsb44xu3uAo8c7FwbF5jhbd" crossorigin="anonymous"></script>
    <script src="https://cdn.jsdelivr.net/npm/katex@0.13.2/dist/contrib/auto-render.min.js" integrity="sha384-vZTG03m+2yp6N6BNi5iM4rW4oIwk5DfcNdFfxkk9ZWpDriOkXX8voJBFrAO7MpVl" crossorigin="anonymous"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/split.js/1.6.4/split.min.js" integrity="sha512-HwVfwWgxD3SrpYgpIEGapjIid6YzmKiY4lwoc55rbO/6Y/2ZSgy6PX7zYUV5wqBD4hTsHzDovN6HqEzc/68lUg==" crossorigin="anonymous"></script>
    <style>
@font-face {
    font-family: 'Linux Libertine'; /* normal */
    src: url('./libertine/LinLibertine_R.otf');
    font-weight: normal;
    font-style: normal;
}

@font-face {
    font-family: 'Linux Libertine'; /* italic */
    src: url('./libertine/LinLibertine_RI.otf');
    font-weight: normal;
    font-style: italic;
}

@font-face {
    font-family: 'Linux Libertine'; /* bold */
    src: url('./libertine/LinLibertine_RB.otf');
    font-weight: bold;
    font-style: normal;
}

@font-face {
    font-family: 'Linux Libertine'; /* bold italic */
    src: url('./libertine/LinLibertine_RBI.otf');
    font-weight: bold;
    font-style: italic;
}

.tag {
    font-size: smaller;
    color: gray;
}

.collok {
    color: #ee0000;
}

small {
    font-size: small;
}

details[disabled] summary,
details.disabled summary {
    pointer-events: none; /* prevents click events */
    text-decoration: line-through;
}

details {
  margin-left: 1.5em;
}

h1 {
    margin: 0;
}

html
{
   font-family: 'Linux Libertine';
}

.katex {
   font-size: 1em;
}

.katex-display {
   font-size: 1.21em;
}

html, body {
    position: absolute;
    height: 100vh;
    width: 100vw;
}

.entry {
   border: 1px solid lightgray;
   padding: 1em;
   margin: 0em 0.5em 1em 0.5em;
}

.split {
    position: fixed;
    display: flex;
    flex-direction: row;
    overflow-y: hidden;
    overflow-x: hidden;
}

.panel {
    overflow: scroll;
}

.gutter {
    background-color: #eee;
    background-repeat: no-repeat;
    background-position: 50%;
}

.gutter.gutter-horizontal {
    background-image: url('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAeCAYAAADkftS9AAAAIklEQVQoU2M4c+bMfxAGAgYYmwGrIIiDjrELjpo5aiZeMwF+yNnOs5KSvgAAAABJRU5ErkJggg==');
    cursor: col-resize;
}

hr:last-child {
    display: none;
}
    </style>
  </head>
  <body class="split">
  <div class="panel" id="main_panel">
'''
FOOTER=r'''
  </div>
  <div class="panel" id="side_panel">
  </div>
  <script>
let scripts = document.body.getElementsByTagName("script");
scripts = Array.prototype.slice.call(scripts);
scripts.forEach(function(script) {
    if (!script.type || !script.type.match(/math\/tex/i)) {
        return -1;
    }
    const display = (script.type.match(/mode\s*=\s*display(;|\s|\n|$)/) != null);

    const katexElement = document.createElement(display ? "div" : "span");
    katexElement.setAttribute("class", display ? "equation" : "inline-equation");
    try {
        katex.render(script.text, katexElement, {
          macros: {
              "\\Σ": "\\sum",
          },
          fleqn: true,
          displayMode: display
        });
    } catch (err) {
        console.error(err);
        katexElement.textContent = script.text;
    }
    script.parentNode.replaceChild(katexElement, script);
});
  </script>
  <script>
    function bindButtons(root) {
        for (let elem of root.querySelectorAll('.more')) {
            elem.onclick = (ev) => {
                ev.preventDefault();
                let parent = document.querySelector(elem.getAttribute("href")).parentElement;
                let child = parent.cloneNode(true);
                bindButtons(child);
                side_panel.prepend(child);
                let tag = child.querySelector('.tag');
                tag.text = 'ⓧ';
                tag.onclick = (ev) => {
                    ev.preventDefault();
                    side_panel.removeChild(child);
                    return false;
                }
                return false;
            };
        }
    }
    if (window.screen.availWidth >= 1200) {
        Split(['#main_panel', '#side_panel'], {
            sizes: [65, 35],
        });
        bindButtons(document);
    }
  </script>
  </body>
</html>
'''
  
if __name__ == "__main__":
    print(HEADER)
    data = load(argv[1]).values()
    data = toposort(data)
    for i in data:
        if i.text is not None:
            for ln in render(i):
                print(ln)
    print(FOOTER)
