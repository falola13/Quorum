import logging

from langchain_core.messages import ToolMessage
from langgraph.runtime import Runtime
from rich import print

from src.agents.agents import (
    build_search_agent,
    critic_chain,
    selector_chain,
    writer_chain,
)
from src.tools.tools import scrape_page

logger = logging.getLogger(__name__)


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
        formatted_result.append(
            f"[{r['id']}] Title: {r['title']}\nURL: {r['url']}\nContent: {r['content']}"
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


def run_search(topic: str) -> list:
    print("\n" + " =" * 50)
    print("step 1 - Search agent is working ...")
    print("=" * 50)

    search_agent = build_search_agent()
    search_result = search_agent.invoke(
        {
            "messages": [
                (
                    "user",
                    f"Find recent, reliable and detailed information about: {topic}",
                )
            ]
        }
    )
    messages = search_result["messages"]
    tool_result = collect_search_result(messages)
    print(tool_result)
    return tool_result


def run_selector(topic: str, results: list[dict]) -> list[int]:
    print("\n" + "=" * 50)
    print("Step 2 - Selector is choosing sources...")
    print("=" * 50)

    selector_result = selector_chain.invoke(
        {"topic": topic, "results": format_results_with_ids(results)}
    )
    return validate_ids(selector_result.ids, results)


def run_scraper(
    results: list[dict], selected_ids: list[int], target: int = 3
) -> list[dict]:
    print("\n" + "=" * 50)
    print("Step 3 - Scraping selected sources ...")
    print("=" * 50)

    by_id = {r["id"]: r for r in results}
    scraped_result = []
    for source_id in selected_ids:
        result = by_id[source_id]

        page = scrape_page(result["url"])
        if page is None:
            continue
        scraped_result.append(
            {
                "id": source_id,
                "title": result["title"],
                "url": result["url"],
                "content": page,
            }
        )
        if len(scraped_result) == target:
            break
    if len(scraped_result) < target and len(scraped_result) >= 1:
        logger.warning("Only %s of %s sources scraped", len(scraped_result), target)
    if len(scraped_result) == 0:
        raise RuntimeError("Could not scrape any of the selected sources")
    print("\n Scraped Result page \n", scraped_result)
    return scraped_result


def run_writer(topic: str, sources: list[dict]):
    print("\n" + " =" * 50)
    print("step 4 - Writer is drafting the report ...")
    print("=" * 50)

    research = format_sources(sources)
    report = writer_chain.invoke(
        {
            "topic": topic,
            "research": research,
        }
    )

    print("\n Final Report\n", report)
    return report


def run_critic(report_result):
    print("\n" + " =" * 50)
    print("step 5 - Critic is reviewing the report ...")
    print("=" * 50)

    feedback = critic_chain.invoke({"report": report_result})
    print("\n critic report \n", feedback)
    return feedback


def run_research_pipeline(topic: str) -> dict:

    state = {}

    # Search
    state["search_results"] = run_search(topic)

    # Source Selector
    state["selected_ids"] = run_selector(topic, state["search_results"])
    print("Selected:", state["selected_ids"])

    # Scraper
    state["sources"] = run_scraper(state["search_results"], state["selected_ids"])

    # Writer Chain
    state["report_result"] = run_writer(topic, state["sources"])

    # Critic Chain
    state["critic_result"] = run_critic(state["report_result"])

    return state
