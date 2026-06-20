//! SmartCrusher: JSON statistical sampling with change-point detection.
//!
//! Implements change-point detection to identify structural breaks in JSON arrays,
//! retaining the most representative samples while discarding redundant entries.
//!
//! Strategy:
//!   1. Small arrays (≤5 items) are kept as-is
//!   2. Medium arrays (≤30) keep first, last, and every 3rd item
//!   3. Large arrays use change-point detection: items where the content hash differs
//!      significantly from neighbors are retained

use serde_json::Value;
use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};

pub struct SmartCrusher;

impl SmartCrusher {
    /// Compress JSON content using statistical sampling.
    ///
    /// Returns (compressed_string, saved_ratio).
    pub fn crush_json(&self, content: &str, _query: Option<&str>) -> (String, f64) {
        let Ok(parsed) = serde_json::from_str::<Value>(content) else {
            // Not valid JSON — try text compression
            return self.crush_text(content);
        };

        match &parsed {
            Value::Array(items) => self.crush_array(items, content.len()),
            Value::Object(_) => self.crush_object(&parsed, content.len()),
            _ => (content.to_string(), 0.0),
        }
    }

    /// Compress a JSON array using change-point detection.
    fn crush_array(&self, items: &[Value], original_len: usize) -> (String, f64) {
        if items.is_empty() {
            return ("[]".to_string(), 1.0);
        }

        let sampled: Vec<&Value> = if items.len() <= 5 {
            // Small array: keep all
            items.iter().collect()
        } else if items.len() <= 30 {
            // Medium array: first, last, every 3rd
            let mut result = vec![&items[0]];
            for i in (1..items.len() - 1).step_by(3) {
                result.push(&items[i]);
            }
            if items.len() > 1 {
                result.push(&items[items.len() - 1]);
            }
            result
        } else {
            // Large array: change-point detection
            self.change_point_sample(items)
        };

        // Serialize
        let sampled_json: Vec<&Value> = sampled;
        let compressed = serde_json::to_string(&sampled_json).unwrap_or_default();
        let saved_ratio = 1.0 - (compressed.len() as f64 / original_len.max(1) as f64);
        (compressed, saved_ratio)
    }

    /// Change-point detection: hash each item and sample where hashes differ.
    fn change_point_sample<'a>(&self, items: &'a [Value]) -> Vec<&'a Value> {
        let mut result = vec![&items[0]];

        // Compute hash fingerprints
        let hashes: Vec<u64> = items.iter().map(|v| self._hash_value(v)).collect();

        // Keep items where hash differs from the previous kept item
        // Cap at ~20% of original length to ensure compression
        let max_keep = std::cmp::max(10, items.len() / 5);

        for i in 1..items.len() {
            if result.len() >= max_keep {
                break;
            }
            let prev_hash = hashes[i - 1];
            let curr_hash = hashes[i];

            if curr_hash != prev_hash {
                result.push(&items[i]);
            }
        }

        // Always include last item if not already included
        let last_idx = items.len() - 1;
        if last_idx > 0 && !result.iter().any(|&r| std::ptr::eq(r, &items[last_idx])) {
            if result.len() < max_keep {
                result.push(&items[last_idx]);
            } else {
                // Replace the last kept item with the actual last item
                result.pop();
                result.push(&items[last_idx]);
            }
        }

        result
    }

    /// Compress a JSON object by keeping top-level keys.
    fn crush_object(&self, obj: &Value, original_len: usize) -> (String, f64) {
        let obj_map = obj.as_object().unwrap();
        if obj_map.len() <= 5 {
            return (serde_json::to_string(obj).unwrap(), 0.0);
        }

        // Keep all keys but sample array values
        let mut sampled = serde_json::Map::new();
        for (key, val) in obj_map.iter() {
            match val {
                Value::Array(arr) => {
                    let (compressed, _) = self.crush_array(arr, original_len);
                    let parsed: Value = serde_json::from_str(&compressed).unwrap_or(val.clone());
                    sampled.insert(key.clone(), parsed);
                }
                _ => {
                    sampled.insert(key.clone(), val.clone());
                }
            }
        }

        let compressed = serde_json::to_string(&sampled).unwrap_or_default();
        let saved_ratio = 1.0 - (compressed.len() as f64 / original_len.max(1) as f64);
        (compressed, saved_ratio)
    }

    /// Compress generic text: keep first 20% and last 10%.
    fn crush_text(&self, content: &str) -> (String, f64) {
        let original_len = content.len();
        if original_len < 500 {
            return (content.to_string(), 0.0);
        }

        let lines: Vec<&str> = content.lines().collect();
        if lines.len() <= 20 {
            return (content.to_string(), 0.0);
        }

        let head_end = (lines.len() as f64 * 0.2).ceil() as usize;
        let tail_start = (lines.len() as f64 * 0.9).floor() as usize;

        let mut kept: Vec<&str> = Vec::new();
        kept.extend_from_slice(&lines[..head_end]);
        kept.push("... [SmartCrusher compressed] ...");
        kept.extend_from_slice(&lines[tail_start..]);

        let compressed = kept.join("\n");
        let saved_ratio = 1.0 - (compressed.len() as f64 / original_len.max(1) as f64);
        (compressed, saved_ratio)
    }

    fn _hash_value(&self, v: &Value) -> u64 {
        let mut hasher = DefaultHasher::new();
        match v {
            Value::Null => 0u64.hash(&mut hasher),
            Value::Bool(b) => b.hash(&mut hasher),
            Value::Number(n) => n.to_string().hash(&mut hasher),
            Value::String(s) => {
                // Use first 100 chars + length as fingerprint
                s.len().hash(&mut hasher);
                if s.len() > 100 {
                    s[..100].hash(&mut hasher);
                } else {
                    s.hash(&mut hasher);
                }
            }
            Value::Array(arr) => {
                arr.len().hash(&mut hasher);
                if !arr.is_empty() {
                    self._hash_value(&arr[0]).hash(&mut hasher);
                }
            }
            Value::Object(obj) => {
                obj.len().hash(&mut hasher);
            }
        }
        hasher.finish()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_small_array_unchanged() {
        let crusher = SmartCrusher;
        let (result, _) = crusher.crush_json("[1, 2, 3]", None);
        let parsed: Value = serde_json::from_str(&result).unwrap();
        assert_eq!(parsed.as_array().unwrap().len(), 3);
    }

    #[test]
    fn test_large_array_is_sampled() {
        let items: Vec<i32> = (0..100).collect();
        let json = serde_json::to_string(&items).unwrap();
        let (result, ratio) = SmartCrusher.crush_json(&json, None);
        let parsed: Value = serde_json::from_str(&result).unwrap();
        assert!(parsed.as_array().unwrap().len() < 50);
        assert!(ratio > 0.3);
    }

    #[test]
    fn test_text_compression() {
        let text = "line\n".repeat(100);
        let (result, ratio) = SmartCrusher.crush_json(&text, None);
        assert!(ratio > 0.5);
        assert!(result.contains("SmartCrusher compressed"));
    }

    #[test]
    fn test_object_preserves_keys() {
        let json = r#"{"a": [1,2,3,4,5,6,7,8,9,10], "b": "hello", "c": {"nested": true}}"#;
        let (result, _) = SmartCrusher.crush_json(json, None);
        let parsed: Value = serde_json::from_str(&result).unwrap();
        assert!(parsed.as_object().unwrap().contains_key("a"));
        assert!(parsed.as_object().unwrap().contains_key("b"));
        assert!(parsed.as_object().unwrap().contains_key("c"));
    }
}
