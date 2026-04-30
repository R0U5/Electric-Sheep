#!/usr/bin/env python3
"""
sheepgrep — a recursive file search tool with regex, context lines, and file type filtering.

Usage:
    python3 sheepgrep.py -r <pattern> <path>     Search recursively
    python3 sheepgrep.py <pattern> <path>       Search single directory (non-recursive)
    python3 sheepgrep.py <pattern> <file>       Search single file

Flags:
    -r, --recursive        Walk subdirectories
    -i, --ignore-case      Case-insensitive matching
    -w, --word-match       Match only word boundaries (--word-boundaries)
    -t, --filetype          Only files matching extension, e.g. py, js, txt
    -c, --count             Show match count per file instead of lines
    -A, --after <n>         Print n lines after each match
    -B, --before <n>        Print n lines before each match
    -C, --context <n>       Print n lines of context around matches
    -l, --files-with-matches  Print only filenames with matches
    -n, --line-number      Prefix output with line numbers
    -v, --invert            Show lines that do NOT match
    --no-extensions         Don't search files with no extension
"""

import argparse
import os
import re
import sys
from pathlib import Path

DEFAULT_FILETYPES = {'py', 'js', 'ts', 'tsx', 'jsx', 'md', 'txt', 'json', 'yaml', 'yml', 'toml', 'sh', 'bash', 'zsh', 'c', 'cpp', 'h', 'hpp', 'rs', 'go', 'java', 'kt', 'swift', 'html', 'css', 'scss', 'sass', 'less', 'sql', 'rb', 'php', 'lua', 'r', 'R', 'scala', 'clj', 'ex', 'exs', 'erl', 'hs', 'elm', 'purs', 'ml', 'fs', 'vue', 'svelte', 'toml', 'ini', 'cfg', 'conf', 'xml', 'xaml', 'yaml', 'yml', 'sh', 'bash', 'zsh', 'fish', 'ps1', 'bat', 'cmd', 'dockerfile', 'makefile', 'cmake', 'groovy', 'gradle', 'env', 'gitignore', 'editorconfig'}


