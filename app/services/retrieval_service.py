from __future__ import annotations

import hashlib
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any

from app.core.config import settings
from app.services.spring_api_service import SpringApiService

try:
    import chromadb
except Exception:  # pragma: no cover
    chromadb = None

try:
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover
    SentenceTransformer = None


@dataclass
class RetrievalSource:
    type: str
    title: str
    snippet: str
    score: float
    metadata: dict[str, Any]


@dataclass
class RetrievalResult:
    answer_hint: str
    sources: list[RetrievalSource]


class _EmbeddingAdapter:
    def __init__(self) -> None:
        self._model = None
        self._lock = Lock()

    def _fallback_embed_one(self, text: str) -> list[float]:
        dims = 256
        vector = [0.0] * dims
        tokens = re.findall(r"[0-9A-Za-z가-힣]+", (text or "").lower())
        if not tokens:
            return vector
        for token in tokens:
            index = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16) % dims
            vector[index] += 1.0
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]

    def _ensure_model(self):
        if self._model is not None:
            return self._model
        if SentenceTransformer is None:
            return None
        with self._lock:
            if self._model is not None:
                return self._model
            self._model = SentenceTransformer(settings.CHROMA_EMBEDDING_MODEL)
            return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        model = None
        try:
            model = self._ensure_model()
        except Exception:
            model = None
        if model is None:
            return [self._fallback_embed_one(text) for text in texts]
        vectors = model.encode(texts, normalize_embeddings=True)
        return [list(map(float, row)) for row in vectors]


