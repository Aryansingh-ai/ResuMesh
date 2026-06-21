"""
RAG Career Coach — LangGraph-powered conversational AI assistant.
Uses ChromaDB as the retrieval layer and a configurable LLM.
"""

from typing import Dict, Any, List, Optional, AsyncGenerator
from dataclasses import dataclass, field
import structlog

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from typing_extensions import Annotated, TypedDict

from app.core.config import settings
from app.core.metrics import rag_queries_total

logger = structlog.get_logger(__name__)

SYSTEM_PROMPT = """You are ResuMesh Career Coach — an expert AI assistant helping professionals 
optimize their job applications, improve their resumes, and advance their careers.

You have access to the user's resume data and job analysis results. Use this context to provide
highly specific, actionable advice.

Your expertise includes:
- Resume optimization and ATS optimization
- Skill gap analysis and learning roadmaps
- Interview preparation and behavioral questions
- Salary negotiation strategies
- Career trajectory planning
- Industry-specific insights

Always be:
- Specific (use actual skills and role names from context)
- Actionable (give concrete steps, not vague advice)
- Encouraging (maintain a positive, growth-oriented tone)
- Honest (don't sugarcoat skill gaps)

Context about the user:
{user_context}
"""


class AgentState(TypedDict):
    """State shared across the LangGraph agent nodes."""
    messages: Annotated[list, add_messages]
    user_context: str
    retrieved_docs: List[str]
    final_response: Optional[str]


def _get_llm():
    """Get the configured LLM based on settings."""
    provider = settings.LLM_PROVIDER.lower()

    if provider == "groq" and settings.GROQ_API_KEY:
        from langchain_groq import ChatGroq
        return ChatGroq(
            model="llama-3.1-8b-instant",
            api_key=settings.GROQ_API_KEY,
            temperature=0.7,
            max_tokens=2000,
        )
    elif provider == "gemini" and settings.GOOGLE_API_KEY:
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.7,
        )
    else:
        # Default: Ollama (self-hosted, free)
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=0.7,
        )


class RAGCareerCoach:
    """
    LangGraph-based conversational career coach with RAG retrieval.
    """

    def __init__(self, embedding_service=None):
        self.embedding_service = embedding_service
        self._graph = None
        self._llm = None

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state machine."""
        graph = StateGraph(AgentState)

        # Add nodes
        graph.add_node("retrieve", self._retrieve_node)
        graph.add_node("generate", self._generate_node)

        # Add edges
        graph.set_entry_point("retrieve")
        graph.add_edge("retrieve", "generate")
        graph.add_edge("generate", END)

        return graph.compile()

    async def _retrieve_node(self, state: AgentState) -> Dict[str, Any]:
        """Retrieve relevant documents from ChromaDB."""
        retrieved_docs = []

        if self.embedding_service:
            try:
                last_message = state["messages"][-1]
                query = last_message.content if hasattr(last_message, "content") else str(last_message)

                # Search resumes and jobs
                similar_resumes = await self.embedding_service.find_similar_resumes(query, n_results=2)
                similar_jobs = await self.embedding_service.find_similar_jobs(query, n_results=2)

                for item in similar_resumes:
                    if item.get("document"):
                        retrieved_docs.append(f"[Resume Context]: {item['document'][:500]}")

                for item in similar_jobs:
                    if item.get("document"):
                        retrieved_docs.append(f"[Job Context]: {item['document'][:500]}")

            except Exception as e:
                logger.warning("RAG retrieval failed", error=str(e))

        return {"retrieved_docs": retrieved_docs}

    async def _generate_node(self, state: AgentState) -> Dict[str, Any]:
        """Generate a response using the LLM with retrieved context."""
        if self._llm is None:
            self._llm = _get_llm()

        # Build context
        user_context = state.get("user_context", "No user context available.")
        retrieved = state.get("retrieved_docs", [])
        if retrieved:
            user_context += "\n\nRetrieved Context:\n" + "\n".join(retrieved[:3])

        # Build messages
        system_msg = SystemMessage(content=SYSTEM_PROMPT.format(user_context=user_context))
        messages = [system_msg] + state["messages"]

        try:
            response = await self._llm.ainvoke(messages)
            final_response = response.content
        except Exception as e:
            logger.error("LLM generation failed", error=str(e))
            final_response = (
                "I'm having trouble connecting to my AI backend right now. "
                "Please check that your LLM service (Ollama/Groq/Gemini) is configured correctly."
            )

        return {
            "messages": [AIMessage(content=final_response)],
            "final_response": final_response,
        }

    async def chat(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        user_context: str = "",
    ) -> str:
        """
        Process a chat message and return the AI response.

        Args:
            user_message: The user's current message.
            conversation_history: List of previous messages.
            user_context: Serialized user profile/resume/job context.

        Returns:
            AI response string.
        """
        if self._graph is None:
            self._graph = self._build_graph()

        # Convert history to LangChain messages
        messages = []
        for msg in conversation_history[-10:]:  # Keep last 10 messages
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))

        messages.append(HumanMessage(content=user_message))

        initial_state = AgentState(
            messages=messages,
            user_context=user_context,
            retrieved_docs=[],
            final_response=None,
        )

        try:
            result = await self._graph.ainvoke(initial_state)
            response = result.get("final_response", "I couldn't generate a response.")
            rag_queries_total.labels(status="success").inc()
            return response
        except Exception as e:
            logger.error("RAG coach error", error=str(e), exc_info=True)
            rag_queries_total.labels(status="error").inc()
            raise
