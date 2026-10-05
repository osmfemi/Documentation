#!/usr/bin/env python3

import html
import json
import re
import shutil
import sys
from pathlib import Path


SOURCE_ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "../Documentation").resolve()
PROJECT_ROOT = Path.cwd()
CONTENT_ROOT = PROJECT_ROOT / "content/docs"
ASSET_ROOT = PROJECT_ROOT / "public/assets"

SPACES = (
    ("imhex", "imhex"),
    ("pattern_language", "pattern-language"),
)


def route_for(_space_source: str, space_route: str, relative_path: str) -> str:
    if relative_path == "README.md":
        return space_route

    route = re.sub(r"/README\.md$", "", relative_path)
    route = re.sub(r"\.md$", "", route)

    return f"{space_route}/{route}"


def extract_frontmatter(markdown: str) -> tuple[str, str]:
    if not markdown.startswith("---\n"):
        return markdown, ""

    end = markdown.find("\n---\n", 4)
    if end == -1:
        return markdown, ""

    lines = markdown[4:end].splitlines()
    description = ""
    for index, line in enumerate(lines):
        if not line.startswith("description:"):
            continue
        value = line[len("description:") :].strip()
        if value and value not in (">-", "|"):
            description = value.strip("'\"")
        else:
            description = " ".join(
                nested.strip()
                for nested in lines[index + 1 :]
                if nested[:1].isspace()
            )
        break

    return markdown[end + 5 :], description


def clean_text(value: str) -> str:
    value = re.sub(r"<br\s*/?\s*>", " ", value, flags=re.IGNORECASE)
    value = re.sub(r"<[^>]+>", "", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def slugify_asset_name(value: str) -> str:
    value = re.sub(r"\.[^.]+$", "", value)
    value = re.sub(r"vizualizer|visualiser", "visualizer", value, flags=re.IGNORECASE)
    value = re.sub(r"infered", "inferred", value, flags=re.IGNORECASE)
    value = re.sub(r"higlighted", "highlighted", value, flags=re.IGNORECASE)
    value = re.sub(r"imput", "input", value, flags=re.IGNORECASE)
    value = re.sub(r"\bcx\b", "context", value, flags=re.IGNORECASE)
    return re.sub(r"^-|-$", "", re.sub(r"[^a-zA-Z0-9]+", "-", value)).lower()


source_files = []
source_routes = {}

for space_source, space_route in SPACES:
    directory = SOURCE_ROOT / space_source
    for source_file in directory.rglob("*.md"):
        relative_path = source_file.relative_to(directory).as_posix()
        if relative_path == "SUMMARY.md" or (
            space_source == "imhex"
            and relative_path in {"common/README.md", "views/README.md"}
        ):
            continue
        route = route_for(space_source, space_route, relative_path)
        page = {
            "file": source_file.resolve(),
            "relative_path": relative_path,
            "route": route,
        }
        source_files.append(page)
        source_routes[source_file.resolve()] = f"/{route}"

shutil.rmtree(CONTENT_ROOT, ignore_errors=True)
shutil.rmtree(ASSET_ROOT, ignore_errors=True)

copied_assets = {}
used_asset_paths = set()


def migrate_asset(source_file: Path, page_route: str, raw_reference: str, context: str) -> str:
    unescaped_reference = raw_reference.replace(r"\_", "_")
    source_asset = (source_file.parent / unescaped_reference).resolve()
    if not source_asset.exists():
        asset_directory = next(parent for parent in source_file.parents if (parent / ".gitbook/assets").is_dir()) / ".gitbook/assets"
        matches = list(asset_directory.rglob(source_asset.name))
        if not matches:
            expected_name = slugify_asset_name(source_asset.name)
            matches = [
                candidate
                for candidate in asset_directory.rglob("*")
                if candidate.is_file() and slugify_asset_name(candidate.name) == expected_name
            ]
        if len(matches) != 1:
            raise FileNotFoundError(f"Could not uniquely resolve {raw_reference} from {source_file}")
        source_asset = matches[0].resolve()
    if source_asset in copied_assets:
        return copied_assets[source_asset]

    extension = source_asset.suffix.lower()
    relative_asset_path = unescaped_reference.split(".gitbook/assets/")[-1]
    source_path = Path(relative_asset_path)
    name = slugify_asset_name(source_path.stem)
    page_name = page_route.rsplit("/", 1)[-1]
    if name == page_name:
        name = "overview"
    elif name.startswith(f"{page_name}-"):
        name = name[len(page_name) + 1 :]
    if name in {"data", "hex"} and source_path.parent.name not in {"assets", "."}:
        name = slugify_asset_name(f"{source_path.parent.name}-{name}")
    name = {
        "input-maths": "mathematical-input",
        "input-num": "numerical-input",
        "input-pattern": "binary-pattern-input",
        "input-regex": "regex-input",
        "input-text": "text-input",
        "screenshot-0": "analysis-workspace",
        "screenshot-1": "data-processing-workspace",
        "lcase": "lowercase-hex",
        "cx-menu": "context-menu",
        "prev-next-btn": "previous-next-buttons",
        "hide-show-rows": "row-visibility",
    }.get(name, name)
    if source_path.parent.name == "menu" and context:
        name = slugify_asset_name(context)
    name = name or "image"
    public_path = f"/assets/{page_route}/{name}{extension}"
    duplicate = 2

    while public_path in used_asset_paths:
        public_path = f"/assets/{page_route}/{name}-{duplicate}{extension}"
        duplicate += 1

    destination = PROJECT_ROOT / "public" / public_path.removeprefix("/")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_asset, destination)
    used_asset_paths.add(public_path)
    copied_assets[source_asset] = public_path
    return public_path


