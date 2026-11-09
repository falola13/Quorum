import logging

from rich import print

from src.agents.agents import (
    build_search_agent,
    critic_chain,
    selector_chain,
    writer_chain,
)
from src.helper.helper import (
    build_sources_section,
    collect_search_result,
    format_results_with_ids,
    format_sources,
    today_time,
    validate_ids,
)
from src.tools.tools import scrape_page

logger = logging.getLogger(__name__)


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
    failed = []
    for source_id in selected_ids:
        result = by_id[source_id]

        page = scrape_page(result["url"])
        if page is None:
            if result.get("snippet"):
                failed.append(
                    {
                        "id": source_id,
                        "title": result["title"],
                        "url": result["url"],
                        "content": result["snippet"],
                        "kind": "snippet",
                    }
                )

            continue
        scraped_result.append(
            {
                "id": source_id,
                "title": result["title"],
                "url": result["url"],
                "content": page,
                "kind": "page",
            }
        )
        if len(scraped_result) == target:
            break
    for f in failed:
        if len(scraped_result) == target:
            break
        scraped_result.append(f)
    pages = sum(1 for s in scraped_result if s["kind"] == "page")
    snippets = sum(1 for s in scraped_result if s["kind"] == "snippet")

    if pages < target and scraped_result:
        logger.warning(
            "Only %s of %s sources scraped in full, %s from snippets",
            pages,
            target,
            snippets,
        )
    if not scraped_result:
        raise RuntimeError("Could not scrape any of the selected sources")
    print("\n Scraped Result page \n", scraped_result)
    return scraped_result


def run_writer(topic: str, sources: list[dict]):
    print("\n" + " =" * 50)
    print("step 4 - Writer is drafting the report ...")
    print("=" * 50)

    research = format_sources(sources)
    report = writer_chain.invoke(
        {"topic": topic, "research": research, "today": today_time()}
    )

    source = build_sources_section(sources)
    final_report = f"{report}\n\n{source}"
    print("\n Final Report\n", final_report)
    return final_report


def run_critic(report_result):
    print("\n" + " =" * 50)
    print("step 5 - Critic is reviewing the report ...")
    print("=" * 50)

    feedback = critic_chain.invoke({"report": report_result, "today": today_time()})
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
