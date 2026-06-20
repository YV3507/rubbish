//! CodeGraph: SQLite-backed symbol graph with project indexing.
//!
//! Indexes source files by extracting symbols and call edges via the parser,
//! then stores them in SQLite for efficient querying (callers, callees, FTS5 search).

use rusqlite::{Connection, Result, params};
use std::path::{Path, PathBuf};
use std::fs;

use crate::codegraph::parser;

/// A symbol tuple: (id, name, kind, file_path, line).
pub type SymbolInfo = (String, String, String, String, i32);

pub struct CodeGraph {
    conn: Connection,
}

impl CodeGraph {
    /// Open (or create) the graph database at the given path.
    pub fn new(db_path: &str) -> Result<Self> {
        let conn = Connection::open(db_path)?;
        conn.execute_batch(
            "PRAGMA journal_mode=WAL;
             PRAGMA synchronous=NORMAL;

             CREATE TABLE IF NOT EXISTS nodes (
                 id TEXT PRIMARY KEY,
                 name TEXT NOT NULL,
                 kind TEXT NOT NULL,
                 file_path TEXT,
                 line INTEGER
             );
             CREATE TABLE IF NOT EXISTS edges (
                 source_id TEXT NOT NULL,
                 target_id TEXT NOT NULL,
                 edge_type TEXT NOT NULL,
                 PRIMARY KEY (source_id, target_id, edge_type)
             );
             CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);
             CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id);
             CREATE INDEX IF NOT EXISTS idx_nodes_name ON nodes(name);
             CREATE INDEX IF NOT EXISTS idx_nodes_file ON nodes(file_path);

