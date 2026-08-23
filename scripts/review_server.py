#!/usr/bin/env python3
"""
Local transcript review UI for the OneTyler Cloud Living knowledge repo.

Serves a browser interface on http://127.0.0.1:7777 for reading collected
transcripts, recording verdicts and corrections, and writing them straight back
into the repo's markdown files so the result is an ordinary reviewable diff.

Stdlib only — no pip install, no build step. Binds to loopback only.

    python3 scripts/review_server.py
    python3 scripts/review_server.py --port 7778 --no-browser

Everything it writes lands in transcripts/*.md. Commit and open a PR as normal,
or use the Git panel in the UI.
"""
import argparse, html, json, re, subprocess, sys, webbrowser
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

REPO = Path(__file__).resolve().parent.parent
TDIR = REPO / "transcripts"
STATUS = REPO / "scripts" / "review_status.py"

CONTRIB = REPO / "contributors.json"


def contributors():
    """GitHub usernames allowed in the `reviewer` field. Read fresh each request so
    adding someone to contributors.json takes effect without a server restart."""
    try:
        d = json.loads(CONTRIB.read_text(encoding="utf-8"))
        return [c["github"] for c in d.get("contributors", []) if c.get("github")]
    except Exception:
        return []


# Ordered so rewritten frontmatter keeps a stable, diff-friendly shape.
SOURCE_KEYS = ["conversation_id", "answered_by", "date", "exchanges",
               "dropped_sample_prompts", "foundry_feedback", "user_comments"]
REVIEW_KEYS = ["review_status", "reviewer", "routing_verdict", "reassign_to",
               "answer_verdict", "diagnosis", "fix_target", "kb_action",
               "kb_files", "action_status", "notes"]

CHOICES = {
    "review_status":   ["pending", "reviewed", "excluded"],
    "routing_verdict": ["", "correct", "wrong-agent", "ambiguous"],
    "reassign_to":     ["", "ops-center", "bp-general", "sac", "identity", "team"],
    "answer_verdict":  ["", "good", "incomplete", "wrong", "stale", "refused"],
    "diagnosis":       ["", "n-a", "no-search", "search-empty", "search-irrelevant",
                        "retrieved-ok-answered-badly", "routing-only"],
    "fix_target":      ["", "none", "knowledge-file", "agent-instructions",
                        "team-routing", "sample-prompts"],
    "kb_action":       ["", "none", "add", "update", "split"],
    "action_status":   ["", "open", "applied", "wontfix"],
}
HELP = {
    "reviewer":        "Your GitHub username. Add yourself to contributors.json first.",
    "routing_verdict": "Did the right sub-agent handle this?",
    "reassign_to":     "Which agent should have. Only if wrong-agent.",
    "answer_verdict":  "Quality of the answer that was given.",
    "diagnosis":       "WHY it went wrong — read the 'Tools called' line on each exchange.",
    "fix_target":      "Where the fix belongs. Pick agent-instructions or team-routing when "
                       "no knowledge file needs to change.",
    "kb_action":       "What must happen to the corpus. 'none' is a valid, useful answer.",
    "kb_files":        "Comma-separated paths, e.g. Knowledge-OpsCenter/Misc-Links.md",
    "action_status":   "Claude sets this to 'applied' once the change ships.",
    "notes":           "One line. Long-form goes in Proposed fix below.",
}


# ---------------------------------------------------------------- file I/O
def tfiles():
    return sorted(f for f in TDIR.rglob("*.md") if f.name not in ("INDEX.md", "README.md"))


def parse(p):
    txt = p.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", txt, re.S)
    if not m:
        return None, txt
    fm = {}
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    return fm, m.group(2)


