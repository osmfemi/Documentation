#!/usr/bin/env python3

import argparse
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DESTINATION = PROJECT_ROOT / "content/docs/pattern-language/libraries"


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Pattern Language library documentation")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--generated-root", type=Path, help="Convert an existing generated docs tree")
    source.add_argument("--imhex", type=Path, help="Path to an ImHex AppImage")
    parser.add_argument("--patterns", type=Path, help="Path to an ImHex-Patterns checkout")
    parser.add_argument("--destination", type=Path, default=DEFAULT_DESTINATION)
    return parser.parse_args()


def generate_markdown(imhex: Path, patterns: Path, destination: Path) -> None:
    includes = patterns.resolve() / "includes"
    sources = sorted(
        path
        for path in includes.rglob("*")
        if path.is_file()
        and path.suffix in {".pat", ".hexpat"}
        and "impl" not in path.relative_to(includes).parts
    )
    if not sources:
        raise RuntimeError(f"No Pattern Language libraries found under {includes}")

    for source in sources:
        relative_path = source.relative_to(includes)
        output = destination / Path(f"{relative_path}.md")
        output.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                str(imhex.resolve()),
                "--pl",
                "docs",
                "--includes",
                str(includes),
                "--define",
                "__IMHEX__",
                "--noimpls",
                "--pattern",
                str(source),
                "--output",
                str(output),
            ],
            check=True,
        )


def extract_frontmatter(markdown: str) -> str:
    if not markdown.startswith("---\n"):
        return markdown

    end = markdown.find("\n---\n", 4)
    return markdown if end == -1 else markdown[end + 5 :]


def escape_mdx_text(markdown: str) -> str:
    parts = re.split(r"(```[\s\S]*?```)", markdown)
    for index in range(0, len(parts), 2):
        inline_parts = re.split(r"(`[^`\n]+`|\$\$[\s\S]*?\$\$|\$[^$\n]+\$)", parts[index])
        for inline_index in range(0, len(inline_parts), 2):
            inline_parts[inline_index] = (
                inline_parts[inline_index]
                .replace("{", "&#123;")
                .replace("}", "&#125;")
            )
        parts[index] = "".join(inline_parts)
    return "".join(parts)


def normalize_relative_path(source: Path, root: Path) -> Path:
    relative = source.relative_to(root)
    parts = list(relative.parts)
    parts[-1] = parts[-1].removesuffix(".md")
    return Path(*parts)


def convert_markdown(markdown: str, route: Path) -> str:
    body = extract_frontmatter(markdown)
    title_match = re.search(r"^#\s+(.+)$", body, flags=re.MULTILINE)
    title = title_match.group(1).strip() if title_match else re.sub(r"\.(?:hex)?pat$", "", route.name)
    body = re.sub(r"^\s*#\s+.+\n+", "", body, count=1)
    body = escape_mdx_text(body).strip()

    frontmatter = "\n".join(
        (
            "---",
            f"title: {json.dumps(title)}",
            f"description: {json.dumps(f'Documentation for {title}.')}",
            "published: true",
            "toc:",
            "  visible: true",
            "---",
            "",
        )
    )
    return f"{frontmatter}{body}\n"


def replace_generated_pages(source_root: Path, destination: Path) -> int:
    source_files = sorted(
        path
        for path in source_root.rglob("*")
        if path.is_file() and path.name.endswith((".pat.md", ".hexpat.md"))
    )
    if not source_files:
        raise RuntimeError(f"No generated library documentation found under {source_root}")

    converted = {}
    for source_file in source_files:
        relative_path = normalize_relative_path(source_file, source_root)
        if relative_path in converted:
            raise RuntimeError(f"Multiple generated pages resolve to {relative_path}")
        converted[relative_path] = convert_markdown(source_file.read_text(), relative_path)

    destination.mkdir(parents=True, exist_ok=True)
    generated_directories = [
        path
        for path in destination.rglob("*")
        if path.is_dir() and path.name.endswith((".pat", ".hexpat"))
    ]
    for directory in sorted(generated_directories, key=lambda path: len(path.parts), reverse=True):
        shutil.rmtree(directory)

    for relative_path, markdown in converted.items():
        output = destination / relative_path / "index.mdx"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(markdown)

    return len(converted)


def main() -> None:
    arguments = parse_arguments()
    destination = arguments.destination.resolve()

    if arguments.generated_root:
        count = replace_generated_pages(arguments.generated_root.resolve(), destination)
    else:
        if not arguments.patterns:
            raise SystemExit("--patterns is required when using --imhex")
        with tempfile.TemporaryDirectory(prefix="pattern-language-docs-") as temporary:
            generated_root = Path(temporary)
            generate_markdown(arguments.imhex, arguments.patterns, generated_root)
            count = replace_generated_pages(generated_root, destination)

    print(f"Generated {count} Pattern Language library pages in {destination}")


if __name__ == "__main__":
    main()
