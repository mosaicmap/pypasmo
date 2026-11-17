#!/usr/bin/env python3
"""Convert the documentation (README.md and doc/) to simple HTML pages (standard library only).

    python tools/md2html.py OUTDIR      write OUTDIR/index.html (from README.md), OUTDIR/doc/...
    python tools/md2html.py --check     only check the links and anchors of the documentation

Only the Markdown that the documentation uses is supported: headings, paragraphs, lists
(nested by indentation), fenced code blocks, tables, `code`, **bold**, *italic*, links,
images, <https://...> and the HTML tags <br> and <nobr>. Links to .md files become links to
.html files, anchors are made as on GitHub. A link to a file outside README.md and doc/
(e.g. ../tests/...) is not in the HTML documentation: its text stays, without the link.
Images and other files in doc/ are copied; all pages use OUTDIR/style.css. Broken links
and anchors are errors.
"""
import html
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TITLE = "pypasmo documentation"

# style.css, used by all pages (the colours swap in the dark mode of the browser)
CSS = """\
:root { --fg: #1f2328; --bg: #ffffff; --line: #d1d9e0; --code: #f6f8fa; --link: #0969da; }
@media (prefers-color-scheme: dark) {
  :root { --fg: #e6edf3; --bg: #0d1117; --line: #3d444d; --code: #161b22; --link: #4493f8; }
}
body { max-width: 56rem; margin: 0 auto; padding: 0 1rem 3rem; background: var(--bg);
       color: var(--fg); font: 16px/1.5 system-ui, sans-serif; }
a { color: var(--link); }
h1, h2 { border-bottom: 1px solid var(--line); }
code, pre { font-family: Consolas, Menlo, monospace; background: var(--code); }
pre { padding: 0.8rem; overflow-x: auto; }
table { border-collapse: collapse; display: block; overflow-x: auto; }
th, td { border: 1px solid var(--line); padding: 0.3rem 0.6rem; text-align: left;
         vertical-align: top; }
img { max-width: 100%; }
nobr { white-space: nowrap; }
"""

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="stylesheet" href="{css}">
</head>
<body>
{body}
</body>
</html>
"""

FENCE = re.compile(r"^(\s*)```")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
ITEM = re.compile(r"^(\s*)([-*+]|\d+[.)])(\s+)(.*)$")
TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$")
RAW_TAG = re.compile(r"</?nobr>|<br\s*/?>", re.I)
ENTITY = re.compile(r"&(#\d+|#x[0-9a-fA-F]+|[A-Za-z]+);")


def slug(text):
    """The anchor of a heading as GitHub makes it (text without the Markdown marks)."""
    s = text.strip().lower()
    s = re.sub(r"[^\w\- ]", "", s)
    return s.replace(" ", "-")


def plain(md):
    """The visible text of inline Markdown (for anchors and the page title)."""
    s = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", md)
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
    s = re.sub(r"<[^>]+>", "", s)
    return s.replace("`", "").replace("**", "").replace("*", "")


def emphasis(text):
    """**bold** and *italic* (in text with the code spans already taken out)."""
    text = re.sub(r"\*\*(?=\S)(.+?)(?<=\S)\*\*", r"<strong>\1</strong>", text)
    return re.sub(r"(?<![\w*])\*(?=[^\s*])(.+?)(?<=[^\s*])\*(?![\w*])", r"<em>\1</em>", text)


class Page:
    def __init__(self, conv, src):
        self.conv = conv
        self.src = src                      # path relative to ROOT
        self.anchors = {}
        self.links = []                     # (target path or None, anchor, line text)
        self.title = None

    # ---------------------------------------------------------------- inline
    def inline(self, text):
        keep = []

        def hold(s):
            keep.append(s)
            return f"\x00{len(keep) - 1}\x00"

        # code spans first: nothing inside them is Markdown
        text = re.sub(r"(`+)(.+?)\1",
                      lambda m: hold(f"<code>{html.escape(m.group(2).strip(), False)}</code>"),
                      text)
        text = RAW_TAG.sub(lambda m: hold("<br>" if m.group(0)[1] in "bB" else m.group(0).lower()),
                           text)
        text = re.sub(r"<(https?://[^>\s]+)>",
                      lambda m: hold(f'<a href="{html.escape(m.group(1))}">'
                                     f'{html.escape(m.group(1), False)}</a>'), text)
        text = ENTITY.sub(lambda m: hold(m.group(0)), text)
        text = html.escape(text, False)
        text = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)",
                      lambda m: hold(self.image(m.group(1), m.group(2))), text)
        text = re.sub(r"\[((?:[^\[\]]|\x00)+)\]\(([^)\s]+)\)",
                      lambda m: hold(self.link(m.group(1), m.group(2))), text)
        text = emphasis(text)
        while "\x00" in text:
            text = re.sub(r"\x00(\d+)\x00", lambda m: keep[int(m.group(1))], text)
        return text

    def target(self, url):
        """(html url, path relative to ROOT or None, anchor) of a link in this page."""
        if re.match(r"^[a-z]+:", url):
            return url, None, None
        path, _, anchor = url.partition("#")
        if not path:
            return url, self.src, anchor
        rel = (ROOT / self.src).parent.joinpath(path).resolve()
        try:
            rel = rel.relative_to(ROOT)
        except ValueError:
            return None, None, None
        return path, rel, anchor

    def link(self, text, url):
        text = emphasis(text)
        new, rel, anchor = self.target(url)
        if rel is not None:
            self.links.append((rel, anchor, url))
        if rel is not None and rel.suffix == ".md":
            new = self.conv.html_url(self.src, rel) + (f"#{anchor}" if anchor else "")
            if text == html.escape(url, False):     # [doc/index.md](doc/index.md): the new name
                text = html.escape(new, False)
        elif rel is not None and not self.conv.published(rel):
            return text                     # a file that is not in the HTML documentation
        if new is None:
            return text
        return f'<a href="{html.escape(new)}">{text}</a>'

    def image(self, alt, url):
        _, rel, _ = self.target(url)
        if rel is not None:
            self.links.append((rel, "", url))
        return f'<img src="{html.escape(url)}" alt="{alt}">'

    # ---------------------------------------------------------------- blocks
    def blocks(self, lines, tight=False):
        out = []
        i = 0
        while i < len(lines):
            line = lines[i]
            if not line.strip():
                i += 1
                continue
            m = FENCE.match(line)
            if m:
                ind = len(m.group(1))
                j = i + 1
                while j < len(lines) and not FENCE.match(lines[j]):
                    j += 1
                code = [ln[ind:] if ln[:ind].strip() == "" else ln.lstrip() for ln in lines[i + 1:j]]
                out.append("<pre><code>" + html.escape("\n".join(code), False) + "</code></pre>")
                i = j + 1
                continue
            m = HEADING.match(line)
            if m:
                level, text = len(m.group(1)), m.group(2)
                base = slug(plain(text))
                a, n = base, 0
                while a in self.anchors:
                    n += 1
                    a = f"{base}-{n}"
                self.anchors[a] = True
                if level == 1 and self.title is None:
                    self.title = plain(text)
                out.append(f'<h{level} id="{a}">{self.inline(text)}</h{level}>')
                i += 1
                continue
            if line.lstrip().startswith("|") and i + 1 < len(lines) and TABLE_SEP.match(lines[i + 1]):
                j = i + 2
                while j < len(lines) and lines[j].lstrip().startswith("|"):
                    j += 1
                out.append(self.table(lines[i], lines[i + 2:j]))
                i = j
                continue
            m = ITEM.match(line)
            if m:
                i = self.list(lines, i, out)
                continue
            j = i + 1
            while j < len(lines) and lines[j].strip() and not self.starts_block(lines[j]):
                j += 1
            text = self.inline(" ".join(ln.strip() for ln in lines[i:j]))
            out.append(text if tight else f"<p>{text}</p>")
            i = j
        return "\n".join(out)

    @staticmethod
    def starts_block(line):
        return bool(FENCE.match(line) or HEADING.match(line) or ITEM.match(line)
                    or line.lstrip().startswith("|"))

    def list(self, lines, i, out):
        m = ITEM.match(lines[i])
        ind = len(m.group(1))
        ordered = m.group(2)[0].isdigit()
        items, loose = [], False
        while i < len(lines):
            m = ITEM.match(lines[i])
            if not m or len(m.group(1)) != ind or m.group(2)[0].isdigit() != ordered:
                break
            content = len(m.group(1)) + len(m.group(2)) + len(m.group(3))
            body = [m.group(4)]
            i += 1
            while i < len(lines):
                ln = lines[i]
                if not ln.strip():
                    # a blank line: the item goes on only with an indented line after it
                    k = i
                    while k < len(lines) and not lines[k].strip():
                        k += 1
                    if k < len(lines) and len(lines[k]) - len(lines[k].lstrip()) >= content:
                        body += [""] * (k - i)
                        loose = True
                        i = k
                        continue
                    break
                lead = len(ln) - len(ln.lstrip())
                if lead >= content:
                    body.append(ln[content:])
                elif ITEM.match(ln) or HEADING.match(ln) or FENCE.match(ln) or ln.lstrip().startswith("|"):
                    break
                else:
                    body.append(ln.strip())          # a lazy continuation line
                i += 1
            items.append(body)
            if i < len(lines) and not lines[i].strip():
                k = i
                while k < len(lines) and not lines[k].strip():
                    k += 1
                m2 = ITEM.match(lines[k]) if k < len(lines) else None
                if m2 and len(m2.group(1)) == ind and m2.group(2)[0].isdigit() == ordered:
                    loose = True
                    i = k
        tag = "ol" if ordered else "ul"
        out.append(f"<{tag}>")
        for body in items:
            out.append("<li>" + self.blocks(body, tight=not loose) + "</li>")
        out.append(f"</{tag}>")
        return i

    def table(self, head, rows):
        def cells(line):
            s = line.strip()
            s = s[1:] if s.startswith("|") else s
            s = s[:-1] if s.endswith("|") else s
            parts, cur, code = [], "", False
            for ch in s:
                if ch == "`":
                    code = not code
                if ch == "|" and not code:
                    parts.append(cur)
                    cur = ""
                else:
                    cur += ch
            parts.append(cur)
            return [p.strip() for p in parts]

        hc = cells(head)
        out = ["<table>", "<thead><tr>" + "".join(f"<th>{self.inline(c)}</th>" for c in hc)
               + "</tr></thead>", "<tbody>"]
        for r in rows:
            rc = (cells(r) + [""] * len(hc))[:len(hc)]
            out.append("<tr>" + "".join(f"<td>{self.inline(c)}</td>" for c in rc) + "</tr>")
        out += ["</tbody>", "</table>"]
        return "\n".join(out)


class Converter:
    def __init__(self):
        self.sources = [Path("README.md")] + sorted(
            p.relative_to(ROOT) for p in (ROOT / "doc").rglob("*.md"))
        self.files = sorted(p.relative_to(ROOT) for p in (ROOT / "doc").rglob("*")
                            if p.is_file() and p.suffix != ".md")

    def published(self, rel):
        return rel in self.sources or rel in self.files

    @staticmethod
    def out_name(rel):
        return Path("index.html") if rel == Path("README.md") else rel.with_suffix(".html")

    def html_url(self, src, rel):
        a, b = self.out_name(src).parent, self.out_name(rel)
        up = len(a.parts)
        common = 0
        while common < up and common < len(b.parts) - 1 and a.parts[common] == b.parts[common]:
            common += 1
        return "/".join([".."] * (up - common) + list(b.parts[common:]))

    def convert(self):
        pages = {}
        for rel in self.sources:
            page = Page(self, rel)
            text = (ROOT / rel).read_text(encoding="utf-8").replace("\r\n", "\n")
            page.body = page.blocks(text.split("\n"))
            pages[rel] = page
        errors = []
        for page in pages.values():
            for rel, anchor, url in page.links:
                if rel.suffix == ".md" and rel not in pages:
                    errors.append(f"{page.src}: {url}: no such page")
                elif rel.suffix == ".md":
                    if anchor and anchor not in pages[rel].anchors:
                        errors.append(f"{page.src}: {url}: no such anchor")
                elif not (ROOT / rel).exists():
                    errors.append(f"{page.src}: {url}: no such file")
        return pages, errors

    def write(self, outdir, pages):
        for rel, page in pages.items():
            target = outdir / self.out_name(rel)
            target.parent.mkdir(parents=True, exist_ok=True)
            css = "../" * len(self.out_name(rel).parent.parts) + "style.css"
            title = page.title or TITLE
            if rel != Path("README.md"):
                title = f"{title} - pypasmo"
            target.write_text(PAGE.format(title=html.escape(title), css=css, body=page.body),
                              encoding="utf-8", newline="\n")
        (outdir / "style.css").write_text(CSS, encoding="utf-8", newline="\n")
        for rel in self.files:
            (outdir / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(str(ROOT / rel), str(outdir / rel))


def build(outdir):
    """Write the HTML documentation into outdir; returns the list of written files."""
    conv = Converter()
    pages, errors = conv.convert()
    if errors:
        raise SystemExit("md2html: broken links\n  " + "\n  ".join(errors))
    outdir = Path(outdir)
    conv.write(outdir, pages)
    return sorted(p for p in outdir.rglob("*") if p.is_file())


def main(argv):
    if argv == ["--check"]:
        conv = Converter()
        pages, errors = conv.convert()
        links = sum(len(p.links) for p in pages.values())
        print(f"{len(pages)} pages, {links} links, {len(errors)} broken")
        for e in errors:
            print("  " + e)
        return 1 if errors else 0
    if len(argv) != 1 or argv[0].startswith("-"):
        print(__doc__.strip())
        return 2
    made = build(argv[0])
    print(f"md2html: {len(made)} files in {argv[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
