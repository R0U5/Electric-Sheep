#!/usr/bin/env python3
"""Test the database engine with various queries."""

from database import Database

def test_create_and_insert():
    db = Database()
    
    # Create table
    db.execute("CREATE TABLE users (id INTEGER, name TEXT, age INTEGER)")
    
    # Insert rows
    db.execute("INSERT INTO users VALUES (1, 'Alice', 30)")
    db.execute("INSERT INTO users VALUES (2, 'Bob', 25)")
    db.execute("INSERT INTO users VALUES (3, 'Charlie', 35)")
    
    # Select all
    rows = db.execute("SELECT * FROM users")
    assert len(rows) == 3
    assert rows[0] == (1, 'Alice', 30)
    assert rows[1] == (2, 'Bob', 25)
    assert rows[2] == (3, 'Charlie', 35)
    print("✓ CREATE and INSERT passed")

def test_select_where():
    db = Database()
    db.execute("CREATE TABLE products (id INTEGER, name TEXT, price INTEGER)")
    db.execute("INSERT INTO products VALUES (100, 'Widget', 50)")
    db.execute("INSERT INTO products VALUES (101, 'Gadget', 100)")
    db.execute("INSERT INTO products VALUES (102, 'Thingy', 75)")
    
    # Equality
    rows = db.execute("SELECT * FROM products WHERE id = 101")
    assert len(rows) == 1
    assert rows[0] == (101, 'Gadget', 100)
    
    # Greater than
    rows = db.execute("SELECT * FROM products WHERE price > 60")
    assert len(rows) == 2
    assert set(rows) == {(101, 'Gadget', 100), (102, 'Thingy', 75)}
    
    # Less than or equal
    rows = db.execute("SELECT * FROM products WHERE price <= 75")
    assert len(rows) == 2
    assert set(rows) == {(100, 'Widget', 50), (102, 'Thingy', 75)}
    print("✓ SELECT WHERE passed")

def test_column_projection():
    db = Database()
    db.execute("CREATE TABLE employees (id INTEGER, first_name TEXT, last_name TEXT, salary INTEGER)")
    db.execute("INSERT INTO employees VALUES (1, 'John', 'Doe', 60000)")
    db.execute("INSERT INTO employees VALUES (2, 'Jane', 'Smith', 75000)")
    
    # Select specific columns
    rows = db.execute("SELECT first_name, salary FROM employees")
    assert rows == [('John', 60000), ('Jane', 75000)]
    
    rows = db.execute("SELECT last_name FROM employees WHERE id = 2")
    assert rows == [('Smith',)]
    print("✓ Column projection passed")

def test_duplicate_primary_key():
    db = Database()
    db.execute("CREATE TABLE items (code INTEGER, description TEXT)")
    db.execute("INSERT INTO items VALUES (1, 'First')")
    db.execute("INSERT INTO items VALUES (1, 'Duplicate')")  # Should be allowed for now
    
    rows = db.execute("SELECT * FROM items WHERE code = 1")
    assert len(rows) == 2
    assert set(rows) == {(1, 'First'), (1, 'Duplicate')}
    print("✓ Duplicate primary key handled")

def test_range_query_with_index():
    db = Database()
    db.execute("CREATE TABLE scores (student_id INTEGER, score INTEGER)")
    for i in range(20):
        db.execute(f"INSERT INTO scores VALUES ({i}, {i * 5})")
    
    # Range query on primary key (student_id) - use direct API
    table = db.tables['scores']
    rows = table.select_range(5, 10)
    assert len(rows) == 5
    for i, row in enumerate(rows, start=5):
        assert row == (i, i * 5)
    print("✓ Range query with index passed")

def test_error_handling():
    db = Database()
    
    # Create duplicate table
    db.execute("CREATE TABLE t1 (a INTEGER)")
    try:
        db.execute("CREATE TABLE t1 (b INTEGER)")
        assert False, "Should have raised error"
    except ValueError:
        pass
    
    # Insert with wrong column count
    try:
        db.execute("INSERT INTO t1 VALUES (1, 2)")
        assert False, "Should have raised error"
    except ValueError:
        pass
    
    # Select from non-existent table
    try:
        db.execute("SELECT * FROM nonexistent")
        assert False, "Should have raised error"
    except ValueError:
        pass
    
    print("✓ Error handling passed")

def test_performance():
    """Insert many rows and query."""
    import time
    db = Database()
    db.execute("CREATE TABLE big (id INTEGER, data TEXT)")
    
    n = 10000
    start = time.time()
    for i in range(n):
        db.execute(f"INSERT INTO big VALUES ({i}, 'data_{i}')")
    insert_time = time.time() - start
    
    # Query by primary key
    start = time.time()
    for i in range(0, n, 1000):
        rows = db.execute(f"SELECT * FROM big WHERE id = {i}")
        assert len(rows) == 1
    query_time = time.time() - start
    
    print(f"  Insert {n} rows: {insert_time:.2f}s ({insert_time/n*1000:.2f}ms per row)")
    print(f"  Query by PK: {query_time:.2f}s")
    print("✓ Performance test completed")

if __name__ == '__main__':
    test_create_and_insert()
    test_select_where()
    test_column_projection()
    test_duplicate_primary_key()
    test_range_query_with_index()
    test_error_handling()
    test_performance()
    print("\nAll database tests passed!")