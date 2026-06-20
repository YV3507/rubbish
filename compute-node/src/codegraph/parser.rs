//! Parser: regex-based multi-language code parser.
//!
//! Extracts symbols (functions, classes, methods), call edges, and definition edges.
//! Does NOT store full AST — only the relational structure.
//!
//! Supports: Python, JavaScript/TypeScript, Rust, Go, Java/Kotlin/Scala, C/C++, Ruby
//! (Add new languages by extending LANGUAGE_PATTERNS)

use regex::Regex;

/// A symbol extracted from source code.
#[derive(Debug, Clone)]
pub struct Symbol {
    pub id: String,
    pub name: String,
    pub kind: String,        // "function", "class", "method", "interface", etc.
    pub file_path: String,
    pub line: usize,
}

/// A directed edge between two symbols.
#[derive(Debug, Clone)]
pub struct Edge {
    pub source_id: String,
    pub target_id: String,
    pub edge_type: String,   // "calls", "defines", "extends", "implements"
}

/// Language-specific extraction patterns.
struct LangPatterns {
    /// Regexes that match symbol definitions. Captures: name, kind
    symbol_defs: Vec<(Regex, &'static str)>,
    /// Regex that matches function/method calls. Captures: name
    call_pattern: Regex,
    /// File extensions for this language.
    extensions: &'static [&'static str],
}

fn build_lang_patterns() -> Vec<(&'static str, LangPatterns)> {
    // Python
    let py_call = Regex::new(r"([a-zA-Z_]\w*)\s*\(").unwrap();
    let py_sym1 = Regex::new(r"^\s*(?:async\s+)?def\s+([a-zA-Z_]\w*)\s*\(").unwrap();
    let py_sym2 = Regex::new(r"^\s*class\s+([a-zA-Z_]\w*)").unwrap();

    // JavaScript / TypeScript
    let js_call = Regex::new(r"([a-zA-Z_$]\w*)\s*\(").unwrap();
    let js_sym1 = Regex::new(r"^\s*(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z_$]\w*)\s*\(").unwrap();
    let js_sym2 = Regex::new(r"^\s*(?:export\s+)?class\s+([a-zA-Z_$]\w*)").unwrap();
    let js_sym3 = Regex::new(r"^\s*(?:export\s+)?(?:const|let|var)\s+([a-zA-Z_$]\w*)\s*=\s*(?:async\s+)?(?:function|\(|=>)").unwrap();
    let js_sym4 = Regex::new(r"^\s*(?:export\s+)?interface\s+([a-zA-Z_$]\w*)").unwrap();

    // Rust
    let rs_call = Regex::new(r"([a-zA-Z_]\w*)\s*\(").unwrap();
    let rs_sym1 = Regex::new(r"^\s*(?:pub\s+)?(?:unsafe\s+)?fn\s+([a-zA-Z_]\w*)").unwrap();
    let rs_sym2 = Regex::new(r"^\s*(?:pub\s+)?(?:trait|struct|enum|impl|mod|type)\s+([a-zA-Z_]\w*)").unwrap();

    // Go
    let go_call = Regex::new(r"([a-zA-Z_]\w*)\s*\(").unwrap();
    let go_sym1 = Regex::new(r"^\s*func\s+(?:\([^)]*\)\s+)?([a-zA-Z_]\w*)").unwrap();
    let go_sym2 = Regex::new(r"^\s*type\s+([a-zA-Z_]\w*)\s+(struct|interface)").unwrap();

    // Java / Kotlin
    let java_call = Regex::new(r"([a-zA-Z_]\w*)\s*\(").unwrap();
    let java_sym1 = Regex::new(r"^\s*(?:public|private|protected|static|\s)*\s*(?:class|interface|abstract\s+class)\s+([a-zA-Z_]\w*)").unwrap();
    let java_sym2 = Regex::new(r"^\s*(?:public|private|protected|static|\s)*\s+\w+\s+([a-zA-Z_]\w*)\s*\(").unwrap();
    let java_sym3 = Regex::new(r"^\s*(?:fun|override\s+fun)\s+([a-zA-Z_]\w*)\s*\(").unwrap(); // Kotlin

    // C/C++
    let c_call = Regex::new(r"([a-zA-Z_]\w*)\s*\(").unwrap();
    let c_sym1 = Regex::new(r"^\s*(?:static\s+|virtual\s+|inline\s+|extern\s+)?(?:int|void|char|float|double|long|short|unsigned|signed|size_t|bool|uint8_t|uint16_t|uint32_t|uint64_t|int8_t|int16_t|int32_t|int64_t|char\s*\*|const\s+\w+|std::\w+)\s+\*?\s*([a-zA-Z_]\w*)\s*\(").unwrap();
    let c_sym2 = Regex::new(r"^\s*(?:class|struct)\s+([a-zA-Z_]\w*)").unwrap();

    // Ruby
    let rb_call = Regex::new(r"(?:\.|::)?\s*([a-zA-Z_]\w*)\s*\(").unwrap();
    let rb_sym1 = Regex::new(r"^\s*(?:def\s+(?:self\.)?([a-zA-Z_]\w*))").unwrap();
    let rb_sym2 = Regex::new(r"^\s*class\s+([a-zA-Z_]\w*)").unwrap();
    let rb_sym3 = Regex::new(r"^\s*module\s+([a-zA-Z_]\w*)").unwrap();

    vec![
        ("python", LangPatterns {
            symbol_defs: vec![(py_sym1, "function"), (py_sym2, "class")],
            call_pattern: py_call,
            extensions: &["py"],
        }),
        ("javascript", LangPatterns {
            symbol_defs: vec![(js_sym1, "function"), (js_sym2, "class"), (js_sym3, "function"), (js_sym4, "interface")],
            call_pattern: js_call,
            extensions: &["js", "jsx", "ts", "tsx", "mjs", "cjs"],
        }),
        ("rust", LangPatterns {
            symbol_defs: vec![(rs_sym1, "function"), (rs_sym2, "type")],
            call_pattern: rs_call,
            extensions: &["rs"],
        }),
        ("go", LangPatterns {
            symbol_defs: vec![(go_sym1, "function"), (go_sym2, "type")],
            call_pattern: go_call,
            extensions: &["go"],
        }),
        ("java", LangPatterns {
            symbol_defs: vec![(java_sym1, "class"), (java_sym2, "method"), (java_sym3, "function")],
            call_pattern: java_call,
            extensions: &["java", "kt", "scala"],
        }),
        ("c_cpp", LangPatterns {
            symbol_defs: vec![(c_sym1, "function"), (c_sym2, "type")],
            call_pattern: c_call,
            extensions: &["c", "cpp", "cc", "cxx", "h", "hpp", "hh"],
        }),
        ("ruby", LangPatterns {
            symbol_defs: vec![(rb_sym1, "function"), (rb_sym2, "class"), (rb_sym3, "module")],
            call_pattern: rb_call,
            extensions: &["rb"],
        }),
    ]
}