class RetrievalService:
    GUIDE_BY_INTENT = {
        "policy": None,
        "howto": None,
        "host_help": {"audience": "host"},
        "my_status": {"feature": "mypage"},
        "admin_contact": {"feature": "admin_contact"},
        "search_help": {"feature": "event_search"},
    }

    def __init__(self) -> None:
        self.spring = SpringApiService()
        self._embedder = _EmbeddingAdapter()
        self._client = None
        self._collection = None
        self._init_lock = Lock()
        self._rag_dir = Path(__file__).resolve().parents[2] / "data" / "rag"
        if settings.CHROMA_REINDEX_ON_BOOT:
            try:
                self.rebuild_index(force=True)
            except Exception:
                pass

    def _build_chunks(self) -> list[dict[str, Any]]:
        chunks: list[dict[str, Any]] = []
        if not self._rag_dir.exists():
            return chunks

        chunk_index = 0
        for path in sorted(self._rag_dir.glob("*.md")):
            raw = path.read_text(encoding="utf-8")
            doc_title = self._extract_title(raw, fallback=path.stem.replace("_", " "))
            sections = self._split_sections(raw)
            for section_title, content in sections:
                for piece in self._split_chunk_body(content):
                    text = piece.strip()
                    if len(text) < 25:
                        continue
                    chunk_index += 1
                    chunks.append(
                        {
                            "id": f"{path.stem}-{chunk_index}",
                            "text": text,
                            "title": doc_title,
                            "section": section_title or doc_title,
                            "document": path.name,
                            "source_type": "guide",
                            "audience": self._infer_audience(path.name),
                            "feature": self._infer_feature(path.name, text),
                        }
                    )
        return chunks

    def _extract_title(self, raw: str, fallback: str) -> str:
        for line in raw.splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                return stripped[2:].strip()
        return fallback

    def _split_sections(self, raw: str) -> list[tuple[str, str]]:
        current_title = ""
        current_lines: list[str] = []
        sections: list[tuple[str, str]] = []
        for line in raw.splitlines():
            if line.strip().startswith("## "):
                if current_lines:
                    sections.append((current_title, "\n".join(current_lines).strip()))
                    current_lines = []
                current_title = line.strip()[3:].strip()
            elif line.strip().startswith("# "):
                if current_lines:
                    sections.append((current_title, "\n".join(current_lines).strip()))
                    current_lines = []
                current_title = line.strip()[2:].strip()
            else:
                current_lines.append(line)
        if current_lines:
            sections.append((current_title, "\n".join(current_lines).strip()))
        return [(title, content) for title, content in sections if content.strip()]

    def _split_chunk_body(self, content: str, max_chars: int = 420) -> list[str]:
        blocks = [block.strip() for block in re.split(r"\n\s*\n", content) if block.strip()]
        chunks: list[str] = []
        current = ""
        for block in blocks:
            candidate = f"{current}\n\n{block}".strip() if current else block
            if len(candidate) <= max_chars:
                current = candidate
                continue
            if current:
                chunks.append(current)
            if len(block) <= max_chars:
                current = block
            else:
                sentences = re.split(r"(?<=[.!?。]|다\.|\n)", block)
                current = ""
                for sentence in sentences:
                    sentence = sentence.strip()
                    if not sentence:
                        continue
                    candidate = f"{current} {sentence}".strip() if current else sentence
                    if len(candidate) <= max_chars:
                        current = candidate
                    else:
                        if current:
                            chunks.append(current)
                        current = sentence
        if current:
            chunks.append(current)
        return chunks

    def _infer_audience(self, filename: str) -> str:
        name = filename.lower()
        if "host" in name or "booth" in name:
            return "host"
        return "user"

    def _infer_feature(self, filename: str, text: str) -> str:
        merged = f"{filename} {text}".lower()
        if "refund" in merged or "환불" in merged or "취소" in merged:
            return "refund"
        if "payment" in merged or "결제" in merged:
            return "payment"
        if "inquiry" in merged or "문의" in merged:
            return "inquiry"
        if "mypage" in merged or "마이페이지" in merged or "상태" in merged:
            return "mypage"
        if "booth" in merged or "부스" in merged:
            return "booth"
        if "report" in merged or "신고" in merged:
            return "report"
        if "host" in merged or "주최자" in merged:
            return "host"
        if "search" in merged or "행사 찾기" in merged or "검색" in merged:
            return "event_search"
        if "admin contact" in merged or "관리자 문의" in merged:
            return "admin_contact"
        return "general"

    def _collection_name(self) -> str:
        return settings.CHROMA_COLLECTION_NAME

    def _source_hash(self, chunks: list[dict[str, Any]]) -> str:
        digest = hashlib.sha256()
        for chunk in chunks:
            digest.update(chunk["id"].encode("utf-8"))
            digest.update(chunk["text"].encode("utf-8"))
        return digest.hexdigest()

    def _ensure_collection(self):
        if self._collection is not None:
            return self._collection
        with self._init_lock:
            if self._collection is not None:
                return self._collection
            self._collection = self._build_or_load_collection(force=False)
            return self._collection

    def _build_or_load_collection(self, *, force: bool):
        chunks = self._build_chunks()
        if chromadb is None:
            return False

        os.makedirs(settings.CHROMA_PERSIST_DIRECTORY, exist_ok=True)
        self._client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIRECTORY)
        collection = self._client.get_or_create_collection(name=self._collection_name(), metadata={"hnsw:space": "cosine"})
        current_hash = self._source_hash(chunks)
        need_reindex = force
        try:
            meta = collection.metadata or {}
            if not need_reindex:
                need_reindex = not (meta.get("source_hash") == current_hash and collection.count() == len(chunks))
        except Exception:
            need_reindex = True

        if need_reindex and chunks:
            try:
                existing = collection.get(include=[])
                existing_ids = existing.get("ids") or []
                if existing_ids:
                    collection.delete(ids=existing_ids)
            except Exception:
                pass

            embeddings = self._embedder.embed([chunk["text"] for chunk in chunks])
            collection.add(
                ids=[chunk["id"] for chunk in chunks],
                documents=[chunk["text"] for chunk in chunks],
                metadatas=[
                    {
                        "title": chunk["title"],
                        "section": chunk["section"],
                        "document": chunk["document"],
                        "type": chunk["source_type"],
                        "audience": chunk["audience"],
                        "feature": chunk["feature"],
                    }
                    for chunk in chunks
                ],
                embeddings=embeddings,
            )
            try:
                collection.modify(metadata={"source_hash": current_hash, "chunk_count": len(chunks)})
            except Exception:
                pass
        return collection

    def rebuild_index(self, *, force: bool = True) -> dict[str, Any]:
        with self._init_lock:
            collection = self._build_or_load_collection(force=force)
            self._collection = collection
        return self.get_status()

    def get_status(self) -> dict[str, Any]:
        rag_files = sorted(path.name for path in self._rag_dir.glob("*.md")) if self._rag_dir.exists() else []
        chunks = self._build_chunks()
        collection = self._ensure_collection()
        indexed_count = 0
        metadata = {}
        if collection:
            try:
                indexed_count = int(collection.count())
                metadata = collection.metadata or {}
            except Exception:
                indexed_count = 0
                metadata = {}
        return {
            "enabled": bool(collection),
            "provider": "chromadb" if chromadb is not None else "fallback",
            "collectionName": settings.CHROMA_COLLECTION_NAME,
            "persistDirectory": settings.CHROMA_PERSIST_DIRECTORY,
            "embeddingModel": settings.CHROMA_EMBEDDING_MODEL,
            "ragFiles": rag_files,
            "ragFileCount": len(rag_files),
            "chunkCount": len(chunks),
            "indexedCount": indexed_count,
            "collectionMetadata": metadata,
        }

    def _metadata_filter(self, intent: str | None) -> dict[str, Any] | None:
        hint = self.GUIDE_BY_INTENT.get(intent)
        if isinstance(hint, dict):
            return hint
        return None

    async def retrieve(self, message: str, *, intent: str | None = None, limit: int | None = None) -> RetrievalResult:
        final_limit = max(2, int(limit or settings.CHROMA_TOP_K))
        sources: list[RetrievalSource] = []
        collection = self._ensure_collection()

        if collection:
            query_embeddings = self._embedder.embed([message])
            where = self._metadata_filter(intent)
            try:
                result = collection.query(query_embeddings=query_embeddings, n_results=final_limit, where=where)
                docs = (result.get("documents") or [[]])[0]
                metas = (result.get("metadatas") or [[]])[0]
                distances = (result.get("distances") or [[]])[0]
                for idx, doc in enumerate(docs):
                    meta = metas[idx] or {}
                    distance = float(distances[idx] or 0.0) if idx < len(distances) else 0.0
                    score = max(0.0, 1.0 - distance)
                    snippet = str(doc).strip().replace("\n", " ")
                    sources.append(
                        RetrievalSource(
                            type=str(meta.get("type") or "guide"),
                            title=str(meta.get("section") or meta.get("title") or "운영 가이드"),
                            snippet=snippet[:220],
                            score=score,
                            metadata=meta,
                        )
                    )
            except Exception:
                sources = []

        faq_items = await self.spring.get_public_faqs()
        sources.extend(self._rank_faqs(message, faq_items or [], limit=settings.CHROMA_FAQ_TOP_K))

        deduped: list[RetrievalSource] = []
        seen: set[tuple[str, str]] = set()
        for source in sorted(sources, key=lambda item: item.score, reverse=True):
            key = (source.type, source.title)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(source)
            if len(deduped) >= final_limit:
                break

        answer_hint = "\n\n".join(f"[{item.title}]\n{item.snippet}" for item in deduped)
        return RetrievalResult(answer_hint=answer_hint, sources=deduped)

    def _rank_faqs(self, message: str, items: list[dict[str, Any]], limit: int = 2) -> list[RetrievalSource]:
        message_tokens = set(token for token in re.findall(r"[0-9A-Za-z가-힣]+", (message or "").lower()) if len(token) >= 2)
        scored: list[tuple[int, dict[str, Any]]] = []
        for item in items:
            if item.get("enabled") is False:
                continue
            haystack = " ".join([
                str(item.get("title") or ""),
                str(item.get("question") or ""),
                str(item.get("answer") or ""),
                " ".join(item.get("keywords") or []),
            ]).lower()
            score = 0
            for token in message_tokens:
                if token in haystack:
                    score += 2
            if score:
                scored.append((score, item))

        sources: list[RetrievalSource] = []
        for score, item in sorted(scored, key=lambda row: row[0], reverse=True)[:limit]:
            sources.append(
                RetrievalSource(
                    type="faq",
                    title=str(item.get("title") or item.get("question") or "운영 FAQ"),
                    snippet=str(item.get("answer") or "")[:220],
                    score=float(score),
                    metadata={"question": item.get("question") or ""},
                )
            )
        return sources
