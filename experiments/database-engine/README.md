# Minimal Relational Database Engine

A from-scratch implementation of a relational database engine with:
- B-tree indexing for efficient range queries
- SQL-like query parser (SELECT, INSERT, CREATE TABLE)
- Persistent storage using binary files
- Basic query execution engine
- Memory-mapped I/O for performance

## Architecture

1. **Storage Engine**: Manages pages, free space, and persistence
2. **B-tree Index**: Balanced tree structure for fast lookups
3. **Parser**: Converts SQL-like queries into execution plans
4. **Executor**: Executes query plans using the storage engine
5. **Catalog**: Stores table metadata (schema, indexes)

## Features

- CREATE TABLE with column definitions
- INSERT rows with automatic indexing
- SELECT with WHERE clauses (equality and range)
- B-tree range scans
- Persistent storage across sessions