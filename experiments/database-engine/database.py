"""
Minimal relational database engine.

Supports:
- CREATE TABLE with column definitions
- INSERT rows with automatic primary key indexing
- SELECT with WHERE clauses (equality, range)
- B-tree indexing on primary key (first column)
- In-memory storage (no persistence yet)
"""

from typing import List, Tuple, Dict, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum
import re

from btree import BPlusTree


class DataType(Enum):
    INTEGER = 'INTEGER'
    TEXT = 'TEXT'


@dataclass
class Column:
    name: str
    dtype: DataType


@dataclass
class TableSchema:
    columns: List[Column]
    # For simplicity, first column is primary key
    primary_key: int = 0
    
    def column_index(self, name: str) -> int:
        """Return index of column with given name."""
        for i, col in enumerate(self.columns):
            if col.name.lower() == name.lower():
                return i
        raise ValueError(f"Column '{name}' not found")
    
    def validate_row(self, row: Tuple) -> None:
        """Validate row data types."""
        if len(row) != len(self.columns):
            raise ValueError(f"Expected {len(self.columns)} columns, got {len(row)}")
        
        for i, (val, col) in enumerate(zip(row, self.columns)):
            if col.dtype == DataType.INTEGER:
                if not isinstance(val, int):
                    raise ValueError(f"Column {col.name} expects INTEGER, got {type(val)}")
            elif col.dtype == DataType.TEXT:
                if not isinstance(val, str):
                    raise ValueError(f"Column {col.name} expects TEXT, got {type(val)}")


class Table:
    """A table with schema, rows, and primary key index."""
    
    def __init__(self, name: str, schema: TableSchema):
        self.name = name
        self.schema = schema
        self.rows: List[Tuple] = []
        # B+ tree index mapping primary key -> row indices (list for duplicates)
        self.index = BPlusTree(order=8)
        # Map from row index to primary key (for deletion tracking)
        self.row_to_key: Dict[int, Any] = {}
    
    def insert(self, row: Tuple) -> None:
        """Insert a row into the table."""
        self.schema.validate_row(row)
        pk = row[self.schema.primary_key]
        
        row_idx = len(self.rows)
        self.rows.append(row)
        self.index.insert(pk, row_idx)
        self.row_to_key[row_idx] = pk
    
    def select_all(self) -> List[Tuple]:
        """Return all rows in insertion order."""
        return self.rows.copy()
    
    def select_where(self, column: Union[str, int], op: str, value: Any) -> List[Tuple]:
        """Return rows where column op value."""
        if isinstance(column, str):
            col_idx = self.schema.column_index(column)
        else:
            col_idx = column
        
        if col_idx == self.schema.primary_key and op == '=':
            # Use index for primary key equality
            row_indices = self.index.search(value)
            return [self.rows[i] for i in row_indices]
        
        # Otherwise scan
        results = []
        for row in self.rows:
            col_val = row[col_idx]
            match op:
                case '=':
                    if col_val == value:
                        results.append(row)
                case '!=':
                    if col_val != value:
                        results.append(row)
                case '<':
                    if col_val < value:
                        results.append(row)
                case '>':
                    if col_val > value:
                        results.append(row)
                case '<=':
                    if col_val <= value:
                        results.append(row)
                case '>=':
                    if col_val >= value:
                        results.append(row)
                case _:
                    raise ValueError(f"Unsupported operator: {op}")
        
        return results
    
    def select_range(self, start_key: Any, end_key: Any) -> List[Tuple]:
        """Return rows where primary key in range [start_key, end_key)."""
        if self.schema.primary_key != 0:
            # For simplicity, only support range on first column
            raise NotImplementedError("Range queries only supported on first column")
        
        index_results = self.index.range_query(start_key, end_key)
        return [self.rows[row_idx] for _, row_idx in index_results]
    
    def __len__(self) -> int:
        return len(self.rows)


