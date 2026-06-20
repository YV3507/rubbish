//! Routers: framework routing extraction (Gin, Spring, Express, etc.).
//!
//! Uses regex patterns to extract HTTP route definitions from source code
//! of popular web frameworks.

use regex::Regex;

pub struct RouterExtractor;

impl RouterExtractor {
    /// Extract route definitions from a source file.
    ///
    /// Returns a list of (method, path) tuples, e.g. ("GET", "/api/users").
    pub fn extract_routes(&self, content: &str, framework: &str) -> Vec<(String, String)> {
        match framework {
            "gin" => self.extract_gin(content),
            "express" | "fastify" => self.extract_express(content),
            "spring" => self.extract_spring(content),
            "axum" | "actix" => self.extract_axum(content),
            "fastapi" | "flask" => self.extract_python(content),
            _ => vec![],
        }
    }

    /// Gin: router.GET("/path", handler)
    fn extract_gin(&self, content: &str) -> Vec<(String, String)> {
        let re = Regex::new(r#"(?m)\.(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s*\(\s*"([^"]+)""#).unwrap();
        re.captures_iter(content)
            .map(|c| (c[1].to_string(), c[2].to_string()))
            .collect()
    }

    /// Express: router.get("/path", handler) or app.get("/path")
    fn extract_express(&self, content: &str) -> Vec<(String, String)> {
        let re = Regex::new(r#"(?m)\.(get|post|put|delete|patch|head|options)\s*\(\s*['"]([^'"]+)['"]"#).unwrap();
        re.captures_iter(content)
            .map(|c| (c[1].to_uppercase(), c[2].to_string()))
            .collect()
    }

    /// Spring: @GetMapping("/path") or @RequestMapping("/path", method=GET)
    fn extract_spring(&self, content: &str) -> Vec<(String, String)> {
        let mut routes = Vec::new();
        let re = Regex::new(r#"(?m)@(Get|Post|Put|Delete|Patch)Mapping\s*\(\s*"([^"]+)""#).unwrap();
        for c in re.captures_iter(content) {
            routes.push((c[1].to_uppercase(), c[2].to_string()));
        }
        // Also handle @RequestMapping
        let rm_re = Regex::new(r#"(?m)@RequestMapping\s*\(\s*(?:value\s*=\s*)?"([^"]+)""#).unwrap();
        for c in rm_re.captures_iter(content) {
            routes.push(("GET".to_string(), c[1].to_string()));
        }
        routes
    }

    /// Axum: .route("/path", get(handler))
    fn extract_axum(&self, content: &str) -> Vec<(String, String)> {
        let re = Regex::new(r#"(?m)\.route\s*\(\s*"([^"]+)""#).unwrap();
        re.captures_iter(content)
            .map(|c| ("GET".to_string(), c[1].to_string()))
            .collect()
    }

    /// FastAPI/Flask: @app.get("/path") or @app.route("/path")
    fn extract_python(&self, content: &str) -> Vec<(String, String)> {
        let mut routes = Vec::new();
        let re = Regex::new(r#"(?m)\.(get|post|put|delete|patch)\(["]([^"]+)["]"#).unwrap();
        for c in re.captures_iter(content) {
            routes.push((c[1].to_uppercase(), c[2].to_string()));
        }
        // Also handle @app.route("/path")
        let route_re = Regex::new(r#"(?m)@.*\.route\(["]([^"]+)["]"#).unwrap();
        for c in route_re.captures_iter(content) {
            routes.push(("GET".to_string(), c[1].to_string()));
        }
        routes
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_gin_routes() {
        let code = r#"
            router.GET("/api/users", handler)
            router.POST("/api/users", createHandler)
        "#;
        let extractor = RouterExtractor;
        let routes = extractor.extract_routes(code, "gin");
        assert!(routes.contains(&("GET".to_string(), "/api/users".to_string())));
        assert!(routes.contains(&("POST".to_string(), "/api/users".to_string())));
    }

    #[test]
    fn test_express_routes() {
        let code = r#"
            app.get("/api/users", getUsers);
            router.post("/api/users", createUser);
        "#;
        let extractor = RouterExtractor;
        let routes = extractor.extract_routes(code, "express");
        assert!(routes.contains(&("GET".to_string(), "/api/users".to_string())));
        assert!(routes.contains(&("POST".to_string(), "/api/users".to_string())));
    }

    #[test]
    fn test_fastapi_routes() {
        let code = r#"
            @app.get("/health")
            @router.post("/api/data")
        "#;
        let extractor = RouterExtractor;
        let routes = extractor.extract_routes(code, "fastapi");
        assert!(routes.contains(&("GET".to_string(), "/health".to_string())));
        assert!(routes.contains(&("POST".to_string(), "/api/data".to_string())));
    }
}
