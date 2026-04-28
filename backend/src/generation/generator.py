"""Direct answer generation from retrieved chunks using OpenRouter."""

import requests
from typing import List, Dict, Tuple
from ..utils.config import OPENROUTER_API_KEY, OPENROUTER_MODEL, OPENROUTER_BASE_URL
from ..utils.logging_utils import get_api_logger

logger = get_api_logger()

_CHAT_ENDPOINT = f"{OPENROUTER_BASE_URL}/chat/completions"


class DirectGenerator:
    """Generate answers directly from retrieved chunks via OpenRouter."""

    def __init__(self):
        if not OPENROUTER_API_KEY:
            error_msg = (
                "OPENROUTER_API_KEY not found in environment variables. "
                "Required for answer generation."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        self.model_name = OPENROUTER_MODEL
        self.headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }
        logger.info(f"DirectGenerator initialized | backend=openrouter | model={self.model_name}")

    def generate_answer(
        self,
        question: str,
        chunks_with_scores: List[Tuple[Dict, float, Dict]],
    ) -> Dict:
        """
        Generate answer directly from chunks.

        Args:
            question: User's question
            chunks_with_scores: List of (chunk, score, debug_scores) tuples

        Returns:
            Dictionary with answer_markdown, sources, and confidence
        """
        if not chunks_with_scores:
            return {
                "answer_markdown": "Information not found in provided handbooks.",
                "sources": [],
                "confidence": 0.0,
            }

        context = self._format_context(chunks_with_scores)
        system_prompt, user_message = self._build_messages(question, context)

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.1,
        }

        try:
            raw = requests.post(
                _CHAT_ENDPOINT,
                headers=self.headers,
                json=payload,
                timeout=60,
            )
            raw.raise_for_status()
            data = raw.json()

            answer_markdown = data["choices"][0]["message"]["content"].strip()
            logger.info(
                f"Answer generated | model={self.model_name} "
                f"| tokens_used={data.get('usage', {})}"
            )

        except requests.HTTPError as e:
            logger.error(
                f"OpenRouter HTTP error | model={self.model_name} "
                f"| status={e.response.status_code} "
                f"| body={e.response.text[:500]!r} "
                f"| question_preview={question[:120]!r}",
                exc_info=True,
            )
            answer_markdown = "Error generating answer. Please try again."

        except Exception as e:
            logger.error(
                f"Error generating answer | model={self.model_name} "
                f"| question_preview={question[:120]!r} "
                f"| error={type(e).__name__}: {e}",
                exc_info=True,
            )
            answer_markdown = "Error generating answer. Please try again."

        sources = self._extract_sources(chunks_with_scores)
        confidence = self._compute_confidence(chunks_with_scores)

        return {
            "answer_markdown": answer_markdown,
            "sources": sources,
            "confidence": confidence,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _format_context(self, chunks_with_scores: List[Tuple[Dict, float, Dict]]) -> str:
        """Format chunks into a numbered context string (no source labels — LLM must not repeat them)."""
        parts = []
        for i, (chunk, score, _debug) in enumerate(chunks_with_scores, 1):
            parts.append(f"Context {i}:\n{chunk['text']}\n")
        return "\n".join(parts)

    def _build_messages(self, question: str, context: str) -> Tuple[str, str]:
        """Return (system_prompt, user_message) for the chat API."""
        system_prompt = (
            "You are the official NITK Surathkal Academic Advisor. "
            "Answer questions about academic regulations, curriculum, grading, "
            "attendance, examinations, and other policies using ONLY the provided "
            "context from official NITK handbooks.\n\n"
            "**Rules:**\n\n"
            "1. **Answer only what is asked.** Do not add unsolicited advice, tips, "
            "reminders, or next-step suggestions. Stick strictly to the question.\n\n"
            "2. **Medium-length answers only.** Not too short (do not omit relevant "
            "details that directly answer the question), and not too long (do not pad "
            "with information the user did not ask for). A few sentences to a short "
            "paragraph or a brief list is ideal for most questions.\n\n"
            "3. **Use ONLY the provided context.** Never invent rules, policies, numbers, "
            "or procedures. If the context does not contain the answer, respond: "
            "\"This information is not available in the provided handbooks. "
            "Please contact the Academic Section for clarification.\"\n\n"
            "4. **No source citations.** Do not mention document names, page numbers, "
            "handbook titles, filenames, or phrases like 'According to...'. "
            "The UI already shows sources separately.\n\n"
            "5. **Exact numbers.** State credit counts, percentages, grade points, and "
            "deadlines exactly as they appear in the context — never round or approximate.\n\n"
            "6. **UG vs PG.** If the question applies to both levels, address both under "
            "separate short headers: `### B.Tech (UG)` and `### M.Tech / PhD (PG)`.\n\n"
            "7. **Formatting.** Use bold for key terms/numbers. Use bullet points or "
            "a table only when the information is genuinely list-like or comparative. "
            "Do not force structure onto a simple factual answer."
        )

        user_message = (
            f"**QUESTION:** {question}\n\n"
            f"**CONTEXT:**\n{context}\n\n"
            "**ANSWER:**\n"
            "Answer the question above using only the context provided. "
            "Be concise and focused — answer what was asked and nothing more. "
            "Do not mention any document names or page numbers."
        )

        return system_prompt, user_message

    def _extract_sources(self, chunks_with_scores: List[Tuple[Dict, float, Dict]]) -> List[Dict]:
        """Extract and deduplicate source information from chunks."""
        import math

        sources = []
        seen_chunk_ids: set = set()

        for chunk, score, _debug in chunks_with_scores:
            chunk_id = chunk["chunk_id"]
            if chunk_id in seen_chunk_ids:
                continue
            seen_chunk_ids.add(chunk_id)

            pdf_name = chunk.get("source") or chunk.get("pdf_name", "Unknown")
            page_start = chunk.get("page_start", chunk.get("page", 0))
            page_end = chunk.get("page_end", page_start)

            # Sigmoid normalisation: maps cross-encoder scores to 0–1
            # scale=8.0 → 0.27 ≈ 0.90 (90 %), 0.05 ≈ 0.60 (60 %)
            normalized_score = 1.0 / (1.0 + math.exp(-8.0 * score))

            sources.append({
                "chunk_id": chunk_id,
                "text": chunk.get("text", ""),
                "pdf_name": pdf_name,
                "page_start": page_start,
                "page_end": page_end,
                "score": round(normalized_score, 2),
            })

        return sources

    def _compute_confidence(self, chunks_with_scores: List[Tuple[Dict, float, Dict]]) -> float:
        """
        Compute overall confidence from the top cross-encoder score.
        Sigmoid with scale=8.0 maps the score range to 0–1.
        """
        if not chunks_with_scores:
            return 0.0

        import math

        top_score = chunks_with_scores[0][1]
        confidence = 1.0 / (1.0 + math.exp(-8.0 * top_score))
        return round(confidence, 2)
