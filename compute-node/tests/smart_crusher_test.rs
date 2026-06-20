use rubbish_compute::headroom::smart_crusher::SmartCrusher;
use rubbish_compute::headroom::pipeline::CompressionPipeline;
use rubbish_compute::headroom::hybrid_scorer::HybridScorer;

#[test]
fn smart_crusher_empty_array() {
    let crusher = SmartCrusher;
    let (content, ratio) = crusher.crush_json("[]", None);
    assert_eq!(content, "[]");
    assert!(ratio >= 0.0);
}

#[test]
fn smart_crusher_small_array() {
    let crusher = SmartCrusher;
    let input = r#"[{"a":1},{"a":2},{"a":3}]"#;
    let (compressed, ratio) = crusher.crush_json(input, None);
    assert!(ratio >= 0.0);
    assert!(!compressed.is_empty());
}

#[test]
fn smart_crusher_large_array() {
    let crusher = SmartCrusher;
    let items: Vec<String> = (0..100).map(|i| format!(r#"{{"id":{}}}"#, i)).collect();
    let input = format!("[{}]", items.join(","));
    let (compressed, ratio) = crusher.crush_json(&input, None);
    assert!(ratio > 0.5);
    assert!(!compressed.is_empty());
}

#[test]
fn smart_crusher_short_text_unchanged() {
    // Short text (< 500 chars) should be unchanged
    let crusher = SmartCrusher;
    let (content, ratio) = crusher.crush_json("not json", None);
    assert_eq!(content, "not json");
    assert_eq!(ratio, 0.0);
}

#[test]
fn compression_pipeline_runs() {
    let pipeline = CompressionPipeline;
    let input = r#"[{"x":1},{"x":2},{"x":3},{"x":4},{"x":5},{"x":6}]"#;
    let (output, ratio) = pipeline.run(input, Some("test query"));
    assert!(!output.is_empty());
    assert!(ratio >= 0.0);
}

#[test]
fn hybrid_scorer_combines_scores() {
    let scorer = HybridScorer;
    let score = scorer.hybrid_score(0.5, 0.8, 0.25);
    assert!((score - 0.725).abs() < 1e-6);
}

#[test]
fn hybrid_scorer_pure_bm25() {
    let scorer = HybridScorer;
    let score = scorer.hybrid_score(1.0, 0.0, 1.0);
    assert!((score - 1.0).abs() < 1e-6);
}
