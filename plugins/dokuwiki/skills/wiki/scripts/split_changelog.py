#!/usr/bin/env python3
"""Split a yearly changelog page into monthly subpages."""

import re
import subprocess
import sys
from collections import OrderedDict

DOKUWIKI = "python .claude/skills/wiki/scripts/dokuwiki.py"

MESES = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}

def dw(*args):
    result = subprocess.run(
        DOKUWIKI.split() + list(args),
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"Error: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return result.stdout

def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <year>", file=sys.stderr)
        print(f"  e.g. {sys.argv[0]} 2013", file=sys.stderr)
        sys.exit(1)

    year = sys.argv[1]
    base_page = f"changelog:ello:{year}"

    # Get current page
    content = dw("get", base_page)

    # Split into entries by "==== DD/MM/YYYY -"
    entry_pattern = re.compile(
        r'^(?:==== )?(\S+)/(\d{2})/(\d{4}) - .*?$',
        re.MULTILINE
    )

    entries = list(entry_pattern.finditer(content))

    if not entries:
        print(f"No entries found in {base_page}", file=sys.stderr)
        sys.exit(1)

    # Group by month
    months = OrderedDict()
    for i, match in enumerate(entries):
        month_int = int(match.group(2))
        start_pos = match.start()
        if i + 1 < len(entries):
            end_pos = entries[i + 1].start()
        else:
            end_pos = len(content)
        entry_text = content[start_pos:end_pos]
        months.setdefault(month_int, []).append(entry_text)

    # Save each month
    for month_int, entries_list in months.items():
        month_str = f"{month_int:02d}"
        page = f"{base_page}:{month_str}"

        page_content = f"~~NOTOC~~\n\n"
        page_content += f"====== Registro de Atualizações - {MESES[month_int]} de {year} ======\n\n"
        page_content += f"  * [[{base_page}|Voltar para {year}]]\n\n"
        page_content += "".join(entries_list)

        print(f"Saving {page}...")
        result = subprocess.run(
            DOKUWIKI.split() + ["save", page, "--file", "-"],
            input=page_content,
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"Error saving {page}: {result.stderr}", file=sys.stderr)
            sys.exit(1)
        print(f"  -> {result.stdout.strip()}")

    # Update main page with links
    main_content = "~~NOTOC~~\n\n"
    main_content += f"====== Registro de Atualizações {year} ======\n\n"
    for month_int in reversed(sorted(months.keys())):
        month_str = f"{month_int:02d}"
        main_content += f"  * [[{base_page}:{month_str}|{MESES[month_int]}]]\n"

    print(f"Saving {base_page} (main page)...")
    result = subprocess.run(
        DOKUWIKI.split() + ["save", base_page, "--file", "-"],
        input=main_content,
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"Error saving main page: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    print(f"  -> {result.stdout.strip()}")

    print(f"\nDone! Created {len(months)} monthly pages:")
    for month_int in sorted(months.keys()):
        print(f"  {base_page}:{month_int:02d}")

if __name__ == "__main__":
    main()
