"""职位导入和去重测试。"""

from sqlalchemy.orm import Session

from jobos.services.job_service import JobService


def test_job_is_deduplicated_and_raw_text_is_preserved(session: Session) -> None:
    service = JobService(session)
    first, created = service.import_text(
        "Python 兼职开发", "示例科技", "远程兼职，使用 Python 和 FastAPI", "same-id"
    )
    second, created_again = service.import_text(
        "Python 兼职开发", "示例科技", "远程兼职，使用 Python 和 FastAPI\n", "same-id"
    )
    assert created is True
    assert created_again is False
    assert first.id == second.id
    assert second.description_raw
    assert second.description_normalized
