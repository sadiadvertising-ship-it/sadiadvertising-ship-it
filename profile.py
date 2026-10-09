import json
import os
import urllib.request
from xml.sax.saxutils import escape

USER = "sadiadvertising-ship-it"
W = 58

info = [
    ("OS", "macOS 14, iOS, Android"),
    ("Host", "SILOG ZF, Kavy Corp"),
    ("Kernel", "Electronic & Multimedia Engineer"),
    ("IDE", "Cursor, Claude Code, Xcode"),
    None,
    ("Languages.Programming", "TypeScript, Python, SQL"),
    ("Languages.Computer", "HTML, CSS, JSON, YAML, ZPL"),
    ("Languages.Real", "Spanish, English"),
    None,
    ("Stack.Web", "Next.js, React, React Native"),
    ("Stack.Data", "Supabase, PostgreSQL, Vercel"),
    ("Stack.AI", "Claude API, WhatsApp agents"),
    ("Research", "EEG + UX (OpenBCI, MinCiencias)"),
]

contact = [
    ("Email", "dfelipeburbano@gmail.com"),
    ("LinkedIn", "diegoburbano-ai"),
    ("Web", "kavycorp.com/diego"),
]

themes = {
    "dark": dict(bg="#161b22", text="#c9d1d9", key="#ffa657", value="#a5d6ff", cc="#616e7f", add="#3fb950", rm="#f85149"),
    "light": dict(bg="#f6f8fa", text="#24292f", key="#953800", value="#0a3069", cc="#c2cfde", add="#1a7f37", rm="#cf222e"),
}


def gql(query, token, **variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {token}"},
    )
    res = json.load(urllib.request.urlopen(req))
    if "errors" in res:
        raise SystemExit(res["errors"])
    return res["data"]


def fetch(token):
    q = """query($login: String!) { user(login: $login) {
      id
      followers { totalCount }
      repositoriesContributedTo(contributionTypes: [COMMIT, PULL_REQUEST, REPOSITORY]) { totalCount }
      repositories(ownerAffiliations: OWNER, first: 100) {
        totalCount
        nodes { name isPrivate defaultBranchRef { name } }
      }
    } }"""
    u = gql(q, token, login=USER)["user"]
    s = dict(
        repos=u["repositories"]["totalCount"],
        contributed=u["repositories"]["totalCount"] + u["repositoriesContributedTo"]["totalCount"],
        private=sum(r["isPrivate"] for r in u["repositories"]["nodes"]),
        followers=u["followers"]["totalCount"],
        commits=0, add=0, rm=0,
    )
    hq = """query($owner: String!, $name: String!, $id: ID!, $after: String) {
      repository(owner: $owner, name: $name) { defaultBranchRef { target { ... on Commit {
        history(author: {id: $id}, first: 100, after: $after) {
          totalCount
          pageInfo { hasNextPage endCursor }
          nodes { additions deletions }
        }
      } } } } }"""
    for r in u["repositories"]["nodes"]:
        if not r["defaultBranchRef"]:
            continue
        after = None
        while True:
            h = gql(hq, token, owner=USER, name=r["name"], id=u["id"], after=after)
            h = h["repository"]["defaultBranchRef"]["target"]["history"]
            for c in h["nodes"]:
                s["add"] += c["additions"]
                s["rm"] += c["deletions"]
            if after is None:
                s["commits"] += h["totalCount"]
            if not h["pageInfo"]["hasNextPage"]:
                break
            after = h["pageInfo"]["endCursor"]
    return s


def field(keys, value, width=W):
    keys = keys.split(".")
    used = 2 + len(".".join(keys)) + 1 + 2 + len(value)
    segs = [(". ", "cc")]
    for i, k in enumerate(keys):
        if i:
            segs.append((".", None))
        segs.append((k, "key"))
    segs += [(":", None), (" " + "." * (width - used) + " ", "cc"), (value, "value")]
    return segs


def header(title):
    return [(title, None), (" -" + "—" * (W - len(title) - 5) + "-—-", None)]


def build(s):
    rows = [header("diego@burbano")]
    for item in info:
        if item is None:
            rows.append([(". ", "cc")])
            continue
        rows.append(field(*item))
    rows.append([])
    rows.append(header("- Contact"))
    rows += [field(k, v) for k, v in contact]
    rows.append([])
    rows.append(header("- GitHub Stats"))

    n = lambda x: f"{x:,}"
    left = 32
    repos = field("Repos", n(s["repos"]), left - len(f" {{Private: {s['private']}}}"))
    repos += [(" {", None), ("Private", "key"), (": ", None), (str(s["private"]), "value"), ("}", None)]
    repos += [(" | ", None)] + field("Contributed", n(s["contributed"]), W - left - 1)[1:]
    commits = field("Commits", n(s["commits"]), left)
    commits += [(" | ", None)] + field("Followers", n(s["followers"]), W - left - 1)[1:]
    rows += [repos, commits]

    loc = n(s["add"] - s["rm"])
    tail = f" ( {n(s['add'])}++, {n(s['rm'])}-- )"
    lines = field("Lines of Code on GitHub", loc, W - len(tail))
    lines += [(" ( ", None), (n(s["add"]) + "++", "add"), (", ", None), (n(s["rm"]) + "--", "rm"), (" )", None)]
    rows.append(lines)
    return rows


def svg(theme, rows, art):
    t = themes[theme]
    art_lh, info_lh = 11, 21
    height = max(len(art) * art_lh, len(rows) * info_lh) + 30
    out = [
        "<?xml version='1.0' encoding='UTF-8'?>",
        f'<svg xmlns="http://www.w3.org/2000/svg" width="985px" height="{height}px" '
        "font-family=\"ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace\">",
        "<style>",
        "text, tspan {white-space: pre;}",
        *(f".{c} {{fill: {t[c]};}}" for c in ("key", "value", "cc", "add", "rm")),
        "</style>",
        f'<rect width="985px" height="{height}px" fill="{t["bg"]}" rx="15"/>',
        f'<text x="15" y="26" fill="{t["text"]}" font-size="10px">',
    ]
    for i, line in enumerate(art):
        out.append(f'<tspan x="15" y="{26 + i * art_lh}">{escape(line)}</tspan>')
    out.append("</text>")
    out.append(f'<text x="435" y="34" fill="{t["text"]}" font-size="15px">')
    for i, row in enumerate(rows):
        y = 34 + i * info_lh
        parts = [f'<tspan x="435" y="{y}">']
        for text, cls in row:
            attr = f' class="{cls}"' if cls else ""
            parts.append(f"<tspan{attr}>{escape(text)}</tspan>")
        parts.append("</tspan>")
        out.append("".join(parts))
    out.append("</text>")
    out.append("</svg>")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    token = os.environ.get("ACCESS_TOKEN")
    if token:
        s = fetch(token)
        with open(os.path.join(here, "stats.json"), "w") as f:
            json.dump(s, f, indent=2)
    with open(os.path.join(here, "stats.json")) as f:
        s = json.load(f)
    rows = build(s)
    for theme in themes:
        with open(os.path.join(here, "art", f"{theme}.txt")) as f:
            art = f.read().splitlines()
        with open(os.path.join(here, f"{theme}_mode.svg"), "w") as f:
            f.write(svg(theme, rows, art))
