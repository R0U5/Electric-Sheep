"""
B+ Tree implementation for a database index.

Supports:
- Insert key-value pairs
- Search by key (exact match)
- Range queries (start_key <= key < end_key)
- In-memory storage with persistence hooks

The tree is balanced and maintains a minimum fill factor.
"""

import bisect
from typing import List, Optional, Tuple, Any, Iterator


class Node:
    """Base class for B+ tree nodes."""
    __slots__ = ('keys', 'parent')
    
    def __init__(self):
        self.keys: List[Any] = []
        self.parent: Optional['InternalNode'] = None
    
    def is_leaf(self) -> bool:
        return isinstance(self, LeafNode)
    
    def is_full(self, order: int) -> bool:
        """Check if node has maximum allowed keys."""
        return len(self.keys) >= order
    
    def is_underfilled(self, order: int) -> bool:
        """Check if node has fewer than minimum keys."""
        return len(self.keys) < (order // 2)


class LeafNode(Node):
    """Leaf node containing key-value pairs."""
    __slots__ = ('values', 'next_leaf')
    
    def __init__(self):
        super().__init__()
        self.values: List[Any] = []
        self.next_leaf: Optional['LeafNode'] = None  # linked list for range queries
    
    def insert(self, key: Any, value: Any, order: int) -> Optional['LeafNode']:
        """Insert key-value into leaf. Return new sibling if split."""
        pos = bisect.bisect_left(self.keys, key)
        
        # If key exists, append value (allow duplicates for now)
        if pos < len(self.keys) and self.keys[pos] == key:
            self.values[pos].append(value)
            return None
        
        self.keys.insert(pos, key)
        self.values.insert(pos, [value])
        
        if self.is_full(order):
            return self._split(order)
        return None
    
    def _split(self, order: int) -> 'LeafNode':
        """Split leaf node, return new sibling."""
        split_idx = order // 2
        new_leaf = LeafNode()
        
        new_leaf.keys = self.keys[split_idx:]
        new_leaf.values = self.values[split_idx:]
        
        self.keys = self.keys[:split_idx]
        self.values = self.values[:split_idx]
        
        # Maintain linked list
        new_leaf.next_leaf = self.next_leaf
        self.next_leaf = new_leaf
        
        return new_leaf
    
    def search(self, key: Any) -> List[Any]:
        """Return values associated with key, empty list if not found."""
        pos = bisect.bisect_left(self.keys, key)
        if pos < len(self.keys) and self.keys[pos] == key:
            return self.values[pos]
        return []
    
    def range_query(self, start_key: Any, end_key: Any) -> Iterator[Tuple[Any, Any]]:
        """Yield (key, value) pairs from start_key inclusive to end_key exclusive."""
        node: Optional['LeafNode'] = self
        while node is not None:
            for i, key in enumerate(node.keys):
                if key < start_key:
                    continue
                if key >= end_key:
                    return
                for val in node.values[i]:
                    yield (key, val)
            node = node.next_leaf


class InternalNode(Node):
    """Internal node containing keys and child pointers."""
    __slots__ = ('children',)
    
    def __init__(self):
        super().__init__()
        self.children: List[Node] = []
    
    def insert_child(self, key: Any, child: Node, order: int) -> Optional['InternalNode']:
        """Insert key-child pair. Return new sibling if split."""
        pos = bisect.bisect_left(self.keys, key)
        self.keys.insert(pos, key)
        self.children.insert(pos + 1, child)
        child.parent = self
        
        if self.is_full(order):
            return self._split(order)
        return None
    
    def _split(self, order: int) -> 'InternalNode':
        """Split internal node, return new sibling."""
        split_idx = order // 2
        new_node = InternalNode()
        pivot_key = self.keys[split_idx]
        
        new_node.keys = self.keys[split_idx + 1:]
        new_node.children = self.children[split_idx + 1:]
        
        self.keys = self.keys[:split_idx]
        self.children = self.children[:split_idx + 1]
        
        # Update parent references
        for child in new_node.children:
            child.parent = new_node
        
        return new_node, pivot_key
    
    def find_child(self, key: Any) -> Node:
        """Return child that should contain the given key."""
        pos = bisect.bisect_right(self.keys, key)
        return self.children[pos]


class BPlusTree:
    """B+ Tree index."""
    
    def __init__(self, order: int = 4):
        self.order = order
        self.root: Node = LeafNode()
        self.size = 0
    
    def insert(self, key: Any, value: Any) -> None:
        """Insert key-value pair."""
        leaf = self._find_leaf(key)
        split_result = leaf.insert(key, value, self.order)
        
        if split_result is not None:
            self._split_leaf(leaf, split_result)
        
        self.size += 1
    
    def _find_leaf(self, key: Any) -> LeafNode:
        """Find leaf node that should contain key."""
        node = self.root
        while not node.is_leaf():
            node = node.find_child(key)
        return node
    
    def _split_leaf(self, leaf: LeafNode, new_leaf: LeafNode) -> None:
        """Handle leaf split, propagating up the tree."""
        # Get smallest key from new leaf
        pivot_key = new_leaf.keys[0]
        
        if leaf.parent is None:
            # Create new root
            new_root = InternalNode()
            new_root.keys = [pivot_key]
            new_root.children = [leaf, new_leaf]
            leaf.parent = new_root
            new_leaf.parent = new_root
            self.root = new_root
            return
        
        parent = leaf.parent
        parent_insert = parent.insert_child(pivot_key, new_leaf, self.order)
        
        if parent_insert is not None:
            new_internal, new_pivot = parent_insert
            self._split_internal(parent, new_internal, new_pivot)
    
    def _split_internal(self, node: InternalNode, new_node: InternalNode, pivot_key: Any) -> None:
        """Handle internal node split."""
        if node.parent is None:
            new_root = InternalNode()
            new_root.keys = [pivot_key]
            new_root.children = [node, new_node]
            node.parent = new_root
            new_node.parent = new_root
            self.root = new_root
            return
        
        parent = node.parent
        parent_insert = parent.insert_child(pivot_key, new_node, self.order)
        
        if parent_insert is not None:
            new_internal, new_pivot = parent_insert
            self._split_internal(parent, new_internal, new_pivot)
    
    def search(self, key: Any) -> List[Any]:
        """Return all values associated with key."""
        leaf = self._find_leaf(key)
        return leaf.search(key)
    
    def range_query(self, start_key: Any, end_key: Any) -> List[Tuple[Any, Any]]:
        """Return all key-value pairs in range [start_key, end_key)."""
        start_leaf = self._find_leaf(start_key)
        return list(start_leaf.range_query(start_key, end_key))
    
    def __len__(self) -> int:
        return self.size