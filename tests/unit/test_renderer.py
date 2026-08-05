"""简历渲染测试。"""

from pathlib import Path

import pytest
from jobos.artifacts.renderer import ResumeRenderer


@pytest.mark.asyncio
async def test_renderer_creates_html_and_pdf(tmp_path: Path) -> None:
    template_dir = Path(__file__).parents[2] / "jobos/artifacts/resume_templates"
    renderer = ResumeRenderer(template_dir, tmp_path)
    html = renderer.render_html(
        {
            "target_title": "Python 开发",
            "summary": "摘要",
            "skills": ["Python"],
            "experiences": [],
            "education": [],
        },
        {"name": "测试用户", "email": "a@example.com", "phone": "", "city": "上海"},
    )
    assert "测试用户" in html.read_text(encoding="utf-8")
    pdf = await renderer.render_pdf(html)
    assert pdf.read_bytes().startswith(b"%PDF")
