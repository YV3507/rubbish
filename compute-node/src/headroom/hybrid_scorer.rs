//! HybridScorer: BM25 + Embedding hybrid scoring (adapter for Python-provided embeddings).

pub struct HybridScorer;

impl HybridScorer {
    /// Combine BM25 score with embedding similarity score.
    ///
    /// `bm25_score` comes from FTS5 search.
    /// `embedding_score` is provided by Python side via ONNX Runtime.
    pub fn hybrid_score(&self, bm25_score: f64, embedding_score: f64, alpha: f64) -> f64 {
        alpha * bm25_score + (1.0 - alpha) * embedding_score
    }
}
