//! Rubbish Compute Node: Rust Axum microservice for CodeGraph and compression.
//!
//! Configuration via environment variables:
//!   - `COMPUTE_DB_PATH` - SQLite database path (default: `./data/codegraph.db`)
//!   - `COMPUTE_PORT`    - HTTP listen port (default: `8080`)

use std::path::Path;

use axum::Router;
use tokio::net::TcpListener;
use tower_http::cors::CorsLayer;

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt::init();

    // Resolve database path: env var or default
    let db_path = std::env::var("COMPUTE_DB_PATH")
        .unwrap_or_else(|_| "./data/codegraph.db".to_string());

    // Ensure parent directory exists for file-based databases
    if db_path != ":memory:" {
        if let Some(parent) = Path::new(&db_path).parent() {
            std::fs::create_dir_all(parent).ok();
        }
    }

    let db_path_leak: &'static str = Box::leak(db_path.into_boxed_str());

    let app = Router::new()
        .merge(rubbish_compute::api::routes(db_path_leak))
        .layer(CorsLayer::permissive());

    let port = std::env::var("COMPUTE_PORT")
        .unwrap_or_else(|_| "8080".to_string());
    let addr = format!("0.0.0.0:{}", port);

    let listener = TcpListener::bind(&addr).await.unwrap();
    tracing::info!("Compute node listening on {}, db_path={}", addr, db_path_leak);
    axum::serve(listener, app).await.unwrap();
}
