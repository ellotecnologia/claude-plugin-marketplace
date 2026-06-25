#!/usr/bin/env python3
"""DokuWiki CLI — stdlib-only client for the DokuWiki JSON-RPC API."""

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

class DokuWikiConfig:
    def __init__(self, url, user=None, password=None, token=None, timeout=30):
        self.url = url.rstrip("/")
        self.user = user
        self.password = password
        self.token = token
        self.timeout = timeout


def _parse_dotenv(path):
    """Parse a .env file, returning a dict of key→value."""
    result = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                result[k] = v
    except OSError:
        pass
    return result


def load_config(url=None, user=None, password=None, token=None):
    env = {}

    # .env in CWD
    env.update(_parse_dotenv(".env"))

    # ~/.config/dokuwiki/config.toml
    toml_path = Path.home() / ".config" / "dokuwiki" / "config.toml"
    if toml_path.exists():
        toml = _parse_dotenv(toml_path)  # key = value lines; handles the same simple format
        env.setdefault("DOKUWIKI_URL", toml.get("url", ""))
        env.setdefault("DOKUWIKI_USER", toml.get("user", ""))
        env.setdefault("DOKUWIKI_PASS", toml.get("pass", ""))
        env.setdefault("DOKUWIKI_TOKEN", toml.get("token", ""))

    # OS env vars override file config
    for k in ("DOKUWIKI_URL", "DOKUWIKI_USER", "DOKUWIKI_PASS", "DOKUWIKI_TOKEN"):
        if k in os.environ:
            env[k] = os.environ[k]

    # CLI flags take highest priority
    resolved_url = url or env.get("DOKUWIKI_URL", "")
    resolved_user = user or env.get("DOKUWIKI_USER") or None
    resolved_pass = password or env.get("DOKUWIKI_PASS") or None
    resolved_token = token or env.get("DOKUWIKI_TOKEN") or None

    if not resolved_url:
        sys.exit(
            "Error: DOKUWIKI_URL is required. "
            "Set it via --url, the DOKUWIKI_URL env var, .env file, "
            "or ~/.config/dokuwiki/config.toml"
        )

    return DokuWikiConfig(
        url=resolved_url,
        user=resolved_user,
        password=resolved_pass,
        token=resolved_token,
    )


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class DokuWikiError(Exception):
    def __init__(self, code, message):
        super().__init__(f"DokuWiki error {code}: {message}")
        self.code = code
        self.message = message


class _PostRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Follow redirects while preserving POST method and body."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new_req = urllib.request.Request(
            newurl,
            data=req.data,
            headers={k: v for k, v in req.header_items()},
            method=req.get_method(),
        )
        return new_req


_OPENER = urllib.request.build_opener(_PostRedirectHandler)


