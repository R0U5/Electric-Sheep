#!/usr/bin/env python3
"""
Sliding Block Puzzle (15-Puzzle)
A classic sliding tile puzzle game for the terminal.

Rules:
- Arrange tiles 1-15 in order (empty space at bottom-right)
- Move tiles by sliding into the empty space
- Use WASD or arrow keys to move the empty space
- Q to quit

The puzzle is always solvable because we generate it by
shuffling the solved state with valid moves.
"""

import random
import sys
import os
import tty
import termios
import select


def clear_screen():
    """Clear the terminal."""
    os.system('clear' if os.name == 'posix' else 'cls')


def getch():
    """Get a single character from terminal without needing Enter."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch


def check_key():
    """Non-blocking key check for real-time input."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(sys.stdin.fileno())
        ready, _, _ = select.select([sys.stdin], [], [], 0)
        if ready:
            return sys.stdin.read(1)
        return None
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


class SlidingPuzzle:
    SIZE = 4
    EMPTY = 0
    
    def __init__(self):
        self.board = []
        self.moves = 0
        self.empty_pos = (3, 3)
        self.solved = False
        self.init_board()
    
    def init_board(self):
        """Create solved state and shuffle it."""
        # Start with solved state: 1-15 in order, 0 (empty) at bottom-right
        self.board = [
            [1, 2, 3, 4],
            [5, 6, 7, 8],
            [9, 10, 11, 12],
            [13, 14, 15, self.EMPTY]
        ]
        self.empty_pos = (3, 3)
        self.moves = 0
        self.solved = False
        
        # Shuffle by making random valid moves (guarantees solvability)
        self.shuffle_board(200)
    
    def shuffle_board(self, num_moves):
        """Shuffle by making random valid moves from solved state."""
        moves = []
        for _ in range(num_moves):
            valid = self.get_valid_moves()
            if valid:
                move = random.choice(valid)
                self._apply_move(move[0], move[1])
                moves.append(move)
    
    def get_valid_moves(self):
        """Get list of valid slide directions based on empty space position."""
        row, col = self.empty_pos
        moves = []
        
        # Empty can move UP (tile from above slides down) if not in top row
        if row > 0:
            moves.append((row - 1, col))
        # Empty can move DOWN if not in bottom row
        if row < self.SIZE - 1:
            moves.append((row + 1, col))
        # Empty can move LEFT if not in leftmost column
        if col > 0:
            moves.append((row, col - 1))
        # Empty can move RIGHT if not in rightmost column
        if col < self.SIZE - 1:
            moves.append((row, col + 1))
        
        return moves
    
    def _apply_move(self, new_row, new_col):
        """Internal: apply a move without validation (for shuffle)."""
        old_row, old_col = self.empty_pos
        self.board[old_row][old_col] = self.board[new_row][new_col]
        self.board[new_row][new_col] = self.EMPTY
        self.empty_pos = (new_row, new_col)
    
    def move_tile(self, direction):
        """Move based on WASD (where the empty space moves)."""
        row, col = self.empty_pos
        new_row, new_col = row, col
        
        if direction == 'w':  # Empty moves UP (WASD style - tile from north slides down)
            new_row = row - 1
        elif direction == 's':  # Empty moves DOWN
            new_row = row + 1
        elif direction == 'a':  # Empty moves LEFT
            new_col = col - 1
        elif direction == 'd':  # Empty moves RIGHT
            new_col = col + 1
        else:
            return False
        
        # Validate move
        if 0 <= new_row < self.SIZE and 0 <= new_col < self.SIZE:
            # Move the tile into the empty space
            self.board[row][col] = self.board[new_row][new_col]
            self.board[new_row][new_col] = self.EMPTY
            self.empty_pos = (new_row, new_col)
            self.moves += 1
            self.check_solved()
            return True
        return False
    
    def check_solved(self):
        """Check if the puzzle is in solved state."""
        expected = 1
        for row in range(self.SIZE):
            for col in range(self.SIZE):
                if row == self.SIZE - 1 and col == self.SIZE - 1:
                    # Last position should be empty
                    if self.board[row][col] != self.EMPTY:
                        self.solved = False
                        return
                else:
                    if self.board[row][col] != expected:
                        self.solved = False
                        return
                    expected += 1
        self.solved = True
    
    def is_valid_move(self, direction):
        """Check if a move is valid without executing it."""
        row, col = self.empty_pos
        if direction == 'w':
            return row > 0
        elif direction == 's':
            return row < self.SIZE - 1
        elif direction == 'a':
            return col > 0
        elif direction == 'd':
            return col < self.SIZE - 1
        return False
    
    def render(self):
        """Render the puzzle board."""
        print("╔════╦════╦════╦════╗")
        for row in range(self.SIZE):
            line = "║"
            for col in range(self.SIZE):
                val = self.board[row][col]
                if val == self.EMPTY:
                    line += "    ║"
                elif val < 10:
                    line += f"  {val} ║"
                else:
                    line += f" {val} ║"
            print(line)
            if row < self.SIZE - 1:
                print("╠════╬════╬════╬════╣")
        print("╚════╩════╩════╩════╝")
    
    def get_instructions(self):
        """Get the instructions string."""
        return """
┌─────────────────────────────────────────────────────────┐
│  SLIDING PUZZLE (15-Puzzle)                             │
│  Arrange tiles 1-15 in order. Empty space at bottom.    │
│                                                         │
│  CONTROLS:                                              │
│    W/A/S/D = Move the empty space (slides adjacent)     │
│    Q = Quit                                             │
│    R = Restart with new shuffle                         │
│                                                         │
│  Move count: {:3d}                                      │
└─────────────────────────────────────────────────────────┘""".format(self.moves)
    
    def get_win_message(self):
        """Get the victory message."""
        msgs = [
            "🎉 SOLVED! Great job! 🎉",
            "⭐ Perfect! You did it! ⭐",
            "🏆 Excellent sliding skills! 🏆",
            "✨ Victory! Puzzle mastered! ✨"
        ]
        return random.choice(msgs)


def play_game():
    """Main game loop."""
    puzzle = SlidingPuzzle()
    
    # Save terminal settings
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    
    try:
        while True:
            clear_screen()
            print(puzzle.get_instructions())
            print()
            puzzle.render()
            
            if puzzle.solved:
                print()
                print(f"    {puzzle.get_win_message()}")
                print(f"    Completed in {puzzle.moves} moves!")
                print()
                print("    Press R to restart, Q to quit...")
            
            # Get input
            key = getch()
            key = key.lower()
            
            if key == 'q':
                clear_screen()
                print("Thanks for playing!")
                break
            elif key == 'r':
                puzzle = SlidingPuzzle()
            elif key in ['w', 'a', 's', 'd']:
                if puzzle.solved:
                    continue  # No moves after winning until restart
                valid = puzzle.is_valid_move(key)
                if valid:
                    puzzle.move_tile(key)
                # Invalid moves just do nothing (no penalty)
            elif key == '\x03':  # Ctrl+C
                break
                
    finally:
        # Restore terminal settings
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        print("\nGoodbye!")


if __name__ == "__main__":
    play_game()
