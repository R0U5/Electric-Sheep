#!/usr/bin/env python3
"""
Procedural Dungeon Generator using Binary Space Partitioning (BSP)
Generates random dungeons with rooms connected by corridors, rendered as ASCII art.
No external dependencies — pure Python.
"""

import random
from typing import Optional, Tuple, List

class BSPNode:
    """Node in a Binary Space Partitioning tree for dungeon generation."""
    def __init__(self, x: int, y: int, width: int, height: int):
        self.x = x  # Top-left corner X
        self.y = y  # Top-left corner Y
        self.width = width
        self.height = height
        self.left: Optional[BSPNode] = None
        self.right: Optional[BSPNode] = None
        self.room: Optional[Tuple[int, int, int, int]] = None  # (x, y, w, h) of room inside this node

    def split(self, min_size: int) -> bool:
        """Split the node into two children if possible. Returns True if split happened."""
        if self.left or self.right:
            return False  # Already split

        # Decide split direction: prefer splitting along the longer axis
        if self.width > self.height * 1.25:
            vertical = True
        elif self.height > self.width * 1.25:
            vertical = False
        else:
            vertical = random.choice([True, False])

        if vertical:
            # Vertical split (left/right)
            if self.width < min_size * 2:
                return False
            split_pos = random.randint(min_size, self.width - min_size)
            self.left = BSPNode(self.x, self.y, split_pos, self.height)
            self.right = BSPNode(self.x + split_pos, self.y, self.width - split_pos, self.height)
        else:
            # Horizontal split (top/bottom)
            if self.height < min_size * 2:
                return False
            split_pos = random.randint(min_size, self.height - min_size)
            self.left = BSPNode(self.x, self.y, self.width, split_pos)
            self.right = BSPNode(self.x, self.y + split_pos, self.width, self.height - split_pos)
        return True

    def create_room(self, min_room_size: int, max_room_size: int) -> None:
        """Create a random room inside this node's bounds."""
        # Room must be at least 1 tile away from node edges (for walls)
        max_w = min(max_room_size, self.width - 2)
        max_h = min(max_room_size, self.height - 2)
        if max_w < min_room_size or max_h < min_room_size:
            return

        room_w = random.randint(min_room_size, max_w)
        room_h = random.randint(min_room_size, max_h)
        room_x = self.x + random.randint(1, self.width - room_w - 1)
        room_y = self.y + random.randint(1, self.height - room_h - 1)
        self.room = (room_x, room_y, room_w, room_h)


def collect_leaves(node: BSPNode) -> List[BSPNode]:
    """Recursively collect all leaf nodes (nodes with no children) from the BSP tree."""
    if not node.left and not node.right:
        return [node]
    leaves = []
    if node.left:
        leaves.extend(collect_leaves(node.left))
    if node.right:
        leaves.extend(collect_leaves(node.right))
    return leaves


def generate_dungeon(
    grid_width: int = 80,
    grid_height: int = 24,
    min_split_size: int = 8,
    min_room_size: int = 4,
    max_room_size: int = 10,
    max_depth: int = 5
) -> Tuple[List[List[str]], List[BSPNode]]:
    """
    Generate a random dungeon using BSP.
    Returns (grid, leaf_nodes) where grid is a 2D list of characters, leaf_nodes are room-bearing nodes.
    """
    root = BSPNode(0, 0, grid_width, grid_height)
    nodes = [root]

    # Recursively split nodes up to max_depth
    for _ in range(max_depth):
        new_nodes = []
        for node in nodes:
            if node.split(min_split_size):
                new_nodes.append(node.left)
                new_nodes.append(node.right)
        nodes = new_nodes
        if not nodes:
            break

    # Collect leaf nodes and create rooms in them
    leaves = collect_leaves(root)
    for leaf in leaves:
        leaf.create_room(min_room_size, max_room_size)

    # Initialize grid with walls
    grid = [['#' for _ in range(grid_width)] for _ in range(grid_height)]

    # Draw rooms (floor tiles)
    for leaf in leaves:
        if not leaf.room:
            continue
        x, y, w, h = leaf.room
        for i in range(x, x + w):
            for j in range(y, y + h):
                if 0 <= i < grid_width and 0 <= j < grid_height:
                    grid[j][i] = '.'

    # Connect rooms with simple L-shaped corridors between consecutive leaves
    for i in range(len(leaves) - 1):
        r1 = leaves[i].room
        r2 = leaves[i + 1].room
        if not r1 or not r2:
            continue

        # Center of each room
        x1 = r1[0] + r1[2] // 2
        y1 = r1[1] + r1[3] // 2
        x2 = r2[0] + r2[2] // 2
        y2 = r2[1] + r2[3] // 2

        # Draw horizontal segment first, then vertical
        for x in range(min(x1, x2), max(x1, x2) + 1):
            if 0 <= x < grid_width and 0 <= y1 < grid_height:
                grid[y1][x] = '.'
        for y in range(min(y1, y2), max(y1, y2) + 1):
            if 0 <= x2 < grid_width and 0 <= y < grid_height:
                grid[y][x2] = '.'

    return grid, leaves


def print_dungeon(grid: List[List[str]]) -> None:
    """Print the dungeon grid to terminal."""
    for row in grid:
        print(''.join(row))


if __name__ == "__main__":
    random.seed()  # Use system random seed for different output each run
    grid, leaves = generate_dungeon()
    print_dungeon(grid)
    print(f"\nGenerated {len([leaf for leaf in leaves if leaf.room])} rooms")