             CREATE VIRTUAL TABLE IF NOT EXISTS fts_symbols USING fts5(
                 id, name, content, tokenize='porter unicode61'
             );",
        )?;
        Ok(Self { conn })
    }

    /// Index a source file — parse and store symbols + edges.
    pub fn index_file(&self, file_path: &str, content: &str) -> Result<(usize, usize)> {
        let (symbols, edges) = parser::parse_file(file_path, content);

        for sym in &symbols {
            self.conn.execute(
                "INSERT OR IGNORE INTO nodes (id, name, kind, file_path, line) VALUES (?1, ?2, ?3, ?4, ?5)",
                params![sym.id, sym.name, sym.kind, sym.file_path, sym.line as i64],
            )?;
            // Add to FTS5 index
            self.conn.execute(
                "INSERT OR IGNORE INTO fts_symbols (id, name, content) VALUES (?1, ?2, ?3)",
                params![sym.id, sym.name, format!("{} {} {}", sym.name, sym.kind, sym.file_path)],
            )?;
        }

        for edge in &edges {
            self.conn.execute(
                "INSERT OR IGNORE INTO edges (source_id, target_id, edge_type) VALUES (?1, ?2, ?3)",
                params![edge.source_id, edge.target_id, edge.edge_type],
            )?;
        }

        Ok((symbols.len(), edges.len()))
    }

    /// Index an entire project directory recursively.
    pub fn index_project(&self, project_path: &str) -> Result<(usize, usize)> {
        let path = Path::new(project_path);
        if !path.is_dir() {
            // Single file
            if path.is_file() {
                let content = fs::read_to_string(path).unwrap_or_default();
                return self.index_file(project_path, &content);
            }
            return Ok((0, 0));
        }

        let mut total_nodes = 0;
        let mut total_edges = 0;

        let _walker = fs::read_dir(path).map_err(|_e| {
            rusqlite::Error::InvalidPath(PathBuf::from(project_path))
        })?;

        self.index_dir_recursive(path, &mut total_nodes, &mut total_edges)?;

        Ok((total_nodes, total_edges))
    }

    fn index_dir_recursive(&self, dir: &Path, total_nodes: &mut usize, total_edges: &mut usize) -> Result<()> {
        let entries = fs::read_dir(dir).map_err(|_| {
            rusqlite::Error::InvalidPath(dir.to_path_buf())
        })?;

        for entry in entries.flatten() {
            let entry_path = entry.path();
            if entry_path.is_dir() {
                // Skip hidden directories and common ignore dirs
                let name = entry_path.file_name().unwrap_or_default().to_string_lossy();
                if name.starts_with('.') || name == "node_modules" || name == "target"
                    || name == "__pycache__" || name == ".git" || name == "venv"
                    || name == ".venv"
                {
                    continue;
                }
                self.index_dir_recursive(&entry_path, total_nodes, total_edges)?;
            } else if entry_path.is_file() {
                let ext = entry_path.extension().and_then(|e| e.to_str()).unwrap_or("");
                // Only index supported source files
                let supported = ["py", "js", "jsx", "ts", "tsx", "rs", "go", "java", "kt", "scala", "rb", "c", "cpp", "h", "hpp"];
                if !supported.contains(&ext) {
                    continue;
                }
                let content = fs::read_to_string(&entry_path).unwrap_or_default();
                if content.is_empty() {
                    continue;
                }
                let path_str = entry_path.to_string_lossy().to_string();
                match self.index_file(&path_str, &content) {
                    Ok((n, e)) => {
                        *total_nodes += n;
                        *total_edges += e;
                    }
                    Err(err) => {
                        eprintln!("Warning: failed to index {}: {}", path_str, err);
                    }
                }
            }
        }
        Ok(())
    }

    /// Search symbols by name (FTS5 + BM25).
    pub fn search(&self, query: &str, limit: usize) -> Result<Vec<(String, String, String, f64)>> {
        let mut stmt = self.conn.prepare(
            "SELECT n.id, n.name, n.kind, bm25(fts_symbols, 0.0, 0.0, 1.0) as score
             FROM fts_symbols
             JOIN nodes n ON n.id = fts_symbols.id
             WHERE fts_symbols MATCH ?1
             ORDER BY score
             LIMIT ?2",
        )?;
        let rows = stmt.query_map(params![query, limit as i64], |row| {
            Ok((
                row.get::<_, String>(0)?,
                row.get::<_, String>(1)?,
                row.get::<_, String>(2)?,
                row.get::<_, f64>(3)?,
            ))
        })?;
        let mut result = vec![];
        for row in rows {
            result.push(row?);
        }
        Ok(result)
    }

    /// Get callers of a given node (who calls this node?).
    /// Edges store target_id as "file_path:name" (without line number),
    /// while node IDs are "file_path:name:line". Uses LIKE prefix match.
    pub fn get_callers(&self, node_id: &str) -> Result<Vec<(String, String, String)>> {
        let mut stmt = self.conn.prepare(
            "SELECT n.id, n.name, n.file_path FROM nodes n
             JOIN edges e ON e.source_id = n.id
             WHERE ?1 LIKE (e.target_id || ':%') AND e.edge_type = 'calls'
             ORDER BY n.name",
        )?;
        let rows = stmt.query_map(params![node_id], |row| {
            Ok((
                row.get::<_, String>(0)?,
                row.get::<_, String>(1)?,
                row.get::<_, String>(2)?,
            ))
        })?;
        let mut result = vec![];
        for row in rows {
            result.push(row?);
        }
        Ok(result)
    }

    /// Get callees (who does this node call?).
    /// Edges store target_id as "file_path:name" (without line number),
    /// while node IDs are "file_path:name:line". Uses LIKE prefix match.
    pub fn get_callees(&self, node_id: &str) -> Result<Vec<(String, String, String)>> {
        let mut stmt = self.conn.prepare(
            "SELECT n.id, n.name, n.file_path FROM nodes n
             JOIN edges e ON n.id LIKE (e.target_id || ':%') AND e.source_id = ?1 AND e.edge_type = 'calls'
             ORDER BY n.name",
        )?;
        let rows = stmt.query_map(params![node_id], |row| {
            Ok((
                row.get::<_, String>(0)?,
                row.get::<_, String>(1)?,
                row.get::<_, String>(2)?,
            ))
        })?;
        let mut result = vec![];
        for row in rows {
            result.push(row?);
        }
        Ok(result)
    }

    /// Get symbol by name (fuzzy, returns first match).
    pub fn get_symbol_by_name(&self, name: &str) -> Result<Option<SymbolInfo>> {
        let mut stmt = self.conn.prepare(
            "SELECT id, name, kind, file_path, line FROM nodes WHERE name = ?1 LIMIT 1",
        )?;
        let mut rows = stmt.query_map(params![name], |row| {
            Ok((
                row.get::<_, String>(0)?,
                row.get::<_, String>(1)?,
                row.get::<_, String>(2)?,
                row.get::<_, String>(3)?,
                row.get::<_, i32>(4)?,
            ))
        })?;
        match rows.next() {
            Some(row) => Ok(Some(row?)),
            None => Ok(None),
        }
    }

    /// Get statistics about the indexed graph.
    pub fn stats(&self) -> Result<(usize, usize, usize)> {
        let nodes: i64 = self.conn.query_row("SELECT COUNT(*) FROM nodes", [], |row| row.get(0))?;
        let edges: i64 = self.conn.query_row("SELECT COUNT(*) FROM edges", [], |row| row.get(0))?;
        let fts: i64 = self.conn.query_row("SELECT COUNT(*) FROM fts_symbols", [], |row| row.get(0))?;
        Ok((nodes as usize, edges as usize, fts as usize))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_index_and_search() {
        let graph = CodeGraph::new(":memory:").unwrap();
        graph.index_file("test.py", "def hello(): pass").unwrap();
        let results = graph.search("hello", 10).unwrap();
        assert!(!results.is_empty());
        assert_eq!(results[0].1, "hello");
    }

    #[test]
    fn test_index_project_dir() {
        // Use a UUID-style temp dir to avoid collisions
        let dir = std::env::temp_dir().join(format!("codegraph_test_{}", std::process::id()));
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(&dir).unwrap();
        fs::write(dir.join("main.py"), "def greet(): return say_hi()").unwrap();
        fs::write(dir.join("ignored.txt"), "not code").unwrap();

        let graph = CodeGraph::new(":memory:").unwrap();
        let (nodes, edges) = graph.index_project(dir.to_str().unwrap()).unwrap();
        assert!(nodes >= 1, "Expected >=1 node, got {nodes}");
        assert!(edges >= 1, "Expected >=1 call edge, got {edges}");

        let _ = fs::remove_dir_all(&dir);
    }
}
