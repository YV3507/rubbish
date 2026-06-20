use axum::{
    body::Body,
    http::{Method, Request, StatusCode},
    Router,
};
use tower::ServiceExt;

fn app() -> Router {
    rubbish_compute::api::routes(":memory:")
}

#[tokio::test]
async fn health_endpoint() {
    let response = app()
        .oneshot(
            Request::builder()
                .method(Method::GET)
                .uri("/health")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::OK);
}

#[tokio::test]
async fn graph_index_endpoint() {
    let response = app()
        .oneshot(
            Request::builder()
                .method(Method::POST)
                .uri("/graph/index")
                .header("Content-Type", "application/json")
                .body(Body::from(r#"{"path": "/test"}"#))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::OK);
}

#[tokio::test]
async fn graph_explore_endpoint() {
    let response = app()
        .oneshot(
            Request::builder()
                .method(Method::POST)
                .uri("/graph/explore")
                .header("Content-Type", "application/json")
                .body(Body::from(r#"{"symbol": "test_fn", "depth": 3}"#))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::OK);
}

#[tokio::test]
async fn graph_callers_endpoint() {
    let response = app()
        .oneshot(
            Request::builder()
                .method(Method::POST)
                .uri("/graph/callers")
                .header("Content-Type", "application/json")
                .body(Body::from(r#"{"node_id": "func_123", "depth": 2}"#))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::OK);
}

#[tokio::test]
async fn compress_crush_endpoint() {
    let response = app()
        .oneshot(
            Request::builder()
                .method(Method::POST)
                .uri("/compress/crush")
                .header("Content-Type", "application/json")
                .body(Body::from(
                    r#"{"content": "[1,2,3,4,5,6,7,8,9,10]", "query": "error"}"#,
                ))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::OK);
}
