"""将结构化简历渲染为 HTML 和 PDF。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import async_playwright


class ResumeRenderer:
    """使用 Jinja2 生成 HTML，并优先通过 Playwright 输出 PDF。"""

    def __init__(self, template_dir: Path, output_dir: Path) -> None:
        self.template_dir = template_dir
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.environment = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(("html", "xml")),
        )

    def render_html(
        self,
        resume: dict[str, Any],
        profile: dict[str, Any],
        *,
        template_name: str = "technical_resume.html.j2",
        filename: str = "resume.html",
    ) -> Path:
        """把结构化简历与由代码注入的联系方式渲染为 HTML。"""
        template = self.environment.get_template(template_name)
        destination = self.output_dir / filename
        destination.write_text(
            template.render(resume=resume, profile=profile),
            encoding="utf-8",
        )
        return destination

    async def render_pdf(self, html_path: Path, *, filename: str = "resume.pdf") -> Path:
        """输出 A4 PDF；浏览器未安装时生成可打开的最小回退 PDF。"""
        destination = self.output_dir / filename
        try:
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(headless=True)
                try:
                    page = await browser.new_page(viewport={"width": 1280, "height": 900})
                    await page.goto(html_path.resolve().as_uri(), wait_until="networkidle")
                    await page.emulate_media(media="print")
                    await page.pdf(
                        path=str(destination),
                        format="A4",
                        print_background=True,
                        margin={
                            "top": "12mm",
                            "right": "12mm",
                            "bottom": "12mm",
                            "left": "12mm",
                        },
                    )
                finally:
                    await browser.close()
        except PlaywrightError:
            destination.write_bytes(_minimal_pdf("JobOS-CN Resume"))
        return destination


def _minimal_pdf(text: str) -> bytes:
    """生成符合 PDF 结构的单页文档，供无浏览器的离线环境使用。"""
    safe_text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 14 Tf 72 760 Td ({safe_text}) Tj ET".encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    document = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, body in enumerate(objects, start=1):
        offsets.append(len(document))
        document.extend(f"{index} 0 obj\n".encode("ascii"))
        document.extend(body)
        document.extend(b"\nendobj\n")
    xref_offset = len(document)
    document.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    document.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        document.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    document.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(document)
