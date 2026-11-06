from langchain_core.messages import ToolMessage

from src.pipelines.pipeline import collect_search_result, format_results_with_ids


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
