import pytest
from langchain_core.messages import ToolMessage

from src.pipelines.pipeline import (
    collect_search_result,
    format_results_with_ids,
    run_scraper,
    validate_ids,
)


def test_removes_duplicate_urls():
    fake = [
        ToolMessage(
            content="fake", tool_call_id="g", artifact=[{"url": "A"}, {"url": "B"}]
        ),
        ToolMessage(
            content="fake", tool_call_id="f", artifact=[{"url": "B"}, {"url": "C"}]
        ),
    ]
    result = collect_search_result(fake)
    url = [r["url"] for r in result]
    assert url == [
        "A",
        "B",
        "C",
    ]


def test_empty_messages():
    fake = []

    result = collect_search_result(fake)

    assert result == []


def test_ids_are_numbered():
    fake = [
        ToolMessage(
            content="fake", tool_call_id="g", artifact=[{"url": "A"}, {"url": "B"}]
        ),
        ToolMessage(
            content="fake", tool_call_id="f", artifact=[{"url": "B"}, {"url": "C"}]
        ),
    ]
    result = collect_search_result(fake)
    ids = [r["id"] for r in result]
    assert ids == [
        1,
        2,
        3,
    ]


def test_format_results_with_ids():
    fake = [
        {
            "id": 1,
            "title": "A list",
            "url": "https://www.exam.com",
            "snippet": "A snippet",
        },
        {
            "id": 2,
            "title": "A list 2",
            "url": "https://www.exam3.com",
            "snippet": "A snippet2",
        },
        {
            "id": 3,
            "title": "A list 3",
            "url": "https://www.examr3.com",
            "snippet": "A snippet4",
        },
    ]
    text = format_results_with_ids(fake)
    print(text)
    assert "[1]" in text
    assert "[2]" in text
    assert "[3]" in text
    assert "https://www.examr3.com" in text


def test_validate_ids_drops_unknown():
    model_ids = [2, 9, 1]
    result = [{"id": 1}, {"id": 2}, {"id": 3}]
    valid = validate_ids(model_ids, result)

    assert valid == [2, 1]


def test_validate_ids_drops_repeats():
    model_ids = [3, 3, 1]
    result = [{"id": 1}, {"id": 2}, {"id": 3}]

    valid = validate_ids(model_ids, result)

    assert valid == [3, 1]


def test_run_scraper_skips_failed_pages(monkeypatch):
    def fake_scrape(url):
        if url == "B":
            return None
        return "page text"

    monkeypatch.setattr("src.pipelines.pipeline.scrape_page", fake_scrape)

    results = [
        {
            "id": 1,
            "title": "A list",
            "url": "A",
            "snippet": "A snippet",
        },
        {
            "id": 2,
            "title": "A list 2",
            "url": "B",
            "snippet": "A snippet2",
        },
        {
            "id": 3,
            "title": "A list 3",
            "url": "C",
            "snippet": "A snippet4",
        },
    ]
    page = run_scraper(results, [1, 2, 3])
    s = [s["id"] for s in page]

    assert s == [
        1,
        3,
    ]


def test_run_scraper_stops_at_target(monkeypatch):
    def fake_scrape(url):
        if url == "B":
            return None
        return "page text"

    fake_results = [
        {
            "id": 1,
            "url": "A",
            "title": "A list",
        },
        {
            "id": 2,
            "url": "B",
            "title": "A list",
        },
        {
            "id": 3,
            "url": "C",
            "title": "A list",
        },
        {
            "id": 4,
            "url": "D",
            "title": "A list",
        },
        {
            "id": 5,
            "url": "E",
            "title": "A list",
        },
    ]
    called = []

    monkeypatch.setattr("src.pipelines.pipeline.scrape_page", fake_scrape)
    page = run_scraper(fake_results, [1, 2, 3, 4, 5])
    for r in page:
        url = r["url"]
        called.append(url)

    assert [p["id"] for p in page] == [1, 3, 4]
    assert "E" not in called


def test_run_scraper_raises_when_all_fail():
    def fake_scrape(url):
        if url == "A" or url == "B":
            return None
        return "page test"

    results = [{"id": 1, "url": "A"}, {"id": 2, "url": "B"}]

    with pytest.raises(RuntimeError):
        run_scraper(results, [1, 2])