def resolve_doc_link(source_file: Path, href: str) -> str:
    normalized_href = href.replace(r"\_", "_")
    target_path, separator, fragment = normalized_href.partition("#")
    if not target_path:
        return href

    target = (source_file.parent / target_path).resolve()
    candidates = [target, Path(f"{target}.md"), target / "README.md"]
    if target.suffix == ".pat":
        candidates.append(Path(f"{target}.md"))

    for candidate in candidates:
        route = source_routes.get(candidate)
        if route:
            return f"{route}{f'#{fragment}' if separator else ''}"
    return href


def convert_hints(markdown: str) -> str:
    def replacement(match: re.Match) -> str:
        style, content = match.groups()
        label = "Danger" if style == "danger" else "Warning" if style == "warning" else "Note"
        quoted = "\n".join(f"> {line}" for line in content.splitlines())
        return f"> **{label}**\n>\n{quoted}"

    return re.sub(
        r'\{% hint style="([^"]+)" %\}\n([\s\S]*?)\n\{% endhint %\}',
        replacement,
        markdown,
    )


def convert_directives(markdown: str) -> str:
    markdown = convert_hints(markdown)
    markdown = re.sub(r"^\{% (?:content-ref|endcontent-ref|code|endcode|tabs|endtabs)[^%]*%\}\n?", "", markdown, flags=re.MULTILINE)
    markdown = re.sub(r'^\{% tab title="([^"]+)" %\}\n?', r"### \1\n\n", markdown, flags=re.MULTILINE)
    markdown = re.sub(r"^\{% endtab %\}\n?", "", markdown, flags=re.MULTILINE)
    markdown = re.sub(r'^\{% embed url="([^"]+)" %\}\n?', r"[\1](\1)\n", markdown, flags=re.MULTILINE)
    return markdown.replace("&#x20;", " ")


