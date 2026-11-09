import os

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from src.tools.tools import search

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Model Initialization
llm = ChatGoogleGenerativeAI(api_key=GOOGLE_API_KEY, model="gemini-3.5-flash-lite")


SEARCH_PROMPT = """You are a research search agent.
Always call the search tool. Do not answer from your own knowledge.
If the first results are thin or outdated, search again with a better query.

Never drop or invent URLs."""


class SourceSelection(BaseModel):
    ids: list[int] = Field(
        description="IDs of the most relevant and reliable results, best first"
    )


# 1st Agent: Search Agent
def build_search_agent():
    return create_agent(
        model=llm,
        tools=[search],
        system_prompt=SEARCH_PROMPT,
    )


# Writer chain
writer_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an expert research writer. Write clear, structured and insightful reports. Today's date is {today}",
        ),
        (
            "human",
            """Write a detailed research report on the topic below.
            
        Instructions:
        - After every factual claim, cite the source ID in square brackets, like [2]. If several sources support a claim, use [2][5].
        - Only use ID that appear in the research below.
        - If a source mentions another study (for example "a Brookings survey found..."), cite the ID of the source you read it in.
        - don't write a Sources section; it will be added automatically
        
        Topic: {topic}

        Research Gathered:
        {research}

        Structure the report as:
        - Introduction
        - Key Findings (minimum 3 well-explained points)
        - Conclusion
        
        
        Sources marked (snippet only) are short summaries, not full pages, so treat them as weaker evidence and don't base a key finding on them alone
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
            "You are a sharp and constructive research critic. Be honest and specific. Today's date is {today}. Do not treat sources from before today as future or hypothetical",
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

selector_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a research assistant that picks the best sources for a topic.",
        ),
        (
            "human",
            """
             
            Topic: 
            {topic} 
            

            Results:
            {results}

            Pick the 5 most relevant and reliable results, ranked best first, answering with their IDs only
            """,
        ),
    ]
)

selector_chain = selector_prompt | llm.with_structured_output(SourceSelection)
