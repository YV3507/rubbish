//! Search: re-exported from CodeGraph methods.
//!
//! FTS5 full-text search is now integrated into the CodeGraph struct.
//! This module provides a thin convenience wrapper for backward compatibility.

use crate::codegraph::graph::CodeGraph;

/// Search symbols using FTS5 + BM25 via the CodeGraph instance.
pub fn search_symbols(graph: &CodeGraph, query: &str, limit: usize) -> Vec<(String, String, String, f64)> {
    graph.search(query, limit).unwrap_or_default()
}

#[cfg(test)]
mod tests {
    use crate::codegraph::graph::CodeGraph;
    use super::*;

    #[test]
    fn test_search_wrapper() {
        let graph = CodeGraph::new(":memory:").unwrap();
        graph.index_file("test.py", "def search_func(): pass").unwrap();
        let results = search_symbols(&graph, "search_func", 10);
        assert!(!results.is_empty());
        assert_eq!(results[0].1, "search_func");
    }
}
