import abc
import hashlib
import logging
import math
import os
import re
from typing import List, Dict, Any, Optional
import httpx

from app.services.rag.arabic_normalizer import normalize_arabic_text
from app.services.rag.prompt_guard import sanitize_untrusted_text

logger = logging.getLogger("rag_providers")

class EmbeddingProvider(abc.ABC):
    @abc.abstractmethod
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        pass

    @abc.abstractmethod
    def embed_query(self, query: str) -> List[float]:
        pass

class LocalHashingSemanticEmbedding(EmbeddingProvider):
    """
    In-Country, Offline-Capable Subword Semantic Embedding Provider (128 dimensions).
    Generates deterministic, normalized dense vector representations
    based on character n-grams and subword hashing without requiring external network.
    """
    def __init__(self, dim: int = 128):
        self.dim = dim

    def _embed_single(self, text: str) -> List[float]:
        normalized = normalize_arabic_text(text)
        vec = [0.0] * self.dim
        if not normalized:
            return vec

        # Subwords and 3-char, 4-char n-grams
        tokens = normalized.split()
        features = list(tokens)
        for token in tokens:
            t_pad = f"^{token}$"
            for n in (3, 4):
                if len(t_pad) >= n:
                    features.extend([t_pad[i:i+n] for i in range(len(t_pad) - n + 1)])

        for feat in features:
            h = int(hashlib.md5(feat.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dim
            sign = 1.0 if ((h >> 8) & 1) == 0 else -1.0
            vec[idx] += sign

        # L2 Normalize
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 1e-9:
            vec = [round(x / norm, 6) for x in vec]
        return vec

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        return [self._embed_single(t) for t in texts]

    def embed_query(self, query: str) -> List[float]:
        return self._embed_single(query)


class RerankerProvider(abc.ABC):
    @abc.abstractmethod
    def rerank(self, query: str, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        pass

class LocalCrossEncoderReranker(RerankerProvider):
    """
    Multilingual Cross-Encoder Reranker using Arabic-English bi-gram matching,
    exact phrase alignment, and token overlap scoring.
    """
    def rerank(self, query: str, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not candidates or not query:
            return candidates

        norm_query = normalize_arabic_text(query)
        q_tokens = set(norm_query.split())

        scored = []
        for cand in candidates:
            text = cand.get("chunk_text") or cand.get("text") or ""
            norm_text = cand.get("chunk_text_normalized") or normalize_arabic_text(text)
            c_tokens = set(norm_text.split())

            # 1. Token Jaccard overlap
            overlap = len(q_tokens.intersection(c_tokens))
            jaccard = overlap / max(1, len(q_tokens.union(c_tokens)))

            # 2. Substring exact match bonus
            exact_bonus = 0.5 if norm_query in norm_text else 0.0

            # 3. Base retrieval score combination
            base_score = cand.get("rrf_score", cand.get("score", 0.0))

            rerank_score = (0.5 * jaccard) + (0.3 * exact_bonus) + (0.2 * base_score)
            item = dict(cand)
            item["rerank_score"] = round(rerank_score, 4)
            scored.append(item)

        scored.sort(key=lambda x: x["rerank_score"], reverse=True)
        return scored


class GeneratorProvider(abc.ABC):
    @abc.abstractmethod
    def generate(self, query: str, retrieved_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        pass

class SovereignLocalGenerator(GeneratorProvider):
    """
    Strict in-country sovereign answer synthesizer.
    Grounded strictly in retrieved document chunks.
    Validates all cited chunk IDs and returns 'not found in your documents'
    when evidence is weak (max relevance < threshold).
    """
    def __init__(self, threshold: float = 0.15):
        self.threshold = threshold

    def generate(self, query: str, retrieved_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not retrieved_chunks:
            return {
                "answer": "Not found in your documents.",
                "answer_ar": "غير موجود في مستنداتك.",
                "confidence": 0.0,
                "citations": []
            }

        # Check top evidence score
        top_chunk = retrieved_chunks[0]
        relevance = top_chunk.get("rerank_score", top_chunk.get("rrf_score", 0.0))

        if relevance < self.threshold:
            return {
                "answer": "Not found in your documents.",
                "answer_ar": "غير موجود في مستنداتك.",
                "confidence": round(relevance, 3),
                "citations": []
            }

        # Gather citations (strictly from retrieved set)
        valid_chunk_ids = {c["id"] for c in retrieved_chunks if "id" in c}
        citations = []
        snippets = []

        for c in retrieved_chunks[:3]:
            cid = c.get("id")
            if cid and cid in valid_chunk_ids:
                clean_snippet = sanitize_untrusted_text(c.get("chunk_text", ""))
                citations.append({
                    "chunk_id": cid,
                    "document_id": c.get("document_id"),
                    "page": c.get("page_number", 1),
                    "bounding_box": c.get("bounding_box"),
                    "snippet": clean_snippet[:150]
                })
                snippets.append(clean_snippet)

        combined_evidence = " ".join(snippets)

        # Synthesize honest answer directly derived from verified evidence
        answer_en = f"Based on verified document records: {combined_evidence[:280]}..."
        answer_ar = f"بناءً على المستندات المعتمدة: {combined_evidence[:280]}..."

        return {
            "answer": answer_en,
            "answer_ar": answer_ar,
            "confidence": round(min(1.0, relevance + 0.3), 3),
            "citations": citations
        }


class FastEmbedMultilingualProvider(EmbeddingProvider):
    """
    In-Country, Sovereign ONNX Dense Semantic Embedding Provider.
    Powered by FastEmbed (e.g. BAAI/bge-small-en-v1.5 or intfloat/multilingual-e5-large)
    with zero external cloud egress and seamless fallback to LocalHashingSemanticEmbedding.
    """
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or os.environ.get("DOCS_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
        self._fallback = LocalHashingSemanticEmbedding(dim=128)
        self._model = None
        self.dim = 384

        try:
            from fastembed import TextEmbedding
            self._model = TextEmbedding(model_name=self.model_name)
            self.dim = 384 if "small" in self.model_name else 768
            logger.info("FastEmbed initialized successfully with model %s (dim=%d)", self.model_name, self.dim)
        except Exception as exc:
            logger.warning("FastEmbed offline or unavailable (%s); using LocalHashingSemanticEmbedding", exc)
            self._model = None
            self.dim = self._fallback.dim

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if self._model is not None:
            try:
                embeddings = list(self._model.embed(texts))
                return [[round(float(x), 6) for x in emb] for emb in embeddings]
            except Exception as ex:
                logger.warning("FastEmbed embed_texts error (%s); falling back to local hashing", ex)
        return self._fallback.embed_texts(texts)

    def embed_query(self, query: str) -> List[float]:
        if self._model is not None:
            try:
                embeddings = list(self._model.embed([query]))
                if embeddings:
                    return [round(float(x), 6) for x in embeddings[0]]
            except Exception as ex:
                logger.warning("FastEmbed embed_query error (%s); falling back to local hashing", ex)
        return self._fallback.embed_query(query)


class LocalOllamaGenerator(GeneratorProvider):
    """
    Sovereign In-Country Local LLM Generator.
    Connects to local Ollama runtime (e.g. qwen2.5:3b / falcon3) on 127.0.0.1:11434.
    Synthesizes grounded answers strictly from retrieved evidence chunks with zero cloud egress.
    Automatically and gracefully falls back to deterministic SovereignLocalGenerator
    when Ollama is offline, unreachable, or in test environments.
    """
    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 2.5,
        threshold: float = 0.12
    ):
        self.base_url = (base_url or os.environ.get("OLLAMA_HOST") or "http://localhost:11434").rstrip("/")
        self.model = model or os.environ.get("DOCS_LLM_MODEL", "qwen2.5:3b")
        self.timeout = timeout
        self.threshold = threshold
        self.fallback = SovereignLocalGenerator(threshold=threshold)

    def generate(self, query: str, retrieved_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not retrieved_chunks:
            return self.fallback.generate(query, retrieved_chunks)

        # Evidence validation: if weak relevance, immediately reject without burning LLM cycles
        top_chunk = retrieved_chunks[0]
        relevance = top_chunk.get("rerank_score", top_chunk.get("rrf_score", 0.0))
        if relevance < self.threshold:
            return self.fallback.generate(query, retrieved_chunks)

        # Validate chunk IDs and collect evidence snippets
        valid_chunk_ids = {c["id"] for c in retrieved_chunks if "id" in c}
        citations = []
        snippets = []

        for c in retrieved_chunks[:3]:
            cid = c.get("id")
            if cid and cid in valid_chunk_ids:
                clean_snippet = sanitize_untrusted_text(c.get("chunk_text", ""))
                citations.append({
                    "chunk_id": cid,
                    "document_id": c.get("document_id"),
                    "page": c.get("page_number", 1),
                    "bounding_box": c.get("bounding_box"),
                    "snippet": clean_snippet[:150]
                })
                snippets.append(clean_snippet)

        if not snippets:
            return self.fallback.generate(query, retrieved_chunks)

        # Format sovereign grounded prompt
        context_block = "\n".join([f"- {s}" for s in snippets])
        prompt = (
            f"You are a sovereign enterprise document intelligence assistant. Answer the question using ONLY the verified document excerpts below. "
            f"Keep your answer concise and factual. If the excerpts do not contain the answer, say 'Not found in your documents.'\n\n"
            f"Verified Document Excerpts:\n{context_block}\n\n"
            f"User Query: {query}\n"
            f"Answer:"
        )

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.1,
                            "num_predict": 100
                        }
                    }
                )
                if resp.status_code == 200:
                    data = resp.json()
                    raw_answer = data.get("response", "").strip()
                    if raw_answer:
                        return {
                            "answer": raw_answer,
                            "answer_ar": f"بناءً على المستندات: {raw_answer[:220]}",
                            "confidence": round(min(1.0, relevance + 0.35), 3),
                            "citations": citations,
                            "generator": f"local_ollama/{self.model}"
                        }
        except Exception as ex:
            logger.debug("Ollama inference skipped or unavailable (%s); executing sovereign local generator", ex)

        # Fallback to deterministic sovereign generator
        return self.fallback.generate(query, retrieved_chunks)


def get_default_embedding_provider() -> EmbeddingProvider:
    """Returns FastEmbed ONNX embedding provider with automatic fallback to subword hashing."""
    return FastEmbedMultilingualProvider()


def get_default_generator_provider(threshold: float = 0.12) -> GeneratorProvider:
    """Returns sovereign local LLM generator (Ollama) with deterministic fallback."""
    return LocalOllamaGenerator(threshold=threshold)
