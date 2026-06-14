import json

from hermes_reach.cli import main, search_data
from hermes_reach.search import search_run


def _json_from_cli(capsys, argv):
    rc = main(argv)
    captured = capsys.readouterr()
    return rc, json.loads(captured.out), captured


def test_search_json_contract_all(capsys):
    rc, data, _ = _json_from_cli(capsys, ["search", "all", "Hermes Agent discussion", "--format", "json"])

    assert rc == 0
    assert set(data) == {"query", "platform", "mode", "paid_api_required", "actions"}
    assert data["platform"] == "all"
    assert data["mode"] == "hermes_action_plan"
    assert data["paid_api_required"] is False
    assert len(data["actions"]) == 7
    for action in data["actions"]:
        assert set(action) == {
            "platform",
            "status",
            "query",
            "recommended_tool",
            "direct_url",
            "site_query",
            "frontend_url",
            "approval_required",
            "paid_api_required",
            "evidence_needed",
            "caveat",
        }
        assert action["paid_api_required"] is False
        assert isinstance(action["evidence_needed"], list)


def test_search_help_includes_platform_choices(capsys):
    try:
        main(["search", "--help"])
    except SystemExit as exc:
        assert exc.code == 0
    out = capsys.readouterr().out
    assert "Build a Hermes-usable search plan" in out
    assert "{all,web,x,reddit,tiktok,instagram,youtube,github}" in out


def test_search_reddit_uses_loginless_redlib(capsys):
    rc, data, _ = _json_from_cli(capsys, ["search", "reddit", "Hermes Agent", "--format", "json"])

    assert rc == 0
    action = data["actions"][0]
    assert action["platform"] == "reddit"
    assert "redlib.perennialte.ch" in action["direct_url"]
    assert action["approval_required"] is False
    assert action["paid_api_required"] is False


def test_search_tiktok_marks_gap_not_fake_coverage(capsys):
    rc, data, _ = _json_from_cli(capsys, ["search", "tiktok", "Hermes Agent", "--format", "json"])

    assert rc == 0
    action = data["actions"][0]
    assert action["platform"] == "tiktok"
    assert action["status"] == "gap"
    assert action["approval_required"] is True
    assert "site:tiktok.com" in action["site_query"]


def test_search_python_api_returns_structured_run():
    run = search_data("github", "Hermes Agent")

    assert run.platform == "github"
    assert run.paid_api_required is False
    assert run.actions[0].platform == "github"
    assert run.actions[0].recommended_tool.startswith("GitHub MCP")


def test_search_run_all_never_requires_paid_api_by_default():
    run = search_run("all", "Hermes Agent")

    assert run.paid_api_required is False
    assert all(action.paid_api_required is False for action in run.actions)