/// Detect language from file extension.
fn detect_language(path: &str) -> Option<LangPatterns> {
    let ext = path.rsplit('.').next()?;
    build_lang_patterns().into_iter().find(|(_, lp)| {
        lp.extensions.contains(&ext)
    }).map(|(_, lp)| lp)
}

/// Extract symbol definitions from a line.
fn extract_defs(line: &str, line_num: usize, file_path: &str, patterns: &LangPatterns) -> Vec<Symbol> {
    let mut symbols = Vec::new();
    for (re, kind) in &patterns.symbol_defs {
        if let Some(caps) = re.captures(line) {
            let name = caps.get(1).unwrap().as_str().to_string();
            let id = format!("{}:{}:{}", file_path, name, line_num);
            symbols.push(Symbol {
                id,
                name,
                kind: kind.to_string(),
                file_path: file_path.to_string(),
                line: line_num,
            });
        }
    }
    symbols
}

/// Extract function/method calls from a line within the current symbol context.
fn extract_calls(line: &str, _line_num: usize, current_sym: Option<&Symbol>, patterns: &LangPatterns) -> Vec<Edge> {
    let mut edges = Vec::new();
    let Some(sym) = current_sym else { return edges };

    for cap in patterns.call_pattern.captures_iter(line) {
        let callee = cap.get(1).unwrap().as_str();
        // Skip keywords and common noise
        if matches!(callee, "if" | "for" | "while" | "switch" | "catch" | "return"
            | "elif" | "else" | "try" | "except" | "with" | "not" | "and" | "or"
            | "in" | "is" | "assert" | "raise" | "yield" | "await" | "async"
            | "this" | "super" | "new" | "delete" | "typeof" | "instanceof"
            | "println" | "print" | "len" | "range" | "map" | "filter" | "zip"
            | "self" | "Some" | "None" | "Ok" | "Err" | "Box" | "Arc" | "Rc"
            | "vec" | "vec!" | "format!" | "panic!" | "assert_eq!" | "assert!")
        {
            continue;
        }
        let target_id = format!("{}:{}", sym.file_path, callee);
        edges.push(Edge {
            source_id: sym.id.clone(),
            target_id,
            edge_type: "calls".to_string(),
        });
    }
    edges
}

