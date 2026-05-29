"""CLI entry point for camofox-extract."""

from __future__ import annotations

import json
import sys

import click

from camofox_extract.client import CamofoxClient, CamofoxError
from camofox_extract.extractor import extract_urls


@click.command()
@click.argument("urls", nargs=-1)
@click.option("--url", "-u", "extra_urls", multiple=True, help="URL to extract (alternative to positional args)")
@click.option("--camofox-url", envvar="CAMOFOX_URL", default="http://localhost:9377", help="Camofox server URL")
@click.option("--camofox-api-key", envvar="CAMOFOX_API_KEY", default="", help="Camofox API key")
@click.option("--timeout", "-t", default=30, type=int, help="Navigation timeout in seconds")
@click.option("--raw", is_flag=True, help="Output raw accessibility tree instead of markdown")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON array")
@click.option("--cleanup", is_flag=True, help="Clean up session after extraction")
def main(
    urls: tuple[str, ...],
    extra_urls: tuple[str, ...],
    camofox_url: str,
    camofox_api_key: str,
    timeout: int,
    raw: bool,
    as_json: bool,
    cleanup: bool,
) -> None:
    """Extract clean content from URLs using Camofox anti-detection browser.

    Pass URLs as positional arguments or with -u/--url flags.

    \b
    Examples:
        camofox-extract https://example.com
        camofox-extract -u https://a.com -u https://b.com
        camofox-extract --json https://example.com
    """
    all_urls = list(urls) + list(extra_urls)

    if not all_urls:
        click.echo("Error: No URLs provided. Pass URLs as arguments or use -u/--url.", err=True)
        sys.exit(1)

    # Validate URLs
    for u in all_urls:
        if not u.startswith(("http://", "https://")):
            click.echo(f"Warning: URL does not start with http(s)://: {u}", err=True)

    client = CamofoxClient(base_url=camofox_url, api_key=camofox_api_key)

    try:
        results = extract_urls(
            all_urls,
            client=client,
            timeout=timeout,
        )
    except CamofoxError as e:
        click.echo(f"Error connecting to Camofox: {e}", err=True)
        sys.exit(1)

    if cleanup:
        client.cleanup()

    # Output
    if as_json:
        click.echo(json.dumps(results, indent=2))
    else:
        for i, result in enumerate(results):
            if i > 0:
                click.echo("\n---\n")

            title = result.get("title", "")
            header = result["url"]
            if title:
                header += f" — {title}"
            click.echo(f"## {header}\n")

            if result.get("error"):
                click.echo(f"Error: {result['error']}")
            elif raw:
                click.echo(result.get("raw_content", "(no content)"))
            else:
                click.echo(result.get("content", "(no content)"))

    # Exit code
    failed = any(r.get("error") for r in results)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
