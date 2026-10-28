"""Deterministic standard-library SVG for reconstructed coverage counts."""

import argparse
from pathlib import Path
from xml.sax.saxutils import escape

from .common import read


def render(report):
    if report.get("schema") != "bc014-synthetic-coverage/1":
        raise ValueError("Wrong coverage report schema")
    rows = [
        ("interior/free_volume", "Interior, free volume", 80),
        ("interior/fixed_volume", "Interior, fixed volume", 120),
        ("interior/GI", "Interior, glucose + insulin", 160),
        ("gain_boundary/free_volume", "Gain boundary, free volume", 230),
    ]
    left, width = 250, 430

    def x(value):
        return left + width * value

    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="900" height="310" viewBox="0 0 900 310">',
        '<rect width="900" height="310" fill="white"/>',
        '<text x="20" y="28" font-family="sans-serif" font-size="18">'
        "BC-014 synthetic pointwise gain inclusion</text>",
        '<text x="20" y="48" font-family="sans-serif" font-size="12">'
        "Dots: included/planned; bars: 95% Wilson Monte Carlo intervals</text>",
        f'<rect x="{left}" y="206" width="{width}" height="42" fill="#f1f3f5"/>',
        f'<line x1="{x(0.95):.2f}" y1="58" x2="{x(0.95):.2f}" y2="184" '
        'stroke="#b14242" stroke-dasharray="5 4"/>',
        f'<text x="{x(0.95) - 44:.2f}" y="55" font-family="sans-serif" '
        'font-size="11" fill="#b14242">nominal 0.95</text>',
    ]
    for key, label, y in rows:
        item = report["summary"][key]
        low, high = item["wilson_95"]
        value = item["conservative_rate"]
        count = f"{item['included']}/{item['planned']}"
        parts.extend(
            [
                f'<text x="20" y="{y + 4}" font-family="sans-serif" font-size="12">'
                f"{escape(label)}</text>",
                f'<line x1="{x(low):.2f}" y1="{y}" x2="{x(high):.2f}" y2="{y}" '
                'stroke="#2f6a92" stroke-width="3"/>',
                f'<line x1="{x(low):.2f}" y1="{y - 5}" x2="{x(low):.2f}" y2="{y + 5}" '
                'stroke="#2f6a92"/>',
                f'<line x1="{x(high):.2f}" y1="{y - 5}" x2="{x(high):.2f}" y2="{y + 5}" '
                'stroke="#2f6a92"/>',
                f'<circle cx="{x(value):.2f}" cy="{y}" r="5" fill="#113d59"/>',
                f'<text x="700" y="{y + 4}" font-family="sans-serif" font-size="12">'
                f"{count} ({value:.3f})</text>",
            ]
        )
    parts.extend(
        [
            '<text x="20" y="211" font-family="sans-serif" font-size="11" fill="#555">'
            "Exact parameter boundary: no nominal 95% target</text>",
            f'<line x1="{left}" y1="267" x2="{left + width}" y2="267" stroke="#333"/>',
        ]
    )
    for value in (0, 0.25, 0.5, 0.75, 1):
        parts.extend(
            [
                f'<line x1="{x(value):.2f}" y1="267" x2="{x(value):.2f}" y2="273" stroke="#333"/>',
                f'<text x="{x(value) - 10:.2f}" y="289" font-family="sans-serif" '
                f'font-size="11">{value:g}</text>',
            ]
        )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Choose a new figure path")
    args.output.write_text(render(read(args.report)))
