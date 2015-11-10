#!/usr/bin/env python

from itertools import chain
import sys, re

def _match_from(line):
    return re.match(r'^\s*from (?P<module>.+)(?P<the_rest>\s+import .*)$', line)

def _has_unclosed_parens(line):
    """
    Assumes there's no more than one pair of parens (or just one "("), which is reasonable for
    import lines.
    """
    if '(' in line:
        _, rest = line.split('(')
        return ')' not in rest
    return False

def sort_imports(lines):
    """
    `lines` is an iterable containing a line per element.
    """
    # Join multiline imports into single elements in the list.
    line_it = iter(lines)
    _lines = []
    while True:
        try:
            line = line_it.next()
        except StopIteration:
            break
        if _has_unclosed_parens(line):
            while True:
                try:
                    next_line = line_it.next()
                    line += next_line
                    if ')' in next_line:
                        break
                except StopIteration:
                    break
        _lines.append(line)
    lines = _lines

    # Partition into chunks to sort individually, divided by blank lines.
    chunks, chunk = [], []
    for line in lines:
        if not line.strip():
            chunks.extend([chunk, [line]])
            chunk = []
        else:
            chunk.append(line)
    chunks.append(chunk)

    def key(line):
        # Ignores parens when sorting.
        line = line.strip().replace('(', '').replace(')', '')
        m = _match_from(line)
        if m:
            return 'import {0} from {1}'.format(m.group('module'), m.group('the_rest'))
        return line

    return list(chain.from_iterable(map(lambda lines: sorted(lines, key=key), chunks)))


if __name__ == '__main__':
    lines = sys.stdin
    for line in sort_imports(lines):
        print line,


# Use `nosetests sort_imports.py` to run tests.
def test_sort_imports():
    lines = ([
        'import b\n', 'import a\n', 'from a import foo\n', 'from a import bar, baz\n', 'import a, b\n',
        '\n',
        'import two\n', 'import one\n',
        '\n',
        'import 3\n', 'import (2,\n', '        1\n', '        0)\n', 'import 1\n',
    ])
    sorted_lines = sort_imports(lines)
    print 'Sorted:'
    print [e for e in sorted_lines]
    assert sorted_lines == ([
        'import a\n', 'from a import bar, baz\n', 'from a import foo\n', 'import a, b\n', 'import b\n',
        '\n',
        'import one\n', 'import two\n',
        '\n',
        'import 1\n', 'import (2,\n        1\n        0)\n', 'import 3\n',
    ])

