"""Analyzer tests — mock the Anthropic client so no API key is needed."""
import json
from unittest.mock import MagicMock, patch

import pytest

from iac_explainer.analyzer import analyze, AnalysisError
from iac_explainer.schemas import Analysis, Severity


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_tool_use_block(payload: dict) -> MagicMock:
    block = MagicMock()
    block.type = "tool_use"
    block.input = payload
    return block


def _make_response(payload: dict) -> MagicMock:
    response = MagicMock()
    response.stop_reason = "tool_use"
    response.content = [_make_tool_use_block(payload)]
    return response


MINIMAL_ANALYSIS = {
    "summary": "A simple private S3 bucket for storing application logs.",
    "resources": [
        {
            "resource_type": "aws_s3_bucket",
            "name": "app_logs",
            "purpose": "Stores application log files privately.",
        }
    ],
    "cost": {
        "low_usd_monthly": 0.50,
        "high_usd_monthly": 5.00,
        "confidence": "low",
        "caveats": [
            "Assumes us-east-1 pricing.",
            "Storage cost depends on log volume.",
        ],
    },
    "security_findings": [],
    "overall_risk": "info",
}


# ── Happy path ────────────────────────────────────────────────────────────────

class TestAnalyzeSuccess:
    @patch("iac_explainer.analyzer.client")
    def test_returns_analysis_object(self, mock_client):
        mock_client.messages.create.return_value = _make_response(MINIMAL_ANALYSIS)
        result = analyze("resource \"aws_s3_bucket\" \"app_logs\" {}", [])
        assert isinstance(result, Analysis)

    @patch("iac_explainer.analyzer.client")
    def test_summary_preserved(self, mock_client):
        mock_client.messages.create.return_value = _make_response(MINIMAL_ANALYSIS)
        result = analyze("...", [])
        assert result.summary == MINIMAL_ANALYSIS["summary"]

    @patch("iac_explainer.analyzer.client")
    def test_cost_fields(self, mock_client):
        mock_client.messages.create.return_value = _make_response(MINIMAL_ANALYSIS)
        result = analyze("...", [])
        assert result.cost.low_usd_monthly == 0.50
        assert result.cost.high_usd_monthly == 5.00
        assert result.cost.confidence == Severity.low
        assert len(result.cost.caveats) >= 1

    @patch("iac_explainer.analyzer.client")
    def test_no_findings_overall_risk_info(self, mock_client):
        mock_client.messages.create.return_value = _make_response(MINIMAL_ANALYSIS)
        result = analyze("...", [])
        assert result.overall_risk == Severity.info
        assert result.security_findings == []

    @patch("iac_explainer.analyzer.client")
    def test_passes_raw_hcl_in_user_message(self, mock_client):
        mock_client.messages.create.return_value = _make_response(MINIMAL_ANALYSIS)
        raw = 'resource "aws_s3_bucket" "logs" {}'
        analyze(raw, [])
        call_kwargs = mock_client.messages.create.call_args.kwargs
        user_content = call_kwargs["messages"][0]["content"]
        assert raw in user_content

    @patch("iac_explainer.analyzer.client")
    def test_passes_parsed_resources_in_user_message(self, mock_client):
        mock_client.messages.create.return_value = _make_response(MINIMAL_ANALYSIS)
        resources = [{"type": "aws_s3_bucket", "name": "logs", "config": {}}]
        analyze("...", resources)
        call_kwargs = mock_client.messages.create.call_args.kwargs
        user_content = call_kwargs["messages"][0]["content"]
        assert "aws_s3_bucket" in user_content

    @patch("iac_explainer.analyzer.client")
    def test_tool_choice_is_forced(self, mock_client):
        mock_client.messages.create.return_value = _make_response(MINIMAL_ANALYSIS)
        analyze("...", [])
        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["tool_choice"] == {"type": "tool", "name": "submit_analysis"}

    @patch("iac_explainer.analyzer.client")
    def test_security_findings_parsed(self, mock_client):
        payload = dict(MINIMAL_ANALYSIS)
        payload["security_findings"] = [
            {
                "severity": "critical",
                "resource": "aws_s3_bucket.public_assets",
                "issue": "Bucket is publicly readable.",
                "recommendation": "Set block_public_acls = true.",
            }
        ]
        payload["overall_risk"] = "critical"
        mock_client.messages.create.return_value = _make_response(payload)
        result = analyze("...", [])
        assert len(result.security_findings) == 1
        assert result.security_findings[0].severity == Severity.critical
        assert result.overall_risk == Severity.critical


# ── Error handling ────────────────────────────────────────────────────────────

class TestAnalyzeErrors:
    @patch("iac_explainer.analyzer.client")
    def test_missing_tool_block_raises_analysis_error(self, mock_client):
        response = MagicMock()
        response.stop_reason = "end_turn"
        response.content = []  # no tool_use block
        mock_client.messages.create.return_value = response
        with pytest.raises(AnalysisError, match="tool_use"):
            analyze("...", [])

    @patch("iac_explainer.analyzer.client")
    def test_rate_limit_retries_then_raises(self, mock_client):
        import anthropic as _anthropic
        mock_client.messages.create.side_effect = _anthropic.RateLimitError(
            message="rate limited",
            response=MagicMock(status_code=429, headers={}),
            body={},
        )
        with pytest.raises(AnalysisError, match="unavailable"):
            analyze("...", [])
        assert mock_client.messages.create.call_count == 3  # _MAX_RETRIES

    @patch("iac_explainer.analyzer.client")
    def test_4xx_non_retryable_raises_immediately(self, mock_client):
        import anthropic as _anthropic
        mock_client.messages.create.side_effect = _anthropic.APIStatusError(
            message="bad request",
            response=MagicMock(status_code=400, headers={}),
            body={},
        )
        with pytest.raises(AnalysisError, match="400"):
            analyze("...", [])
        assert mock_client.messages.create.call_count == 1  # no retry
