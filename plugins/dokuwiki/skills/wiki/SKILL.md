---
description: Read and write pages on the team DokuWiki at wiki.ellotecnologia.com
allowed-tools: Bash(python ${CLAUDE_SKILL_DIR}/scripts/dokuwiki.py *)
---

Use `python ${CLAUDE_SKILL_DIR}/scripts/dokuwiki.py` to interact with the DokuWiki at wiki.ellotecnologia.com.

Auth comes from the environment (`DOKUWIKI_URL`, `DOKUWIKI_USER`, `DOKUWIKI_PASS`, or `DOKUWIKI_TOKEN`) or a `.env` file in the working directory. You never need to pass credentials explicitly.

## Commands

| Command | Description |
|---|---|
| `get PAGE` | Get wiki syntax of a page |
| `save PAGE --text "..." [--summary "..."] [--minor]` | Create or replace a page |
| `save PAGE --file path.txt` | Save from file (`-` = stdin) |
| `append PAGE --text "..."` | Append text to a page |
| `list [--namespace NS] [--depth N]` | List pages (depth 0 = all sub-namespaces) |
| `search QUERY` | Full-text search |
| `info PAGE [--author]` | Page metadata (id, rev, size, title) |
| `html PAGE` | Page rendered as HTML |
| `history PAGE` | Revision history |
| `links PAGE` | Links found on a page |
| `backlinks PAGE` | Pages that link to this page |
| `recent [--since TIMESTAMP]` | Recent page changes |
| `lock PAGE [PAGE...]` | Lock pages for editing |
| `unlock PAGE [PAGE...]` | Unlock pages |
| `whoami` | Authenticated user info |
| `list-media [--namespace NS] [--pattern REGEX]` | List media files |
| `get-media MEDIA [--output FILE]` | Download a media file |
| `save-media MEDIA --file FILE [--overwrite]` | Upload a media file |
| `delete-media MEDIA` | Delete a media file |
| `acl-check PAGE [--user USER] [--group GROUP]` | Check permission level |
| `version` | Wiki software version |

## Examples

```bash
# Read a page
python ${CLAUDE_SKILL_DIR}/scripts/dokuwiki.py get start

# List all pages in the "projects" namespace
python ${CLAUDE_SKILL_DIR}/scripts/dokuwiki.py list --namespace projects --depth 0

# Search
python ${CLAUDE_SKILL_DIR}/scripts/dokuwiki.py search "deployment guide"

# Create or update a page (plain-language content only — see Audience and content guidelines below)
python ${CLAUDE_SKILL_DIR}/scripts/dokuwiki.py save projects:mypage --text "= Title =\nContent here." --summary "initial draft"

# Append a section
python ${CLAUDE_SKILL_DIR}/scripts/dokuwiki.py append projects:mypage --text "\n== New Section ==\nMore content."

# Get page metadata
python ${CLAUDE_SKILL_DIR}/scripts/dokuwiki.py info projects:mypage --author

# Delete a page (save empty text)
python ${CLAUDE_SKILL_DIR}/scripts/dokuwiki.py save projects:mypage --text "" --summary "deleted"
```

## Page ID format

DokuWiki uses colon-separated namespaces: `namespace:subnamespace:pagename`. The root page is `start`. Use lowercase with underscores for spaces.

## ACL permission levels

`acl-check` returns an integer: 0=none, 1=read, 2=edit, 4=create, 8=upload, 16=delete.

## Audience and content guidelines

Content written or edited on this wiki is for **software users and support analysts**, not developers. Before saving or appending any page, apply these rules:

- **No technical jargon.** Avoid terms like "API", "endpoint", "null pointer", "stack trace", "regex", "schema", "payload", "thread", "cache invalidation", etc. Use plain language instead (e.g. "the system didn't respond" rather than "the API timed out").
- **No source code.** Do not include code snippets, function names, file paths, class names, SQL queries, config keys, or stack traces — even as examples or for "context". If the source material contains code, summarize what it *does* in plain language instead of quoting it.
- **No internal implementation details.** Don't reference internal architecture, database tables, microservices, branch names, repo names, or internal tooling.
- **Write for a non-technical reader.** Assume the reader is a support analyst or end user troubleshooting an issue or learning a workflow — not a programmer. Prefer step-by-step instructions, screenshots/descriptions of UI, and plain explanations of cause and effect ("this happens because X", not "this happens because the cache TTL expired").
- **Define necessary terms.** If a domain term is unavoidable (e.g. a product feature name), briefly explain what it means in plain words the first time it's used on the page.
- **Rewrite, don't copy.** When pulling content from tickets, code comments, commit messages, or developer chat, rewrite it for the target audience rather than pasting it verbatim.

When in doubt, prefer a simpler, less precise explanation over a technically precise but jargon-heavy one.