def exchanges_of(body):
    """[(n, tools, question, answer, review_text)] in document order."""
    out = []
    for m in re.finditer(r"## Exchange (\d+)\n(.*?)(?=\n## Exchange |\n---\n\n## Proposed fix|\Z)",
                         body, re.S):
        n, blk = m.group(1), m.group(2)
        tools = (re.search(r"\*\*Tools called:\*\* (.*)", blk) or [None, ""])[1].strip()
        q = (re.search(r"\*\*Q:\*\*\n\n((?:> .*\n?)+)", blk) or [None, ""])[1]
        q = re.sub(r"^> ?", "", q, flags=re.M).strip()
        a = (re.search(r"\*\*A:\*\*\n\n```markdown\n(.*?)\n```", blk, re.S) or [None, ""])[1]
        rv = (re.search(r"<!-- review:\d+ -->\n(.*?)<!-- /review:\d+ -->", blk, re.S) or [None, ""])[1]
        out.append((n, tools, q, a, rv.strip()))
    return out


def first_question(body, words=14):
    """Opening words of the first real question — the only reliable way to tell
    transcripts apart in a list, since filenames are just dates and hashes."""
    m = re.search(r"\*\*Q:\*\*\n\n((?:> .*\n?)+)", body)
    if not m:
        return ""
    q = re.sub(r"\s+", " ", re.sub(r"^> ?", "", m.group(1), flags=re.M)).strip()
    w = q.split()
    return " ".join(w[:words]) + ("…" if len(w) > words else "")


def proposed_of(body):
    m = re.search(r"<!-- proposed-fix -->\n(.*?)<!-- /proposed-fix -->", body, re.S)
    return m.group(1).strip() if m else ""


def save(p, fm_new, ex_reviews, proposed):
    fm, body = parse(p)
    if fm is None:
        raise ValueError("no frontmatter")
    fm.update({k: (v or "").replace("\n", " ").strip() for k, v in fm_new.items()})

    L = ["---"]
    for k in SOURCE_KEYS:
        if k in fm:
            L.append(f"{k}: {fm[k]}")
    L += ["", "# ---- review fields: edit these ----"]
    for k in REVIEW_KEYS:
        L.append(f"{k}: {fm.get(k, '')}".rstrip())
    for k, v in fm.items():                                  # keep anything unrecognised
        if k not in SOURCE_KEYS and k not in REVIEW_KEYS:
            L.append(f"{k}: {v}")
    L.append("---")

    for n, txt in ex_reviews.items():
        body = re.sub(rf"(<!-- review:{n} -->\n).*?(<!-- /review:{n} -->)",
                      lambda m: m.group(1) + (txt.strip() + "\n" if txt.strip() else "") + m.group(2),
                      body, flags=re.S)
    body = re.sub(r"(<!-- proposed-fix -->\n).*?(<!-- /proposed-fix -->)",
                  lambda m: m.group(1) + (proposed.strip() + "\n" if proposed.strip() else "") + m.group(2),
                  body, flags=re.S)
    p.write_text("\n".join(L) + "\n" + body, encoding="utf-8")


def refresh_index():
    try:
        subprocess.run([sys.executable, str(STATUS)], cwd=REPO,
                       capture_output=True, timeout=60)
    except Exception:
        pass


def git(*args, timeout=60):
    r = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, timeout=timeout)
    return r.returncode, (r.stdout + r.stderr).strip()


