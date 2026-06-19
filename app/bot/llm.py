from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core import settings

llm_model = ChatGoogleGenerativeAI(model=settings.GEMINI_MODEL)
str_parser = StrOutputParser()
