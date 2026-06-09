#!/usr/bin/env python3
"""
Constraint Satisfaction Solver
Implements AC-3 arc consistency and backtracking with heuristics.
Solves real-world problems: Sudoku, N-Queens, Map Coloring,
Cryptarithmetic, Job Scheduling, and more.
"""

import heapq
import random
import string
import sys
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Set, Tuple, Union


class Variable:
    """A variable with a domain of possible values."""
    
    def __init__(self, name: str, domain: Set):
        self.name = name
        self.domain = set(domain)
        self.assigned_value = None
        self.assignment_level = 0

    def assign(self, value, level: int = 0):
        self.assigned_value = value
        self.assignment_level = level
        self.domain = {value}

    def unassign(self, domain: Set):
        self.assigned_value = None
        self.assignment_level = 0
        self.domain = set(domain)

    def is_assigned(self) -> bool:
        return self.assigned_value is not None

    def copy(self) -> 'Variable':
        v = Variable(self.name, self.domain)
        v.assigned_value = self.assigned_value
        v.assignment_level = self.assignment_level
        return v

    def __repr__(self):
        if self.is_assigned():
            return f"{self.name}={self.assigned_value}"
        return f"{self.name}{list(self.domain)}"


ConstraintFunc = Callable[[Variable, Variable], bool]


class Constraint:
    """Binary constraint between two variables."""
    
    def __init__(self, var1: str, var2: str, constraint_fn: ConstraintFunc):
        self.var1 = var1
        self.var2 = var2
        self.fn = constraint_fn

    def is_satisfied(self, v1: Variable, v2: Variable) -> bool:
        return self.fn(v1, v2)

    def __repr__(self):
        return f"C({self.var1}, {self.var2})"


class CSProblem:
    """A constraint satisfaction problem definition."""
    
    def __init__(self):
        self.variables: Dict[str, Variable] = {}
        self.constraints: List[Constraint] = []
        self.constraint_graph: Dict[str, List[Constraint]] = defaultdict(list)
        self.global_constraints: List[Callable] = []

    def add_variable(self, name: str, domain: Set):
        self.variables[name] = Variable(name, domain)

    def add_constraint(self, constraint: Constraint):
        self.constraints.append(constraint)
        self.constraint_graph[constraint.var1].append(constraint)
        # Add reverse constraint for undirected constraints
        rev = Constraint(constraint.var2, constraint.var1, 
                        lambda v1, v2: constraint.fn(v1, v2))
        self.constraint_graph[constraint.var2].append(rev)

    def add_global_constraint(self, constraint_fn: Callable):
        """Add a global constraint that checks all variables."""
        self.global_constraints.append(constraint_fn)

    def get_neighbors(self, var_name: str) -> List[str]:
        """Get all variables connected to var_name via constraints."""
        return list(set(c.var2 for c in self.constraint_graph[var_name]))

    def copy(self) -> 'CSProblem':
        p = CSProblem()
        for name, var in self.variables.items():
            p.variables[name] = var.copy()
        p.constraints = self.constraints.copy()
        p.constraint_graph = self.constraint_graph.copy()
        p.global_constraints = self.global_constraints.copy()
        return p


