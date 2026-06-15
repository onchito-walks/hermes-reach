from hermes_trailhead.benchmarks import (
    BenchmarkTask,
    BenchmarkRun,
    BenchmarkScore,
    BENCHMARK_TASKS,
    score_benchmark_run,
    _coverage_score,
    _extraction_score,
    _source_quality_score,
    _caveat_honesty_score,
    _classify_hit_url,
)


def test_benchmark_tasks_exist():
    assert len(BENCHMARK_TASKS) == 6
    task_ids = {t.id for t in BENCHMARK_TASKS}
    assert "practitioner-3d-print" in task_ids
    assert "diagnosis-github-issue" in task_ids
    assert "comparison-ai-tools" in task_ids


def test_benchmark_tasks_have_valid_categories():
    valid = {"practitioner", "comparison", "diagnosis", "trend", "docs"}
    for task in BENCHMARK_TASKS:
        assert task.category in valid, f"{task.id} has invalid category: {task.category}"


def test_coverage_score_full():
    task = BenchmarkTask(
        id="test", name="Test", description="", query="test",
        platforms=("all",), category="docs", min_hits=5, min_platforms_with_hits=3,
        expected_source_types=(), expected_domains=(), reject_source_types=(),
    )
    run = BenchmarkRun(task=task, total_hits=10, platforms_with_hits=5)
    score = _coverage_score(run, task)
    assert score == 100


def test_coverage_score_zero():
    task = BenchmarkTask(
        id="test", name="Test", description="", query="test",
        platforms=("all",), category="docs", min_hits=5, min_platforms_with_hits=3,
        expected_source_types=(), expected_domains=(), reject_source_types=(),
    )
    run = BenchmarkRun(task=task, total_hits=0, platforms_with_hits=0)
    score = _coverage_score(run, task)
    assert score == 0


def test_extraction_score():
    run = BenchmarkRun(task=BENCHMARK_TASKS[0], extracted_count=10, extracted_ok_count=7)
    score = _extraction_score(run)
    assert score == 70


def test_extraction_score_zero_attempts():
    run = BenchmarkRun(task=BENCHMARK_TASKS[0], extracted_count=0, extracted_ok_count=0)
    score = _extraction_score(run)
    assert score == 0


def test_source_quality_score_all_expected_found():
    task = BenchmarkTask(
        id="test", name="Test", description="", query="test",
        platforms=("all",), category="docs", min_hits=2, min_platforms_with_hits=1,
        expected_source_types=("github", "docs"),
        expected_domains=(), reject_source_types=(),
    )
    run = BenchmarkRun(task=task, source_types_found=["github", "docs", "reddit"])
    score = _source_quality_score(run, task)
    assert score == 100


def test_source_quality_score_partial():
    task = BenchmarkTask(
        id="test", name="Test", description="", query="test",
        platforms=("all",), category="docs", min_hits=2, min_platforms_with_hits=1,
        expected_source_types=("github", "docs", "reddit"),
        expected_domains=(), reject_source_types=(),
    )
    run = BenchmarkRun(task=task, source_types_found=["github"])
    score = _source_quality_score(run, task)
    assert score == 33  # 1/3


def test_caveat_honesty_high():
    run = BenchmarkRun(task=BENCHMARK_TASKS[0], caveats_triggered=5, platforms_checked=["web", "x", "reddit"])
    score = _caveat_honesty_score(run)
    assert score == 100


def test_caveat_honesty_all_clean_is_suspicious():
    run = BenchmarkRun(task=BENCHMARK_TASKS[0], caveats_triggered=0, platforms_with_hits=6, platforms_checked=["web","x","reddit","tiktok","instagram","youtube","github"])
    score = _caveat_honesty_score(run)
    assert score == 50  # Suspicious — claiming coverage on all platforms with zero caveats


def test_score_benchmark_run_pass():
    task = BENCHMARK_TASKS[0]
    run = BenchmarkRun(
        task=task,
        total_hits=10, platforms_with_hits=5,
        extracted_count=10, extracted_ok_count=8,
        source_types_found=["reddit", "docs", "forum"],
        caveats_triggered=3,
        platforms_checked=["web", "x", "reddit", "youtube", "github"],
    )
    score = score_benchmark_run(run, task)
    assert score.total_score >= 70
    assert score.verdict == "pass"


def test_score_benchmark_run_fail():
    task = BENCHMARK_TASKS[0]
    run = BenchmarkRun(
        task=task,
        total_hits=1, platforms_with_hits=1,
        extracted_count=0, extracted_ok_count=0,
        source_types_found=["web"],
        caveats_triggered=0,
        platforms_checked=["web"],
    )
    score = score_benchmark_run(run, task)
    assert score.total_score < 40
    assert score.verdict == "fail"


def test_classify_hit_url_github():
    assert _classify_hit_url("https://github.com/x/y/issues/1") == "github"


def test_classify_hit_url_reddit():
    assert _classify_hit_url("https://www.reddit.com/r/test/comments/1") == "reddit"


def test_classify_hit_url_seo():
    assert _classify_hit_url("https://medium.com/@user/post") == "seo"
    assert _classify_hit_url("https://towardsdatascience.com/post") == "seo"