def convert_assets(markdown: str, page: dict) -> str:
    contexts = {}
    figure_pattern = re.compile(
        r'<figure><img src="([^"]+)" alt="([^"]*)"[^>]*><figcaption>([\s\S]*?)</figcaption></figure>'
    )
    for match in figure_pattern.finditer(markdown):
        contexts[match.group(1)] = clean_text(match.group(3)) or clean_text(match.group(2))

    references = list(re.finditer(r'(?:\.\.?/)*\.gitbook/assets/[^"\')<>\s]+', markdown))
    for match in references:
        raw_reference = match.group(0)
        public_path = migrate_asset(
            page["file"], page["route"], raw_reference, contexts.get(raw_reference, "")
        )
        markdown = markdown.replace(raw_reference, public_path)

    def figure_replacement(match: re.Match) -> str:
        src, alt_text, caption_html = match.groups()
        caption = clean_text(caption_html)
        image_alt = clean_text(alt_text) or caption or "Screenshot"
        attributes = (
            f'src="{html.escape(src, quote=True)}" '
            f'alt="{html.escape(image_alt, quote=True)}"'
        )
        if caption:
            attributes += f' caption="{html.escape(caption, quote=True)}"'
        return f"<DocumentedImage {attributes} />"

    markdown = re.sub(
        r'(?:<div[^>]*>)?<figure><img src="([^"]+)" alt="([^"]*)"[^>]*><figcaption>([\s\S]*?)</figcaption></figure>(?:</div>)?',
        figure_replacement,
        markdown,
    )
    return re.sub(
        r'<img src="([^"]+)" alt="([^"]*)"[^>]*>',
        lambda match: f"![{clean_text(match.group(2))}]({match.group(1)})",
        markdown,
    )


def convert_links(markdown: str, page: dict) -> str:
    replacements = {
        "https://app.gitbook.com/o/xfl3734L2rDBS2sD53Zi/s/xj7sbzGbHH260vbpZOu1/": "/imhex",
        "https://app.gitbook.com/o/xfl3734L2rDBS2sD53Zi/s/WZzDdGjxmgMSIE3xly6o/": "/pattern-language",
        "https://docs.werwolv.net/imhex/": "/imhex/",
        "https://docs.werwolv.net/pattern-language/": "/pattern-language/",
    }
    for old, new in replacements.items():
        markdown = markdown.replace(old, new)

    def markdown_link(match: re.Match) -> str:
        href = match.group(1)
        if not href.startswith(".") and not re.match(r"^[^/:#]+\.md(?:#|$)", href):
            return match.group(0)
        return f"]({resolve_doc_link(page['file'], href)})"

    markdown = re.sub(r"\]\(([^)]+)\)", markdown_link, markdown)

    def html_link(match: re.Match) -> str:
        href = match.group(1)
        if not href.startswith(".") and not re.match(r"^[^/:#]+\.md(?:#|$)", href):
            return match.group(0)
        return f'href="{resolve_doc_link(page["file"], href)}"'

    markdown = re.sub(r'href="([^"]+)"', html_link, markdown)
    return re.sub(
        r"\]\((https?://[^)]+)\)",
        lambda match: "](" + match.group(1).replace(r"\_", "_") + ")",
        markdown,
    )


def convert_special_markup(markdown: str, page: dict) -> str:
    if page["route"] == "imhex":
        return markdown.replace(
            '<DocumentedImage src="/assets/imhex/analysis-workspace.png" alt="Screenshot" />',
            '<DocumentedImage src="/assets/imhex/analysis-workspace.png" alt="ImHex analysis workspace" />',
        ).replace(
            '<DocumentedImage src="/assets/imhex/data-processing-workspace.png" alt="Screenshot" />',
            '<DocumentedImage src="/assets/imhex/data-processing-workspace.png" alt="ImHex data processing workspace" />',
        )

    if page["route"] != "imhex/common/input-text-boxes":
        return markdown.replace("<div>\n", "").replace("</div>\n", "")

    inputs = """<div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">

<InputTypeCard title="Mathematical Input" image="/assets/imhex/common/input-text-boxes/mathematical-input.png" alt="Mathematical input">

This field expects a mathematical expression such as `-1234.5`, `0xABCD`, `5 + 7`, or `log(e) / 2`. Hexadecimal values must be prefixed with `0x`.

</InputTypeCard>

<InputTypeCard title="Numerical Input" image="/assets/imhex/common/input-text-boxes/numerical-input.png" alt="Numerical input">

This field expects a floating point, decimal, or hexadecimal number.

</InputTypeCard>

<InputTypeCard title="Binary Pattern Input" image="/assets/imhex/common/input-text-boxes/binary-pattern-input.png" alt="Binary pattern input">

This field expects a binary pattern such as `0F ?? A?`. The characters 0 through 9 and A through F specify a fixed nibble, while a question mark specifies a wildcard. See [Binary Pattern](/imhex/common/binary-pattern) for details.

</InputTypeCard>

<InputTypeCard title="Regex Input" image="/assets/imhex/common/input-text-boxes/regex-input.png" alt="Regex input">

This field expects a regular expression. See the [regular expression cheatsheet](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Regular_Expressions/Cheatsheet) for details.

</InputTypeCard>

<InputTypeCard title="Text Input" image="/assets/imhex/common/input-text-boxes/text-input.png" alt="Text input">

This field accepts any valid UTF-8 string without special formatting.

</InputTypeCard>

</div>"""
    return re.sub(r"<table[\s\S]*?</table>", inputs, markdown, count=1)


