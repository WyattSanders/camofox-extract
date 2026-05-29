"""camofox-extract: Extract clean markdown from any URL using Camofox anti-detection browser."""

from camofox_extract.client import CamofoxClient
from camofox_extract.extractor import extract_urls
from camofox_extract.markdown import accessibility_tree_to_markdown

__version__ = "0.1.0"
__all__ = ["CamofoxClient", "extract_urls", "accessibility_tree_to_markdown"]
