#!/usr/bin/env python3
"""
Clean references-2.bib.

Fixes, in order:
  1. Duplicate fields inside one entry (BibTeX warns, biblatex can reject).
     Keeps the FIRST occurrence, drops later ones.
  2. Malformed author fields such as  author = {, Hafner}
  3. Scraped page titles: strips everything from the first  {\textbar}
     ("| Springer Nature Link", "| Request PDF", "| Cambridge Core", etc.)
  4. Scraped titles ending "- Google Search".

Does NOT delete entries, reorder them, or touch anything else.
Uncited entries never print, so they are left alone.

Usage:
    python3 fix_bib.py references-2.bib references-2-clean.bib
"""
import re, sys, shutil
from collections import Counter

def split_entries(text):
    """Yield (preamble, entry_text) chunks, splitting on @type{key at column 0."""
    idx = [m.start() for m in re.finditer(r'(?m)^@\w+\s*\{', text)]
    if not idx:
        return [text]
    chunks = [text[:idx[0]]]
    for a, b in zip(idx, idx[1:] + [len(text)]):
        chunks.append(text[a:b])
    return chunks

def field_name(line):
    m = re.match(r'\s*([A-Za-z_-]+)\s*=', line)
    return m.group(1).lower() if m else None

def fix_entry(entry, log):
    lines = entry.split('\n')
    seen = set()
    out = []
    key = re.match(r'@\w+\s*\{\s*([^,]+)', entry)
    key = key.group(1).strip() if key else '?'
    depth = 0
    for line in lines:
        fn = field_name(line)
        # only treat as a field line when we are at entry top level
        if fn and depth <= 1:
            if fn in seen:
                log.append(f'  {key}: dropped duplicate field "{fn}"')
                depth += line.count('{') - line.count('}')
                continue
            seen.add(fn)
        depth += line.count('{') - line.count('}')
        out.append(line)
    entry = '\n'.join(out)

    # malformed author: leading comma inside the braces
    m = re.search(r'author\s*=\s*\{\s*,\s*([^}]*)\}', entry)
    if m:
        name = m.group(1).strip()
        entry = entry[:m.start()] + 'author = {{' + name + '}}' + entry[m.end():]
        log.append(f'  {key}: repaired author field "{{, {name}}}" -> "{{{{{name}}}}}"')

    # scraped page titles
    def trim_title(mt):
        body = mt.group(1)
        cut = body.split(r'{\textbar}')[0].strip().rstrip(',').strip()
        cut = re.sub(r'\s*-\s*\{Google\}\s*\{Search\}\s*$', '', cut).strip()
        if cut != body.strip():
            log.append(f'  {key}: trimmed scraped page title')
        return 'title = {' + cut + '}'
    entry = re.sub(r'title\s*=\s*\{((?:[^{}]|\{[^{}]*\})*)\}', trim_title, entry, count=1)
    return entry

def main():
    src, dst = sys.argv[1], sys.argv[2]
    text = open(src, encoding='utf-8').read()
    before_entries = len(re.findall(r'(?m)^@\w+\s*\{', text))
    before_balance = text.count('{') - text.count('}')

    log = []
    chunks = split_entries(text)
    fixed = [chunks[0]] + [fix_entry(c, log) for c in chunks[1:]]
    result = ''.join(fixed)

    after_entries = len(re.findall(r'(?m)^@\w+\s*\{', result))
    after_balance = result.count('{') - result.count('}')

    print(f'entries: {before_entries} -> {after_entries}')
    print(f'brace balance: {before_balance} -> {after_balance}  (0 is correct)')
    if before_balance != 0:
        print('  !! source file is already unbalanced; find the missing brace before trusting output')
    print(f'\n{len(log)} change(s):')
    for l in log:
        print(l)
    if after_entries != before_entries:
        print('\n!! entry count changed, NOT writing output'); sys.exit(1)
    open(dst, 'w', encoding='utf-8').write(result)
    print(f'\nwritten: {dst}')

if __name__ == '__main__':
    main()
