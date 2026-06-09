#!/usr/bin/env python3
"""
String Diff Tool — LCS-based diff with multiple output formats.
Usage: string_diff.py [options] <file_a> <file_b>
       string_diff.py [options] --string-a "text" --string-b "text"
       cat <file> | string_diff.py --string-b "other text"
"""

import argparse
import json
import sys
from dataclasses import dataclass
from typing import List, Tuple, Optional

@dataclass
class DiffOp:
    op: str  # 'equal', 'insert', 'delete'
    a_start: int
    a_end: int
    b_start: int
    b_end: int
    a_content: str
    b_content: str

def _diff_by_char(a: str, b: str) -> List[DiffOp]:
    """Diff by individual characters."""
    n, m = len(a), len(b)
    
    # Build LCS table
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if a[i-1] == b[j-1]:
                dp[i][j] = dp[i-1][j-1] + 1
            else:
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])
    
    # Backtrack to build the diff
    return _backtrack_diff(a, b, dp, n, m)

def _diff_by_line(a_lines: List[str], b_lines: List[str]) -> List[DiffOp]:
    """Diff by lines."""
    n, m = len(a_lines), len(b_lines)
    
    # Build LCS table
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if a_lines[i-1] == b_lines[j-1]:
                dp[i][j] = dp[i-1][j-1] + 1
            else:
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])
    
    return _backtrack_diff_lines(a_lines, b_lines, dp, n, m)

def _backtrack_diff(a: str, b: str, dp, i: int, j: int) -> List[DiffOp]:
    """Backtrack through LCS table to build diff operations (character mode)."""
    if i == 0 and j == 0:
        return []
    
    ops = []
    
    if i > 0 and j > 0 and a[i-1] == b[j-1]:
        ops = _backtrack_diff(a, b, dp, i-1, j-1)
        ops.append(DiffOp('equal', i-1, i, j-1, j, a[i-1], b[j-1]))
    elif j > 0 and (i == 0 or dp[i][j-1] >= dp[i-1][j]):
        ops = _backtrack_diff(a, b, dp, i, j-1)
        ops.append(DiffOp('insert', i, i, j-1, j, '', b[j-1]))
    elif i > 0 and (j == 0 or dp[i][j-1] < dp[i-1][j]):
        ops = _backtrack_diff(a, b, dp, i-1, j)
        ops.append(DiffOp('delete', i-1, i, j, j, a[i-1], ''))
    
    ops.reverse()  # Backtracking produces operations in reverse order
    return ops

def _backtrack_diff_lines(a_lines: List[str], b_lines: List[str], dp, i: int, j: int) -> List[DiffOp]:
    """Backtrack through LCS table to build diff operations (line mode)."""
    if i == 0 and j == 0:
        return []
    
    ops = []
    
    if i > 0 and j > 0 and a_lines[i-1] == b_lines[j-1]:
        ops = _backtrack_diff_lines(a_lines, b_lines, dp, i-1, j-1)
        ops.append(DiffOp('equal', i-1, i, j-1, j, a_lines[i-1], b_lines[j-1]))
    elif j > 0 and (i == 0 or dp[i][j-1] >= dp[i-1][j]):
        ops = _backtrack_diff_lines(a_lines, b_lines, dp, i, j-1)
        ops.append(DiffOp('insert', i, i, j-1, j, '', b_lines[j-1]))
    elif i > 0 and (j == 0 or dp[i][j-1] < dp[i-1][j]):
        ops = _backtrack_diff_lines(a_lines, b_lines, dp, i-1, j)
        ops.append(DiffOp('delete', i-1, i, j, j, a_lines[i-1], ''))
    
    ops.reverse()  # Backtracking produces operations in reverse order
    return ops

def diff_strings(a: str, b: str, line_mode: bool = False) -> List[DiffOp]:
    """Compute diff between two strings using LCS-based approach.
    
    Args:
        a: First string
        b: Second string  
        line_mode: If True, split by newlines and diff by lines. If False, diff by characters.
    """
    if line_mode:
        return _diff_by_line(a.split('\n'), b.split('\n'))
    else:
        return _diff_by_char(a, b)

def format_human(ops: List[DiffOp], line_mode: bool = False) -> str:
    """Format diff as human-readable output."""
    lines = []
    for op in ops:
        if line_mode:
            if op.op == 'equal':
                lines.append(f"  {op.a_content}")
            elif op.op == 'delete':
                lines.append(f"- {op.a_content}")
            elif op.op == 'insert':
                lines.append(f"+ {op.b_content}")
        else:
            # Character mode
            if op.op == 'equal':
                lines.append(f"  {op.a_content}")
            elif op.op == 'delete':
                lines.append(f"- {op.a_content}")
            elif op.op == 'insert':
                lines.append(f"+ {op.b_content}")
    return '\n'.join(lines)