def build_parser():
    parser = argparse.ArgumentParser(
        description='sheepgrep — recursive file search with regex support',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('pattern', help='Regex pattern to search for')
    parser.add_argument('path', nargs='?', default='.', help='File or directory to search')
    parser.add_argument('-r', '--recursive', action='store_true', help='Recursive search')
    parser.add_argument('-i', '--ignore-case', action='store_true', help='Case-insensitive')
    parser.add_argument('-w', '--word-match', action='store_true', help='Match whole words only')
    parser.add_argument('-t', '--filetype', action='append', dest='filetypes', default=[], help='File extensions to include (without dot)')
    parser.add_argument('-c', '--count', action='store_true', help='Show match count per file')
    parser.add_argument('-A', '--after', type=int, default=0, help='Lines after match')
    parser.add_argument('-B', '--before', type=int, default=0, help='Lines before match')
    parser.add_argument('-C', '--context', type=int, default=0, help='Context lines before and after')
    parser.add_argument('-l', '--files-with-matches', action='store_true', dest='files_only', help='Only show filenames')
    parser.add_argument('-n', '--line-number', action='store_true', help='Show line numbers')
    parser.add_argument('-v', '--invert', action='store_true', help='Invert match (show non-matches)')
    parser.add_argument('--no-extensions', action='store_true', help='Skip files with no extension')
    parser.add_argument('--hidden', action='store_true', help='Include hidden files/directories')
    return parser


def get_files(root_path, recursive, filetypes, no_extensions, hidden):
    root = Path(root_path).resolve()
    if root.is_file():
        yield str(root)
        return

    if not root.is_dir():
        return

    for entry in os.scandir(root):
        if not hidden and entry.name.startswith('.'):
            continue
        if entry.is_dir():
            if recursive:
                yield from get_files(entry.path, recursive, filetypes, no_extensions, hidden)
        elif entry.is_file():
            ext = Path(entry.name).suffix.lstrip('.')
            # If filetypes specified, filter by them
            if filetypes:
                if ext.lower() not in {ft.lower() for ft in filetypes}:
                    continue
            else:
                # Default: skip files with no extension unless told otherwise
                if no_extensions and not ext:
                    continue
                if not no_extensions and not ext and ext.lower() not in DEFAULT_FILETYPES:
                    # Skip files without recognized extensions unless no-extensions flag is set
                    pass  # Currently we only filter when filetypes is explicit

            # Actually: if no explicit filetypes, use DEFAULT but skip no-extension unless --no-extensions
            if not filetypes:
                if not ext and not no_extensions:
                    # Skip files without extension when using default set
                    if ext.lower() not in DEFAULT_FILETYPES:
                        continue
                elif ext.lower() not in DEFAULT_FILETYPES and not no_extensions:
                    if not ext:
                        continue

            yield entry.path


def search_file(filepath, pattern, flags, args):
    """Search a single file for pattern. Returns list of (line_num, line_content, matches)."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
    except (PermissionError, IsADirectoryError):
        return []
    except OSError:
        return []

    results = []
    flag = 0 if flags & re.IGNORECASE else re.MULTILINE
    if flags & re.IGNORECASE:
        flag = re.IGNORECASE | re.MULTILINE
    else:
        flag = re.MULTILINE

    try:
        compiled = re.compile(pattern, flag)
    except re.error as e:
        print(f"[sheepgrep] Invalid regex: {e}", file=sys.stderr)
        sys.exit(2)

    for i, line in enumerate(lines, 1):
        line_matches = args.invert ^ bool(compiled.search(line))
        if line_matches:
            matches = compiled.findall(line)
            results.append((i, line.rstrip('\n\r'), matches))

    return results


def print_result(filepath, line_num, line_content, matches, args, count_mode=False):
    if count_mode:
        print(f"{filepath}")
        return
    if args.files_only:
        print(f"{filepath}")
        return

    prefix = ""
    if args.line_number:
        prefix = f"{line_num}:"
    color_matched = os.environ.get('SHEEPGREP_COLOR', 'auto')
    if color_matched == 'always' or (color_matched == 'auto' and sys.stdout.isatty()):
        highlighted = highlight_matches(line_content, matches, args.pattern)
        print(f"{prefix}{highlighted}")
    else:
        print(f"{prefix}{line_content}")


def highlight_matches(line, matches, pattern):
    """Replace matched portions with ANSI-colored text."""
    ESC = '\x1b'
    RED = f"{ESC}[31m"
    GREEN = f"{ESC}[32m"
    RESET = f"{ESC}[0m"

    if not matches:
        return line

    # Build a list of (start, end) positions of all matches
    positions = []
    try:
        for m in re.finditer(pattern, line, re.IGNORECASE):
            positions.append((m.start(), m.end()))
    except re.error:
        return line

    if not positions:
        return line

    # Merge overlapping positions
    positions.sort()
    merged = [positions[0]]
    for start, end in positions[1:]:
        last = merged[-1]
        if start <= last[1]:
            merged[-1] = (last[0], max(last[1], end))
        else:
            merged.append((start, end))

    # Build highlighted string by slicing the line and inserting color codes
    result = []
    pos = 0
    for start, end in merged:
        result.append(line[pos:start])
        result.append(f"{RED}{line[start:end]}{RESET}")
        pos = end
    result.append(line[pos:])
    return ''.join(result)


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.pattern:
        parser.print_help()
        sys.exit(1)

    # Resolve path
    path = args.path or '.'

    # Context setup
    before = args.before + args.context
    after = args.after + args.context

    # Build regex flags
    flags = re.IGNORECASE if args.ignore_case else 0

    # Word boundary adjustment
    pattern = args.pattern
    if args.word_match:
        pattern = r'\b' + pattern + r'\b'

    # Collect files to search
    files = list(get_files(path, args.recursive, args.filetypes, args.no_extensions, args.hidden))

    if not files:
        print(f"[sheepgrep] No files found to search in: {path}", file=sys.stderr)
        sys.exit(1)

    total_matches = 0
    files_with_matches = 0

    for filepath in files:
        results = search_file(filepath, pattern, flags, args)

        if not results:
            continue

        files_with_matches += 1
        match_count = len(results)

        if args.count:
            print_result(filepath, 0, f"  {match_count} matches", [], args, count_mode=True)
            continue

        if args.files_only:
            print_result(filepath, 0, "", [], args)
            continue

        # Show context: need to collect nearby lines too
        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                all_lines = f.readlines()
        except OSError:
            continue

        for lineno, line_content, matches in results:
            start = max(0, lineno - 1 - before)
            end = min(len(all_lines), lineno + after)
            for lnum in range(start, end):
                if lnum + 1 == lineno:
                    print_result(filepath, lnum + 1, all_lines[lnum].rstrip('\n\r'), matches, args)
                else:
                    prefix = f"{lnum + 1}:" if args.line_number else ""
                    print(f"{prefix}  {all_lines[lnum].rstrip('\n\r')}")

        total_matches += match_count

    # Summary
    if not args.files_only and not args.count:
        plural_es = "es" if total_matches != 1 else ""
    plural_s = "s" if files_with_matches != 1 else ""
    print(f"\n[sheepgrep] {total_matches} match{plural_es} across {files_with_matches} file{plural_s}")

    sys.exit(0)


if __name__ == '__main__':
    main()