class Database:
    """Main database instance with catalog of tables."""
    
    def __init__(self):
        self.tables: Dict[str, Table] = {}
    
    def create_table(self, name: str, columns: List[Tuple[str, str]]) -> None:
        """Create a new table."""
        if name in self.tables:
            raise ValueError(f"Table '{name}' already exists")
        
        col_objs = []
        for col_name, type_str in columns:
            type_str = type_str.upper()
            if type_str == 'INTEGER':
                dtype = DataType.INTEGER
            elif type_str == 'TEXT':
                dtype = DataType.TEXT
            else:
                raise ValueError(f"Unsupported data type: {type_str}")
            col_objs.append(Column(col_name, dtype))
        
        schema = TableSchema(col_objs)
        table = Table(name, schema)
        self.tables[name] = table
    
    def insert(self, table_name: str, values: List[Any]) -> None:
        """Insert a row into table."""
        table = self._get_table(table_name)
        table.insert(tuple(values))
    
    def select(self, table_name: str, columns: List[str] = None,
               where: Optional[Tuple[str, str, Any]] = None) -> List[Tuple]:
        """Select rows from table."""
        table = self._get_table(table_name)
        
        if where is None:
            rows = table.select_all()
        else:
            col, op, val = where
            rows = table.select_where(col, op, val)
        
        # Project columns
        if columns is None:
            return rows
        
        col_indices = [table.schema.column_index(col) for col in columns]
        return [tuple(row[i] for i in col_indices) for row in rows]
    
    def _get_table(self, name: str) -> Table:
        if name not in self.tables:
            raise ValueError(f"Table '{name}' does not exist")
        return self.tables[name]
    
    def execute(self, sql: str) -> List[Tuple]:
        """Execute a SQL-like statement."""
        # Very basic parser - just for demo
        sql = sql.strip().rstrip(';')
        tokens = re.split(r'\s+', sql, flags=re.IGNORECASE)
        
        if not tokens:
            raise ValueError("Empty SQL")
        
        cmd = tokens[0].upper()
        
        if cmd == 'CREATE':
            # CREATE TABLE table_name (col1 TYPE, col2 TYPE)
            if tokens[1].upper() != 'TABLE':
                raise ValueError("Expected CREATE TABLE")
            table_name = tokens[2]
            
            # Extract column definitions
            cols_str = ' '.join(tokens[3:])
            # Remove parentheses
            cols_str = cols_str.strip('()')
            col_defs = []
            for col_str in cols_str.split(','):
                col_str = col_str.strip()
                if not col_str:
                    continue
                parts = col_str.split()
                if len(parts) < 2:
                    raise ValueError(f"Invalid column definition: {col_str}")
                col_name = parts[0]
                col_type = parts[1]
                col_defs.append((col_name, col_type))
            
            self.create_table(table_name, col_defs)
            return []
        
        elif cmd == 'INSERT':
            # INSERT INTO table_name VALUES (val1, val2, ...)
            if tokens[1].upper() != 'INTO':
                raise ValueError("Expected INSERT INTO")
            table_name = tokens[2]
            
            # Find VALUES clause
            values_idx = -1
            for i, tok in enumerate(tokens):
                if tok.upper() == 'VALUES':
                    values_idx = i
                    break
            
            if values_idx == -1:
                raise ValueError("Expected VALUES clause")
            
            values_str = ' '.join(tokens[values_idx + 1:])
            values_str = values_str.strip('()')
            values = []
            for val_str in values_str.split(','):
                val_str = val_str.strip()
                # Try to parse as int
                try:
                    val = int(val_str)
                except ValueError:
                    # Remove quotes
                    if val_str.startswith("'") and val_str.endswith("'"):
                        val = val_str[1:-1]
                    elif val_str.startswith('"') and val_str.endswith('"'):
                        val = val_str[1:-1]
                    else:
                        val = val_str
                values.append(val)
            
            self.insert(table_name, values)
            return []
        
        elif cmd == 'SELECT':
            # SELECT col1, col2 FROM table WHERE col = value
            # Simple parsing - just for demo
            from_idx = -1
            where_idx = -1
            for i, tok in enumerate(tokens):
                if tok.upper() == 'FROM':
                    from_idx = i
                elif tok.upper() == 'WHERE':
                    where_idx = i
            
            if from_idx == -1:
                raise ValueError("Expected FROM clause")
            
            # Parse columns
            col_str = ' '.join(tokens[1:from_idx])
            if col_str == '*':
                columns = None
            else:
                columns = [c.strip() for c in col_str.split(',')]
            
            table_name = tokens[from_idx + 1]
            
            # Parse WHERE if present
            where = None
            if where_idx != -1:
                where_tokens = tokens[where_idx + 1:]
                if len(where_tokens) != 3:
                    raise ValueError("WHERE clause should be 'column operator value'")
                col, op, val_str = where_tokens
                # Parse value
                try:
                    val = int(val_str)
                except ValueError:
                    if val_str.startswith("'") and val_str.endswith("'"):
                        val = val_str[1:-1]
                    elif val_str.startswith('"') and val_str.endswith('"'):
                        val = val_str[1:-1]
                    else:
                        val = val_str
                where = (col, op, val)
            
            return self.select(table_name, columns, where)
        
        else:
            raise ValueError(f"Unsupported command: {cmd}")


# Simple CLI for testing
def main():
    db = Database()
    
    print("Minimal SQL Database Engine")
    print("Supported commands: CREATE TABLE, INSERT, SELECT")
    print("Type 'exit' to quit.")
    
    while True:
        try:
            line = input("sql> ").strip()
            if not line:
                continue
            if line.lower() == 'exit':
                break
            
            result = db.execute(line)
            if result:
                for row in result:
                    print(row)
        except Exception as e:
            print(f"Error: {e}")


if __name__ == '__main__':
    main()