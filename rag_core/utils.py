from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage, \
    AIMessage
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import MessagesState


class GraphUtils:
    def __init__(self):
        self.str_parser = StrOutputParser()

    async def _get_chat_history_str(self, state: MessagesState) -> str:
        chat_history = []
        for message in state["messages"]:
            role = ""
            if isinstance(message, HumanMessage):
                role = "user"
            elif isinstance(message, SystemMessage):
                role = "system"
            elif isinstance(message, ToolMessage):
                role = "tool"
            elif isinstance(message, AIMessage):
                role = "AI"

            chat_history.append(
                f"[{role}]: {await self.str_parser.ainvoke(message)}"
            )

        return "\n".join(chat_history)
