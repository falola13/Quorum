from datetime import date

from langchain_core.messages import ToolMessage


def collect_search_result(messages) -> list:
    tool_result = []
    seen_urls = set()
    for m in messages:
        if isinstance(m, ToolMessage):
            for a in m.artifact:
                if a["url"] in seen_urls:
                    continue
                seen_urls.add(a["url"])
                tool_result.append(a)
    for i, r in enumerate(tool_result, start=1):
        r["id"] = i
    return tool_result


def format_results_with_ids(results: list[dict]) -> str:
    formatted_result = []
    for r in results:
        formatted_result.append(
            f"[{r['id']}] Title: {r['title']}\nURL: {r['url']}\nSnippet: {r['snippet']}"
        )
    return "\n\n".join(formatted_result)


def format_sources(sources: list[dict]) -> str:
    formatted_result = []
    for r in sources:
        label = " (snippet only)" if r["kind"] == "snippet" else ""
        formatted_result.append(
            f"[{r['id']}]{label} Title: {r['title']}\nURL: {r['url']}\nContent: {r['content']}"
        )
    return "\n\n".join(formatted_result)


def validate_ids(ids: list[int], results: list[dict]) -> list[int]:
    valid_ids = []
    real_ids = {r["id"] for r in results}
    seen = set()
    for i in ids:
        if i in real_ids and i not in seen:
            seen.add(i)
            valid_ids.append(i)
    return valid_ids


def today_time():
    return date.today().isoformat()
