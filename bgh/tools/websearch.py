"""Pesquisa web sem API paga: DuckDuckGo lite/html + extracao de pagina em texto puro."""

import html as htmllib
import re
import urllib.parse
from html.parser import HTMLParser

import requests

from .guard import STOPPED_NOTE, stopped

UA = "Mozilla/5.0 (X11; Linux x86_64) bgh-motor/0.1 (agente local)"

SEARCH_SPEC = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Pesquisa na internet (DuckDuckGo, sem chave de API). Devolve titulo, URL e resumo dos resultados.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Termos da busca"},
                "top_k": {"type": "integer", "description": "Quantidade de resultados (padrao 6, max 10)"},
            },
            "required": ["query"],
        },
    },
}

EXTRACT_SPEC = {
    "type": "function",
    "function": {
        "name": "web_extract",
        "description": "Baixa uma pagina web e devolve o texto do conteudo (para confirmar informacao da busca).",
        "parameters": {
            "type": "object",
            "properties": {"url": {"type": "string", "description": "URL http(s) completa"}},
            "required": ["url"],
        },
    },
}


def _clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    return htmllib.unescape(re.sub(r"\s+", " ", text)).strip()


def _real_url(href: str) -> str:
    """DuckDuckGo envolve links em /l/?uddg=<encodado>; recupera a URL original."""
    href = htmllib.unescape(href)
    if href.startswith("//"):
        href = "https:" + href
    parsed = urllib.parse.urlparse(href)
    if "duckduckgo.com" in parsed.netloc and parsed.path.rstrip("/").endswith("/l"):
        q = urllib.parse.parse_qs(parsed.query)
        if "uddg" in q:
            return q["uddg"][0]
    return href


def parse_lite(html_text: str, top_k: int) -> list[dict]:
    links = re.findall(
        r"<a rel=\"nofollow\" href=\"([^\"]+)\"[^>]*>(.*?)</a>", html_text, re.S
    )
    snippets = re.findall(r"<td class='result-snippet'>(.*?)</td>", html_text, re.S)
    results = []
    for i, (href, title) in enumerate(links[:top_k]):
        results.append(
            {
                "title": _clean(title),
                "url": _real_url(href),
                "snippet": _clean(snippets[i]) if i < len(snippets) else "",
            }
        )
    return results


def parse_html_page(html_text: str, top_k: int) -> list[dict]:
    links = re.findall(r"<a class=\"result__a\" href=\"([^\"]+)\">(.*?)</a>", html_text, re.S)
    snippets = re.findall(r"<a class=\"result__snippet\"[^>]*>(.*?)</a>", html_text, re.S)
    results = []
    for i, (href, title) in enumerate(links[:top_k]):
        results.append(
            {
                "title": _clean(title),
                "url": _real_url(href),
                "snippet": _clean(snippets[i]) if i < len(snippets) else "",
            }
        )
    return results


def web_search(args: dict, ctx) -> str:
    query = str(args.get("query", "")).strip()
    if not query:
        return "ERRO: busca sem termos"
    if stopped(ctx):
        return STOPPED_NOTE
    top_k = min(int(args.get("top_k") or 6), 10)
    endpoints = [
        ("https://lite.duckduckgo.com/lite/", parse_lite),
        ("https://html.duckduckgo.com/html/", parse_html_page),
    ]
    last_error = ""
    for url, parser in endpoints:
        try:
            resp = requests.post(
                url,
                data={"q": query},
                headers={"User-Agent": UA},
                timeout=15,
            )
            if resp.ok:
                results = parser(resp.text, top_k)
                if results:
                    lines = []
                    for i, r in enumerate(results, start=1):
                        lines.append(f"{i}. {r['title']}\n   URL: {r['url']}\n   {r['snippet']}")
                    return "\n".join(lines)
            last_error = f"HTTP {resp.status_code}"
        except requests.RequestException as exc:
            last_error = str(exc)
    return f"Sem resultados para '{query}' (ultimo erro: {last_error}). Tente outros termos."


class _TextExtractor(HTMLParser):
    SKIP = {"script", "style", "nav", "footer", "header", "noscript", "svg"}

    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip_depth += 1
        elif tag in ("p", "div", "br", "li", "h1", "h2", "h3", "h4", "tr"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth == 0 and data.strip():
            self.parts.append(data.strip())


def web_extract(args: dict, ctx) -> str:
    url = str(args.get("url", "")).strip()
    if not url.startswith(("http://", "https://")):
        return "ERRO: URL invalida"
    if stopped(ctx):
        return STOPPED_NOTE
    try:
        resp = requests.get(url, headers={"User-Agent": UA}, timeout=20, allow_redirects=True)
    except requests.RequestException as exc:
        return f"ERRO ao baixar {url}: {exc}"
    ctype = resp.headers.get("content-type", "")
    if "html" not in ctype and not resp.text.lstrip().lower().startswith(("<!doctype", "<html")):
        return f"ERRO: conteudo nao e HTML ({ctype or 'desconhecido'}); use read_file para PDF/binario so com ferramenta adequada."
    parser = _TextExtractor()
    try:
        parser.feed(resp.text)
    except Exception:  # noqa: BLE001 - HTML quebrado nao deve derrubar o agente
        pass
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(parser.parts)).strip()
    if not text:
        return f"A pagina {url} nao tem texto legivel (pode exigir JavaScript)."
    if len(text) > 8000:
        return text[:8000] + f"\n...[texto cortado; {len(text)} chars no total em {url}]"
    return text
