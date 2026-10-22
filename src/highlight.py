"""Turn (start, end, weight) spans into colored HTML.

weight > 0  -> spam (warm red)
weight < 0  -> ham  (cool blue)
The stronger the weight, the stronger the color.
"""
import html
import re

_AR = re.compile(r"[\u0600-\u06FF]")


def _dir(text):
    """Explicit direction per message so Arabic reads right-to-left everywhere."""
    return "rtl" if _AR.search(text) else "ltr"


SPAM_RGB = (227, 73, 72)    # #e34948
HAM_RGB = (42, 120, 214)    # #2a78d6
SURFACE = "#f7f9fb"         # cool off-white
INK = "#0b0b0b"
MUTED = "#52514e"
LINE = "#d9dee5"

APPROACH_COLORS = {          # fixed order, follows the approach everywhere
    "Traditional": "#2a78d6",
    "Naive Bayes": "#eb6834",
    "Transformer": "#1baf7a",
    "LLM zero-shot": "#eda100",
}


def _bg(weight, max_abs):
    if max_abs <= 0 or weight == 0:
        return None
    alpha = min(1.0, abs(weight) / max_abs) * 0.75 + 0.1
    r, g, b = SPAM_RGB if weight > 0 else HAM_RGB
    return f"rgba({r},{g},{b},{alpha:.2f})"


def color_text(text, spans, max_abs=None):
    """Return HTML for one message with its spans colored."""
    spans = sorted([s for s in spans if s[2] != 0], key=lambda s: s[0])
    if max_abs is None:
        max_abs = max([abs(w) for _, _, w in spans], default=0)
    out, pos = [], 0
    for start, end, weight in spans:
        if start < pos:
            continue
        out.append(html.escape(text[pos:start]))
        bg = _bg(weight, max_abs)
        piece = html.escape(text[start:end])
        out.append(
            f'<span title="{weight:+.3f}" style="background:{bg};'
            f'border-radius:3px;padding:0 2px">{piece}</span>' if bg else piece
        )
        pos = end
    out.append(html.escape(text[pos:]))
    return "".join(out)


def _verdict(pred, prob, true_label):
    mark = ""
    if true_label is not None:
        mark = " ✓" if pred == true_label else " ✗"
    p = "" if prob is None else f" ({prob:.2f})"
    return f"{pred}{p}{mark}"


def page(body):
    return (
        f'<div style="background:{SURFACE};color:{INK};padding:14px 16px;'
        f'font-family:system-ui,Segoe UI,Tahoma,sans-serif;font-size:15px;'
        f'line-height:1.9;border:1px solid {LINE}">{body}</div>'
    )


def legend():
    sw = lambda rgb: f"background:rgba({rgb[0]},{rgb[1]},{rgb[2]},0.7);padding:0 6px;border-radius:3px"
    return (
        f'<div style="font-size:13px;color:{MUTED};margin-bottom:8px">'
        f'<span style="{sw(SPAM_RGB)}">spam</span> &nbsp; '
        f'<span style="{sw(HAM_RGB)}">ham</span> &nbsp; '
        f'darker = stronger · hover for weight</div>'
    )


def side_by_side(text, results, true_label=None, note=None):
    """One message, one column per approach.

    results: {approach_name: {"pred": str, "prob": float|None, "spans": [...]}}
    """
    cols = []
    for name, r in results.items():
        color = APPROACH_COLORS.get(name, MUTED)
        cols.append(
            f'<div style="padding:6px 10px;border-left:3px solid {color}">'
            f'<div style="font-size:13px;color:{MUTED}">{name} → '
            f'<b style="color:{INK}">{_verdict(r["pred"], r.get("prob"), true_label)}</b></div>'
            f'<div dir="{_dir(text)}" style="text-align:start;unicode-bidi:plaintext">'
            f'{color_text(text, r["spans"])}</div></div>'
        )
    head = f'<div style="font-size:13px;color:{MUTED}">true label: <b>{true_label}</b>'
    head += f" · {html.escape(note)}" if note else ""
    head += "</div>"
    grid = (
        '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));'
        f'gap:8px;margin:4px 0 14px">{"".join(cols)}</div>'
    )
    return head + grid


def scoreboard(rows, approaches):
    """HTML table: messages x approaches, ✓ / ✗ per cell.

    rows: list of dicts with keys text, label, note, preds{approach: pred}
    """
    th = "".join(
        f'<th style="padding:6px 8px;border-bottom:2px solid {APPROACH_COLORS.get(a, MUTED)};'
        f'font-weight:600">{a}</th>' for a in approaches
    )
    body = []
    for r in rows:
        cells = []
        for a in approaches:
            ok = r["preds"][a] == r["label"]
            cells.append(
                f'<td style="text-align:center;padding:6px 8px;border-bottom:1px solid {LINE};'
                f'color:{"#0ca30c" if ok else "#d03b3b"}">{"✓" if ok else "✗ " + r["preds"][a]}</td>'
            )
        body.append(
            f'<tr><td dir="{_dir(r["text"])}" style="text-align:start;padding:6px 8px;border-bottom:1px solid {LINE}">'
            f'{html.escape(r["text"])}<div style="font-size:12px;color:{MUTED}">'
            f'{r["label"]} · {html.escape(r["note"])}</div></td>{"".join(cells)}</tr>'
        )
    return (
        '<table style="border-collapse:collapse;width:100%;font-size:14px">'
        f'<thead><tr><th style="text-align:start;padding:6px 8px">Message</th>{th}</tr></thead>'
        f'<tbody>{"".join(body)}</tbody></table>'
    )
