"""
html_render.py — Jinja2 + Playwright HTML → PDF 渲染层
================================================================
build.py cmd_make 调用本模块，把 assemble_content() 输出的 content dict
通过 Jinja2 模板 + Playwright Chromium headless 渲染成简历 PDF。

输入：content dict（形状由 build.py assemble_content() 决定）
输出：PDF bytes 或落到文件

关键约束（不要破坏）：
  - 模板只能引用 content 字段，不能内联文本（CLAUDE.md 同步检查清单硬规则）
  - 所有变量在模板里必须 |e 转义（防 HTML 注入）
  - 1 页硬约束由 build.py make 事后用 pdfinfo 检测；本模块不做 compression
  - 字体本地内嵌（auto-apply/fonts/IBMPlexSerif-*.woff2）不依赖网络

依赖：
  python3 -m pip install playwright jinja2
  python3 -m playwright install chromium
"""
import base64
import os
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

# 渲染引擎按需惰性 import（Playwright 优先，WeasyPrint 回退），
# 见 html_to_pdf()。顶部不再硬 import，避免任一引擎缺失时整模块无法加载。


# ============================================================
# 路径
# ============================================================
HERE = Path(__file__).resolve().parent          # auto-apply/
FONTS_DIR = HERE / "fonts"
TEMPLATES_DIR = HERE / "templates"


# ============================================================
# 字体内嵌：woff2 → Base64 @font-face CSS
# ============================================================

_FONT_FACES = [
    # (family, weight, style, woff2_filename)
    ("IBM Plex Serif", 400, "normal", "IBMPlexSerif-Regular.woff2"),
    ("IBM Plex Serif", 400, "italic", "IBMPlexSerif-Italic.woff2"),
    ("IBM Plex Serif", 700, "normal", "IBMPlexSerif-Bold.woff2"),
    ("IBM Plex Serif", 700, "italic", "IBMPlexSerif-BoldItalic.woff2"),
    # IBM Plex Sans 暂时也内嵌（A 模板不用，D 模板用；备用）
    ("IBM Plex Sans", 400, "normal", "IBMPlexSans-Regular.woff2"),
    ("IBM Plex Sans", 400, "italic", "IBMPlexSans-Italic.woff2"),
    ("IBM Plex Sans", 700, "normal", "IBMPlexSans-Bold.woff2"),
    ("IBM Plex Sans", 700, "italic", "IBMPlexSans-BoldItalic.woff2"),
]

_FONTS_CSS_CACHE = None  # 字体 Base64 转换昂贵（~700KB CSS），缓存一次


def build_fonts_css():
    """读 4+4 个 woff2 → Base64 → @font-face CSS。模块级缓存避免重复读盘。"""
    global _FONTS_CSS_CACHE
    if _FONTS_CSS_CACHE is not None:
        return _FONTS_CSS_CACHE
    parts = []
    for family, weight, style, filename in _FONT_FACES:
        path = FONTS_DIR / filename
        if not path.is_file():
            raise RuntimeError(f"字体文件不存在：{path}")
        b64 = base64.b64encode(path.read_bytes()).decode("ascii")
        parts.append(
            f"@font-face {{\n"
            f"  font-family: '{family}';\n"
            f"  font-weight: {weight};\n"
            f"  font-style: {style};\n"
            f"  src: url(data:font/woff2;base64,{b64}) format('woff2');\n"
            f"}}"
        )
    _FONTS_CSS_CACHE = "\n".join(parts)
    return _FONTS_CSS_CACHE


# ============================================================
# Jinja2
# ============================================================

_JINJA = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(enabled_extensions=("html", "j2", "html.j2")),
    trim_blocks=True,
    lstrip_blocks=True,
)


def render_html(template_name, context):
    """渲染 Jinja2 模板，注入 fonts_css。
    template_name: 文件名（相对 templates/，如 'resume.html.j2'）
    context: dict，会被 |e 转义后填入模板
    返回完整 HTML 字符串。
    """
    tpl = _JINJA.get_template(template_name)
    # 注入 fonts_css（不能被转义，所以模板里用 {{ fonts_css }} 不加 |e）
    full_context = dict(context)
    full_context["fonts_css"] = build_fonts_css()
    return tpl.render(**full_context)


