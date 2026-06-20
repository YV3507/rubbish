//! CodeGraph: AST-based code analysis with tree-sitter.
//!
//! This module manages code indexing, symbol graph construction,
//! FTS5 search, and impact analysis via RWR PageRank.

pub mod graph;
pub mod impact;
pub mod parser;
pub mod routers;
pub mod search;