def format_unified(ops: List[DiffOp], a_name: str = 'a', b_name: str = 'b', line_mode: bool = False) -> str:
    """Format diff as unified diff style (like GNU diff -u)."""
    hunks = []
    current_hunk = None
    equal_count = 0
    
    line_a = 0
    line_b = 0
    
    for op in ops:
        if op.op == 'equal':
            if current_hunk is None:
                current_hunk = {'start_a': line_a, 'start_b': line_b, 'lines': [], 'equal_count': 0}
            current_hunk['lines'].append(f" {op.a_content}")
            current_hunk['equal_count'] += 1
            equal_count += 1
            line_a += 1
            line_b += 1
        elif op.op == 'delete':
            if current_hunk is None:
                current_hunk = {'start_a': line_a, 'start_b': line_b, 'lines': [], 'equal_count': 0}
            current_hunk['lines'].append(f"-{op.a_content}")
            current_hunk['equal_count'] = 0
            equal_count = 0
            line_a += 1
        elif op.op == 'insert':
            if current_hunk is None:
                current_hunk = {'start_a': line_a, 'start_b': line_b, 'lines': [], 'equal_count': 0}
            current_hunk['lines'].append(f"+{op.b_content}")
            current_hunk['equal_count'] = 0
            equal_count = 0
            line_b += 1
        
        # Flush hunk if too many equal lines separate changes
        if current_hunk and current_hunk['equal_count'] > 3:
            hunks.append(current_hunk)
            current_hunk = None
    
    if current_hunk:
        hunks.append(current_hunk)
    
    if not hunks:
        return f"--- {a_name}\n+++ {b_name}\nNo differences."
    
    # Build output
    result = [f"--- {a_name}", f"+++ {b_name}"]
    
    for hunk in hunks:
        # Count total lines in hunk
        del_count = sum(1 for l in hunk['lines'] if l.startswith('-'))
        ins_count = sum(1 for l in hunk['lines'] if l.startswith('+'))
        result.append(f"@@ -{hunk['start_a'] + 1},{del_count} +{hunk['start_b'] + 1},{ins_count} @@")
        result.extend(hunk['lines'])
    
    return '\n'.join(result)

def format_json(ops: List[DiffOp], line_mode: bool = False) -> str:
    """Format diff as JSON."""
    result = {
        'operations': [],
        'stats': {'equal': 0, 'insertions': 0, 'deletions': 0}
    }
    
    for op in ops:
        result['operations'].append({
            'type': op.op,
            'a_range': [op.a_start, op.a_end],
            'b_range': [op.b_start, op.b_end],
            'a_content': op.a_content,
            'b_content': op.b_content
        })
        if op.op == 'equal':
            result['stats']['equal'] += 1 if line_mode else len(op.a_content)
        elif op.op == 'insert':
            result['stats']['insertions'] += 1 if line_mode else len(op.b_content)
        elif op.op == 'delete':
            result['stats']['deletions'] += 1 if line_mode else len(op.a_content)
    
    return json.dumps(result, indent=2)

def format_side_by_side(ops: List[DiffOp], width: int = 40) -> str:
    """Format diff as side-by-side view."""
    left_lines = []
    
    for op in ops:
        if op.op == 'equal':
            left_lines.append(f" {op.a_content:<{width}} │ {op.b_content}")
        elif op.op == 'delete':
            left_lines.append(f"-{op.a_content}")
        elif op.op == 'insert':
            left_lines.append(f"{'':>{width}} │ +{op.b_content}")
    
    return '\n'.join(left_lines)

def format_minimal(ops: List[DiffOp], line_mode: bool = False) -> str:
    """Format as minimal edit script."""
    lines = []
    for op in ops:
        if op.op == 'delete':
            lines.append(f"{op.a_end}d\n{op.a_content}\n")
        elif op.op == 'insert':
            lines.append(f"{op.a_start}i\n{op.b_content}\n")
        elif op.op == 'equal':
            lines.append(f"{op.a_start}c\n{op.a_content}\n")
    return ''.join(lines)

def main():
    parser = argparse.ArgumentParser(
        description='String Diff Tool — compare two strings or files with multiple output formats',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s file1.txt file2.txt
  %(prog)s --string-a "hello world" --string-b "hello there"
  %(prog)s -f json file1.txt file2.txt
  %(prog)s --format unified-diff file1.txt file2.txt
  cat file1.txt | %(prog)s --string-b "$(cat file2.txt)"
''')
    
    parser.add_argument('file_a', nargs='?', help='First file (or use --string-a)')
    parser.add_argument('file_b', nargs='?', help='Second file (or use --string-b)')
    
    parser.add_argument('--string-a', help='First string instead of file')
    parser.add_argument('--string-b', help='Second string instead of file')
    
    parser.add_argument('-f', '--format', choices=['human', 'unified', 'json', 'side-by-side', 'minimal'],
                       default='human', help='Output format (default: human)')
    parser.add_argument('-w', '--width', type=int, default=40, help='Width for side-by-side view (default: 40)')
    parser.add_argument('-l', '--lines', action='store_true', help='Diff by lines instead of characters')
    
    args = parser.parse_args()
    
    # Get strings to compare
    if args.string_a is not None and args.string_b is not None:
        a, b = args.string_a, args.string_b
        a_name, b_name = 'string-a', 'string-b'
    elif args.string_a is not None or args.string_b is not None:
        print("Error: must specify both --string-a and --string-b, or provide two files", file=sys.stderr)
        sys.exit(1)
    elif args.file_a and args.file_b:
        try:
            with open(args.file_a, 'r') as f:
                a = f.read()
            with open(args.file_b, 'r') as f:
                b = f.read()
            a_name, b_name = args.file_a, args.file_b
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    elif not sys.stdin.isatty():
        # stdin -> use --string-b for the other string
        a = sys.stdin.read()
        if args.string_b:
            b = args.string_b
            a_name, b_name = 'stdin', 'string-b'
        else:
            print("Error: stdin requires --string-b to be set", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)
    
    # Compute diff
    ops = diff_strings(a, b, line_mode=args.lines)
    
    # Format and output
    if args.format == 'human':
        print(format_human(ops, line_mode=args.lines))
    elif args.format == 'unified':
        print(format_unified(ops, a_name, b_name, line_mode=args.lines))
    elif args.format == 'json':
        print(format_json(ops, line_mode=args.lines))
    elif args.format == 'side-by-side':
        print(format_side_by_side(ops, args.width))
    elif args.format == 'minimal':
        print(format_minimal(ops, line_mode=args.lines), end='')

if __name__ == '__main__':
    main()