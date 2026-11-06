from langchain_core.messages import ToolMessage
from rich import print

from src.agents.agents import (
    build_reader_agent,
    build_search_agent,
    critic_chain,
    writer_chain,
)


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

    return tool_result


def run_reader(topic: str, results) -> str:
    print("\n" + "=" * 50)
    print("step 2 - reader agent is scraping top resources ...")
    print("=" * 50)

    prompt = (
        f"Based on the following search results about '{topic}', "
        f"pick the most relevant URLs and scrape them for deeper content.\n\n"
        f"Search Results:\n{format_results_with_ids(results)}"
    )

    reader_agent = build_reader_agent()
    reader_result = reader_agent.invoke({"messages": [("user", prompt)]})
    content = reader_result["messages"][-1].text

    print("\nscraped content:\n", content)
    return content


def run_writer(topic: str, search_results, scrape_results):
    print("\n" + " =" * 50)
    print("step 3 - Writer is drafting the report ...")
    print("=" * 50)

    research_combined = (
        f"SEARCH RESULTS : \n {search_results} \n\n"
        f"DETAILED SCRAPED CONTENT : \n {scrape_results}"
    )

    report = writer_chain.invoke(
        {
            "topic": topic,
            "research": research_combined,
        }
    )

    print("\n Final Report\n", report)
    return report


def run_critic(report_result):
    print("\n" + " =" * 50)
    print("step 4 - Critic is reviewing the report ...")
    print("=" * 50)

    feedback = critic_chain.invoke({"report": report_result})
    print("\n critic report \n", feedback)
    return feedback


def run_research_pipeline(topic: str) -> dict:

    state = {}

    # Search
    search_result = run_search(topic)
    state["search_results"] = search_result

    # Scraper
    scraper_result = run_reader(topic, state["search_results"])
    state["scraper_results"] = scraper_result

    # Writer Chain
    report_result = run_writer(topic, state["search_results"], state["scraper_results"])
    state["report_result"] = report_result

    # Critic Chain
    critic_result = run_critic(state["report_result"])
    state["critic_result"] = critic_result

    return state
