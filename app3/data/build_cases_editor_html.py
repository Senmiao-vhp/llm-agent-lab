"""从带分区注释的 JSONL 生成「可编辑金标」网页：逐条改 JSON，校验后下载或写回本地文件。

支持：
  - 行首为 ``#`` 的分区标题行（如 ``# 1. current_status_estimate``），导出时按原顺序写回；
  - 空行在解析时忽略，导出时在相邻分区之间插入一个空行（与当前 ``eval_cases_350.jsonl`` 版式一致）。

在 ``llm-agent-lab/app3`` 下执行（或任意 cwd，路径相对于本脚本所在 ``data/``）::

  python data/build_cases_editor_html.py
  python data/build_cases_editor_html.py --input data/eval_cases_350.jsonl --output data/eval_runs/samples_editor_350.html

**写回磁盘**：用 Chrome / Edge 打开生成的 HTML（建议用本机 HTTP 提供，例如
``python -m http.server`` 在 ``data/eval_runs`` 目录），点击「绑定金标文件…」
选择 ``eval_cases_350.jsonl``，编辑后点「保存到已绑定文件」。
若浏览器不支持 File System Access API，请使用「下载 JSONL」覆盖保存到同路径。
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from html import escape
from pathlib import Path


def parse_jsonl_with_headers(path: Path) -> list[dict]:
    """返回 ``[{ "title": str | None, "items": [dict, ...] }, ...]``。"""
    lines = path.read_text(encoding="utf-8").splitlines()
    sections: list[dict] = []
    current: dict | None = None
    for line in lines:
        raw = line.rstrip("\n\r")
        st = raw.strip()
        if not st:
            continue
        if st.startswith("#"):
            current = {"title": raw, "items": []}
            sections.append(current)
        else:
            if current is None:
                current = {"title": None, "items": []}
                sections.append(current)
            current["items"].append(json.loads(st))
    return sections


def serialize_sections(sections: list[dict]) -> str:
    out_lines: list[str] = []
    for i, sec in enumerate(sections):
        title = sec.get("title")
        if title:
            out_lines.append(str(title))
        for obj in sec["items"]:
            out_lines.append(json.dumps(obj, ensure_ascii=False, separators=(",", ":")))
        if i < len(sections) - 1:
            out_lines.append("")
    return "\n".join(out_lines) + ("\n" if out_lines else "")


def main() -> None:
    ap = argparse.ArgumentParser(description="生成可编辑 JSONL 审核页（支持分区注释）")
    ap.add_argument(
        "--input",
        type=Path,
        default=None,
        help="金标 JSONL（默认同目录 eval_cases_350.jsonl）",
    )
    ap.add_argument(
        "--output",
        type=Path,
        default=None,
        help="输出 HTML（默认 data/eval_runs/samples_editor_350.html）",
    )
    args = ap.parse_args()

    data_dir = Path(__file__).resolve().parent
    cases_path = (args.input if args.input is not None else data_dir / "eval_cases_350.jsonl").resolve()
    if not cases_path.is_file():
        raise SystemExit(f"缺少文件: {cases_path}")

    eval_runs = data_dir / "eval_runs"
    eval_runs.mkdir(parents=True, exist_ok=True)
    out_path = (
        args.output.resolve()
        if args.output is not None
        else (eval_runs / "samples_editor_350.html").resolve()
    )

    sections = parse_jsonl_with_headers(cases_path)
    n = sum(len(s["items"]) for s in sections)
    if n == 0:
        raise SystemExit(f"未解析到任何 JSON 对象: {cases_path}")

    intents = sorted(
        {
            str((obj.get("gold") or {}).get("primary_intent") or "")
            for sec in sections
            for obj in sec["items"]
            if isinstance(obj.get("gold"), dict) and (obj.get("gold") or {}).get("primary_intent")
        }
    )

    seed_obj = {"sections": sections, "source_name": cases_path.name}
    seed_json = json.dumps(seed_obj, ensure_ascii=False)
    # 避免 HTML 中误解析出 </script>；JSON.parse 仍会把 \u003c 还原为 <
    seed_html_embed = seed_json.replace("<", "\\u003c")

    gen = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    abs_cases = str(cases_path)
    script_path = str(Path(__file__).resolve())

    intent_buttons = (
        '<button type="button" class="on" data-intent-filter="all">全部</button>'
        + "".join(
            f'<button type="button" data-intent-filter="{escape(i)}">{escape(i)}</button>' for i in intents
        )
    )

    css = """
