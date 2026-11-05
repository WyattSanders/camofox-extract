# camofox-extract

**Extract clean markdown from any URL — bypass Cloudflare, bot detection, and paywalls.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Regular web scrapers get blocked. [Camofox](https://github.com/jo-inc/camofox-browser) uses a patched Firefox engine with anti-detection at the C++ level — it looks like a real browser because it *is* one. This tool wraps the Camofox REST API to extract clean, structured content from any URL in seconds.

## Why?

| Scraping Method | Cloudflare | Bot Detection | Paywalls | JS Rendering |
|----------------|:----------:|:-------------:|:--------:|:------------:|
| `requests` + `BeautifulSoup` | ❌ | ❌ | ❌ | ❌ |
| Headless Chrome / Puppeteer | ⚠️ | ❌ | ⚠️ | ✅ |
| Playwright + stealth | ⚠️ | ⚠️ | ⚠️ | ✅ |
| **camofox-extract** | ✅ | ✅ | ✅ | ✅ |

Camofox patches Firefox at the C++ level (WebDriver API, canvas fingerprint, audio context, font enumeration) — it's not just a user-agent swap.

## Install

Not published on PyPI yet. Install from GitHub:

```bash
pip install git+https://github.com/WyattSanders/camofox-extract.git
# or, from a clone (with test deps):
pip install -e ".[dev]" && pytest
```

You also need a running [Camofox server](https://github.com/jo-inc/camofox-browser):

```bash
# Docker (recommended)
docker run -d -p 9377:9377 ghcr.io/jo-inc/camofox-browser:latest

# Or install from source
npm install -g camofox-browser
camofox-browser
```

## Quick Start

```bash
# Extract a single URL → clean markdown
camofox-extract https://example.com

# Multiple URLs
camofox-extract https://example.com https://news.ycombinator.com

# JSON output (for programmatic use)
camofox-extract --json https://example.com

# Raw accessibility tree (for debugging)
camofox-extract --raw https://example.com

# Custom Camofox server
camofox-extract --camofox-url http://my-server:9377 https://example.com
```

### Example Output

```markdown
# Example Domain

This domain is for use in documentation examples without
needing permission. Avoid use in operations.

[Learn more](https://iana.org/domains/example)
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CAMOFOX_URL` | `http://localhost:9377` | Camofox server URL |
| `CAMOFOX_API_KEY` | _(empty)_ | API key (optional for local) |

## Python API

### High-Level (recommended)

```python
from camofox_extract import extract_urls

results = extract_urls(
    ["https://example.com", "https://news.ycombinator.com"],
    camofox_url="http://localhost:9377",
)

for r in results:
    print(f"# {r['title']}")
    print(r['content'])
    print("---")
```

### Low-Level Client

```python
from camofox_extract import CamofoxClient

with CamofoxClient(base_url="http://localhost:9377") as client:
    tab_id = client.create_tab()
    client.navigate(tab_id, "https://example.com")
    client.wait_for_ready(tab_id)
    
    # Get clean markdown
    from camofox_extract import accessibility_tree_to_markdown
    raw = client.snapshot(tab_id)
    markdown = accessibility_tree_to_markdown(raw)
    
    client.close_tab(tab_id)
```

### Screenshot

```python
with CamofoxClient() as client:
    tab_id = client.create_tab()
    client.navigate(tab_id, "https://example.com")
    client.wait_for_ready(tab_id)
    
    png_bytes = client.screenshot(tab_id)
    with open("screenshot.png", "wb") as f:
        f.write(png_bytes)
```

## How It Works

```
URL → Camofox Browser → Accessibility Tree → Markdown
         (render JS)      (structured)        (clean text)
```

1. **Connect** to a running Camofox server via REST API
2. **Navigate** to the target URL in a real Firefox tab
3. **Wait** for full page load (network idle, JS executed)
4. **Extract** the accessibility tree (all visible text, links, headings, images)
5. **Convert** to clean markdown — no HTML noise, no scripts, no styles

The accessibility tree is a structured representation of what a screen reader would see: headings, paragraphs, links, images, and lists. It's lightweight (no screenshots) but captures all meaningful content.

## Architecture

```
camofox_extract/
├── __init__.py       # Public API exports
├── client.py         # Camofox REST API client (tabs, navigation, snapshots)
├── extractor.py      # High-level extract_urls() function
├── markdown.py       # Accessibility tree → markdown converter
└── cli.py            # Click-based CLI
```

## Hermes Agent Integration

This package includes a plugin for [Hermes Agent](https://github.com/nousresearch/hermes-agent) that registers `camofox` as a web extract backend:

```yaml
# ~/.hermes/config.yaml
web:
  extract_backend: camofox
```

```bash
# ~/.hermes/.env
CAMOFOX_URL=http://your-server:9377
CAMOFOX_API_KEY=your-key     # optional for localhost
```

### Install the Plugin

```bash
# Option 1: Direct copy (local machine)
cp -r hermes-agent/plugins/web/camofox/ ~/.hermes/hermes-agent/plugins/web/camofox/

# Option 2: From GitHub (any machine)
# Clone this repo
git clone https://github.com/WyattSanders/camofox-extract.git
cp -r camofox-extract/hermes-agent/plugins/web/camofox/ ~/.hermes/hermes-agent/plugins/web/camofox/
```

The plugin imports `camofox_extract`, so also install this package into the
Python environment Hermes runs in (e.g. `~/.hermes/hermes-agent/venv/bin/pip install
git+https://github.com/WyattSanders/camofox-extract.git`). Otherwise
`is_available()` returns False.

Then restart Hermes — built-in web plugins are auto-discovered.

### Verify

```bash
cd ~/.hermes/hermes-agent
python3 -c "from plugins.web.camofox.provider import CamofoxWebExtractProvider; \
p = CamofoxWebExtractProvider(); \
print('Available:', p.is_available(), '| Extract:', p.supports_extract())"
```

Expected output: `Available: True | Extract: True`

## Requirements

- Python ≥ 3.10
- A running [Camofox](https://github.com/jo-inc/camofox-browser) server
- `requests` (HTTP client)
- `click` (CLI)

## License

MIT
