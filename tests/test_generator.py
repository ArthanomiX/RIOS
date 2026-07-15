import json
from unittest.mock import MagicMock, patch

import pytest

from rios.core.schemas import Chunk, ResearchGapCandidate
from rios.gap_engine.generator import generate_gap_candidates


def _chunk(paper_id: str, text: str = "Some evidence text.") -> Chunk:
    return Chunk(chunk_id=f"{paper_id}::0", paper_id=paper_id, text=text)


def _mock_client_returning(text: str):
    """Build a mock genai.Client whose models.generate_content(...) returns
    a response object with a .text attribute, matching the SDK's shape."""
    mock_response = MagicMock()
    mock_response.text = text
    mock_response.prompt_feedback = None
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response
    return mock_client


def test_raises_without_chunks():
    with pytest.raises(ValueError):
        generate_gap_candidates([], domain="Ag Econ", api_key="fake-key")


def test_raises_without_api_key():
    with pytest.raises(ValueError):
        generate_gap_candidates([_chunk("W1")], domain="Ag Econ", api_key="")


@patch("rios.gap_engine.generator.genai.Client")
def test_valid_candidate_is_accepted(mock_client_cls):
    mock_client_cls.return_value = _mock_client_returning(json.dumps([
        {
            "gap_type": "methodological",
            "description": "Combine panel data with ML forecasting.",
            "why_insufficient": "Existing studies use only one method.",
            "expected_contribution": "A hybrid framework.",
            "supporting_paper_ids": ["W1"],
            "confidence_score": 0.8,
        }
    ]))
    candidates = generate_gap_candidates(
        [_chunk("W1")], domain="Ag Econ", api_key="fake-key"
    )
    assert len(candidates) == 1
    c = candidates[0]
    assert isinstance(c, ResearchGapCandidate)
    assert c.supporting_paper_ids == ["W1"]
    assert c.prompt_version == "v1"
    assert c.model_version == "gemini-2.5-flash"
    assert c.review_status.value == "pending"


@patch("rios.gap_engine.generator.genai.Client")
def test_candidate_citing_unknown_paper_id_is_dropped(mock_client_cls):
    mock_client_cls.return_value = _mock_client_returning(json.dumps([
        {
            "gap_type": "empirical",
            "description": "A gap citing a paper we never retrieved.",
            "why_insufficient": "...",
            "expected_contribution": "...",
            "supporting_paper_ids": ["W999"],  # not in our evidence
            "confidence_score": 0.9,
        }
    ]))
    candidates = generate_gap_candidates(
        [_chunk("W1")], domain="Ag Econ", api_key="fake-key"
    )
    assert len(candidates) == 0  # rejected — this is the critical guardrail


@patch("rios.gap_engine.generator.genai.Client")
def test_candidate_with_no_supporting_ids_is_dropped(mock_client_cls):
    mock_client_cls.return_value = _mock_client_returning(json.dumps([
        {
            "gap_type": "empirical",
            "description": "An unsupported gap.",
            "why_insufficient": "...",
            "expected_contribution": "...",
            "supporting_paper_ids": [],
            "confidence_score": 0.5,
        }
    ]))
    candidates = generate_gap_candidates(
        [_chunk("W1")], domain="Ag Econ", api_key="fake-key"
    )
    assert len(candidates) == 0


@patch("rios.gap_engine.generator.genai.Client")
def test_empty_array_response_is_valid(mock_client_cls):
    mock_client_cls.return_value = _mock_client_returning(json.dumps([]))
    candidates = generate_gap_candidates(
        [_chunk("W1")], domain="Ag Econ", api_key="fake-key"
    )
    assert candidates == []


@patch("rios.gap_engine.generator.genai.Client")
def test_markdown_fenced_json_is_handled(mock_client_cls):
    fenced = (
        "```json\n"
        + json.dumps([{
            "gap_type": "theoretical",
            "description": "desc",
            "why_insufficient": "why",
            "expected_contribution": "contribution",
            "supporting_paper_ids": ["W1"],
            "confidence_score": 0.6,
        }])
        + "\n```"
    )
    mock_client_cls.return_value = _mock_client_returning(fenced)
    candidates = generate_gap_candidates(
        [_chunk("W1")], domain="Ag Econ", api_key="fake-key"
    )
    assert len(candidates) == 1


@patch("rios.gap_engine.generator.genai.Client")
def test_invalid_json_raises_runtime_error(mock_client_cls):
    mock_client_cls.return_value = _mock_client_returning("not json at all")
    with pytest.raises(RuntimeError):
        generate_gap_candidates([_chunk("W1")], domain="Ag Econ", api_key="fake-key")


@patch("rios.gap_engine.generator.genai.Client")
def test_empty_text_response_raises_runtime_error(mock_client_cls):
    mock_client_cls.return_value = _mock_client_returning("")
    with pytest.raises(RuntimeError):
        generate_gap_candidates([_chunk("W1")], domain="Ag Econ", api_key="fake-key")


@patch("rios.gap_engine.generator.genai.Client")
def test_sdk_exception_is_wrapped_in_runtime_error(mock_client_cls):
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("auth failed")
    mock_client_cls.return_value = mock_client
    with pytest.raises(RuntimeError):
        generate_gap_candidates([_chunk("W1")], domain="Ag Econ", api_key="fake-key")
