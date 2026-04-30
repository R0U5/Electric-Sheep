#!/usr/bin/env python3
"""
A* Pathfinder with Recursive Backtracking Maze Generator

Runs A* pathfinding on optionally-generated mazes. Shows the open/closed set
evolution, the final path, and stats. Two modes: maze mode (generate first)
or direct mode (pathfind a custom grid).
"""

import heapq
import random
import sys

# ─── A* core ────────────────────────────────────────────────────────────────

def astar(grid, start, goal):
    rows, cols = len(grid), len(grid[0])
    def heuristic(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])  # Manhattan

    open_set = []
    heapq.heappush(open_set, (0, start))
    came_from = {}
    g_score = {start: 0}
    f_score = {start: heuristic(start, goal)}
    closed = set()
    open_remaining = {start}
    node_expansions = 0

    while open_set:
        _, current = heapq.heappop(open_set)
        open_remaining.discard(current)

        if current == goal:
            # Reconstruct path
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.reverse()
            return {
                "path": path,
                "cost": g_score[goal],
                "expansions": node_expansions,
                "closed": len(closed),
                "open_max": len(open_remaining),
            }

        closed.add(current)

        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            neighbor = (current[0] + dr, current[1] + dc)
            if not (0 <= neighbor[0] < rows and 0 <= neighbor[1] < cols):
                continue
            if grid[neighbor[0]][neighbor[1]] == '#':
                continue

            tentative_g = g_score[current] + 1
            if tentative_g < g_score.get(neighbor, float('inf')):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f = tentative_g + heuristic(neighbor, goal)
                f_score[neighbor] = f
                if neighbor not in open_remaining:
                    heapq.heappush(open_set, (f, neighbor))
                    open_remaining.add(neighbor)
                    node_expansions += 1

    return None  # No path

# ─── Maze generation ────────────────────────────────────────────────────────

def generate_maze(rows, cols):
    # Initialize grid with walls
    grid = [['#'] * cols for _ in range(rows)]
    # Carve using recursive backtracking
    start_r, start_c = 1, 1
    stack = [(start_r, start_c)]
    grid[start_r][start_c] = ' '

    while stack:
        r, c = stack[-1]
        neighbors = []
        for dr, dc in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
            nr, nc = r + dr, c + dc
            if 1 <= nr < rows - 1 and 1 <= nc < cols - 1 and grid[nr][nc] == '#':
                neighbors.append((nr, nc, r + dr // 2, c + dc // 2))
        if neighbors:
            nr, nc, wr, wc = random.choice(neighbors)
            grid[nr][nc] = ' '
            grid[wr][wc] = ' '
            stack.append((nr, nc))
        else:
            stack.pop()

    return grid

# ─── ASCII rendering ─────────────────────────────────────────────────────────

RENDER_CHARS = {
    '#': '██',
    ' ': '  ',
    'S': '🛫',
    'G': '🎯',
    '·': ' ·',
    '*': '██',  # path — override to solid
}

def render(grid, path_set=None, visited=None, start=None, goal=None):
    rows = len(grid)
    out = []
    for r in range(rows):
        row_chars = []
        for c in range(len(grid[r])):
            cell = grid[r][c]
            pos = (r, c)
            if path_set and pos in path_set:
                ch = '**' if cell != 'S' and cell != 'G' else cell * 2
            elif visited and pos in visited:
                ch = '··'
            elif cell == '#':
                ch = '██'
            elif cell == ' ':
                ch = '  '
            else:
                ch = cell * 2
            row_chars.append(ch)
        out.append(' '.join(row_chars))
    return '\n'.join(out)

def parse_direct_grid(lines):
    """Parse a multi-line string grid for direct mode."""
    rows = [list(line) for line in lines if line.strip()]
    # Normalize widths
    max_w = max(len(r) for r in rows)
    for row in rows:
        while len(row) < max_w:
            row.append('#')
    return rows

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    # Default: generate a maze and pathfind
    rows, cols = 21, 31
    maze_mode = True

    args = sys.argv[1:]
    if args:
        if args[0] == '--help':
            print(__doc__)
            print("Usage: python maze_pathfinder.py [--direct]")
            print("  --direct  Read grid from stdin (use S=start, G=goal, # wall, space=open)")
            return
        if args[0] == '--direct':
            maze_mode = False

    if maze_mode:
        print("=== A* Pathfinder + Recursive-Backtracking Maze ===\n")
        random.seed()
        grid = generate_maze(rows, cols)
    else:
        print("=== A* Pathfinder (direct mode) ===\n")
        print("Enter your grid (S=start, G=goal, # wall, space=open). Empty line to finish:")
        lines = []
        while True:
            try:
                line = input()
                if line.strip() == '':
                    break
                lines.append(line.rstrip('\n'))
            except EOFError:
                break
        if not lines:
            print("No grid provided. Generating maze instead.")
            grid = generate_maze(21, 31)
        else:
            grid = parse_direct_grid(lines)

    rows, cols = len(grid), len(grid[0])

    # Place start and goal
    cells = [(r, c) for r in range(rows) for c in range(cols) if grid[r][c] == ' ']
    random.shuffle(cells)
    start, goal = cells[0], cells[1]
    grid[start[0]][start[1]] = 'S'
    grid[goal[0]][goal[1]] = 'G'

    print(f"Grid: {cols}x{rows}  |  Start: {start}  |  Goal: {goal}\n")

    result = astar(grid, start, goal)

    if result is None:
        print("No path found.")
        return

    path_set = set(result['path'])
    print(f"Path length (steps): {result['cost']}")
    print(f"Nodes expanded:      {result['expansions']}")
    print(f"Closed set size:      {result['closed']}")
    print(f"Max open set size:   {result['open_max']}")

    print(f"\n{'='*cols*2}")
    print(render(grid, path_set=path_set))
    print(f"{'='*cols*2}")
    print(f"\n  Legend: ██ wall   ·· explored   ** path   🛫 start   🎯 goal")

if __name__ == '__main__':
    main()