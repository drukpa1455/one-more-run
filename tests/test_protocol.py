import math

import pytest

from one_more_run.protocol import MAX_CANDIDATE_BYTES, identify_candidate


def test_candidate_identity_is_structural():
    left, left_sha256 = identify_candidate({"steps": 80, "learning_rate": 0.05})
    right, right_sha256 = identify_candidate({"learning_rate": 0.05, "steps": 80})

    assert left == right
    assert left_sha256 == right_sha256


def test_candidate_identity_rejects_non_json_values():
    with pytest.raises(ValueError, match="finite JSON"):
        identify_candidate({"metric": math.nan})


def test_candidate_identity_is_bounded():
    with pytest.raises(ValueError, match="exceeds"):
        identify_candidate({"source": "x" * MAX_CANDIDATE_BYTES})
