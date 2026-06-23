import json

from hermes_trailhead.cli import main
from hermes_trailhead.gauntlet import GAUNTLET_CASES, run_gauntlet, run_gauntlet_case


def test_gauntlet_covers_all_promised_hard_source_lanes():
    result = run_gauntlet()
    lanes = set(result["hard_source_lanes"])
    assert {
        "web",
        "docs",
        "github",
        "reddit",
        "x",
        "youtube_transcript",
        "tiktok_discovery",
        "instagram_discovery",
        "forum",
        "pdf",
    }.issubset(lanes)


def test_gauntlet_passes_as_offline_product_contract():
    result = run_gauntlet()
    assert result["mode"] == "offline_deterministic_product_contract"
    assert result["aggregate"]["average_score"] >= 90
    assert result["aggregate"]["fails"] == 0
    assert result["aggregate"]["partials"] == 0


def test_youtube_transcript_lane_requires_transcript_shaped_content():
    transcript_cases = [
        case for case in GAUNTLET_CASES
        if any(f.should_have_transcript for f in case.fixtures)
    ]
    assert transcript_cases
    for case in transcript_cases:
        score = run_gauntlet_case(case)
        transcript_findings = [f for f in score.findings if f.lane == "youtube_transcript"]
        assert transcript_findings
        assert all(f.transcript_ok for f in transcript_findings)
        assert score.transcript_score == 100


def test_visual_social_lanes_are_discovery_only_not_fake_extraction():
    case = next(c for c in GAUNTLET_CASES if c.id == "blocked-visual-social-honesty")
    score = run_gauntlet_case(case)
    by_lane = {finding.lane: finding for finding in score.findings}

    assert by_lane["tiktok_discovery"].blocked_ok is True
    assert by_lane["tiktok_discovery"].extraction_ok is True
    assert by_lane["tiktok_discovery"].score == 0
    assert by_lane["instagram_discovery"].blocked_ok is True
    assert by_lane["instagram_discovery"].extraction_ok is True
    assert by_lane["instagram_discovery"].score == 0
    assert by_lane["youtube_transcript"].transcript_ok is True


def test_gauntlet_cli_json_contract(capsys):
    rc = main(["gauntlet", "--format", "json"])
    captured = capsys.readouterr()
    data = json.loads(captured.out)

    assert rc == 0
    assert set(data) == {"gauntlet_version", "mode", "case_count", "hard_source_lanes", "aggregate", "results"}
    assert data["aggregate"]["fails"] == 0
    assert data["results"][0]["lane_coverage_score"] == 100
