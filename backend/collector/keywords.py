"""Technology keyword whitelist management."""

TECH_KEYWORDS: list[str] = [
    # AI / LLM
    "AI", "大模型", "GPT", "Claude", "LLM", "LangChain", "Agent", "RAG",
    "机器学习", "深度学习", "自然语言处理",
    # Programming Languages
    "Python", "Go", "Rust", "TypeScript", "JavaScript", "Java", "C++", "Zig", "C语言",
    # Frontend
    "React", "Vue", "Svelte", "Next.js", "Nuxt", "前端",
    # Backend / Infra
    "Kubernetes", "Docker", "Terraform", "CI/CD", "后端", "架构",
    "微服务", "DevOps",
    # Database
    "数据库", "Redis", "PostgreSQL", "MySQL", "MongoDB",
    # General Tech
    "开源", "性能优化", "系统设计", "程序员", "编程", "面试",
    "GEO", "WebAssembly", "WASM",
]


def get_all_keywords() -> list[str]:
    """Get the flat list of all tech keywords to search."""
    return TECH_KEYWORDS


def is_tech_related(text: str) -> bool:
    """Quick check if a text is tech-related based on keyword matching."""
    text_lower = text.lower()
    for kw in TECH_KEYWORDS:
        if kw.lower() in text_lower:
            return True
    return False


def filter_tech_posts(posts: list) -> list:
    """Filter out non-tech posts from a list."""
    return [p for p in posts if is_tech_related(
        p.title if hasattr(p, 'title') else p.get('title', '')
    )]
