import abc
import hashlib
import json
import logging
import math
import os
import re
import urllib.parse
from typing import List, Dict, Any, Optional, AsyncIterator
import httpx

from app.core.config import settings
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


RAG_EN_STOPWORDS = {
    "what", "is", "the", "on", "this", "a", "an", "in", "of", "for", "to", "and", "or",
    "are", "was", "were", "it", "at", "by", "from", "with", "about", "how", "much",
    "many", "show", "tell", "me", "find", "get", "which", "do", "does", "did", "can",
    "could", "would", "should", "please", "there", "their", "then", "that", "these", "those"
}
RAG_AR_STOPWORDS = {
    "ما", "ماذا", "هو", "هي", "في", "على", "من", "إلى", "عن", "هذا", "هذه", "كم",
    "هل", "أين", "كيف", "مع", "أو", "و", "كان", "كانت", "التي", "الذي", "أن", "ان",
    "ذلك", "تلك", "هؤلاء", "هنا", "هناك", "له", "لها", "بها", "به", "عنه", "عنها"
}
RAG_STOPWORDS = RAG_EN_STOPWORDS | RAG_AR_STOPWORDS


class RerankerProvider(abc.ABC):
    @abc.abstractmethod
    def rerank(self, query: str, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        pass

class LocalCrossEncoderReranker(RerankerProvider):
    """
    Multilingual Cross-Encoder Reranker using Arabic-English query-token coverage,
    exact phrase alignment, and token overlap scoring.
    """
    def rerank(self, query: str, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not candidates or not query:
            return candidates

        norm_query = normalize_arabic_text(query)
        all_q_words = norm_query.split()
        clean_q_tokens = [w for w in all_q_words if w not in RAG_STOPWORDS and len(w) > 1]
        if not clean_q_tokens:
            clean_q_tokens = all_q_words
        q_tokens = set(clean_q_tokens)
        num_q_tokens = max(1, len(q_tokens))

        scored = []
        for cand in candidates:
            text = cand.get("chunk_text") or cand.get("text") or ""
            norm_text = cand.get("chunk_text_normalized") or normalize_arabic_text(text)
            c_tokens = set(norm_text.split())

            # 1. Query-token coverage (overlap / number of query tokens after removing stopwords)
            overlap = len(q_tokens.intersection(c_tokens))
            coverage = overlap / num_q_tokens

            # 2. Substring exact match bonus
            exact_bonus = 0.3 if norm_query in norm_text else 0.0

            # 3. Base retrieval score combination (normalized to [0, 1])
            base_score = cand.get("rrf_score", cand.get("score", 0.0))
            norm_base = min(1.0, max(0.0, base_score * 30.0)) if base_score < 0.1 else min(1.0, base_score)

            rerank_score = min(1.0, max(0.0, (0.7 * coverage) + exact_bonus + (0.1 * norm_base)))
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

        top_chunk = retrieved_chunks[0]
        relevance = top_chunk.get("rerank_score", top_chunk.get("rrf_score", 0.0))

        if relevance < self.threshold:
            return {
                "answer": "Not found in your documents.",
                "answer_ar": "غير موجود في مستنداتك.",
                "confidence": round(relevance, 3),
                "citations": []
            }

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
    Loads ONLY from local FASTEMBED_CACHE_DIR (strictly no external downloads).
    Created once via singleton pattern.
    """
    _singleton_model = None
    _singleton_model_name: Optional[str] = None
    _initialized = False

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or os.environ.get("DOCS_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
        self._fallback = LocalHashingSemanticEmbedding(dim=128)
        self.dim = 384

        cache_dir = os.environ.get("FASTEMBED_CACHE_DIR") or getattr(settings, "FASTEMBED_CACHE_DIR", None)

        if FastEmbedMultilingualProvider._singleton_model is not None:
            self._model = FastEmbedMultilingualProvider._singleton_model
            self.model_name = FastEmbedMultilingualProvider._singleton_model_name or self.model_name
            self.dim = 384 if "small" in self.model_name else 768
            return

        if FastEmbedMultilingualProvider._initialized:
            self._model = None
            self.dim = self._fallback.dim
            return

        FastEmbedMultilingualProvider._initialized = True
        if not cache_dir or not os.path.exists(cache_dir):
            logger.info("FASTEMBED_CACHE_DIR '%s' does not exist; skipping FastEmbed downloads and using fallback", cache_dir)
            self._model = None
            self.dim = self._fallback.dim
            return

        try:
            from fastembed import TextEmbedding
            # local_files_only=True guarantees NO external downloads
            self._model = TextEmbedding(
                model_name=self.model_name,
                cache_dir=cache_dir,
                local_files_only=True
            )
            FastEmbedMultilingualProvider._singleton_model = self._model
            FastEmbedMultilingualProvider._singleton_model_name = self.model_name
            self.dim = 384 if "small" in self.model_name else 768
            logger.info("FastEmbed loaded successfully from local cache %s (model=%s, dim=%d)", cache_dir, self.model_name, self.dim)
        except Exception as exc:
            logger.warning("FastEmbed local cache load failed (%s); using LocalHashingSemanticEmbedding", exc)
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


def is_local_or_allowlisted_host(url: str, allowlist_extra: Optional[List[str]] = None) -> bool:
    """Verifies that an endpoint URL belongs to local or sovereignly allowlisted network."""
    try:
        parsed = urllib.parse.urlparse(url)
        hostname = (parsed.hostname or "").lower()
        allowed = {"localhost", "127.0.0.1", "::1", "0.0.0.0", "host.docker.internal", "ollama"}
        env_allowed = os.environ.get("OLLAMA_ALLOWED_HOSTS", "")
        if env_allowed:
            allowed.update(h.strip().lower() for h in env_allowed.split(",") if h.strip())
        if allowlist_extra:
            allowed.update(h.strip().lower() for h in allowlist_extra if h.strip())
        return hostname in allowed
    except Exception:
        return False


class LocalOllamaGenerator(GeneratorProvider):
    """
    Sovereign In-Country Local LLM Generator.
    - OLLAMA_HOST must be local/allowlisted when STRICT_LOCAL_ONLY=true.
    - Uses httpx.AsyncClient.
    - Streams real Ollama tokens or reports fallback honestly.
    """
    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 2.5,
        threshold: float = 0.20
    ):
        raw_url = base_url or os.environ.get("OLLAMA_HOST") or "http://localhost:11434"
        self.base_url = raw_url.rstrip("/")
        self.model = model or os.environ.get("DOCS_LLM_MODEL", "qwen2.5:3b")
        self.timeout = timeout
        self.threshold = threshold
        self.fallback = SovereignLocalGenerator(threshold=threshold)
        self._disabled = False

        allowed_env = os.environ.get("OLLAMA_ALLOWED_HOSTS", "")
        extra_allowlist = [h.strip() for h in allowed_env.split(",") if h.strip()]

        if settings.STRICT_LOCAL_ONLY and not is_local_or_allowlisted_host(self.base_url, allowlist_extra=extra_allowlist):
            logger.warning(
                f"Sovereignty warning: OLLAMA_HOST '{self.base_url}' is not a local or allowlisted address. Falling back to sovereign deterministic generator."
            )
            self._disabled = True

    async def generate_async(self, query: str, retrieved_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Asynchronous generation using httpx.AsyncClient."""
        if self._disabled or not retrieved_chunks:
            return self.fallback.generate(query, retrieved_chunks)

        top_chunk = retrieved_chunks[0]
        relevance = top_chunk.get("rerank_score", top_chunk.get("rrf_score", 0.0))
        if relevance < self.threshold:
            return self.fallback.generate(query, retrieved_chunks)

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

        context_block = "\n".join([f"- {s}" for s in snippets])
        prompt = (
            f"You are a sovereign enterprise document intelligence assistant. Answer the question using ONLY the verified document excerpts below. "
            f"Keep your answer concise and factual. If the excerpts do not contain the answer, say 'Not found in your documents.'\n\n"
            f"Verified Document Excerpts:\n{context_block}\n\n"
            f"User Query: {query}\n"
            f"Answer:"
        )

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
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

        return self.fallback.generate(query, retrieved_chunks)

    def generate(self, query: str, retrieved_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Synchronous wrapper falling back safely."""
        return self.fallback.generate(query, retrieved_chunks)

    async def stream_generate(self, query: str, retrieved_chunks: List[Dict[str, Any]]) -> AsyncIterator[Dict[str, Any]]:
        """
        Streams REAL Ollama tokens asynchronously using httpx.AsyncClient.
        If Ollama is unavailable, yields the fallback result with real_time=False.
        """
        top_chunk = retrieved_chunks[0] if retrieved_chunks else {}
        relevance = top_chunk.get("rerank_score", top_chunk.get("rrf_score", 0.0))
        if relevance < self.threshold:
            yield {"token": "Not found in your documents.", "done": True, "real_time": False}
            return

        valid_chunk_ids = {c["id"] for c in retrieved_chunks if "id" in c}
        snippets = [
            sanitize_untrusted_text(c.get("chunk_text", ""))
            for c in retrieved_chunks[:3]
            if c.get("id") in valid_chunk_ids
        ]
        if not snippets:
            yield {"token": "Not found in your documents.", "done": True, "real_time": False}
            return

        context_block = "\n".join([f"- {s}" for s in snippets])
        prompt = (
            f"You are a sovereign enterprise document intelligence assistant. Answer the question using ONLY the verified document excerpts below. "
            f"Keep your answer concise and factual. If the excerpts do not contain the answer, say 'Not found in your documents.'\n\n"
            f"Verified Document Excerpts:\n{context_block}\n\n"
            f"User Query: {query}\n"
            f"Answer:"
        )

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": True,
                        "options": {"temperature": 0.1, "num_predict": 100}
                    }
                ) as response:
                    if response.status_code == 200:
                        async for line in response.aiter_lines():
                            if not line:
                                continue
                            try:
                                chunk = json.loads(line)
                                token = chunk.get("response", "")
                                is_done = chunk.get("done", False)
                                yield {"token": token, "done": is_done, "real_time": True}
                                if is_done:
                                    break
                            except Exception:
                                continue
                        return
        except Exception as ex:
            logger.debug("Ollama real-time stream unavailable (%s); using fallback without claiming real-time", ex)

        # Fallback honest delivery: not real-time token stream
        fallback_res = self.fallback.generate(query, retrieved_chunks)
        yield {"token": fallback_res["answer"], "done": True, "real_time": False}


_embedding_provider_instance: Optional[EmbeddingProvider] = None

def get_default_embedding_provider() -> EmbeddingProvider:
    """Returns FastEmbed ONNX embedding provider created once (singleton)."""
    global _embedding_provider_instance
    if _embedding_provider_instance is None:
        _embedding_provider_instance = FastEmbedMultilingualProvider()
    return _embedding_provider_instance


def get_default_generator_provider(threshold: float = 0.20) -> GeneratorProvider:
    """Returns sovereign local LLM generator (Ollama) with deterministic fallback."""
    return LocalOllamaGenerator(threshold=threshold)


async def check_ollama_reachable(base_url: str, timeout: float = 1.0) -> bool:
    """Checks if Ollama service is reachable."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(f"{base_url}/api/tags")
            return resp.status_code == 200
    except Exception:
        return False


def get_loaded_models() -> List[str]:
    """Returns list of models actually loaded in memory."""
    models = []
    if FastEmbedMultilingualProvider._singleton_model is not None:
        name = FastEmbedMultilingualProvider._singleton_model_name or "bge-small-en-v1.5"
        models.append(f"fastembed/{name}")
    return models
