#!/usr/bin/env python3
"""Render self-contained profile cards. Python standard library only."""
import argparse
import base64
import datetime as dt
import html
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
QUERY = '''query($login: String!, $cursor: String) {
  user(login: $login) {
    followers { totalCount }
    repositories(first: 100, after: $cursor, ownerAffiliations: OWNER, privacy: PUBLIC) {
      totalCount nodes { stargazerCount }
      pageInfo { hasNextPage endCursor }
    }
    contributionsCollection { startedAt endedAt totalCommitContributions }
  }
}'''


def graphql(token, username, cursor=None):
    payload = json.dumps({"query": QUERY, "variables": {"login": username, "cursor": cursor}}).encode()
    for attempt in range(3):
        request = urllib.request.Request(
            "https://api.github.com/graphql", data=payload,
            headers={"Authorization": "Bearer " + token, "Content-Type": "application/json",
                     "User-Agent": "sina-profile-card", "Accept": "application/vnd.github+json"})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                result = json.load(response)
            if result.get("errors"):
                raise RuntimeError("GraphQL: " + "; ".join(e.get("message", "unknown error") for e in result["errors"]))
            user = result.get("data", {}).get("user")
            if not user:
                raise RuntimeError("GitHub user not found")
            return user
        except urllib.error.HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise RuntimeError("GitHub HTTP error " + str(error.code)) from None
        except (urllib.error.URLError, TimeoutError):
            if attempt == 2:
                raise RuntimeError("GitHub request failed after three attempts") from None
        time.sleep(2 ** attempt)


def fetch_stats(token, username):
    cursor = None
    stars = 0
    seen = set()
    while True:
        user = graphql(token, username, cursor)
        repos = user["repositories"]
        stars += sum(r["stargazerCount"] for r in repos["nodes"])
        page = repos["pageInfo"]
        if not page["hasNextPage"]:
            break
        cursor = page["endCursor"]
        if not cursor or cursor in seen:
            raise RuntimeError("Invalid GitHub pagination cursor")
        seen.add(cursor)
    return {
        "repos": repos["totalCount"], "stars": stars,
        "followers": user["followers"]["totalCount"],
        "commits": user["contributionsCollection"]["totalCommitContributions"],
        "period_start": user["contributionsCollection"]["startedAt"],
        "period_end": user["contributionsCollection"]["endedAt"],
        "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    }


def esc(value):
    return html.escape(str(value), quote=True)


def validate(config, stats):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}", config["username"]):
        raise ValueError("Invalid GitHub username")
    for theme in config["themes"].values():
        if not all(re.fullmatch(r"#[0-9a-fA-F]{6}", color) for color in theme.values()):
            raise ValueError("Theme colors must be six-digit hex")
    for field in config["fields"]:
        if len(field["label"]) > 9 or not field["lines"]:
            raise ValueError("Field labels must have at most 9 characters and nonempty lines")
        if any(len(line) > 42 for line in field["lines"]):
            raise ValueError("Split long field values into lines of at most 42 characters")
    for key in ("repos", "stars", "commits", "followers"):
        if stats.get(key) is not None and (type(stats[key]) is not int or stats[key] < 0):
            raise ValueError("Invalid statistic: " + key)


