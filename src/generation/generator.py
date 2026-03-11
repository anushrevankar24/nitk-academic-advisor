"""Direct answer generation from retrieved chunks using Gemini."""

from google import genai
from google.genai import types
from typing import List, Dict, Tuple
from ..utils.config import GEMINI_API_KEY, GEMINI_MODEL
from ..utils.logging_utils import get_api_logger

logger = get_api_logger()


class DirectGenerator:
    """Generate answers directly from retrieved chunks."""
    
    def __init__(self):
        if not GEMINI_API_KEY:
            error_msg = "GEMINI_API_KEY not found in environment variables. Required for answer generation."
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        try:
            self.client = genai.Client(api_key=GEMINI_API_KEY)
            self.model_name = GEMINI_MODEL
            logger.info(f"DirectGenerator initialized with model: {GEMINI_MODEL}")
        except Exception as e:
            # Log without exposing the API key
            logger.error(f"Failed to initialize Gemini: {str(e)}")
            raise
    
    def generate_answer(
        self, 
        question: str, 
        chunks_with_scores: List[Tuple[Dict, float, Dict]]
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
                "confidence": 0.0
            }
        
        # Format context from chunks
        context = self._format_context(chunks_with_scores)
        
        # Generate answer with optimized prompt
        prompt = self._build_prompt(question, context)
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1
                )
            )
            
            answer_markdown = response.text.strip()
            
        except Exception as e:
            logger.error(f"Error generating answer: {type(e).__name__}")
            answer_markdown = "Error generating answer. Please try again."
        
        # Extract sources
        sources = self._extract_sources(chunks_with_scores)
        
        # Compute confidence based on retrieval scores
        confidence = self._compute_confidence(chunks_with_scores)
        
        return {
            "answer_markdown": answer_markdown,
            "sources": sources,
            "confidence": confidence
        }
    
    def _format_context(self, chunks_with_scores: List[Tuple[Dict, float, Dict]]) -> str:
        """
        Format chunks into context string.
        
        Args:
            chunks_with_scores: List of (chunk, score, debug_scores) tuples
            
        Returns:
            Formatted context string
        """
        context_parts = []
        
        for i, (chunk, score, debug_scores) in enumerate(chunks_with_scores, 1):
            # Handle both old and new chunk formats
            pdf_name = chunk.get('source') or chunk.get('pdf_name', 'Unknown')
            page_start = chunk.get('page_start', chunk.get('page', 0))
            
            citation = f"[{pdf_name} — p.{page_start}]"
            
            context_parts.append(
                f"Source {i} {citation}:\n{chunk['text']}\n"
            )
        
        return "\n".join(context_parts)
    
    def _build_prompt(self, question: str, context: str) -> str:
        """
        Build optimized prompt for direct generation.
        
        Args:
            question: User's question
            context: Formatted context from chunks
            
        Returns:
            Complete prompt
        """
        return f"""You are the official NITK Surathkal Academic Advisor. You answer questions about academic regulations, curriculum, grading, attendance, examinations, and other policies using ONLY the provided context from official NITK handbooks.

**RULES:**
1. Use ONLY the provided context. Never invent rules, policies, or numbers.
2. If the context does not contain enough information to answer, say: "This information is not available in the provided handbooks. Please contact the Academic Section for clarification."
3. When stating a rule or regulation, cite the source inline, e.g., [Btech_Curriculum_2023 — p.12].
4. Structure your answer clearly:
   - Use **numbered lists** for step-by-step procedures or sequential rules
   - Use **bullet points** for listing requirements, eligibility criteria, or options
   - Use **bold** for key terms, thresholds, and important values
   - Use **tables** when comparing categories (e.g., grade points, credit structures)
5. If the question is ambiguous (could apply to UG or PG), answer for both and clearly separate them with headers like "### For B.Tech (UG)" and "### For M.Tech/PhD (PG)".
6. If the context contains tables or structured data (indicated by | separators), preserve that structure in your answer.
7. Be precise with numbers — credit counts, percentages, grade points, and deadlines must be exact as stated in the context.

**QUESTION:** {question}

**CONTEXT:**
{context}

**ANSWER:**
First, identify which source(s) are most relevant to the question. Then provide a clear, structured answer following the rules above."""
    
    def _extract_sources(self, chunks_with_scores: List[Tuple[Dict, float, Dict]]) -> List[Dict]:
        """
        Extract source information from chunks.
        
        Args:
            chunks_with_scores: List of (chunk, score, debug_scores) tuples
            
        Returns:
            List of source dictionaries
        """
        import math
        
        sources = []
        seen_chunk_ids = set()
        
        for chunk, score, debug_scores in chunks_with_scores:
            chunk_id = chunk["chunk_id"]
            
            # Avoid duplicates
            if chunk_id in seen_chunk_ids:
                continue
            
            seen_chunk_ids.add(chunk_id)
            
            # Handle both old and new chunk formats
            pdf_name = chunk.get('source') or chunk.get('pdf_name', 'Unknown')
            page_start = chunk.get('page_start', chunk.get('page', 0))
            page_end = chunk.get('page_end', page_start)
            
            # Normalize cross-encoder score to 0-1 via sigmoid
            # The UI displays score * 100 as a percentage
            # scale=8.0 maps 0.27 -> ~0.90 (90%) and 0.05 -> ~0.60 (60%)
            normalized_score = 1.0 / (1.0 + math.exp(-8.0 * score))
            
            sources.append({
                "chunk_id": chunk_id,
                "text": chunk.get("text", ""),
                "pdf_name": pdf_name,
                "page_start": page_start,
                "page_end": page_end,
                "score": round(normalized_score, 2)
            })
        
        return sources
    
    def _compute_confidence(self, chunks_with_scores: List[Tuple[Dict, float, Dict]]) -> float:
        """
        Compute overall confidence score based on cross-encoder scores.
        Uses sigmoid to map cross-encoder scores (-10 to +10) to 0-1 range.
        
        Args:
            chunks_with_scores: List of (chunk, score, debug_scores) tuples
            
        Returns:
            Confidence score between 0 and 1
        """
        if not chunks_with_scores:
            return 0.0
        
        import math
        
        # Use top score (most relevant chunk) as primary signal
        top_score = chunks_with_scores[0][1]
        
        # Sigmoid mapping: maps cross-encoder scores to 0-1
        # scale=8.0 maps 0.27 -> ~0.90 (90%) and 0.05 -> ~0.60 (60%)
        scale = 8.0
        confidence = 1.0 / (1.0 + math.exp(-scale * top_score))
        
        return round(confidence, 2)
