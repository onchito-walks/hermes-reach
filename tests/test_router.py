from hermes_reach.router import all_routes, route_for


def test_routes_have_required_fields():
    routes = all_routes()
    assert len(routes) >= 6
    for route in routes:
        assert route.key
        assert route.primary
        assert route.rationale
        assert route.evidence_needed
        assert route.competitor_lesson


def test_route_for_browser_login_requires_approval():
    route = route_for("login to a site and fill a form with browser session")
    assert route.key == "interactive-browser"
    assert route.approval_required is True


def test_route_for_known_url_prefers_extract():
    route = route_for("read this known url as markdown")
    assert route.key == "known-url-read"
    assert "web_extract" in route.primary
