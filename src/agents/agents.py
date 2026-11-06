import os

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from src.tools.tools import scrape_url, search

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Model Initialization
llm = ChatGoogleGenerativeAI(api_key=GOOGLE_API_KEY, model="gemini-3.5-flash-lite")


SEARCH_PROMPT = """You are a research search agent.
Always call the search tool. Do not answer from your own knowledge.
If the first results are thin or outdated, search again with a better query.

Never drop or invent URLs."""

READER_PROMPT = """You are a research reader agent.
From the search results you're given, pick the 2-3 most relevant and reliable URLs
and call scrape_url on each one.
If a scrape fails, try the next best URL.

For each page, return:
SOURCE: <url>
<the key facts, figures and findings from the page>

Only use what the pages say. Never invent URLs or facts."""


# 1st Agent: Search Agent
def build_search_agent():
    return create_agent(
        model=llm,
        tools=[search],
        system_prompt=SEARCH_PROMPT,
    )


# 2nd Agent: Reader Agent
def build_reader_agent():
    return create_agent(model=llm, tools=[scrape_url], system_prompt=READER_PROMPT)


# Writer chain
writer_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an expert research writer. Write clear, structured and insightful reports.",
        ),
        (
            "human",
            """Write a detailed research report on the topic below.
        
        Topic: {topic}

        Research Gathered:
        {research}

        Structure the report as:
        - Introduction
        - Key Findings (minimum 3 well-explained points)
        - Conclusion
        - Sources (list all URLs found in the research)
        
        Be detailed, factual and professional.
        """,
        ),
    ]
)

writer_chain = writer_prompt | llm | StrOutputParser()


# critic chain

critic_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a sharp and constructive research critic. Be honest and specific.",
        ),
        (
            "human",
            """Review the research report below and evaluate it strictly.
        
        Report:
        {report}

        Respond in this exact format:

        Score: X/10

        Strengths:
        - ...
        - ...

        Areas to Improve:
        - ...
        - ...

        One line verdict:
        ...
        """,
        ),
    ]
)


critic_chain = critic = critic_prompt | llm | StrOutputParser()
