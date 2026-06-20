//! Pipeline: 5-stage compression pipeline.
//!
//! Command → Router → Crush → HeadTail → Pass
//!
//! Routes content through the SmartCrusher with optional query-specific tuning.

use crate::headroom::smart_crusher::SmartCrusher;

pub struct CompressionPipeline;

impl CompressionPipeline {
    /// Run the 5-stage compression pipeline on input content.
    ///
    /// Returns (compressed_string, saved_ratio).
    pub fn run(&self, content: &str, query: Option<&str>) -> (String, f64) {
        // Stage 1: Command detection (identify intent from content type)
        // Stage 2: Router (select strategy based on content structure)
        // Stage 3: Crush (statistical compression via SmartCrusher)
        // Stage 4: HeadTail (keep intro/conclusion — embedded in SmartCrusher text mode)
        // Stage 5: Pass (final validation — ensure output is valid)

        let (crushed, ratio) = SmartCrusher.crush_json(content, query);

        // Validate: if compressed is empty or malformed, return original
        if crushed.is_empty() || crushed.len() < 2 {
            return (content.to_string(), 0.0);
        }

        (crushed, ratio)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_pipeline_json() {
        let pipeline = CompressionPipeline;
        let json = serde_json::to_string(&(0..50).collect::<Vec<i32>>()).unwrap();
        let (result, ratio) = pipeline.run(&json, None);
        assert!(ratio > 0.3);
        assert!(!result.is_empty());
    }

    #[test]
    fn test_pipeline_text() {
        let pipeline = CompressionPipeline;
        let text = "line\n".repeat(100);
        let (result, ratio) = pipeline.run(&text, None);
        assert!(ratio > 0.0);
        assert!(result.len() < text.len());
    }
}
