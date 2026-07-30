#!/usr/bin/env python3
"""生成扁平、camo 安全的 GitHub 统计 SVG（无 foreignObject / script）。

依赖：仅 Python 标准库。
环境变量：
  GITHUB_TOKEN  GitHub API token（workflow 里用 secrets.GITHUB_TOKEN）
  METRICS_USER  目标用户名（默认 tobyberry666）
输出：./github-metrics.svg
"""
import os
import json
import urllib.request

TOKEN = os.environ.get("GITHUB_TOKEN", "")
USER = os.environ.get("METRICS_USER", "tobyberry666")

LANG_COLORS = {
    "Python": "#3572A5", "JavaScript": "#f1e05a", "TypeScript": "#3178c6",
    "Java": "#b07219", "HTML": "#e34c26", "CSS": "#563d7c", "C": "#555555",
    "C++": "#f34b7d", "C#": "#178600", "Go": "#00ADD8", "Rust": "#dea584",
    "Shell": "#89e051", "Vue": "#41b883", "Swift": "#F05138", "Kotlin": "#A97BFF",
    "Ruby": "#701516", "PHP": "#4F5D95", "Dockerfile": "#384d54",
    "Jupyter Notebook": "#DA5B0B", "Lua": "#000080", "Dart": "#00B4AB",
    "Scala": "#c22d40", "Objective-C": "#438eff", "PowerShell": "#012456",
    "Makefile": "#427819", "Cuda": "#3A4E3A", "Zig": "#ec915c",
}
PALETTE = ["#58a6ff", "#3fb950", "#f778ba", "#d29922", "#a371f7", "#ff7b72"]


def api(url, method="GET", data=None):
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "metrics-svg")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def fmt(n):
    return f"{n:,}"


# ---------- 拉数据 ----------
u = api(f"https://api.github.com/users/{USER}")
name = u.get("name") or USER
followers = u["followers"]
following = u["following"]
public_repos = u["public_repos"]

repos = api(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner&sort=updated")
stars = sum(r.get("stargazers_count", 0) for r in repos)

lang_bytes = {}
for r in repos:
    try:
        langs = api(r["languages_url"])
        for k, v in langs.items():
            lang_bytes[k] = lang_bytes.get(k, 0) + v
    except Exception:
        pass
top = sorted(lang_bytes.items(), key=lambda x: -x[1])[:6]
total = sum(lang_bytes.values()) or 1
langs = [(k, round(v / total * 100, 1)) for k, v in top]

try:
    q = json.dumps({"query": "query{viewer{contributionsCollection{totalCommitContributions restrictedContributionsCount}}}" }).encode()
    resp = api("https://api.github.com/graphql", method="POST", data=q)
    cc = resp["data"]["viewer"]["contributionsCollection"]
    commits = cc["totalCommitContributions"] + cc["restrictedContributionsCount"]
except Exception:
    commits = 0

stats = [
    ("总提交 Commits", commits),
    ("星标 Stars", stars),
    ("关注者 Followers", followers),
    ("正在关注 Following", following),
    ("仓库 Repositories", public_repos),
]

# ---------- 画 SVG ----------
BG = "#0d1117"; CARD = "#161b22"; BORDER = "#30363d"
TEXT = "#e6edf3"; MUTED = "#7d8590"; ACCENT = "#58a6ff"
W, H = 840, 250
p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
      f'font-family="Segoe UI, Helvetica, Arial, sans-serif">']


def card(x, y, w, h, title):
    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{CARD}" stroke="{BORDER}" stroke-width="1"/>'
    # 标题栏：只圆上方（先画圆角整块，再用方块盖住下方圆角）
    s += f'<rect x="{x}" y="{y}" width="{w}" height="44" rx="12" fill="#1f2630"/>'
    s += f'<rect x="{x}" y="{y+22}" width="{w}" height="22" fill="#1f2630"/>'
    s += f'<text x="{x+18}" y="{y+28}" fill="{TEXT}" font-size="16" font-weight="600">{esc(title)}</text>'
    return s


p.append(card(10, 10, 400, 230, "GitHub 统计 · Stats"))
p.append(card(430, 10, 400, 230, "常用语言 · Languages"))

# 统计行
ax, ay = 10, 10
for i, (label, val) in enumerate(stats):
    y = ay + 72 + i * 32
    p.append(f'<circle cx="{ax+24}" cy="{y-4}" r="4" fill="{ACCENT}"/>')
    p.append(f'<text x="{ax+38}" y="{y}" fill="{MUTED}" font-size="14">{esc(label)}</text>')
    p.append(f'<text x="{ax+400-18}" y="{y}" fill="{TEXT}" font-size="15" font-weight="700" text-anchor="end">{fmt(val)}</text>')

# 语言条
bx, by = 430, 10
for i, (lang, pct) in enumerate(langs):
    y = by + 72 + i * 28
    color = LANG_COLORS.get(lang, PALETTE[i % len(PALETTE)])
    p.append(f'<text x="{bx+18}" y="{y}" fill="{TEXT}" font-size="14">{esc(lang)}</text>')
    p.append(f'<text x="{bx+400-18}" y="{y}" fill="{MUTED}" font-size="13" text-anchor="end">{pct}%</text>')
    p.append(f'<rect x="{bx+18}" y="{y+6}" width="{400-36}" height="10" rx="5" fill="#21262d"/>')
    fw = max(2.0, (400 - 36) * pct / 100.0)
    p.append(f'<rect x="{bx+18}" y="{y+6}" width="{fw:.1f}" height="10" rx="5" fill="{color}"/>')

p.append("</svg>")
svg = "\n".join(p)
with open("github-metrics.svg", "w", encoding="utf-8") as f:
    f.write(svg)
print(f"written github-metrics.svg ({len(svg)} bytes, {len(langs)} languages, {commits} commits)")