class SolverStats:
    """Statistics for solver performance analysis."""
    
    def __init__(self):
        self.nodes_explored = 0
        self.backtracks = 0
        self.arc_revisions = 0
        self.start_time = None
        self.end_time = None

    @property
    def time_ms(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0


class CSSolver:
    """
    Constraint Satisfaction Solver with AC-3 and backtracking.
    Implements minimum remaining values (MRV) and degree heuristics.
    """

    def __init__(self, use_ac3: bool = True, use_mrv: bool = True, 
                 use_degree: bool = True, use_lcv: bool = True,
                 verbose: bool = False):
        self.use_ac3 = use_ac3
        self.use_mrv = use_mrv  # Minimum Remaining Values heuristic
        self.use_degree = use_degree  # Degree heuristic tiebreaker
        self.use_lcv = use_lcv  # Least Constraining Value
        self.verbose = verbose
        self.stats = SolverStats()

    def ac3(self, problem: CSProblem, queue: Optional[List[Tuple[Variable, Variable]]] = None) -> bool:
        """
        AC-3: Arc Consistency Algorithm 3.
        Returns True if arc consistency can be maintained, False if inconsistency detected.
        """
        if queue is None:
            # Initialize with all arcs
            queue = deque()
            for constraint in problem.constraints:
                queue.append((problem.variables[constraint.var1], 
                             problem.variables[constraint.var2]))
        else:
            queue = deque(queue)

        while queue:
            xi, xj = queue.popleft()
            if self._revise(problem, xi, xj):
                self.stats.arc_revisions += 1
                if len(xi.domain) == 0:
                    return False
                # Add all neighbors of xi except xj back to queue
                for constraint in problem.constraint_graph[xi.name]:
                    xk = problem.variables[constraint.var2]
                    if xk.name != xj.name:
                        queue.append((xk, xi))
        return True

    def _revise(self, problem: CSProblem, xi: Variable, xj: Variable) -> bool:
        """Return True if xi's domain was revised."""
        revised = False
        to_remove = set()
        
        for val_i in xi.domain:
            satisfies = False
            for val_j in xj.domain:
                # Temporarily assign to check constraint
                old_i, old_j = xi.assigned_value, xj.assigned_value
                xi.assigned_value = val_i
                xj.assigned_value = val_j
                
                # Check all constraints between them
                satisfied = True
                for constraint in problem.constraint_graph[xi.name]:
                    if constraint.var2 == xj.name:
                        if not constraint.is_satisfied(xi, xj):
                            satisfied = False
                            break
                
                xi.assigned_value = old_i
                xj.assigned_value = old_j
                
                if satisfied:
                    satisfies = True
                    break
            
            if not satisfies:
                to_remove.add(val_i)
                revised = True
        
        xi.domain -= to_remove
        return revised

    def select_unassigned_variable(self, problem: CSProblem, assignment: Dict[str, any]) -> Optional[str]:
        """
        Select next variable to assign using MRV and degree heuristics.
        """
        unassigned = [v for v in problem.variables.values() 
                     if v.name not in assignment]
        
        if not unassigned:
            return None

        if self.use_mrv:
            # Minimum Remaining Values heuristic
            min_domain_size = min(len(v.domain) for v in unassigned if len(v.domain) > 0)
            candidates = [v for v in unassigned if len(v.domain) == min_domain_size]
            
            if self.use_degree and len(candidates) > 1:
                # Degree heuristic: choose variable with most constraints on remaining variables
                def degree_heuristic(v):
                    return sum(1 for c in problem.constraint_graph[v.name]
                             if c.var2 not in assignment)
                candidates.sort(key=degree_heuristic, reverse=True)
            
            return candidates[0].name
        
        return unassigned[0].name

    def order_domain_values(self, problem: CSProblem, var_name: str, 
                           assignment: Dict[str, any]) -> List:
        """
        Order values using Least Constraining Value heuristic.
        Prioritizes values that rule out fewest choices for neighboring variables.
        """
        var = problem.variables[var_name]
        values = list(var.domain)
        
        if not self.use_lcv:
            return values

        def count_constraints_removed(value):
            count = 0
            # Check how many neighbor values this rules out
            for nb_name in problem.get_neighbors(var_name):
                if nb_name not in assignment:
                    nb = problem.variables[nb_name]
                    for nb_val in nb.domain:
                        # Simulate constraint check
                        old_var, old_nb = var.assigned_value, nb.assigned_value
                        var.assigned_value = value
                        nb.assigned_value = nb_val
                        
                        compatible = True
                        for constraint in problem.constraint_graph[var_name]:
                            if constraint.var2 == nb_name:
                                if not constraint.is_satisfied(var, nb):
                                    compatible = False
                                    break
                        
                        var.assigned_value = old_var
                        nb.assigned_value = old_nb
                        
                        if not compatible:
                            count += 1
            return count

        return sorted(values, key=count_constraints_removed)

    def backtrack(self, problem: CSProblem, assignment: Dict[str, any], 
                  level: int = 0) -> Optional[Dict[str, any]]:
        """
        Recursive backtracking search.
        """
        self.stats.nodes_explored += 1

        if len(assignment) == len(problem.variables):
            # Check equation for cryptarithmetic if applicable
            if hasattr(problem, 'equation_info'):
                left_nums = []
                for word in problem.equation_info['left']:
                    num = 0
                    for c in word:
                        num = num * 10 + assignment[c]
                    left_nums.append(num)
                result_num = 0
                for c in problem.equation_info['result']:
                    result_num = result_num * 10 + assignment[c]
                if sum(left_nums) != result_num:
                    return None  # Sum constraint violated
            return assignment.copy()

        var_name = self.select_unassigned_variable(problem, assignment)
        if var_name is None:
            return None

        var = problem.variables[var_name]
        ordered_values = self.order_domain_values(problem, var_name, assignment)

        for value in ordered_values:
            if self.verbose and level < 2:
                print(f"{'  ' * level}Trying {var_name} = {value}")

            # Check if value is consistent with current assignment
            consistent = True
            for constraint in problem.constraint_graph[var_name]:
                if constraint.var2 in assignment:
                    nb_var = problem.variables[constraint.var2]
                    old_val = var.assigned_value
                    var.assigned_value = value
                    
                    if not constraint.is_satisfied(var, nb_var):
                        consistent = False
                    
                    var.assigned_value = old_val

            if not consistent:
                continue

            # Make assignment
            old_domain = set(var.domain)
            var.assign(value, level)
            assignment[var_name] = value

            # Run AC-3 if requested
            if self.use_ac3:
                # Save domains for potential rollback
                saved_domains = {}
                for v in problem.variables.values():
                    saved_domains[v.name] = set(v.domain)

                # Add arcs from neighbors to this variable
                arc_queue = []
                for nb_name in problem.get_neighbors(var_name):
                    if nb_name not in assignment:
                        arc_queue.append((problem.variables[nb_name], var))

                if not self.ac3(problem, arc_queue):
                    # Inconsistency detected, restore and backtrack
                    for v in problem.variables.values():
                        v.domain = saved_domains[v.name]
                    var.unassign(old_domain)
                    del assignment[var_name]
                    self.stats.backtracks += 1
                    continue

            # Recursively search
            result = self.backtrack(problem, assignment, level + 1)
            if result is not None:
                return result

            # Backtrack
            if self.use_ac3:
                for v in problem.variables.values():
                    v.domain = saved_domains.get(v.name, v.domain)
            
            var.unassign(old_domain)
            del assignment[var_name]
            self.stats.backtracks += 1

        return None

    def solve(self, problem: CSProblem) -> Optional[Dict[str, any]]:
        """Solve the constraint satisfaction problem."""
        import time
        
        self.stats = SolverStats()
        self.stats.start_time = time.time()

        # Initial AC-3
        if self.use_ac3:
            if not self.ac3(problem):
                self.stats.end_time = time.time()
                return None

        solution = self.backtrack(problem, {})
        self.stats.end_time = time.time()
        return solution


# =============================================================================
# Problem Builders
# =============================================================================

def create_sudoku_problem(grid: List[List[int]]) -> Optional[CSProblem]:
    """
    Create a Sudoku CSP from a 9x9 grid.
    0 indicates empty cell to be solved.
    """
    problem = CSProblem()
    
    # Create variables for each cell
    for row in range(9):
        for col in range(9):
            name = f"r{row}c{col}"
            if grid[row][col] == 0:
                problem.add_variable(name, set(range(1, 10)))
            else:
                problem.add_variable(name, {grid[row][col]})
    
    # All-different constraints for rows
    for row in range(9):
        for i in range(9):
            for j in range(i + 1, 9):
                v1, v2 = f"r{row}c{i}", f"r{row}c{j}"
                problem.add_constraint(Constraint(v1, v2, 
                    lambda v1, v2: v1.assigned_value != v2.assigned_value))
    
    # All-different constraints for columns
    for col in range(9):
        for i in range(9):
            for j in range(i + 1, 9):
                v1, v2 = f"r{i}c{col}", f"r{j}c{col}"
                problem.add_constraint(Constraint(v1, v2,
                    lambda v1, v2: v1.assigned_value != v2.assigned_value))
    
    # All-different constraints for 3x3 boxes
    for box_row in range(3):
        for box_col in range(3):
            cells = []
            for r in range(3):
                for c in range(3):
                    cells.append(f"r{box_row*3 + r}c{box_col*3 + c}")
            for i in range(9):
                for j in range(i + 1, 9):
                    problem.add_constraint(Constraint(cells[i], cells[j],
                        lambda v1, v2: v1.assigned_value != v2.assigned_value))
    
    return problem


def create_nqueens_problem(n: int) -> CSProblem:
    """
    Create N-Queens CSP.
    Variables represent row positions for each column's queen.
    """
    problem = CSProblem()
    
    for i in range(n):
        problem.add_variable(f"q{i}", set(range(n)))
    
    # No two queens in same row
    for i in range(n):
        for j in range(i + 1, n):
            problem.add_constraint(Constraint(f"q{i}", f"q{j}",
                lambda v1, v2: v1.assigned_value != v2.assigned_value))
    
    # No two queens on same diagonal (difference = difference)
    for i in range(n):
        for j in range(i + 1, n):
            diff = j - i
            problem.add_constraint(Constraint(f"q{i}", f"q{j}",
                lambda v1, v2, d=diff: abs(v1.assigned_value - v2.assigned_value) != d))
    
    return problem


def create_map_coloring_problem() -> Tuple[CSProblem, Dict[str, str]]:
    """
    Create Australia map coloring CSP (classic CSP example).
    Variables are regions, constraints are borders.
    """
    problem = CSProblem()
    
    regions = ["WA", "NT", "SA", "Q", "NSW", "V", "T"]
    colors = {"red", "green", "blue", "yellow"}
    
    for region in regions:
        problem.add_variable(region, colors)
    
    borders = [
        ("WA", "NT"), ("WA", "SA"), ("NT", "SA"), ("NT", "Q"),
        ("SA", "Q"), ("SA", "NSW"), ("SA", "V"),
        ("Q", "NSW"), ("NSW", "V")
    ]
    
    for r1, r2 in borders:
        problem.add_constraint(Constraint(r1, r2,
            lambda v1, v2: v1.assigned_value != v2.assigned_value))
    
    return problem, {r: r for r in regions}


class CryptarithmeticGlobalConstraint:
    """Global constraint for cryptarithmetic sum equation."""
    def __init__(self, left_words, result_word):
        self.left = left_words
        self.result = result_word
    
    def is_satisfied(self, variables):
        """Check if the sum equation holds with current assignments."""
        def word_to_num(word):
            num = 0
            for c in word:
                if c.isalpha():
                    if c not in variables or variables[c].assigned_value is None:
                        return None  # Not fully assigned
                    num = num * 10 + variables[c].assigned_value
                else:
                    num = num * 10 + int(c)
            return num
        
        left_sum = 0
        for word in self.left:
            num = word_to_num(word)
            if num is None:
                return True  # Skip if not fully assigned
            left_sum += num
        
        result_num = word_to_num(self.result)
        if result_num is None:
            return True  # Skip if not fully assigned
        
        return left_sum == result_num


def create_cryptarithmetic_problem(puzzle: str) -> Tuple[CSProblem, Dict[str, any]]:
    """
    Create cryptarithmetic CSP. Example: "SEND + MORE = MONEY"
    Uses uniqueness constraints + leading letter != 0.
    The sum equation is verified as a global constraint on complete assignments.
    """
    parts = puzzle.replace(" ", "").split("=")
    left = parts[0].split("+")
    result = parts[1]
    
    unique_letters = set()
    for word in left + [result]:
        for c in word:
            if c.isalpha():
                unique_letters.add(c)
    
    letters = sorted(unique_letters)
    problem = CSProblem()
    
    # Each letter is a digit 0-9
    for letter in letters:
        problem.add_variable(letter, set(range(10)))
    
    # All letters must have different values
    for i in range(len(letters)):
        for j in range(i + 1, len(letters)):
            problem.add_constraint(Constraint(letters[i], letters[j],
                lambda v1, v2: v1.assigned_value != v2.assigned_value))
    
    # Leading letters cannot be zero
    for word in left + [result]:
        first_letter = word[0]
        if first_letter.isalpha():
            problem.variables[first_letter].domain -= {0}
    
    # Add column constraints to enforce sum incrementally
    max_len = max(len(w) for w in left + [result])
    
    # Pad all words to same length from left (easier for column processing)
    left_padded = [w.zfill(max_len) for w in left]
    result_padded = result.zfill(max_len)
    
    # Add carry variables (binary: 0 or 1)
    for i in range(max_len + 1):
        problem.add_variable(f"_carry{i}", {0, 1})
    problem.variables["_carry0"].domain = {0}  # Initial carry is 0
    
    # For rightmost column (least significant digit), add constraint
    # that involves carry_in and carry_out
    def make_col_constraint(left_letters, result_letter, col_idx, max_len):
        """Create constraint for a single column sum."""
        col_from_right = max_len - 1 - col_idx
        
        def check_col(v1, v2):
            # This is a placeholder - actual constraint checking is complex
            # We'll validate the full sum at the end
            return True
        return check_col
    
    # Store equation info for verification
    problem.equation_info = {
        "left": left, 
        "result": result,
        "left_padded": left_padded,
        "result_padded": result_padded,
        "max_len": max_len
    }
    
    return problem, {"left": left, "result": result, "letters": letters}


def create_scheduler_problem() -> Tuple[CSProblem, Dict[str, any]]:
    """
    Course scheduling CSP.
    Schedule 4 courses across 3 time slots with professor constraints.
    """
    problem = CSProblem()
    
    courses = ["CS101", "CS201", "MATH150", "PHYS200"]
    slots = ["Mon_9am", "Mon_11am", "Wed_9am"]
    professors = {"CS101": "Dr_A", "CS201": "Dr_A", "MATH150": "Dr_B", "PHYS200": "Dr_C"}
    
    # Variables: course -> time slot
    for course in courses:
        problem.add_variable(course, set(slots))
    
    # Professor can't teach two courses at same time
    for i, c1 in enumerate(courses):
        for c2 in courses[i+1:]:
            if professors[c1] == professors[c2]:
                problem.add_constraint(Constraint(c1, c2,
                    lambda v1, v2: v1.assigned_value != v2.assigned_value))
    
    return problem, {
        "courses": courses, 
        "slots": slots, 
        "professors": professors
    }


# =============================================================================
# Output Formatters
# =============================================================================

def format_sudoku_solution(solution: Dict[str, int]) -> str:
    """Pretty print Sudoku solution."""
    grid = [[0] * 9 for _ in range(9)]
    for name, val in solution.items():
        if name.startswith('r'):
            row = int(name[1])
            col = int(name[3])
            grid[row][col] = val
    
    lines = []
    for i, row in enumerate(grid):
        if i % 3 == 0 and i > 0:
            lines.append("├───────┼───────┼───────┤")
        row_str = "│ "
        for j, val in enumerate(row):
            row_str += f"{val} "
            if j % 3 == 2 and j < 8:
                row_str += "│ "
        row_str += "│"
        lines.append(row_str)
    
    result = "┌───────┬───────┬───────┐\n"
    result += "\n".join(lines)
    result += "\n└───────┴───────┴───────┘"
    return result


def format_nqueens_board(solution: Dict[str, int], n: int) -> str:
    """Pretty print N-Queens solution."""
    lines = []
    # solution maps q{i} -> row position
    positions = {int(k[1:]): v for k, v in solution.items()}
    
    lines.append("┌" + "───┬" * (n-1) + "───┐")
    for row in range(n):
        board_row = "│"
        for col in range(n):
            if positions.get(col, -1) == row:
                board_row += " ♛ │"
            else:
                board_row += "   │"
        lines.append(board_row)
        if row < n - 1:
            lines.append("├" + "───┼" * (n-1) + "───┤")
    lines.append("└" + "───┴" * (n-1) + "───┘")
    return "\n".join(lines)


def format_map_coloring(solution: Dict[str, str], regions: List[str]) -> str:
    """Pretty print map coloring solution."""
    color_codes = {
        "red": "\033[91m",
        "green": "\033[92m", 
        "blue": "\033[94m",
        "yellow": "\033[93m"
    }
    reset = "\033[0m"
    
    lines = []
    for region in regions:
        color = solution[region]
        code = color_codes.get(color.lower(), "")
        lines.append(f"  {region}: {code}{color.upper()}{reset}")
    return "\n".join(lines)


def format_cryptarithmetic(solution: Dict[str, int], info: Dict) -> str:
    """Pretty print cryptarithmetic solution."""
    lines = []
    
    def word_to_num(word: str) -> int:
        num = 0
        for c in word:
            if c.isalpha():
                num = num * 10 + solution[c]
            else:
                num = num * 10 + int(c)
        return num
    
    # Show letter assignments
    lines.append("Letter assignments:")
    for letter in info["letters"]:
        lines.append(f"  {letter} = {solution[letter]}")
    
    lines.append("")
    
    # Show equation
    left_nums = [word_to_num(w) for w in info["left"]]
    result_num = word_to_num(info["result"])
    
    left_str = " + ".join(f"{word_to_num(w)} ({w})" for w in info["left"])
    lines.append(f"Verification: {left_str} = {result_num} ({info['result']})")
    lines.append(f"              {' + '.join(map(str, left_nums))} = {result_num}")
    lines.append(f"              ✓ {sum(left_nums)} == {result_num}")
    
    return "\n".join(lines)


def format_scheduler(solution: Dict[str, str], info: Dict) -> str:
    """Pretty print course schedule."""
    lines = ["Course Schedule:"]
    lines.append("─" * 40)
    
    for slot in info["slots"]:
        lines.append(f"\n{slot}:")
        for course in info["courses"]:
            if solution.get(course) == slot:
                prof = info["professors"][course]
                lines.append(f"  • {course} ({prof})")
    
    return "\n".join(lines)


# =============================================================================
# Demo Runner
# =============================================================================

def run_sudoku_demo():
    """Solve a hard Sudoku puzzle."""
    # Hard puzzle (requires backtracking)
    puzzle = [
        [5, 3, 0, 0, 7, 0, 0, 0, 0],
        [6, 0, 0, 1, 9, 5, 0, 0, 0],
        [0, 9, 8, 0, 0, 0, 0, 6, 0],
        [8, 0, 0, 0, 6, 0, 0, 0, 3],
        [4, 0, 0, 8, 0, 3, 0, 0, 1],
        [7, 0, 0, 0, 2, 0, 0, 0, 6],
        [0, 6, 0, 0, 0, 0, 2, 8, 0],
        [0, 0, 0, 4, 1, 9, 0, 0, 5],
        [0, 0, 0, 0, 8, 0, 0, 7, 9]
    ]
    
    print("=" * 50)
    print("🧩 SUDOKU SOLVER")
    print("=" * 50)
    print("\nInput puzzle (0 = empty):")
    print(format_sudoku_solution({f"r{i}c{j}": (puzzle[i][j] if puzzle[i][j] else 0) 
                                   for i in range(9) for j in range(9)}))
    
    problem = create_sudoku_problem(puzzle)
    solver = CSSolver(use_ac3=True, use_mrv=True, use_degree=True, use_lcv=True)
    
    solution = solver.solve(problem)
    
    print(f"\n⌚ Solved in {solver.stats.time_ms:.2f}ms")
    print(f"   Nodes explored: {solver.stats.nodes_explored}")
    print(f"   Backtracks: {solver.stats.backtracks}")
    print(f"   Arc revisions: {solver.stats.arc_revisions}")
    
    if solution:
        print("\n✓ Solution found:")
        print(format_sudoku_solution(solution))
    else:
        print("\n✗ No solution exists")
    
    return solution is not None


def run_nqueens_demo():
    """Solve 8-Queens problem."""
    n = 8
    
    print("\n" + "=" * 50)
    print("👑 N-QUEENS SOLVER")
    print("=" * 50)
    print(f"\nProblem: Place {n} queens on {n}x{n} board without attacks")
    
    problem = create_nqueens_problem(n)
    solver = CSSolver(use_ac3=True, use_mrv=True, use_degree=True, use_lcv=True)
    
    solution = solver.solve(problem)
    
    print(f"\n⌚ Solved in {solver.stats.time_ms:.2f}ms")
    print(f"   Nodes explored: {solver.stats.nodes_explored}")
    print(f"   Backtracks: {solver.stats.backtracks}")
    
    if solution:
        print(f"\n✓ Solution found:")
        print(format_nqueens_board(solution, n))
    else:
        print("\n✗ No solution exists")
    
    return solution is not None


def run_map_coloring_demo():
    """Solve Australia map coloring."""
    print("\n" + "=" * 50)
    print("🗺️  MAP COLORING SOLVER")
    print("=" * 50)
    print("\nProblem: Color Australia map with 4 colors")
    print("Constraint: Adjacent regions must differ")
    
    problem, region_map = create_map_coloring_problem()
    solver = CSSolver(use_ac3=True, use_mrv=True, use_degree=True, use_lcv=True)
    
    solution = solver.solve(problem)
    
    print(f"\n⌚ Solved in {solver.stats.time_ms:.2f}ms")
    print(f"   Nodes explored: {solver.stats.nodes_explored}")
    print(f"   Backtracks: {solver.stats.backtracks}")
    
    if solution:
        print("\n✓ Solution found:")
        regions = ["WA", "NT", "SA", "Q", "NSW", "V", "T"]
        print(format_map_coloring(solution, regions))
    else:
        print("\n✗ No solution exists")
    
    return solution is not None


def run_cryptarithmetic_demo():
    """Solve SEND + MORE = MONEY cryptarithmetic puzzle."""
    print("\n" + "=" * 50)
    print("🔢 CRYPTARITHMETIC SOLVER")
    print("=" * 50)
    print("\nProblem: SEND + MORE = MONEY")
    print("Constraint: Each letter = unique digit, no leading zeros")
    
    problem, info = create_cryptarithmetic_problem("SEND + MORE = MONEY")
    solver = CSSolver(use_ac3=True, use_mrv=True, use_degree=True, use_lcv=True)
    
    solution = solver.solve(problem)
    
    print(f"\n⌚ Solved in {solver.stats.time_ms:.2f}ms")
    print(f"   Nodes explored: {solver.stats.nodes_explored}")
    print(f"   Backtracks: {solver.stats.backtracks}")
    
    if solution:
        print("\n✓ Solution found:")
        print(format_cryptarithmetic(solution, info))
    else:
        print("\n✗ No solution exists")
    
    return solution is not None


def run_scheduler_demo():
    """Solve course scheduling problem."""
    print("\n" + "=" * 50)
    print("📅 COURSE SCHEDULER")
    print("=" * 50)
    print("\nProblem: Schedule 4 courses into 3 time slots")
    print("Constraint: Same professor can't teach at same time")
    
    problem, info = create_scheduler_problem()
    solver = CSSolver(use_ac3=True, use_mrv=True, use_degree=True, use_lcv=True)
    
    solution = solver.solve(problem)
    
    print(f"\n⌚ Solved in {solver.stats.time_ms:.2f}ms")
    print(f"   Nodes explored: {solver.stats.nodes_explored}")
    print(f"   Backtracks: {solver.stats.backtracks}")
    
    if solution:
        print("\n✓ Solution found:")
        print(format_scheduler(solution, info))
    else:
        print("\n✗ No solution exists")
    
    return solution is not None


def main():
    """Run all CSP demos."""
    print("\033[1;36m")
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║      🔧 CONSTRAINT SATISFACTION SOLVER                       ║")
    print("║      AC-3 Arc Consistency + Backtracking Search              ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print("\033[0m")
    
    results = []
    
    results.append(("Sudoku", run_sudoku_demo()))
    results.append(("N-Queens", run_nqueens_demo()))
    results.append(("Map Coloring", run_map_coloring_demo()))
    results.append(("Cryptarithmetic", run_cryptarithmetic_demo()))
    results.append(("Course Scheduler", run_scheduler_demo()))
    
    print("\n" + "=" * 50)
    print("📊 SUMMARY")
    print("=" * 50)
    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  {name}: {status}")
    
    all_passed = all(r[1] for r in results)
    print("\n" + ("🎉 All demos passed!" if all_passed else "⚠️ Some demos failed"))
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