def render(config, stats, art, theme_name, mobile=False):
    palette = config["themes"][theme_name]
    width = 600 if mobile else 1200
    start_y = 340 if mobile else 202
    row_gap = 30
    field_gap = 17
    row_height = sum(len(f["lines"]) * row_gap + field_gap for f in config["fields"])
    stats_y = start_y + row_height + 28
    height = stats_y + 220
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
             '<title id="title">' + esc(config["heading"]) + '</title>',
             '<desc id="desc">' + esc(config["alt"]) + '</desc>',
             f'<rect x="1" y="1" width="{width-2}" height="{height-2}" rx="22" fill="{palette["background"]}" stroke="{palette["border"]}" stroke-width="2"/>']

    def text(x, y, value, size=20, color="foreground", weight=400):
        parts.append(f'<text x="{x}" y="{y}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="{size}" font-weight="{weight}" fill="{palette[color]}">{esc(value)}</text>')

    def line(x, y, end):
        parts.append(f'<path d="M{x} {y} H{end}" stroke="{palette["border"]}"/>')

    # Keep the approved character-art portrait unchanged. The nested SVG crops
    # the approved illustration; all profile text and statistics are real SVG text.
    px, py, pw, ph = (24, 24, 180, 268) if mobile else (24, 44, 360, height-84)
    parts.append(f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="15" fill="#0a1119"/>')
    parts.append(f'<svg x="{px}" y="{py}" width="{pw}" height="{ph}" viewBox="40 80 590 850" overflow="hidden" preserveAspectRatio="xMidYMid meet"><defs><clipPath id="portrait-crop"><rect x="40" y="80" width="590" height="850"/></clipPath></defs><image width="1536" height="1024" clip-path="url(#portrait-crop)" href="data:image/png;base64,{art}"/></svg>')
    hx, hy = (228, 105) if mobile else (430, 88)
    text(hx, hy, config["heading"], 32 if mobile else 44, weight=600)
    text(hx, hy+40, "@"+config["username"], 20 if mobile else 22, color="muted")
    if mobile:
        text(hx, hy+94, "~/profile", 18, color="muted")
    x, value_x = (28, 178) if mobile else (430, 602)
    y = start_y
    for field in config["fields"]:
        text(x, y, field["label"], 20, "accent", 600)
        dots_x = x + max(110, len(field["label"])*12+12)
        parts.append(f'<path d="M{dots_x} {y-6} H{value_x-16}" stroke="{palette["muted"]}" stroke-dasharray="1 8" stroke-linecap="round"/>')
        for value in field["lines"]:
            # On mobile use full-width values for long lines, avoiding tiny type.
            if mobile and len(value) > 32:
                raise ValueError("Mobile field line exceeds 32 characters")
            text(value_x, y, value, 20)
            y += row_gap
        y += field_gap
    line(x, stats_y-24, width-32)
    text(x, stats_y+15, config["stats_title"], 30, "accent", 600)
    for index, key in enumerate(("repos", "stars", "commits", "followers")):
        col, row = index % 2, index // 2
        sx = x + col * (280 if mobile else 365)
        sy = stats_y+65+row*47
        label = config["stats_labels"][key]
        text(sx, sy, label, 20, "accent", 600)
        number = stats.get(key)
        value = "—" if number is None else format(number, ",")
        text(sx+130, sy, value, 25, weight=500)
    note = config["stats_note"]
    if mobile:
        text(x, stats_y+156, "Public repos & stars", 16, "muted")
        text(x, stats_y+180, "Commits: last 12 months", 16, "muted")
    else:
        text(x, stats_y+157, note, 16, "muted")
    stamp = stats.get("updated_at")
    updated = config["updated_label"] + " " + stamp[:10] + " UTC" if stamp else config["pending_label"]
    text(x, stats_y+204 if mobile else stats_y+185, updated, 15, "muted")
    parts.append('</svg>')
    return "\n".join(parts)+"\n"


def readme(config):
    alt = esc(config["alt"])
    lines = ['<picture>',
      '  <source media="(prefers-color-scheme: dark) and (max-width: 600px)" srcset="assets/dark_mobile.svg">',
      '  <source media="(max-width: 600px)" srcset="assets/light_mobile.svg">',
      '  <source media="(prefers-color-scheme: dark)" srcset="assets/dark_mode.svg">',
      f'  <img src="assets/light_mode.svg" width="1200" alt="{alt}">', '</picture>', '',
      config["readme_summary"], '', '<details>', '<summary>'+esc(config["details_label"])+ '</summary>', '']
    for item in config["projects"]:
        lines.append('- **'+item["name"]+'** — '+item["description"])
    lines += ['', config["stats_explanation"], '', '</details>', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="Render the last successful snapshot without network")
    args = parser.parse_args()
    config = json.loads((ROOT/"config.json").read_text())
    cache = ROOT/"assets/stats.json"
    if args.offline:
        stats = json.loads(cache.read_text()) if cache.exists() else {}
    else:
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            raise RuntimeError("GITHUB_TOKEN is required; use --offline to render the saved snapshot")
        stats = fetch_stats(token, config["username"])
    validate(config, stats)
    art = base64.b64encode((ROOT/"assets/approved-art.png").read_bytes()).decode("ascii")
    # Prepare all output before writing, so invalid configuration cannot publish a partial card.
    outputs = {ROOT/"README.md": readme(config)}
    for theme in ("dark", "light"):
        for mobile in (False, True):
            name = theme + ("_mobile.svg" if mobile else "_mode.svg")
            outputs[ROOT/"assets"/name] = render(config, stats, art, theme, mobile)
    if not args.offline:
        outputs[cache] = json.dumps(stats, indent=2)+"\n"
    for path, value in outputs.items():
        temporary = path.with_suffix(path.suffix+".tmp")
        temporary.write_text(value, encoding="utf-8")
        temporary.replace(path)
    print("Rendered dark/light desktop/mobile cards and README.")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, KeyError, OSError) as error:
        print("Profile update failed: " + str(error), file=sys.stderr)
        sys.exit(1)
