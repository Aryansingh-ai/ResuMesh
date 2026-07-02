"""
Cover Letter Generator — RAG-powered tailored cover letter generation.
"""

from typing import Optional, List
from loguru import logger

from langchain_core.messages import HumanMessage, SystemMessage
from app.core.config import settings
from app.core.metrics import cover_letter_generations_total


COVER_LETTER_TEMPLATES = {
    "professional": """Generate a professional cover letter with the following structure:
1. Opening paragraph — express genuine interest and mention the specific role
2. 2-3 body paragraphs — highlight 3 key achievements that match the job requirements
3. Closing paragraph — call to action and thank you

Keep it concise (under 400 words). Use a formal but engaging tone.""",

    "enthusiastic": """Generate an enthusiastic, energy-filled cover letter:
1. Compelling opening that immediately grabs attention
2. Personal story about why this company/role excites you
3. 2 key skills with specific measurable examples
4. Strong closing with next steps

Under 350 words. Show personality while remaining professional.""",

    "technical": """Generate a technical cover letter emphasizing:
1. Brief intro with role and strongest technical qualifier
2. Deep dive into 2-3 technical achievements with metrics
3. How your tech stack aligns with their requirements
4. Collaborative and problem-solving closing

Under 400 words. Use technical terminology naturally.""",
}


def _get_llm(provider: Optional[str] = None, api_key: Optional[str] = None, model: Optional[str] = None):
    """Get configured LLM — uses request-level override if provided, falls back to settings."""
    from app.core.config import settings
    provider = (provider or settings.LLM_PROVIDER).lower()
    api_key = api_key or ""

    if provider == "groq":
        key = api_key or settings.GROQ_API_KEY
        if not key:
            raise ValueError("Groq API key not configured. Add it in Settings.")
        from langchain_groq import ChatGroq
        return ChatGroq(model=model or "llama-3.1-8b-instant", api_key=key, temperature=0.8)

    elif provider == "gemini":
        key = api_key or settings.GOOGLE_API_KEY
        if not key:
            raise ValueError("Google API key not configured. Add it in Settings.")
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=model or "gemini-1.5-flash", google_api_key=key, temperature=0.8)

    elif provider == "openai":
        if not api_key:
            raise ValueError("OpenAI API key required. Add it in Settings.")
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model or "gpt-4o-mini", api_key=api_key, temperature=0.8)

    elif provider == "deepseek":
        if not api_key:
            raise ValueError("DeepSeek API key required. Add it in Settings.")
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model or "deepseek-chat",
            api_key=api_key,
            base_url="https://api.deepseek.com/v1",
            temperature=0.8,
        )

    elif provider == "openrouter":
        if not api_key:
            raise ValueError("OpenRouter API key required. Add it in Settings.")
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model or "openai/gpt-4o-mini",
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            temperature=0.8,
        )

    else:
        # Default: Ollama (self-hosted)
        from langchain_ollama import ChatOllama
        return ChatOllama(model=model or settings.OLLAMA_MODEL, base_url=settings.OLLAMA_BASE_URL, temperature=0.8)



class CoverLetterGenerator:
    """Generates tailored cover letters using LLM + resume + job data."""

    async def generate(
        self,
        resume_data: dict,
        job_data: dict,
        tone: str = "professional",
        additional_context: str = "",
        llm_provider: Optional[str] = None,
        llm_api_key: Optional[str] = None,
        llm_model: Optional[str] = None,
    ) -> str:
        """
        Generate a tailored cover letter.

        Args:
            resume_data: Structured parsed resume dictionary.
            job_data: Structured job information dictionary.
            tone: Template tone ('professional', 'enthusiastic', 'technical').
            additional_context: Any extra user notes or instructions.
            llm_provider: Optional override for LLM provider (from request headers).
            llm_api_key: Optional override for LLM API key (from request headers).
            llm_model: Optional override for LLM model name (from request headers).

        Returns:
            Generated cover letter text.
        """
        template = COVER_LETTER_TEMPLATES.get(tone, COVER_LETTER_TEMPLATES["professional"])
        llm = _get_llm(provider=llm_provider, api_key=llm_api_key, model=llm_model)


        # Build context
        skills = resume_data.get("skills", {})
        all_skills = []
        for skill_list in skills.values():
            all_skills.extend(skill_list or [])

        experience_summary = ""
        for exp in (resume_data.get("experience") or [])[:2]:
            experience_summary += f"\n- {exp.get('title', '')} at {exp.get('company', '')} ({exp.get('duration', '')})"

        system_content = f"""You are an expert career coach and professional writer.
        
Candidate Profile:
- Name: {resume_data.get('full_name', 'the candidate')}
- Top Skills: {', '.join(all_skills[:10])}
- Years of Experience: {resume_data.get('total_years_experience', 'N/A')}
- Recent Experience: {experience_summary}

Target Role:
- Title: {job_data.get('title', 'the position')}
- Company: {job_data.get('company', 'the company')}
- Required Skills: {', '.join(job_data.get('required_skills', [])[:8])}
- Location: {job_data.get('location', '')}

{template}

{f'Additional instructions: {additional_context}' if additional_context else ''}

Write ONLY the cover letter text. Do not include any preamble or explanation."""

        messages = [
            SystemMessage(content=system_content),
            HumanMessage(content="Generate the cover letter now."),
        ]

        try:
            response = await llm.ainvoke(messages)
            cover_letter = response.content.strip()
            cover_letter_generations_total.labels(status="success").inc()
            logger.bind(tone=tone, words=len(cover_letter.split().info("Cover letter generated")))
            return cover_letter
        except Exception as e:
            cover_letter_generations_total.labels(status="error").inc()
            logger.bind(error=str(e).error("Cover letter generation failed"))
            raise
