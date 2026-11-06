from langchain_core.messages import ToolMessage

from src.pipelines.pipeline import collect_search_result


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