# ============================================================
# Playwright PDF 渲染
# ============================================================

def html_to_pdf(html_str, out_pdf_path):
    """HTML 字符串 → PDF 文件落地。1 页约束 *不* 在这里强制（交给 build.py）。

    渲染引擎：优先 Playwright/Chromium（视觉最保真）；当浏览器不可用
    （缺 OS 依赖 / 无 root 装不了 install-deps）时自动回退 WeasyPrint ——
    同一份 HTML 模板，纯 Pango/Cairo，无需浏览器。editorial serif 模板不依赖
    浏览器专属 CSS，两条路径视觉基本一致。"""
    try:
        return _html_to_pdf_playwright(html_str, out_pdf_path)
    except Exception as e_pw:
        try:
            from weasyprint import HTML as _WeasyHTML
        except ImportError:
            raise RuntimeError(
                "Playwright 渲染失败且 WeasyPrint 未安装：\n"
                f"  Playwright: {type(e_pw).__name__}: {str(e_pw)[:200]}\n"
                "  → 装浏览器依赖（sudo playwright install-deps chromium）"
                " 或 pip install weasyprint"
            )
        _WeasyHTML(string=html_str).write_pdf(str(out_pdf_path))
        return out_pdf_path


def _html_to_pdf_playwright(html_str, out_pdf_path):
    """主渲染路径：Playwright/Chromium headless。缺浏览器依赖时抛异常，由 html_to_pdf 回退。"""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html_str, wait_until="networkidle")
        page.evaluate("document.fonts.ready")
        page.pdf(
            path=str(out_pdf_path),
            format="Letter",
            print_background=True,
            prefer_css_page_size=True,
            # @page margin 由模板里的 CSS 控制
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        )
        browser.close()
    return out_pdf_path


# ============================================================
# 对外接口（供 build.py cmd_make 调用）
# ============================================================

def render_resume(content, out_pdf_path):
    """content: build.py assemble_content() 返回的 dict
    out_pdf_path: PDF 落地路径
    返回 out_pdf_path。
    """
    html = render_html("resume.html.j2", content)
    return html_to_pdf(html, out_pdf_path)


def render_cl(content, cl_data, out_pdf_path):
    """Cover letter 渲染。
    content: 跟 resume 同一个 content dict（取 contact header）
    cl_data: APP###.yaml 的 cover_letter 段：
      {date, recipient_company, re_line, salutation, body_paragraphs, closing, signature}
    out_pdf_path: PDF 落地路径
    """
    html = render_html("cl.html.j2", {
        "contact": content["contact"],
        "cl": cl_data,
    })
    return html_to_pdf(html, out_pdf_path)


# ============================================================
# CLI 自测
# ============================================================

if __name__ == "__main__":
    # 自测：用 master_resume.yaml 当 content（跑出来类似母版简历），
    # 验证模板能跑通 + 跟 design_A.pdf 视觉一致。
    import yaml as _yaml
    repo_root = HERE.parent
    master = _yaml.safe_load(open(repo_root / "master_resume.yaml", encoding="utf-8"))

    # 母版 yaml → content dict（模拟 assemble_content 输出的最简形态）
    content = {
        "contact": master["contact"],
        "summary": master["summary"],
        "experience": [
            {"title": e["title"], "date": e["date"], "org_line": e["org_line"], "bullets": e["bullets"]}
            for e in master["experience"]
        ],
        "education": master["education"],
        "skills": [{"label": s["label"], "body": s["body"]} for s in master["skills"]],
    }

    out_dir = HERE / "applications" / "_spike"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_pdf = out_dir / "html_render_selftest.pdf"

    print(f"  渲染模板 resume.html.j2 ...")
    render_resume(content, out_pdf)
    size = out_pdf.stat().st_size
    print(f"  ✓ PDF 落地：{out_pdf} ({size/1024:.1f} KB)")
    print(f"\n  自测命令：")
    print(f"    pdfinfo {out_pdf} | grep Pages")
    print(f"    pdftotext -layout {out_pdf} - | head -30")
    print(f"    # 跟 design_A.pdf 视觉对比")
    print(f"    open {out_pdf} && open {out_dir}/design_A.pdf")
