"""状态机测试。"""

import pytest

from jobos.core.errors import InvalidStateTransitionError
from jobos.workflow.state_machine import transition_application, transition_job


def test_valid_transitions() -> None:
    assert transition_job("discovered", "enriched").value == "enriched"
    assert transition_application("planned", "materials_ready").value == "materials_ready"


def test_invalid_transition_is_rejected() -> None:
    with pytest.raises(InvalidStateTransitionError):
        transition_application("planned", "accepted")