:root {
  --bg: #0f1419;
  --surface: #1a222d;
  --surface2: #232d3b;
  --text: #e8eef4;
  --muted: #8b9aab;
  --accent: #3d9cf0;
  --warn: #e0a53d;
  --err: #f05a5a;
  --ok: #3ecf8e;
  --border: rgba(255,255,255,0.08);
  --font: "DM Sans", "Noto Sans SC", system-ui, sans-serif;
  --mono: "JetBrains Mono", "IBM Plex Mono", ui-monospace, monospace;
}
* { box-sizing: border-box; }
body { margin: 0; font-family: var(--font); background: var(--bg); color: var(--text); line-height: 1.55; font-size: 15px; }
.wrap { max-width: 960px; margin: 0 auto; padding: 2rem 1.25rem 4rem; }
h1 { font-size: 1.55rem; font-weight: 700; margin: 0 0 0.5rem; letter-spacing: -0.02em; }
.lead { color: var(--muted); margin: 0 0 0.75rem; font-size: 0.95rem; }
.warn-box {
  background: rgba(224,165,61,0.1); border: 1px solid rgba(224,165,61,0.35); border-radius: 10px;
  padding: 0.75rem 1rem; margin-bottom: 1.25rem; font-size: 0.88rem; color: var(--text);
}
.warn-box strong { color: var(--warn); }
.paths {
  background: var(--surface); border: 1px solid var(--border); border-radius: 10px;
  padding: 0.85rem 1rem; margin-bottom: 1.25rem; font-family: var(--mono); font-size: 0.76rem;
  word-break: break-all; color: var(--muted);
}
.paths strong { color: var(--text); display: block; margin-bottom: 0.35rem; font-family: var(--font); font-size: 0.8rem; }
.toolbar { display: flex; flex-wrap: wrap; gap: 0.65rem; align-items: center; margin-bottom: 1rem; }
.toolbar label { color: var(--muted); font-size: 0.85rem; }
#q {
  flex: 1; min-width: 200px; padding: 0.5rem 0.75rem; border-radius: 8px;
  border: 1px solid var(--border); background: var(--surface2); color: var(--text); font-size: 0.9rem;
}
.btn-row { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 1rem; align-items: center; }
.btn-row button, .btn-row a.file-dl {
  cursor: pointer; border: 1px solid var(--border); background: var(--surface2);
  color: var(--text); padding: 0.45rem 0.85rem; border-radius: 8px; font-size: 0.82rem;
  text-decoration: none; display: inline-block;
}
.btn-row button.primary { background: var(--accent); color: #061018; border-color: transparent; font-weight: 600; }
.btn-row button:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }
.btn-row button.primary:hover { filter: brightness(1.06); color: #061018; }
.btn-row button:disabled { opacity: 0.45; cursor: not-allowed; }
.bound-name { font-size: 0.78rem; color: var(--muted); max-width: 420px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.intent-filters button {
  cursor: pointer; border: 1px solid var(--border); background: var(--surface2);
  color: var(--text); padding: 0.4rem 0.75rem; border-radius: 999px; font-size: 0.8rem;
}
.intent-filters button.on { background: var(--accent); color: #061018; border-color: transparent; font-weight: 600; }
.intent-filters { display: flex; flex-wrap: wrap; gap: 0.35rem; margin-bottom: 1rem; }
.intent-filters::before {
  content: "按 gold.primary_intent 筛选（编辑后失焦会更新分组字段）";
  color: var(--muted); font-size: 0.78rem; width: 100%; margin-bottom: 0.2rem;
}
.stat { color: var(--muted); font-size: 0.85rem; margin-bottom: 1rem; }
.stat b { color: var(--ok); }
.stat b.bad { color: var(--err); }
.sec-h {
  font-size: 0.9rem; color: var(--accent); margin: 1.5rem 0 0.75rem; padding-bottom: 0.35rem;
  border-bottom: 1px solid var(--border); font-family: var(--mono);
}
.sec-h:first-of-type { margin-top: 0.5rem; }
.card {
  background: var(--surface); border: 1px solid var(--border); border-radius: 12px;
  margin-bottom: 1rem; overflow: hidden;
}
.card.bad { border-color: rgba(240,90,90,0.55); }
.card-h { display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem; padding: 0.55rem 1rem; background: var(--surface2); border-bottom: 1px solid var(--border); }
.sid { font-family: var(--mono); font-size: 0.84rem; }
.badge { font-size: 0.72rem; color: var(--muted); font-family: var(--mono); }
.ta-wrap { padding: 0.75rem 1rem 1rem; }
.ta-wrap label { display: block; font-size: 0.75rem; color: var(--muted); margin-bottom: 0.35rem; }
textarea.rec {
  width: 100%; min-height: 220px; resize: vertical; padding: 0.65rem 0.75rem; border-radius: 8px;
  border: 1px solid var(--border); background: #0b0f14; color: var(--text); font-size: 0.8rem;
  font-family: var(--mono); line-height: 1.45;
}
.card.bad textarea.rec { border-color: rgba(240,90,90,0.45); }
.card-actions { display: flex; gap: 0.5rem; flex-wrap: wrap; margin-top: 0.5rem; }
.card-actions button {
  cursor: pointer; border: 1px solid var(--border); background: var(--surface2);
  color: var(--text); padding: 0.3rem 0.55rem; border-radius: 6px; font-size: 0.76rem;
}
.hidden { display: none !important; }
.foot { margin-top: 2rem; padding-top: 1rem; border-top: 1px solid var(--border); color: var(--muted); font-size: 0.78rem; }
.toast {
  position: fixed; bottom: 1.25rem; left: 50%; transform: translateX(-50%);
  background: var(--surface2); border: 1px solid var(--border); color: var(--text);
  padding: 0.5rem 1rem; border-radius: 8px; font-size: 0.85rem; opacity: 0; pointer-events: none;
  transition: opacity 0.2s; z-index: 99; max-width: 90vw;
}
.toast.show { opacity: 1; }
"""

    script = r"""
<script>
(function() {
  const seedEl = document.getElementById("seed");
  const SEED = JSON.parse(seedEl.textContent);
  const listEl = document.getElementById("list");
  const q = document.getElementById("q");
  const cnt = document.getElementById("cnt");
  const badCnt = document.getElementById("badcnt");
  const toast = document.getElementById("toast");
  const bindBtn = document.getElementById("bindFile");
  const saveBtn = document.getElementById("saveFile");
  const boundLabel = document.getElementById("boundLabel");
  const dlAnchor = document.getElementById("dlAnchor");
  let fileHandle = null;
  let intentFilter = "all";

  function flash(msg) {
    toast.textContent = msg;
    toast.classList.add("show");
    clearTimeout(flash._t);
    flash._t = setTimeout(() => toast.classList.remove("show"), 2200);
  }

  function norm(s) { return (s || "").toLowerCase(); }

  function parseCard(card) {
    const ta = card.querySelector("textarea.rec");
    try {
      const o = JSON.parse(ta.value);
      card.classList.remove("bad");
      card.dataset.intent = (o.gold && o.gold.primary_intent) ? String(o.gold.primary_intent) : "";
      const sid = card.querySelector(".sid");
      if (sid) sid.textContent = o.sample_id != null ? String(o.sample_id) : "(无 sample_id)";
      return { ok: true, obj: o };
    } catch (e) {
      card.classList.add("bad");
      return { ok: false, err: e };
    }
  }

  function cardSearchText(card) {
    const ta = card.querySelector("textarea.rec");
    return norm(ta.value);
  }

  function applyFilter() {
    const needle = norm(q.value.trim());
    let shown = 0, bad = 0;
    document.querySelectorAll(".card").forEach(c => {
      parseCard(c);
      if (c.classList.contains("bad")) bad++;
      const okIntent = intentFilter === "all" || c.dataset.intent === intentFilter;
      const okQ = !needle || cardSearchText(c).includes(needle);
      const show = okIntent && okQ;
      c.classList.toggle("hidden", !show);
      if (show) shown++;
    });
    cnt.textContent = String(shown);
    badCnt.textContent = String(bad);
  }

  function buildFileText() {
    const sections = SEED.sections.map(sec => ({
      title: sec.title,
      items: new Array(sec.items.length),
    }));
    document.querySelectorAll(".card").forEach(card => {
      const si = +card.dataset.si;
      const ii = +card.dataset.ii;
      const r = parseCard(card);
      if (!r.ok) throw new Error("存在 JSON 语法错误的卡片，请先修正或点击「校验全部」定位。");
      sections[si].items[ii] = r.obj;
    });
    const lines = [];
    for (let i = 0; i < sections.length; i++) {
      const sec = sections[i];
      if (sec.title) lines.push(sec.title);
      for (const obj of sec.items) {
        lines.push(JSON.stringify(obj));
      }
      if (i < sections.length - 1) lines.push("");
    }
    return lines.join("\n") + "\n";
  }

  function validateAll() {
    let bad = 0;
    document.querySelectorAll(".card").forEach(c => {
      if (!parseCard(c).ok) bad++;
    });
    applyFilter();
    if (bad) flash("有 " + bad + " 条 JSON 无法解析，请检查红色边框卡片");
    else flash("全部 JSON 校验通过");
    return bad === 0;
  }

  function wireDl() {
    try {
      const text = buildFileText();
      const blob = new Blob([text], { type: "application/x-ndjson;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      dlAnchor.href = url;
      dlAnchor.download = SEED.source_name || "cases.jsonl";
    } catch (e) {
      flash(String(e.message || e));
    }
  }

  document.getElementById("validateBtn").addEventListener("click", () => validateAll());

  document.getElementById("refreshDl").addEventListener("click", () => {
    if (!validateAll()) return;
    wireDl();
    flash("已更新下载链接，请点击「下载 JSONL」");
  });

  bindBtn.addEventListener("click", async () => {
    if (!window.showOpenFilePicker) {
      flash("当前环境不支持绑定本地文件，请用「下载 JSONL」覆盖保存");
      return;
    }
    try {
      const [h] = await window.showOpenFilePicker({
        multiple: false,
        mode: "readwrite",
        types: [{ description: "JSON Lines", accept: { "application/jsonl": [".jsonl"], "application/x-ndjson": [".jsonl"], "*/*": [".jsonl"] } }],
      });
      fileHandle = h;
      boundLabel.textContent = h.name || "(已绑定)";
      saveBtn.disabled = false;
      flash("已绑定：保存将写入该文件");
    } catch (e) {
      if (e && e.name !== "AbortError") flash(String(e.message || e));
    }
  });

  saveBtn.addEventListener("click", async () => {
    if (!fileHandle) return;
    if (!validateAll()) return;
    let text;
    try { text = buildFileText(); } catch (e) { flash(String(e.message || e)); return; }
    if (!fileHandle.createWritable) {
      flash("无法写入：请改用 Chrome/Edge 新版，或下载覆盖");
      return;
    }
    try {
      const w = await fileHandle.createWritable();
      await w.write(new Blob([text], { type: "application/x-ndjson;charset=utf-8" }));
      await w.close();
      flash("已保存到磁盘");
    } catch (e) {
      flash("写入失败：" + (e.message || e) + "（可改用下载覆盖）");
    }
  });

  document.querySelectorAll(".intent-filters button").forEach(b => {
    b.addEventListener("click", () => {
      document.querySelectorAll(".intent-filters button").forEach(x => x.classList.toggle("on", x === b));
      intentFilter = b.dataset.intentFilter;
      applyFilter();
    });
  });
  q.addEventListener("input", applyFilter);

  document.body.addEventListener("click", (ev) => {
    const t = ev.target;
    if (t.classList.contains("btn-pretty")) {
      const card = t.closest(".card");
      const ta = card.querySelector("textarea.rec");
      const r = parseCard(card);
      if (r.ok) ta.value = JSON.stringify(r.obj, null, 2);
      else flash("JSON 有误，无法格式化");
    }
  });

  document.body.addEventListener("blur", (ev) => {
    if (ev.target.classList && ev.target.classList.contains("rec")) applyFilter();
  }, true);

  function render() {
    const frag = document.createDocumentFragment();
    SEED.sections.forEach((sec, si) => {
      if (sec.title) {
        const sh = document.createElement("div");
        sh.className = "sec-h";
        sh.textContent = sec.title;
        frag.appendChild(sh);
      }
      sec.items.forEach((obj, ii) => {
        const card = document.createElement("article");
        card.className = "card";
        card.dataset.si = String(si);
        card.dataset.ii = String(ii);
        const g = obj.gold || {};
        const intent = g.primary_intent ? String(g.primary_intent) : "";
        card.dataset.intent = intent;
        const sid = obj.sample_id != null ? String(obj.sample_id) : "";
        const searchPlain = (sid + " " + JSON.stringify(obj)).toLowerCase();
        card.dataset.search = searchPlain;
        const jsonTxt = JSON.stringify(obj, null, 2);
        card.innerHTML = `
          <header class="card-h">
            <code class="sid"></code>
            <span class="badge"></span>
          </header>
          <div class="ta-wrap">
            <label for="ta-${si}-${ii}">单条记录（JSON，可直接改字段）</label>
            <textarea id="ta-${si}-${ii}" class="rec" spellcheck="false"></textarea>
            <div class="card-actions">
              <button type="button" class="btn-pretty">格式化</button>
            </div>
          </div>`;
        card.querySelector(".sid").textContent = sid || "(无 sample_id)";
        card.querySelector(".badge").textContent = intent ? "gold.primary_intent: " + intent : "(无 primary_intent)";
        card.querySelector("textarea.rec").value = jsonTxt;
        frag.appendChild(card);
      });
    });
    listEl.appendChild(frag);
  }

  render();
  applyFilter();
  wireDl();
  saveBtn.disabled = true;
  boundLabel.textContent = "未绑定（可选）";
})();
</script>
"""

    title = f"金标编辑 · {cases_path.name} · {n} 条"
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{escape(title)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,400;9..40,600;9..40,700&amp;family=JetBrains+Mono:wght@400;500&amp;family=Noto+Sans+SC:wght@400;500;600&amp;display=swap" rel="stylesheet" />
<style>{css}</style>
</head>
<body>
<div class="wrap">
  <h1>{escape(title)}</h1>
  <p class="lead">每条卡片内为<strong>完整 JSON 对象</strong>（<code>sample_id</code> / <code>query</code> / <code>gold</code>）。改完后先<strong>校验全部</strong>，再<strong>下载 JSONL</strong>覆盖源文件，或在 Chrome/Edge 中<strong>绑定本地文件后保存</strong>。</p>
  <div class="warn-box"><strong>注意</strong>：导出时会去掉原文件中分区内的多余空行，仅在<strong>分区标题之间</strong>保留一个空行；<code>#</code> 标题行会原样写回。</div>
  <div class="paths">
    <strong>源金标路径（生成时快照）</strong>
    <div><code>{escape(abs_cases)}</code></div>
    <div>生成脚本：<code>{escape(script_path)}</code></div>
  </div>
  <div class="btn-row">
    <button type="button" id="validateBtn">校验全部 JSON</button>
    <button type="button" id="refreshDl">生成下载内容</button>
    <a class="file-dl primary" id="dlAnchor" href="#" download="{escape(cases_path.name)}">下载 JSONL</a>
    <button type="button" id="bindFile">绑定金标文件…</button>
    <button type="button" id="saveFile" disabled>保存到已绑定文件</button>
    <span class="bound-name" id="boundLabel"></span>
  </div>
  <div class="toolbar">
    <label for="q">搜索</label>
    <input type="search" id="q" placeholder="sample_id、问句、意图等任意片段…" autocomplete="off" />
  </div>
  <div class="intent-filters">
{intent_buttons}
  </div>
  <p class="stat">当前显示 <b id="cnt">0</b> 条 · JSON 错误 <b class="bad" id="badcnt">0</b> 条</p>
  <div id="list"></div>
  <p class="foot">生成时间 {escape(gen)}。改完源 JSONL 后请重新运行本脚本以刷新嵌入数据：<code>python data/build_cases_editor_html.py</code></p>
</div>
<div id="toast" class="toast" aria-live="polite"></div>
<script type="application/json" id="seed">{seed_html_embed}</script>
{script}
</body>
</html>"""

    out_path.write_text(html, encoding="utf-8")
    print(out_path, out_path.stat().st_size, "bytes", n, "cases", len(sections), "sections")


if __name__ == "__main__":
    main()
