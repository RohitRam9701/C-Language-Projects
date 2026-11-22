#!/usr/bin/env python3

import json
import subprocess
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "catalog"
LIMIT = 1000

RULES = [
    ("Operating Systems and Kernels", ("kernel", "operating-system", "os", "unix", "linux", "bsd", "bootloader", "firmware")),
    ("Compilers and Language Tools", ("compiler", "interpreter", "parser", "lexer", "ast", "clang", "gcc", "llvm", "linter")),
    ("Databases and Storage", ("database", "sqlite", "storage", "postgres", "redis", "key-value", "keyvalue")),
    ("Networking and Protocols", ("network", "networking", "tcp", "udp", "http", "server", "proxy", "vpn", "dns", "protocol")),
    ("Embedded and IoT", ("embedded", "iot", "arduino", "microcontroller", "stm32", "esp32", "raspberry")),
    ("Graphics and Games", ("game", "gaming", "graphics", "opengl", "vulkan", "sdl", "raylib", "game-engine")),
    ("Security and Cryptography", ("security", "cryptography", "crypto", "password", "hash", "encryption", "vulnerability")),
    ("Algorithms and Data Structures", ("algorithm", "data-structure", "datastructure", "sorting", "leetcode", "competitive-programming")),
    ("Audio and Multimedia", ("audio", "video", "music", "codec", "ffmpeg", "image", "camera", "multimedia")),
    ("Web and Applications", ("web", "html", "css", "javascript", "browser", "webserver", "api")),
    ("Data Science and Machine Learning", ("machine-learning", "data-science", "neural-network", "deep-learning", "numpy", "scientific")),
    ("Learning and Examples", ("learn", "learning", "tutorial", "course", "example", "exercise", "beginner", "101")),
    ("System Utilities", ("cli", "command-line", "terminal", "shell", "utility", "tools", "tool", "system")),
    ("Libraries and Frameworks", ("library", "libraries", "framework", "sdk")),
]


def search_repositories():
    repositories = []
    seen = set()
    per_page = 100
    for page in range(1, (LIMIT // per_page) + 1):
        result = subprocess.run(
            [
                "gh", "api",
                "-H", "Accept: application/vnd.github+json",
                f"/search/repositories?q=language:C+is:public&sort=stars&order=desc&per_page={per_page}&page={page}",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
        for repo in payload.get("items", []):
            full_name = repo["full_name"]
            if full_name in seen:
                continue
            seen.add(full_name)
            repositories.append({
                "full_name": full_name,
                "name": repo["name"],
                "description": repo.get("description") or "",
                "url": repo["html_url"],
                "stars": repo["stargazers_count"],
                "topics": repo.get("topics", []),
                "license": (repo.get("license") or {}).get("spdx_id"),
                "updated_at": repo["updated_at"],
                "archived": repo["archived"],
            })
    return repositories


def category_for(repo):
    haystack = " ".join([
        repo["name"].lower(),
        repo["description"].lower(),
        " ".join(repo["topics"]).lower(),
    ])
    matches = []
    for category, needles in RULES:
        if any(needle in haystack for needle in needles):
            matches.append(category)
    if matches:
        return matches
    return ["Libraries and Frameworks"]


def duplicate_tags(repo, repositories):
    name = repo["name"].lower().replace("_", "-").replace(".", "-")
    tokens = [t for t in name.replace("-", " ").split() if len(t) > 2]
    tags = set(repo["topics"])
    if len(tokens) >= 2:
        stem = "-".join(tokens[:2])
        for other in repositories:
            if other["full_name"] == repo["full_name"]:
                continue
            other_name = other["name"].lower().replace("_", "-").replace(".", "-")
            if stem in other_name:
                tags.add("related-project")
                break
    return sorted(tags)


def main():
    repositories = search_repositories()
    grouped = defaultdict(list)
    for repo in repositories:
        repo["categories"] = category_for(repo)
        repo["topics"] = duplicate_tags(repo, repositories)
        for category in repo["categories"]:
            grouped[category].append(repo)

    CATALOG.mkdir(parents=True, exist_ok=True)
    with (CATALOG / "repositories.json").open("w", encoding="utf-8") as handle:
        json.dump({
            "source": "GitHub repository search",
            "query": "language:C is:public",
            "sort": "stars",
            "order": "desc",
            "limit": LIMIT,
            "count": len(repositories),
            "repositories": repositories,
        }, handle, indent=2)

    lines = [
        "# C Project Catalog",
        "",
        f"This catalog contains {len(repositories)} of the most-starred public GitHub repositories primarily indexed with C.",
        "GitHub's repository search API exposes at most 1,000 results per query, so this is a scalable discovery index rather than a complete fork of every C repository.",
        "",
    ]
    category_names = [name for name, _ in RULES] + ["Libraries and Frameworks"]
    for category in category_names:
        entries = grouped.get(category, [])
        if not entries:
            continue
        lines.extend([f"## {category}", "", "| Repository | Stars | Description | Tags |", "|---|---:|---|---|"])
        for repo in sorted(entries, key=lambda item: (-item["stars"], item["full_name"].lower())):
            description = repo["description"].replace("|", "\\|").replace("\n", " ")
            tags = ", ".join(repo["topics"]) or "-"
            stars = f"{repo['stars']:,}"
            lines.append(f"| [{repo['full_name']}]({repo['url']}) | {stars} | {description} | {tags} |")
        lines.append("")
    (CATALOG / "README.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