def escape_mdx_text(markdown: str) -> str:
    parts = re.split(r"(```[\s\S]*?```)", markdown)
    for index in range(0, len(parts), 2):
        inline_parts = re.split(r"(`[^`\n]+`|\$\$[\s\S]*?\$\$|\$[^$\n]+\$)", parts[index])
        for inline_index in range(0, len(inline_parts), 2):
            inline_parts[inline_index] = re.sub(
                r"<((?:ImHex|Pattern|Type)[^>]+)>",
                r"&lt;\1&gt;",
                inline_parts[inline_index],
            )
            inline_parts[inline_index] = inline_parts[inline_index].replace("{", "&#123;").replace("}", "&#125;")
            inline_parts[inline_index] = inline_parts[inline_index].replace("<br>", "<br />")
        parts[index] = "".join(inline_parts)
    return "".join(parts)


for page in source_files:
    source = page["file"].read_text()
    source_body, source_description = extract_frontmatter(source)
    title_match = re.search(r"^#\s+(.+)$", source_body, flags=re.MULTILINE)
    title = title_match.group(1).strip() if title_match else Path(page["route"]).name
    description = source_description or f"Documentation for {title}."
    body = re.sub(r"^\s*#\s+.+\n+", "", source_body, count=1)
    body = convert_directives(body)
    body = convert_assets(body, page)
    body = convert_links(body, page)
    body = convert_special_markup(body, page)
    body = re.sub(r"^# ", "## ", body, flags=re.MULTILINE)
    body = escape_mdx_text(body).strip()

    frontmatter = "\n".join(
        (
            "---",
            f"title: {json.dumps(title)}",
            f"description: {json.dumps(description)}",
            "published: true",
            "toc:",
            "  visible: true",
            "---",
            "",
        )
    )
    destination = CONTENT_ROOT / page["route"] / "index.mdx"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(f"{frontmatter}{body}\n")

routes = {f"/{page['route']}" for page in source_files}
validation_errors = []
for markdown_file in CONTENT_ROOT.rglob("*.mdx"):
    markdown = markdown_file.read_text()
    if ".gitbook" in markdown or "{%" in markdown or "app.gitbook.com" in markdown:
        validation_errors.append(f"GitBook syntax remains in {markdown_file}")

    references = re.findall(r"!?\[[^\]]*\]\((/[^)\s]+)\)", markdown)
    references.extend(re.findall(r'href="(/[^"]+)"', markdown))
    for reference in references:
        target = reference.split("#", 1)[0].rstrip("/") or "/"
        if target.startswith("/assets/"):
            if not (PROJECT_ROOT / "public" / target.removeprefix("/")).is_file():
                validation_errors.append(f"Missing asset {target} referenced by {markdown_file}")
        elif target not in routes:
            validation_errors.append(f"Missing page {target} referenced by {markdown_file}")

if validation_errors:
    raise RuntimeError("\n".join(validation_errors))

print(
    f"Migrated and validated {len(source_files)} pages and "
    f"{len(copied_assets)} referenced assets."
)