# ---------------------------------------------------------------- rendering
CSS = """
*{box-sizing:border-box}body{margin:0;font:14px/1.55 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
color:#1a1d21;background:#f5f6f8}
a{color:#1c5fbf}header{background:#16203a;color:#fff;padding:12px 20px;display:flex;gap:18px;align-items:center;
position:sticky;top:0;z-index:10}header b{font-size:15px}header a{color:#9fc4ff;text-decoration:none}
.wrap{max-width:1180px;margin:0 auto;padding:20px}
.bar{background:#fff;border:1px solid #dfe3e8;border-radius:8px;padding:12px 16px;margin-bottom:16px}
table{width:100%;border-collapse:collapse;background:#fff;border:1px solid #dfe3e8;border-radius:8px;overflow:hidden}
th,td{padding:8px 10px;text-align:left;border-bottom:1px solid #eef1f4;font-size:13px;white-space:nowrap}
th{background:#f0f2f5;font-weight:600}tr:hover td{background:#fafbfc}
.pill{display:inline-block;padding:1px 8px;border-radius:10px;font-size:11px;font-weight:600}
.pending{background:#fff3d6;color:#8a5a00}.reviewed{background:#dcf5e4;color:#0f6b34}
.excluded{background:#e8e9ec;color:#5b6470}
.bad{background:#fde4e4;color:#a11}.warn{background:#ffeccc;color:#8a4b00}
.card{background:#fff;border:1px solid #dfe3e8;border-radius:8px;padding:16px;margin-bottom:14px}
.q{background:#eef4ff;border-left:3px solid #2b6cb0;padding:10px 12px;border-radius:4px;white-space:pre-wrap}
.a{background:#fafbfc;border:1px solid #e8ebef;border-radius:4px;padding:10px 12px;max-height:340px;
overflow:auto;white-space:pre-wrap;font:12px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace}
.tools{font-size:12px;color:#5b6470;margin:6px 0}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(215px,1fr));gap:12px}
label{display:block;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.03em;color:#4a5260;margin-bottom:3px}
.hint{font-size:11px;color:#6b7280;font-weight:400;text-transform:none;letter-spacing:0}
select,input,textarea{width:100%;padding:6px 8px;border:1px solid #cbd2da;border-radius:5px;font-size:13px;
font-family:inherit;background:#fff}
textarea{min-height:88px;resize:vertical}
button{background:#1c5fbf;color:#fff;border:0;padding:8px 16px;border-radius:6px;font-size:13px;font-weight:600;cursor:pointer}
button:hover{background:#174b98}button.sec{background:#e6e9ee;color:#26303d}button.sec:hover{background:#d7dce3}
.toast{position:fixed;bottom:18px;right:18px;background:#0f6b34;color:#fff;padding:10px 16px;border-radius:6px;
opacity:0;transition:.25s;z-index:50}.toast.on{opacity:1}
.nav{display:flex;justify-content:space-between;margin:16px 0}
td.qcell{white-space:normal;max-width:430px;min-width:300px}
.deleg{font-size:11px;color:#7a5cbf;font-weight:600}
pre.out{background:#10151f;color:#d6dde8;padding:10px;border-radius:6px;font-size:12px;overflow:auto;max-height:240px}
"""

JS = """
async function post(url,body){const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},
body:JSON.stringify(body)});return r.json()}
function toast(m,ok=true){const t=document.getElementById('toast');t.textContent=m;
t.style.background=ok?'#0f6b34':'#a11';t.classList.add('on');setTimeout(()=>t.classList.remove('on'),2600)}
async function saveDoc(path,then){const fields={},ex={};
document.querySelectorAll('[data-fm]').forEach(e=>fields[e.dataset.fm]=e.value);
document.querySelectorAll('[data-ex]').forEach(e=>ex[e.dataset.ex]=e.value);
const proposed=(document.getElementById('proposed')||{}).value||'';
const r=await post('/save',{path,fields,exchanges:ex,proposed});
if(r.ok){toast('Saved to '+r.path);if(then)location.href=then}else toast(r.error||'Save failed',false)}
async function markAndNext(path,next){document.querySelector('[data-fm=review_status]').value='reviewed';
await saveDoc(path,next)}
async function gitDo(action){const branch=(document.getElementById('branch')||{}).value||'';
const msg=(document.getElementById('cmsg')||{}).value||'';
const r=await post('/git',{action,branch,message:msg});
document.getElementById('gitout').textContent=r.output||'(no output)';toast(r.ok?action+' ok':action+' failed',r.ok)}
"""


def page(title, inner):
    return f"""<!doctype html><meta charset=utf-8><title>{html.escape(title)}</title>
<style>{CSS}</style><header><b>Transcript Review</b>
<a href="/">All transcripts</a><a href="/git">Git &amp; PR</a>
<span style="margin-left:auto;font-size:12px;opacity:.7">{html.escape(str(REPO.name))}</span></header>
<div class=wrap>{inner}</div><div class=toast id=toast></div><script>{JS}</script>"""


