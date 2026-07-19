from __future__ import annotations

import ipaddress
import re
import socket
import urllib.error
import urllib.request
from datetime import datetime
from html import unescape
from html.parser import HTMLParser
from typing import Callable
from urllib.parse import urlparse

from .models import ContentBlock, MaterialModality, RawMaterial, SourceType


MAX_WEB_BYTES = 5 * 1024 * 1024


class WebIngestionError(ValueError):
    pass


class _ArticleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.skip = 0
        self.title = ""
        self.publisher = ""
        self.published_at: str | None = None
        self.parts: list[str] = []
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag in {"script", "style", "nav", "footer", "noscript", "svg"}:
            self.skip += 1
        if tag == "title":
            self._in_title = True
        if tag == "meta":
            key = (attributes.get("property") or attributes.get("name") or "").lower()
            value = attributes.get("content", "").strip()
            if key in {"og:title", "twitter:title"} and value:
                self.title = value
            elif key in {"og:site_name", "application-name", "author"} and value and not self.publisher:
                self.publisher = value
            elif key in {"article:published_time", "date", "publishdate", "pubdate"} and value and not self.published_at:
                self.published_at = value

    def handle_endtag(self, tag):
        if tag in {"script", "style", "nav", "footer", "noscript", "svg"} and self.skip:
            self.skip -= 1
        if tag == "title":
            self._in_title = False
        if tag in {"p", "div", "article", "section", "h1", "h2", "h3", "li", "tr"} and not self.skip:
            self.parts.append("\n")

    def handle_data(self, data):
        if self.skip:
            return
        text = unescape(data).strip()
        if not text:
            return
        if self._in_title and not self.title:
            self.title = text
        self.parts.append(text)


def ingest_web_url(url: str, source_type: SourceType = SourceType.NEWS_SUMMARY, *, opener: Callable | None = None, resolver: Callable | None = None) -> RawMaterial:
    _validate_public_url(url, resolver or socket.getaddrinfo)
    request = urllib.request.Request(url, headers={"User-Agent": "ResearchCoach/1.0 (+research-training)"})
    try:
        response = (opener or urllib.request.urlopen)(request, timeout=20)
        with response:
            final_url = response.geturl() if hasattr(response, "geturl") else url
            _validate_public_url(final_url, resolver or socket.getaddrinfo)
            content_type = str(response.headers.get("Content-Type", ""))
            if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
                raise WebIngestionError("网页地址没有返回 HTML 正文")
            data = response.read(MAX_WEB_BYTES + 1)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise WebIngestionError(f"网页读取失败：{exc}") from exc
    if len(data) > MAX_WEB_BYTES:
        raise WebIngestionError("网页正文超过 5MB 限制")
    charset_match = re.search(r"charset=([\w-]+)", content_type, re.I)
    charset = charset_match.group(1) if charset_match else "utf-8"
    try:
        html = data.decode(charset, errors="replace")
    except LookupError:
        html = data.decode("utf-8", errors="replace")
    parser = _ArticleParser()
    parser.feed(html)
    lines = [re.sub(r"\s+", " ", line).strip() for line in " ".join(parser.parts).split("\n")]
    content = "\n".join(dict.fromkeys(line for line in lines if len(line) >= 10))
    if len(content) < 40:
        raise WebIngestionError("网页未提取出足够的研究正文")
    published_at = _parse_date(parser.published_at)
    blocks = [ContentBlock(modality=MaterialModality.TEXT, content=line, paragraph=index, extraction_method="html_article_parser") for index, line in enumerate(content.splitlines(), start=1)]
    return RawMaterial(title=parser.title or urlparse(url).netloc, content=content, source_type=source_type, url=final_url, publisher=parser.publisher or urlparse(final_url).netloc, published_at=published_at, modality=MaterialModality.TEXT, blocks=blocks, usage_rights_confirmed=None, parse_warnings=["网页内容仅用于用户授权的研究训练，请确认使用权限和正文完整性。"])


def _validate_public_url(url: str, resolver: Callable) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise WebIngestionError("仅支持公开的 HTTP/HTTPS 网页地址")
    try:
        addresses = {item[4][0] for item in resolver(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)}
    except OSError as exc:
        raise WebIngestionError(f"网页域名无法解析：{exc}") from exc
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise WebIngestionError("不允许访问本机、内网或保留地址")


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