class DokuWikiClient:
    def __init__(self, config, debug=False):
        self.config = config
        self.debug = debug

    def _call(self, method, params=None):
        # The API is JSON-RPC 2.0 at a single endpoint; method goes in the body, not the URL.
        payload = {"jsonrpc": "2.0", "method": method, "id": 1}
        if params is not None:
            payload["params"] = params
        body = json.dumps(payload).encode()

        req = urllib.request.Request(self.config.url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json")

        if self.config.token:
            req.add_header("Authorization", f"Bearer {self.config.token}")
        elif self.config.user and self.config.password:
            creds = base64.b64encode(
                f"{self.config.user}:{self.config.password}".encode()
            ).decode()
            req.add_header("Authorization", f"Basic {creds}")

        if self.debug:
            print(f"[debug] POST {self.config.url}", file=sys.stderr)
            print(f"[debug] body: {body.decode()}", file=sys.stderr)

        try:
            with _OPENER.open(req, timeout=self.config.timeout) as resp:
                raw = resp.read()
                if self.debug:
                    print(f"[debug] status: {resp.status}", file=sys.stderr)
                    print(f"[debug] response: {raw[:500].decode(errors='replace')}", file=sys.stderr)
        except urllib.error.HTTPError as e:
            raw = e.read()
            if self.debug:
                print(f"[debug] HTTP {e.code}: {raw[:500]}", file=sys.stderr)
            try:
                err_data = json.loads(raw.decode())
                err = err_data.get("error") or {}
                raise DokuWikiError(
                    err.get("code", e.code),
                    err.get("message", e.reason),
                ) from e
            except (json.JSONDecodeError, KeyError):
                raise DokuWikiError(e.code, e.reason) from e
        except urllib.error.URLError as e:
            raise DokuWikiError(0, str(e.reason)) from e

        if not raw:
            raise DokuWikiError(0, f"Empty response from server (method: {method!r})")

        try:
            data = json.loads(raw.decode())
        except json.JSONDecodeError:
            preview = raw[:300].decode(errors="replace")
            raise DokuWikiError(0, f"Non-JSON response: {preview!r}")

        # JSON-RPC 2.0: errors come in the "error" key, successes in "result"
        if "error" in data:
            err = data["error"]
            raise DokuWikiError(err.get("code", -1), err.get("message", "Unknown error"))

        return data["result"]

    # Pages
    def get_page(self, page, rev=0):
        return self._call("core.getPage", {"page": page, "rev": rev})

    def save_page(self, page, text, summary="", isminor=False):
        return self._call("core.savePage", {
            "page": page, "text": text, "summary": summary, "isminor": isminor
        })

    def append_page(self, page, text, summary="", isminor=False):
        return self._call("core.appendPage", {
            "page": page, "text": text, "summary": summary, "isminor": isminor
        })

    def list_pages(self, namespace="", depth=1):
        return self._call("core.listPages", {"namespace": namespace, "depth": depth})

    def search_pages(self, query):
        return self._call("core.searchPages", {"query": query})

    def get_page_info(self, page, rev=0, author=False):
        return self._call("core.getPageInfo", {"page": page, "rev": rev, "author": author})

    def get_page_html(self, page, rev=0):
        return self._call("core.getPageHTML", {"page": page, "rev": rev})

    def get_page_history(self, page, first=0):
        return self._call("core.getPageHistory", {"page": page, "first": first})

    def get_page_links(self, page):
        return self._call("core.getPageLinks", {"page": page})

    def get_page_backlinks(self, page):
        return self._call("core.getPageBackLinks", {"page": page})

    def get_recent_page_changes(self, timestamp=0):
        return self._call("core.getRecentPageChanges", {"timestamp": timestamp})

    def lock_pages(self, pages):
        return self._call("core.lockPages", {"pages": pages})

    def unlock_pages(self, pages):
        return self._call("core.unlockPages", {"pages": pages})

    def whoami(self):
        return self._call("core.whoAmI", None)

    def acl_check(self, page, user="", groups=None):
        return self._call("core.aclCheck", {
            "page": page, "user": user, "groups": groups or []
        })

    # Media
    def list_media(self, namespace="", pattern="", depth=1):
        return self._call("core.listMedia", {
            "namespace": namespace, "pattern": pattern, "depth": depth
        })

    def get_media(self, media, rev=0):
        result = self._call("core.getMedia", {"media": media, "rev": rev})
        return base64.b64decode(result)

    def get_media_info(self, media, rev=0):
        return self._call("core.getMediaInfo", {"media": media, "rev": rev})

    def save_media(self, media, data, overwrite=False):
        return self._call("core.saveMedia", {
            "media": media,
            "base64": base64.b64encode(data).decode("ascii"),
            "overwrite": overwrite,
        })

    def delete_media(self, media):
        return self._call("core.deleteMedia", {"media": media})

    # Info
    def get_wiki_version(self):
        return self._call("core.getWikiVersion", None)


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def out(value):
    """Print a result: plain text for strings/bools/ints, JSON for complex types."""
    if isinstance(value, (dict, list)):
        print(json.dumps(value, indent=2, ensure_ascii=False))
    else:
        print(value)


def _read_text(args):
    """Get page text from --text or --file (- = stdin)."""
    if args.text is not None:
        return args.text
    if args.file == "-":
        return sys.stdin.read()
    if args.file:
        with open(args.file, encoding="utf-8") as f:
            return f.read()
    sys.exit("Error: provide --text or --file")


def _write_output(data, path):
    """Write data (str or bytes) to a file or stdout."""
    if isinstance(data, bytes):
        if path:
            Path(path).write_bytes(data)
        else:
            sys.stdout.buffer.write(data)
    else:
        if path:
            Path(path).write_text(data, encoding="utf-8")
        else:
            print(data)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser():
    p = argparse.ArgumentParser(
        prog="dokuwiki",
        description="CLI for the DokuWiki JSON-RPC API",
    )
    p.add_argument("--url", help="DokuWiki RPC URL (env: DOKUWIKI_URL)")
    p.add_argument("--user", help="Username (env: DOKUWIKI_USER)")
    p.add_argument("--password", help="Password (env: DOKUWIKI_PASS)")
    p.add_argument("--token", help="JWT bearer token (env: DOKUWIKI_TOKEN)")
    p.add_argument("--debug", action="store_true", help="Print raw request/response to stderr")

    sub = p.add_subparsers(dest="command", required=True)

    # get
    s = sub.add_parser("get", help="Get wiki syntax of a page")
    s.add_argument("page")
    s.add_argument("--rev", type=int, default=0, help="Revision timestamp (0=current)")
    s.add_argument("--output", "-o", help="Write to file instead of stdout")

    # save
    s = sub.add_parser("save", help="Save (create/replace) a page")
    s.add_argument("page")
    g = s.add_mutually_exclusive_group()
    g.add_argument("--text", help="Wiki text")
    g.add_argument("--file", "-f", help="File to read text from (- = stdin)")
    s.add_argument("--summary", default="", help="Edit summary")
    s.add_argument("--minor", action="store_true", help="Mark as minor edit")

    # append
    s = sub.add_parser("append", help="Append text to a page")
    s.add_argument("page")
    g = s.add_mutually_exclusive_group()
    g.add_argument("--text", help="Wiki text to append")
    g.add_argument("--file", "-f", help="File to read text from (- = stdin)")
    s.add_argument("--summary", default="", help="Edit summary")
    s.add_argument("--minor", action="store_true", help="Mark as minor edit")

    # list
    s = sub.add_parser("list", help="List pages in a namespace")
    s.add_argument("--namespace", default="", help="Namespace (empty = root)")
    s.add_argument("--depth", type=int, default=1, help="Depth (0 = all sub-namespaces)")

    # search
    s = sub.add_parser("search", help="Full-text search")
    s.add_argument("query")

    # info
    s = sub.add_parser("info", help="Get page metadata")
    s.add_argument("page")
    s.add_argument("--rev", type=int, default=0)
    s.add_argument("--author", action="store_true", help="Include author info")

    # html
    s = sub.add_parser("html", help="Get page rendered as HTML")
    s.add_argument("page")
    s.add_argument("--rev", type=int, default=0)
    s.add_argument("--output", "-o", help="Write to file instead of stdout")

    # history
    s = sub.add_parser("history", help="Get page revision history")
    s.add_argument("page")
    s.add_argument("--first", type=int, default=0, help="Skip first N entries")

    # links
    s = sub.add_parser("links", help="Get links on a page")
    s.add_argument("page")

    # backlinks
    s = sub.add_parser("backlinks", help="Get pages that link to a page")
    s.add_argument("page")

    # recent
    s = sub.add_parser("recent", help="Get recent page changes")
    s.add_argument("--since", type=int, default=0, dest="timestamp",
                   help="Unix timestamp (0 = wiki default window)")

    # lock
    s = sub.add_parser("lock", help="Lock pages for editing")
    s.add_argument("pages", nargs="+")

    # unlock
    s = sub.add_parser("unlock", help="Unlock pages")
    s.add_argument("pages", nargs="+")

    # whoami
    sub.add_parser("whoami", help="Show info about the authenticated user")

    # list-media
    s = sub.add_parser("list-media", help="List media files in a namespace")
    s.add_argument("--namespace", default="")
    s.add_argument("--pattern", default="", help="Regex filter (PHP syntax)")
    s.add_argument("--depth", type=int, default=1)

    # get-media
    s = sub.add_parser("get-media", help="Download a media file")
    s.add_argument("media")
    s.add_argument("--rev", type=int, default=0)
    s.add_argument("--output", "-o", help="Output file path")

    # save-media
    s = sub.add_parser("save-media", help="Upload a media file")
    s.add_argument("media")
    s.add_argument("--file", "-f", required=True, help="Local file to upload")
    s.add_argument("--overwrite", action="store_true")

    # delete-media
    s = sub.add_parser("delete-media", help="Delete a media file")
    s.add_argument("media")

    # acl-check
    s = sub.add_parser("acl-check", help="Check ACL permission level for a page")
    s.add_argument("page")
    s.add_argument("--user", default="")
    s.add_argument("--group", action="append", dest="groups", default=[],
                   metavar="GROUP", help="Group (repeatable)")

    # version
    sub.add_parser("version", help="Print the wiki software version")

    return p


def run(args, client):
    cmd = args.command

    if cmd == "get":
        result = client.get_page(args.page, args.rev)
        _write_output(result, args.output)

    elif cmd == "save":
        text = _read_text(args)
        ok = client.save_page(args.page, text, args.summary, args.minor)
        print("saved" if ok else "failed")

    elif cmd == "append":
        text = _read_text(args)
        ok = client.append_page(args.page, text, args.summary, args.minor)
        print("appended" if ok else "failed")

    elif cmd == "list":
        out(client.list_pages(args.namespace, args.depth))

    elif cmd == "search":
        out(client.search_pages(args.query))

    elif cmd == "info":
        out(client.get_page_info(args.page, args.rev, args.author))

    elif cmd == "html":
        result = client.get_page_html(args.page, args.rev)
        _write_output(result, args.output)

    elif cmd == "history":
        out(client.get_page_history(args.page, args.first))

    elif cmd == "links":
        out(client.get_page_links(args.page))

    elif cmd == "backlinks":
        out(client.get_page_backlinks(args.page))

    elif cmd == "recent":
        out(client.get_recent_page_changes(args.timestamp))

    elif cmd == "lock":
        locked = client.lock_pages(args.pages)
        out(locked)
        failed = set(args.pages) - set(locked)
        if failed:
            print(f"Warning: could not lock: {', '.join(sorted(failed))}", file=sys.stderr)

    elif cmd == "unlock":
        unlocked = client.unlock_pages(args.pages)
        out(unlocked)
        failed = set(args.pages) - set(unlocked)
        if failed:
            print(f"Warning: could not unlock: {', '.join(sorted(failed))}", file=sys.stderr)

    elif cmd == "whoami":
        out(client.whoami())

    elif cmd == "list-media":
        out(client.list_media(args.namespace, args.pattern, args.depth))

    elif cmd == "get-media":
        data = client.get_media(args.media, args.rev)
        if args.output:
            outpath = args.output
        else:
            # default: last component of media ID (e.g. "wiki:logo.png" → "logo.png")
            outpath = args.media.split(":")[-1]
        Path(outpath).write_bytes(data)
        print(f"Saved {len(data)} bytes to {outpath}")

    elif cmd == "save-media":
        data = Path(args.file).read_bytes()
        ok = client.save_media(args.media, data, args.overwrite)
        print("uploaded" if ok else "failed")

    elif cmd == "delete-media":
        ok = client.delete_media(args.media)
        print("deleted" if ok else "failed")

    elif cmd == "acl-check":
        level = client.acl_check(args.page, args.user, args.groups)
        labels = {0: "none", 1: "read", 2: "edit", 4: "create", 8: "upload", 16: "delete"}
        print(f"{level} ({labels.get(level, 'unknown')})")

    elif cmd == "version":
        print(client.get_wiki_version())


def main():
    parser = build_parser()
    args = parser.parse_args()

    config = load_config(
        url=args.url,
        user=args.user,
        password=args.password,
        token=args.token,
    )
    client = DokuWikiClient(config, debug=args.debug)

    try:
        run(args, client)
    except DokuWikiError as e:
        print(f"Error: {e.message} (code {e.code})", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