/// Parse a source file and return extracted symbols and call edges.
pub fn parse_file(file_path: &str, content: &str) -> (Vec<Symbol>, Vec<Edge>) {
    let Some(patterns) = detect_language(file_path) else {
        return (vec![], vec![]);
    };

    let mut symbols = Vec::new();
    let mut edges = Vec::new();
    let mut current_sym: Option<Symbol> = None;

    // Track brace depth to know when we leave a function body
    let mut brace_depth: isize = 0;
    let mut in_body = false;

    for (line_num, line) in content.lines().enumerate() {
        let line_num = line_num + 1;

        // Extract new symbol definitions
        let new_syms = extract_defs(line, line_num, file_path, &patterns);
        for sym in &new_syms {
            symbols.push(sym.clone());
        }

        // Track brace depth for body detection
        if in_body {
            brace_depth += line.matches('{').count() as isize;
            brace_depth -= line.matches('}').count() as isize;
            if brace_depth <= 0 {
                in_body = false;
                current_sym = None;
            }
        }

        // Start tracking new function body
        if !new_syms.is_empty() {
            current_sym = Some(new_syms[0].clone());
            // Python uses indentation, not braces
            if !file_path.ends_with(".py") {
                brace_depth = line.matches('{').count() as isize;
                in_body = brace_depth > 0;
            }
        }

        // For Python, use colon + indent as body marker
        if file_path.ends_with(".py") && !new_syms.is_empty() {
            in_body = true;
        }

        // Extract calls
        edges.extend(extract_calls(line, line_num, current_sym.as_ref(), &patterns));
    }

    (symbols, edges)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_python_function() {
        let code = r#"
def hello(name):
    print(f"Hello {name}")

class Greeter:
    def greet(self):
        self.hello("world")
"#;
        let (syms, _edges) = parse_file("test.py", code);
        assert!(syms.iter().any(|s| s.name == "hello" && s.kind == "function"));
        assert!(syms.iter().any(|s| s.name == "Greeter" && s.kind == "class"));
        assert!(syms.iter().any(|s| s.name == "greet" && s.kind == "function"));
    }

    #[test]
    fn test_parse_js_function() {
        let code = r#"
function add(a, b) {
    return a + b;
}

class Calculator {
    multiply(x, y) {
        return x * y;
    }
}
"#;
        let (syms, _) = parse_file("test.js", code);
        assert!(syms.iter().any(|s| s.name == "add"));
        assert!(syms.iter().any(|s| s.name == "Calculator"));
    }

    #[test]
    fn test_parse_rust_fn() {
        let code = r#"
pub fn compute(input: &str) -> i32 {
    let result = process(input);
    result.len() as i32
}
"#;
        let (syms, edges) = parse_file("test.rs", code);
        assert!(syms.iter().any(|s| s.name == "compute"));
        // Should detect call to "process"
        assert!(edges.iter().any(|e| e.target_id.contains("process")));
    }

    #[test]
    fn test_unknown_extension() {
        let (syms, edges) = parse_file("file.unknown", "some content");
        assert!(syms.is_empty());
        assert!(edges.is_empty());
    }

    #[test]
    fn test_parse_c_function() {
        let code = r#"
int add(int a, int b) {
    return a + b;
}

void greet(const char* name) {
    printf("Hello %s", name);
}
"#;
        let (syms, _) = parse_file("test.c", code);
        assert!(syms.iter().any(|s| s.name == "add"));
        assert!(syms.iter().any(|s| s.name == "greet"));
    }

    #[test]
    fn test_parse_cpp_class() {
        let code = r#"
class Calculator {
    int multiply(int x, int y) {
        return x * y;
    }
};
"#;
        let (syms, _) = parse_file("test.cpp", code);
        assert!(syms.iter().any(|s| s.name == "Calculator"));
    }

    #[test]
    fn test_parse_ruby_def() {
        let code = r#"
def hello(name)
  puts "Hello #{name}"
end

class Greeter
  def greet
    say_hi("world")
  end
end
"#;
        let (syms, edges) = parse_file("test.rb", code);
        assert!(syms.iter().any(|s| s.name == "hello" && s.kind == "function"));
        assert!(syms.iter().any(|s| s.name == "Greeter" && s.kind == "class"));
        assert!(syms.iter().any(|s| s.name == "greet" && s.kind == "function"));
        assert!(edges.iter().any(|e| e.target_id.contains("say_hi")));
    }

    #[test]
    fn test_parse_kotlin_fun() {
        let code = r#"
fun calculate(a: Int, b: Int): Int {
    return a + b
}

override fun toString(): String {
    return "test"
}
"#;
        let (syms, _) = parse_file("test.kt", code);
        assert!(syms.iter().any(|s| s.name == "calculate"));
    }
}
