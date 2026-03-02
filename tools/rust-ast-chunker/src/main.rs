use clap::Parser;
use serde::Serialize;
use std::fs;
use std::path::PathBuf;
use tree_sitter::{Language, Node, Parser as TSParser};

/// CLI Tool to semantically chunk source code using Abstract Syntax Trees (AST).
#[derive(Parser, Debug)]
#[command(version, about, long_about = None)]
struct Args {
    /// Path to the source file
    #[arg(short, long)]
    file: PathBuf,

    /// Force language override (python, javascript, typescript, rust)
    #[arg(short, long)]
    lang: Option<String>,
}

#[derive(Serialize)]
struct Chunk {
    language: String,
    node_type: String,
    name: Option<String>,
    snippet: String,
    start_line: usize,
    end_line: usize,
}

fn main() {
    let args = Args::parse();

    let ext = args
        .file
        .extension()
        .and_then(|e| e.to_str())
        .unwrap_or_else(|| "");

    let lang_str = args.lang.unwrap_or_else(|| ext.to_string());

    let (language, dialect_name) = match lang_str.as_str() {
        "py" | "python" => (tree_sitter_python::language(), "python"),
        "js" | "javascript" => (tree_sitter_javascript::language(), "javascript"),
        "ts" | "typescript" => (tree_sitter_typescript::language_typescript(), "typescript"),
        "tsx" => (tree_sitter_typescript::language_tsx(), "typescript"),
        "rs" | "rust" => (tree_sitter_rust::language(), "rust"),
        _ => {
            eprintln!("Unsupported language extension: '{}'", lang_str);
            std::process::exit(1);
        }
    };

    let source_code = match fs::read_to_string(&args.file) {
        Ok(c) => c,
        Err(e) => {
            eprintln!("Failed to read file: {}", e);
            std::process::exit(1);
        }
    };

    let mut parser = TSParser::new();
    let safe_lang: Language = language.into();
    if let Err(e) = parser.set_language(&safe_lang) {
        eprintln!("Error loading language: {:?}", e);
        std::process::exit(1);
    }

    let tree = match parser.parse(&source_code, None) {
        Some(t) => t,
        None => {
            eprintln!("Failed to parse source file");
            std::process::exit(1);
        }
    };

    let root_node = tree.root_node();
    let mut chunks = Vec::new();

    extract_chunks(
        root_node,
        &source_code,
        dialect_name,
        &mut chunks,
        is_chunkable_node,
    );

    // Filter out tiny chunks
    chunks.retain(|c: &Chunk| c.snippet.trim().len() > 10);

    let stdout = std::io::stdout();
    if let Err(e) = serde_json::to_writer_pretty(stdout, &chunks) {
        eprintln!("Error writing JSON: {}", e);
        std::process::exit(1);
    }
}

/// Recursively traverses the AST and pushes semantically relevant nodes into `chunks`.
fn extract_chunks<F>(
    node: Node,
    source_code: &str,
    language: &str,
    chunks: &mut Vec<Chunk>,
    is_target: F,
) where
    F: Fn(&Node) -> bool + Copy,
{
    if is_target(&node) {
        let snippet = node_context(node, source_code);
        let name_node = get_name_node(node);
        let name = name_node.map(|n| n.utf8_text(source_code.as_bytes()).unwrap_or("").to_string());

        chunks.push(Chunk {
            language: language.to_string(),
            node_type: node.kind().to_string(),
            name,
            snippet,
            start_line: node.start_position().row + 1,
            end_line: node.end_position().row + 1,
        });

        // We don't recurse into target nodes, treating them as atomic units
        // down to the method/function level to avoid over-fragmentation.
        return;
    }

    let mut cursor = node.walk();
    for child in node.children(&mut cursor) {
        extract_chunks(child, source_code, language, chunks, is_target);
    }
}

/// Helper to determine if a node represents a semantic block worth chunking.
fn is_chunkable_node(node: &Node) -> bool {
    let kind = node.kind();
    matches!(
        kind,
        "function_definition" // Python
        | "class_definition"  // Python
        | "function_item"     // Rust
        | "impl_item"         // Rust
        | "struct_item"       // Rust
        | "enum_item"         // Rust
        | "function_declaration" // JS/TS
        | "class_declaration"    // JS/TS
        | "method_definition"    // JS/TS
    )
}

/// Extracts a name identifier for common structure nodes.
fn get_name_node<'a>(node: Node<'a>) -> Option<Node<'a>> {
    node.child_by_field_name("name")
}

/// Extracts the actual text for a node from the complete source.
fn node_context(node: Node, source: &str) -> String {
    let start = node.start_byte();
    let end = node.end_byte();
    source[start..end].to_string()
}
