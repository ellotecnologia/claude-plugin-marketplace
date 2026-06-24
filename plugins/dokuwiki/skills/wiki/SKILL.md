---
description: Read and write pages on the team DokuWiki at wiki.ellotecnologia.com
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/dokuwiki.py *)
---

Use `python3 ${CLAUDE_SKILL_DIR}/scripts/dokuwiki.py` to interact with the DokuWiki at wiki.ellotecnologia.com.

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
python3 ${CLAUDE_SKILL_DIR}/scripts/dokuwiki.py get start

# List all pages in the "projects" namespace
python3 ${CLAUDE_SKILL_DIR}/scripts/dokuwiki.py list --namespace projects --depth 0

# Search
python3 ${CLAUDE_SKILL_DIR}/scripts/dokuwiki.py search "deployment guide"

# Create or update a page
python3 ${CLAUDE_SKILL_DIR}/scripts/dokuwiki.py save projects:mypage --text "= Title =\nContent here." --summary "initial draft"

# Append a section
python3 ${CLAUDE_SKILL_DIR}/scripts/dokuwiki.py append projects:mypage --text "\n== New Section ==\nMore content."

# Get page metadata
python3 ${CLAUDE_SKILL_DIR}/scripts/dokuwiki.py info projects:mypage --author

# Delete a page (save empty text)
python3 ${CLAUDE_SKILL_DIR}/scripts/dokuwiki.py save projects:mypage --text "" --summary "deleted"
```

## Page ID format

DokuWiki uses colon-separated namespaces: `namespace:subnamespace:pagename`. The root page is `start`. Use lowercase with underscores for spaces.

## ACL permission levels

`acl-check` returns an integer: 0=none, 1=read, 2=edit, 4=create, 8=upload, 16=delete.
