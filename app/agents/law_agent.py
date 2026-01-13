from langchain.agents import AgentType, Tool, initialize_agent
from langchain.memory import ConversationBufferMemory
from langchain_core.prompts import PromptTemplate
from langchain_openai import OpenAI

from app.core.config.settings import settings
from app.tools.rag_tool import rag_tool
from app.tools.web_search_tool import web_search_tool


class JapaneseLawAgent:
    def __init__(self):
        # Initialize the LLM
        self.llm = OpenAI(
            openai_api_key=settings.OPENAI_API_KEY,
            model_name=settings.MODEL_NAME,
            temperature=0.1,  # Lower temperature for more consistent answers in legal domain
        )

        # Initialize memory for conversation history
        self.memory = ConversationBufferMemory(
            memory_key="chat_history", return_messages=True
        )

        # Define tools for the agent
        self.tools = [
            Tool(
                name=rag_tool.name, func=rag_tool._run, description=rag_tool.description
            ),
            Tool(
                name=web_search_tool.name,
                func=web_search_tool._run,
                description=web_search_tool.description,
            ),
        ]

        # Create the agent
        self.agent = initialize_agent(
            tools=self.tools,
            llm=self.llm,
            agent=AgentType.CONVERSATIONAL_REACT_DESCRIPTION,
            verbose=True,
            memory=self.memory,
            handle_parsing_errors=True,
        )

        # Customize the agent prompt for Japanese legal domain
        self.custom_prompt = """あなたは日本の法律に関する専門的なアシスタントです。
        次のツールを使用してユーザーの質問に答えてください:

        1. japanese_law_rag_search: 日本の法律文書を検索するためのRAGツール
        2. web_search: 一般情報の検索（後で実装）

        質問に答える際は、関連する法律条文や判例を引用してください。
        専門用語には注意し、必要に応じて日本語と英語の両方で説明してください。

        入力: {input}
        {agent_scratchpad}
        {chat_history}
        """

    def query(self, user_input: str):
        """
        Process a user query using the agent
        """
        try:
            # For now, using the standard agent without custom prompt
            # In a full implementation, we would customize the agent's prompt
            response = self.agent(user_input)
            return response
        except Exception as e:
            return {"error": f"Error processing query: {str(e)}"}

    def reset_memory(self):
        """
        Reset the conversation memory
        """
        self.memory.clear()


# Global instance
law_agent = JapaneseLawAgent()
