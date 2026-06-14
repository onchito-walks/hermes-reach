from hermes_reach.cli import main


def test_doctor_json(capsys):
    rc = main(["doctor", "--json"])
    out = capsys.readouterr().out
    assert '"key": "web-search"' in out
    assert rc in (0, 1)


def test_queue_json(capsys):
    rc = main(["queue", "--json", "--all"])
    out = capsys.readouterr().out
    assert '"key": "agent-reach"' in out
    assert rc == 0


def test_plan_known_channel(capsys):
    rc = main(["plan", "x-search"])
    out = capsys.readouterr().out
    assert "Setup / usage plan" in out
    assert "Guardrail" in out
    assert rc == 0


def test_capability_radar(capsys):
    rc = main(["capability-radar"])
    out = capsys.readouterr().out
    assert "Hermes Capability Radar" in out
    assert "newsletter" in out.lower()
    assert rc == 0
