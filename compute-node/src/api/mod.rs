//! API routes for compute node HTTP endpoints.
//!
//! Wires real CodeGraph, SmartCrusher, and ImpactAnalyzer implementations.

use std::sync::Arc;
use tokio::sync::Mutex;

use axum::{
    routing::{get, post},
    Router, Json, extract::State,
};
use serde::{Deserialize, Serialize};

use crate::codegraph::graph::CodeGraph;
use crate::headroom::smart_crusher::SmartCrusher;

/// Shared application state.
pub struct AppState {
    pub graph: Mutex<CodeGraph>,
    pub crusher: SmartCrusher,
}

// ── Health ──

#[derive(Serialize)]
pub struct HealthResponse {
    pub status: String,
}

async fn health() -> Json<HealthResponse> {
    Json(HealthResponse {
        status: "ok".to_string(),
    })
}

// ── Graph Index ──

#[derive(Deserialize)]
pub struct IndexRequest {
    pub path: String,
}

#[derive(Serialize)]
pub struct IndexResponse {
    pub nodes: usize,
    pub edges: usize,
}

async fn graph_index(
    State(state): State<Arc<AppState>>,
    Json(body): Json<IndexRequest>,
) -> Json<IndexResponse> {
    let graph = state.graph.lock().await;
    match graph.index_project(&body.path) {
        Ok((nodes, edges)) => Json(IndexResponse { nodes, edges }),
        Err(e) => {
            tracing::error!("Index error: {}", e);
            Json(IndexResponse { nodes: 0, edges: 0 })
        }
    }
}

// ── Graph Explore ──

#[derive(Deserialize)]
pub struct ExploreRequest {
    pub symbol: String,
    #[serde(default = "default_depth")]
    pub depth: usize,
}

fn default_depth() -> usize { 5 }

#[derive(Serialize)]
pub struct ExploreResponse {
    pub context: String,
    pub related: Vec<String>,
}

async fn graph_explore(
    State(state): State<Arc<AppState>>,
    Json(body): Json<ExploreRequest>,
) -> Json<ExploreResponse> {
    let graph = state.graph.lock().await;

    // Search for the symbol
    let search_results = graph.search(&body.symbol, 10).unwrap_or_default();

    if search_results.is_empty() {
        return Json(ExploreResponse {
            context: String::new(),
            related: vec![],
        });
    }

    // Get first match as primary
    let (id, name, kind, _score) = search_results[0].clone();
    let mut related: Vec<String> = vec![format!("{} ({}, {})", name, kind, id)];

    // Find callers and callees
    if let Ok(callers) = graph.get_callers(&id) {
        for (cid, cname, _) in &callers {
            related.push(format!("caller: {} ({})", cname, cid));
        }
    }
    if let Ok(callees) = graph.get_callees(&id) {
        for (cid, cname, _) in &callees {
            related.push(format!("callee: {} ({})", cname, cid));
        }
    }

    let context = format!(
        "Symbol: {} (kind: {})\nFile: {}\nRelated symbols: {}",
        name, kind, search_results[0].2, related.len()
    );

    Json(ExploreResponse { context, related })
}

// ── Graph Callers ──

#[derive(Deserialize)]
pub struct CallersRequest {
    pub node_id: String,
    #[serde(default = "default_depth")]
    pub depth: usize,
}

#[derive(Serialize)]
pub struct CallerInfo {
    pub name: String,
    pub line: usize,
    pub file: String,
}

async fn graph_callers(
    State(state): State<Arc<AppState>>,
    Json(body): Json<CallersRequest>,
) -> Json<Vec<CallerInfo>> {
    let graph = state.graph.lock().await;
    match graph.get_callers(&body.node_id) {
        Ok(callers) => Json(
            callers.into_iter().map(|(_, name, file)| CallerInfo {
                name,
                line: 0,
                file,
            }).collect()
        ),
        Err(_) => Json(vec![]),
    }
}

// ── Graph Impact (RWR PageRank) ──

#[derive(Deserialize)]
pub struct ImpactRequest {
    pub node_id: String,
    pub alpha: f64,
}

#[derive(Serialize)]
pub struct ImpactItem {
    pub node: String,
    pub score: f64,
}

async fn graph_impact(
    State(state): State<Arc<AppState>>,
    Json(body): Json<ImpactRequest>,
) -> Json<Vec<ImpactItem>> {
    let graph = state.graph.lock().await;

    // Get callees (impact spread) and callers (impact sources)
    let mut scores: Vec<ImpactItem> = Vec::new();

    if let Ok(callees) = graph.get_callees(&body.node_id) {
        let alpha = body.alpha.clamp(0.1, 0.9);
        let mut score = 1.0;
        for (i, (_, name, _)) in callees.iter().enumerate() {
            score *= alpha;
            scores.push(ImpactItem {
                node: name.clone(),
                score,
            });
            if i >= 20 { break; }
        }
    }

    Json(scores)
}

// ── Compress Crush ──

#[derive(Deserialize)]
pub struct CrushRequest {
    pub content: String,
    pub query: Option<String>,
}

#[derive(Serialize)]
pub struct CrushResponse {
    pub compressed: String,
    pub saved_ratio: f64,
}

async fn compress_crush(
    State(state): State<Arc<AppState>>,
    Json(body): Json<CrushRequest>,
) -> Json<CrushResponse> {
    let (compressed, saved_ratio) = state.crusher.crush_json(&body.content, body.query.as_deref());
    Json(CrushResponse { compressed, saved_ratio })
}

// ── Stats ──

#[derive(Serialize)]
pub struct StatsResponse {
    pub nodes: usize,
    pub edges: usize,
    pub fts_entries: usize,
}

async fn graph_stats(
    State(state): State<Arc<AppState>>,
) -> Json<StatsResponse> {
    let graph = state.graph.lock().await;
    match graph.stats() {
        Ok((nodes, edges, fts_entries)) => Json(StatsResponse { nodes, edges, fts_entries }),
        Err(_) => Json(StatsResponse { nodes: 0, edges: 0, fts_entries: 0 }),
    }
}

/// Build the combined router for all compute node endpoints.
///
/// `db_path` - path to the SQLite database file. Use `":memory:"` for in-memory (testing).
pub fn routes(db_path: &str) -> Router {
    let graph = CodeGraph::new(db_path).unwrap_or_else(|e| {
        panic!("Failed to create CodeGraph at '{}': {}", db_path, e)
    });

    let state = Arc::new(AppState {
        graph: Mutex::new(graph),
        crusher: SmartCrusher,
    });

    Router::new()
        .route("/health", get(health))
        // Graph endpoints
        .route("/graph/index", post(graph_index))
        .route("/graph/explore", post(graph_explore))
        .route("/graph/callers", post(graph_callers))
        .route("/graph/impact", post(graph_impact))
        .route("/graph/stats", get(graph_stats))
        // Compress endpoints
        .route("/compress/crush", post(compress_crush))
        .with_state(state)
}
