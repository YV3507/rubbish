//! Impact: RWR (Random Walk with Restart) PageRank for impact radius analysis.
//!
//! Computes influence scores by walking the call graph from a starting node.

use std::collections::HashMap;

pub struct ImpactAnalyzer;

impl ImpactAnalyzer {
    /// Compute impact scores via RWR PageRank.
    ///
    /// `alpha` is the restart probability (typical: 0.25).
    /// `edges` is a list of (source, target) call edges.
    /// `iterations` limits the walk depth.
    pub fn compute_rwr(
        &self,
        node_id: &str,
        alpha: f64,
        edges: &[(String, String)],
        iterations: usize,
    ) -> HashMap<String, f64> {
        // Build adjacency list
        let mut adj: HashMap<&str, Vec<&str>> = HashMap::new();
        for (src, tgt) in edges {
            adj.entry(src.as_str()).or_default().push(tgt.as_str());
        }

        // Initialize scores
        let mut scores: HashMap<&str, f64> = HashMap::new();
        scores.insert(node_id, 1.0);

        let alpha = alpha.clamp(0.1, 0.9);
        let mut current = node_id;

        for _ in 0..iterations {
            let neighbors = adj.get(current);
            match neighbors {
                Some(nodes) if !nodes.is_empty() => {
                    let spread = alpha / nodes.len() as f64;
                    for n in nodes {
                        *scores.entry(n).or_insert(0.0) += spread;
                    }
                    // Walk to first neighbor
                    current = nodes[0];
                }
                _ => {
                    // Restart: random jump to original node
                    current = node_id;
                    continue;
                }
            }

            // Restart probability
            if rand::random_f64() < (1.0 - alpha) {
                current = node_id;
            }
        }

        scores.into_iter().map(|(k, v)| (k.to_string(), v)).collect()
    }
}

/// Simple RNG helper using std (no external dependency).
mod rand {
    use std::time::{SystemTime, UNIX_EPOCH};

    pub fn random_f64() -> f64 {
        let nanos = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .subsec_nanos();
        (nanos as f64) / 1_000_000_000.0
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_rwr_basic() {
        let analyzer = ImpactAnalyzer;
        let edges = vec![
            ("main".to_string(), "helper".to_string()),
            ("helper".to_string(), "util".to_string()),
            ("main".to_string(), "util".to_string()),
        ];
        let scores = analyzer.compute_rwr("main", 0.25, &edges, 10);
        assert!(scores.contains_key("helper"));
        assert!(scores.contains_key("util"));
    }
}