def list_page():
    rows, counts = [], Counter()
    for f in tfiles():
        fm, body = parse(f)
        if fm is None:
            continue
        st = fm.get("review_status", "pending") or "pending"
        counts[st] += 1
        counts["total"] += 1
        rel = f.relative_to(TDIR).as_posix()
        fb = fm.get("foundry_feedback", "none")
        deleg = fm.get("delegated_to", "")
        short = ", ".join(a.replace(" Assistant", "").replace(" Agent", "")
                          for a in deleg.split(", ") if a) if deleg else ""
        rows.append(
            f"<tr><td class=qcell title=\"{html.escape(first_question(body, 40))}\">"
            f"<a href='/t/{html.escape(rel)}'>{html.escape(first_question(body))}</a></td>"
            f"<td>{html.escape(fm.get('answered_by',''))}"
            f"{'<div class=deleg>&rarr; '+html.escape(short)+'</div>' if short else ''}</td>"
            f"<td>{html.escape((fm.get('date','') or '')[:10])}</td>"
            f"<td>{html.escape(fm.get('exchanges',''))}</td>"
            f"<td>{'<span class=pill.warn>'+html.escape(fb)+'</span>' if fb not in ('none','') else ''}</td>"
            f"<td><span class='pill {st}'>{html.escape(st)}</span></td>"
            f"<td>{html.escape(fm.get('routing_verdict',''))}"
            f"{'&rarr;'+html.escape(fm['reassign_to']) if fm.get('reassign_to') else ''}</td>"
            f"<td>{html.escape(fm.get('answer_verdict',''))}</td>"
            f"<td>{html.escape(fm.get('diagnosis',''))}</td>"
            f"<td>{html.escape(fm.get('fix_target',''))}</td></tr>")
    done, tot = counts["reviewed"], counts["total"]
    pct = (100 * done // tot) if tot else 0
    bar = (f"<div class=bar><b>{done} / {tot} reviewed</b> ({pct}%) &nbsp;·&nbsp; "
           f"{counts['pending']} pending &nbsp;·&nbsp; "
           f"<a href='/git'>commit &amp; open a PR &rarr;</a></div>")
    return page("Transcripts", bar + "<table><tr><th>First question<th>Handled by<th>Date<th>Ex"
                "<th>Foundry FB<th>Status<th>Routing<th>Answer<th>Diagnosis<th>Fix target</tr>"
                + "".join(rows) + "</table>")


def field(k, val):
    hint = f"<span class=hint> — {html.escape(HELP[k])}</span>" if k in HELP else ""
    lab = f"<label>{k.replace('_',' ')}{hint}</label>"
    if k == "reviewer":
        people = contributors()
        if not people:
            return (f"<div>{lab}<input data-fm=reviewer value=\"{html.escape(val)}\" "
                    f"placeholder='contributors.json is empty or unreadable'></div>")
        opts = "".join(f"<option{' selected' if o == val else ''}>{html.escape(o)}</option>"
                       for o in [""] + people)
        stale = ("<div class=hint style='color:#a11'>current value "
                 f"'{html.escape(val)}' is not in contributors.json</div>"
                 if val and val not in people else "")
        return f"<div>{lab}<select data-fm=reviewer>{opts}</select>{stale}</div>"
    if k in CHOICES:
        opts = "".join(f"<option{' selected' if o == val else ''}>{html.escape(o)}</option>"
                       for o in CHOICES[k])
        return f"<div>{lab}<select data-fm={k}>{opts}</select></div>"
    return f"<div>{lab}<input data-fm={k} value=\"{html.escape(val)}\"></div>"


def detail_page(rel):
    p = (TDIR / rel).resolve()
    if not str(p).startswith(str(TDIR.resolve())) or not p.is_file():
        return None
    fm, body = parse(p)
    if fm is None:
        return page("error", "<div class=card>No frontmatter in this file.</div>")
    order = [f.relative_to(TDIR).as_posix() for f in tfiles()]
    i = order.index(rel) if rel in order else 0
    prev_ = f"/t/{order[i-1]}" if i > 0 else ""
    next_ = f"/t/{order[i+1]}" if i < len(order) - 1 else "/"

    head = (f"<div class=bar><b>{html.escape(fm.get('answered_by',''))}</b> · "
            f"{html.escape(fm.get('date',''))} · {html.escape(fm.get('exchanges','0'))} exchange(s)"
            + (f" · <span class='pill warn'>Foundry: {html.escape(fm['foundry_feedback'])}</span>"
               if fm.get("foundry_feedback") not in ("none", "", None) else "")
            + (f" · <i>{html.escape(fm['dropped_sample_prompts'])} canned prompt(s) omitted</i>"
               if fm.get("dropped_sample_prompts", "0") not in ("0", "") else "")
            + (f"<br><b>Delegated to:</b> {html.escape(fm['delegated_to'])}"
               + (f" <span class=hint>({html.escape(fm.get('orchestration',''))})</span>"
                  if fm.get("orchestration") else "")
               if fm.get("delegated_to") else "")
            + f"<br><small style='color:#6b7280'>{html.escape(rel)} · "
              f"conversation {html.escape(fm.get('conversation_id',''))}</small></div>")

    parts = [head, "<div class=card><div class=grid>"
             + "".join(field(k, fm.get(k, "")) for k in REVIEW_KEYS) + "</div></div>"]

    for n, tools, q, a, rv in exchanges_of(body):
        none_tools = "none" in tools.lower()
        parts.append(
            f"<div class=card><b>Exchange {n}</b>"
            f"<div class=tools>Tools called: "
            f"{'<span class=pill.bad>none — answered without searching</span>' if none_tools else html.escape(tools)}</div>"
            f"<div class=q>{html.escape(q)}</div>"
            f"<div style='margin:8px 0 4px;font-size:12px;color:#4a5260'><b>Answer given</b></div>"
            f"<div class=a>{html.escape(a)}</div>"
            f"<label style='margin-top:10px'>Correction — what it should have said"
            f"<span class=hint> — the most useful thing you can write</span></label>"
            f"<textarea data-ex={n}>{html.escape(rv)}</textarea></div>")

    parts.append("<div class=card><label>Proposed fix<span class=hint> — what changes so this is "
                 "right next time? For an instructions or routing fix, say exactly what to add or "
                 "reword. This is committed even when no knowledge file changes.</span></label>"
                 f"<textarea id=proposed style='min-height:130px'>{html.escape(proposed_of(body))}</textarea></div>")

    parts.append(
        f"<div class=nav><div>{f'<a href=\"{prev_}\"><button class=sec>&larr; Previous</button></a>' if prev_ else ''}</div>"
        f"<div style='display:flex;gap:8px'>"
        f"<button class=sec onclick=\"saveDoc('{html.escape(rel)}')\">Save</button>"
        f"<button onclick=\"markAndNext('{html.escape(rel)}','{next_}')\">Mark reviewed &amp; next &rarr;</button>"
        f"</div></div>")
    return page(f"{fm.get('answered_by','')} {rel}", "".join(parts))


def git_page():
    _, branch = git("rev-parse", "--abbrev-ref", "HEAD")
    _, st = git("status", "--porcelain", "--", "transcripts")
    changed = [l for l in st.splitlines() if l.strip()]
    body = (f"<div class=bar>Branch: <b>{html.escape(branch)}</b> · "
            f"{len(changed)} changed file(s) under transcripts/</div>"
            "<div class=card><label>New branch name</label>"
            f"<input id=branch value='review/{branch if branch.startswith('review/') else 'batch'}'>"
            "<label style='margin-top:10px'>Commit message</label>"
            "<input id=cmsg value='Review transcripts: verdicts and proposed fixes'>"
            "<div style='margin-top:12px;display:flex;gap:8px;flex-wrap:wrap'>"
            "<button class=sec onclick=\"gitDo('branch')\">Create branch</button>"
            "<button class=sec onclick=\"gitDo('commit')\">Stage &amp; commit transcripts/</button>"
            "<button onclick=\"gitDo('pr')\">Push &amp; open PR</button>"
            "<button class=sec onclick=\"gitDo('diff')\">Show diff</button></div></div>"
            "<div class=card><b>Output</b><pre class=out id=gitout>"
            + html.escape("\n".join(changed) or "(no changes under transcripts/)")
            + "</pre></div>"
            "<div class=card><small>Reviews are committed even when no knowledge file changes — "
            "a verdict of <code>fix_target: agent-instructions</code> with no <code>kb_files</code> "
            "is a complete, mergeable contribution.</small></div>")
    return page("Git & PR", body)


# ---------------------------------------------------------------- server
class H(BaseHTTPRequestHandler):
    server_version = "TranscriptReview/1.0"

    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="text/html; charset=utf-8"):
        b = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path == "/":
            return self._send(200, list_page())
        if self.path == "/git":
            return self._send(200, git_page())
        if self.path.startswith("/t/"):
            pg = detail_page(unquote(self.path[3:]))
            return self._send(200, pg) if pg else self._send(404, page("404", "Not found"))
        self._send(404, page("404", "Not found"))

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        try:
            data = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return self._send(400, json.dumps({"ok": False, "error": "bad json"}),
                              "application/json")
        if self.path == "/save":
            try:
                rel = data["path"]
                p = (TDIR / rel).resolve()
                if not str(p).startswith(str(TDIR.resolve())) or not p.is_file():
                    raise ValueError("bad path")
                fields = data.get("fields", {})
                rv = (fields.get("reviewer") or "").strip()
                allowed = contributors()
                if rv and rv not in allowed:
                    raise ValueError(f"'{rv}' is not in contributors.json — add them there first")
                if (fields.get("review_status") or "").strip() in ("reviewed", "excluded") and not rv:
                    raise ValueError("pick a reviewer before marking this reviewed or excluded")
                save(p, fields, data.get("exchanges", {}),
                     data.get("proposed", ""))
                refresh_index()
                return self._send(200, json.dumps({"ok": True, "path": rel}), "application/json")
            except Exception as e:
                return self._send(200, json.dumps({"ok": False, "error": str(e)}),
                                  "application/json")
        if self.path == "/git":
            act = data.get("action")
            br = (data.get("branch") or "").strip() or "review/batch"
            msg = (data.get("message") or "").strip() or "Review transcripts"
            try:
                if act == "branch":
                    rc, out = git("switch", "-c", br)
                elif act == "commit":
                    git("add", "--", "transcripts")
                    rc, out = git("commit", "-m", msg)
                elif act == "diff":
                    rc, out = git("diff", "--stat", "--", "transcripts")
                elif act == "pr":
                    _, cur = git("rev-parse", "--abbrev-ref", "HEAD")
                    rc, out = git("push", "-u", "origin", cur, timeout=180)
                    if rc == 0:
                        r = subprocess.run(["gh", "pr", "create", "--fill"], cwd=REPO,
                                           capture_output=True, text=True, timeout=180)
                        rc, out = r.returncode, out + "\n" + r.stdout + r.stderr
                else:
                    rc, out = 1, "unknown action"
                return self._send(200, json.dumps({"ok": rc == 0, "output": out}),
                                  "application/json")
            except FileNotFoundError as e:
                return self._send(200, json.dumps({"ok": False, "output": f"missing tool: {e}"}),
                                  "application/json")
            except Exception as e:
                return self._send(200, json.dumps({"ok": False, "output": str(e)}),
                                  "application/json")
        self._send(404, json.dumps({"ok": False}), "application/json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=7777)
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()
    if not TDIR.is_dir() or not tfiles():
        sys.exit("No transcripts found. Run: python3 scripts/fetch_transcripts.py")
    url = f"http://127.0.0.1:{a.port}/"
    print(f"Transcript review UI  →  {url}")
    print(f"  {len(tfiles())} transcripts in {TDIR.relative_to(REPO)}/   (Ctrl-C to stop)")
    if not a.no_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        # loopback only: never expose review data on the network
        ThreadingHTTPServer(("127.0.0.1", a.port), H).serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    except OSError as e:
        sys.exit(f"Could not bind port {a.port}: {e}\nTry --port 7778")


if __name__ == "__main__":
    main()
