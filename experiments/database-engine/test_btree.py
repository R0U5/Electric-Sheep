#!/usr/bin/env python3
"""Quick test of B+ tree functionality."""

from btree import BPlusTree
import random

def test_basic_insert_search():
    tree = BPlusTree(order=4)
    # Insert some key-value pairs
    for i in range(10):
        tree.insert(i, f'value_{i}')
    
    # Search for existing keys
    for i in range(10):
        results = tree.search(i)
        assert len(results) == 1
        assert results[0] == f'value_{i}'
    
    # Search for non-existent key
    assert tree.search(100) == []
    print("✓ Basic insert/search passed")

def test_duplicate_keys():
    tree = BPlusTree(order=4)
    # Insert duplicate keys
    tree.insert(5, 'val1')
    tree.insert(5, 'val2')
    tree.insert(5, 'val3')
    
    results = tree.search(5)
    assert len(results) == 3
    assert set(results) == {'val1', 'val2', 'val3'}
    print("✓ Duplicate keys passed")

def test_range_query():
    tree = BPlusTree(order=4)
    # Insert shuffled keys
    keys = list(range(20))
    random.shuffle(keys)
    for k in keys:
        tree.insert(k, f'v{k}')
    
    # Range query
    results = tree.range_query(5, 15)
    result_keys = [k for k, v in results]
    assert result_keys == list(range(5, 15))
    print("✓ Range query passed")

def test_large_insert():
    tree = BPlusTree(order=10)
    n = 1000
    for i in range(n):
        tree.insert(i, i*2)
    
    for i in range(n):
        results = tree.search(i)
        assert results == [i*2]
    
    # Verify range
    results = tree.range_query(250, 750)
    assert len(results) == 500
    for k, v in results:
        assert v == k * 2
    print("✓ Large insert passed")

if __name__ == '__main__':
    test_basic_insert_search()
    test_duplicate_keys()
    test_range_query()
    test_large_insert()
    print("All tests passed!")