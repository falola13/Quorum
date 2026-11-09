import logging

from src.helper.helper import builder
from src.pipelines.pipeline import run_research_pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s: %(message)s")
topic = "The impact of AI on the job market in 2026"

# run_research_pipeline(topic)
builder()
