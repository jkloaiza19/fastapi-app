from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from notion_client import AsyncClient as NotionAsyncClient
from openai import AsyncOpenAI
from astrapy import DataAPIClient
from astrapy.constants import VectorMetric
import tiktoken
# from utils.run_in_thread_util import get_threading_util

# from core.config import settings

load_dotenv()
# -----------------------------
# Helpers
# -----------------------------
def sha12(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]

def chunk_id(page_id: str, chunk_index: int, chunk_text: str) -> str:
    # stable deterministic id for chunk
    return f"notion:{page_id}:{chunk_index}:{sha12(chunk_text)}"

def normalize_spaces(s: str) -> str:
    return " ".join((s or "").split())

def count_tokens(text: str, model: str = "text-embedding-3-small") -> int:
    """Count tokens for a given text using tiktoken."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        # Fallback to cl100k_base encoding (used by most modern models)
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))

def split_into_sentences(text: str) -> List[str]:
    """Split text into sentences, handling common edge cases."""
    # Simple sentence splitter - can be improved with spaCy or NLTK for better accuracy
    # Handles: periods, question marks, exclamation marks
    # Preserves: abbreviations like "Dr.", "Mr.", URLs, etc.
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
    return [s.strip() for s in sentences if s.strip()]

def chunk_text_smart(
    text: str, 
    max_tokens: int = 512,  # Most embedding models have 512-8192 token limits
    overlap_tokens: int = 50,
    model: str = "text-embedding-3-small",
    max_bytes: int = 7500  # AstraDB limit is 8000, leave some margin
) -> List[str]:
    """
    Intelligently chunk text by:
    1. Respecting sentence boundaries (no mid-sentence cuts)
    2. Using token count instead of character count
    3. Adding semantic overlap between chunks
    4. Preserving paragraph structure when possible
    5. Enforcing byte size limits for database storage
    """
    text = normalize_spaces(text)
    if not text:
        return []
    
    # Check if entire text fits in one chunk (both tokens and bytes)
    text_bytes = len(text.encode('utf-8'))
    text_tokens = count_tokens(text, model)
    
    if text_tokens <= max_tokens and text_bytes <= max_bytes:
        return [text]
    
    # Split by paragraphs first (preserve structure)
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    
    chunks = []
    current_chunk = []
    current_tokens = 0
    current_bytes = 0
    
    for para in paragraphs:
        para_tokens = count_tokens(para, model)
        para_bytes = len(para.encode('utf-8'))
        
        # If single paragraph is too large, split by sentences
        if para_tokens > max_tokens or para_bytes > max_bytes:
            sentences = split_into_sentences(para)
            
            for sentence in sentences:
                sentence_tokens = count_tokens(sentence, model)
                sentence_bytes = len(sentence.encode('utf-8'))
                
                # If single sentence is still too large, split by words
                if sentence_tokens > max_tokens or sentence_bytes > max_bytes:
                    words = sentence.split()
                    temp_chunk = []
                    temp_tokens = 0
                    temp_bytes = 0
                    
                    for word in words:
                        word_tokens = count_tokens(word, model)
                        word_bytes = len(word.encode('utf-8')) + 1  # +1 for space
                        
                        if temp_tokens + word_tokens > max_tokens or temp_bytes + word_bytes > max_bytes:
                            if temp_chunk:
                                chunks.append(' '.join(temp_chunk))
                                # Keep overlap
                                overlap_words = temp_chunk[-overlap_tokens:] if len(temp_chunk) > overlap_tokens else temp_chunk
                                temp_chunk = overlap_words
                                temp_tokens = count_tokens(' '.join(temp_chunk), model)
                                temp_bytes = len(' '.join(temp_chunk).encode('utf-8'))
                        temp_chunk.append(word)
                        temp_tokens += word_tokens
                        temp_bytes += word_bytes
                    
                    if temp_chunk:
                        current_chunk.extend(temp_chunk)
                        current_tokens = count_tokens(' '.join(current_chunk), model)
                        current_bytes = len(' '.join(current_chunk).encode('utf-8'))
                    continue
                
                # Check if adding this sentence would exceed limit
                if current_tokens + sentence_tokens > max_tokens or current_bytes + sentence_bytes > max_bytes:
                    if current_chunk:
                        chunks.append(' '.join(current_chunk))
                        # Add overlap: keep last few sentences
                        overlap_text = ' '.join(current_chunk[-2:]) if len(current_chunk) >= 2 else ' '.join(current_chunk)
                        current_chunk = [overlap_text, sentence]
                        current_tokens = count_tokens(' '.join(current_chunk), model)
                        current_bytes = len(' '.join(current_chunk).encode('utf-8'))
                    else:
                        current_chunk = [sentence]
                        current_tokens = sentence_tokens
                        current_bytes = sentence_bytes
                else:
                    current_chunk.append(sentence)
                    current_tokens += sentence_tokens
                    current_bytes += sentence_bytes
        
        # Paragraph fits in current chunk
        elif current_tokens + para_tokens <= max_tokens and current_bytes + para_bytes <= max_bytes:
            current_chunk.append(para)
            current_tokens += para_tokens
            current_bytes += para_bytes
        
        # Paragraph doesn't fit - start new chunk
        else:
            if current_chunk:
                chunks.append(' '.join(current_chunk))
                # Add overlap
                overlap_text = current_chunk[-1] if current_chunk else ''
                current_chunk = [overlap_text, para] if overlap_text else [para]
                current_tokens = count_tokens(' '.join(current_chunk), model)
                current_bytes = len(' '.join(current_chunk).encode('utf-8'))
            else:
                current_chunk = [para]
                current_tokens = para_tokens
                current_bytes = para_bytes
    
    # Add remaining chunk
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    # Final validation: ensure no chunk exceeds limits
    validated_chunks = []
    for chunk in chunks:
        chunk_bytes = len(chunk.encode('utf-8'))
        if chunk_bytes > max_bytes:
            # Emergency split: this shouldn't happen but handle it
            # Split by bytes directly
            while chunk:
                safe_chunk = chunk
                while len(safe_chunk.encode('utf-8')) > max_bytes:
                    # Binary search for safe length
                    safe_chunk = safe_chunk[:len(safe_chunk)//2]
                validated_chunks.append(safe_chunk.strip())
                chunk = chunk[len(safe_chunk):].strip()
        else:
            validated_chunks.append(chunk)
    
    return [c.strip() for c in validated_chunks if c.strip()]

# Keep old function for backward compatibility
def chunk_text(text: str, max_chars: int = 1600, overlap: int = 200) -> List[str]:
    """Legacy character-based chunking. Use chunk_text_smart() for better results."""
    text = normalize_spaces(text)
    if not text:
        return []
    chunks = []
    i = 0
    while i < len(text):
        chunks.append(text[i : i + max_chars])
        i += max_chars - overlap
    return [c for c in chunks if c.strip()]

def blocks_to_text(blocks: List[Dict[str, Any]]) -> str:
    """
    Minimal Notion block renderer.
    Extend as needed for code blocks, tables, toggles, etc.
    """
    out: List[str] = []

    def extract_rich(block: Dict[str, Any]) -> str:
        t = block.get("type")
        data = block.get(t, {}) if t else {}
        rich = data.get("rich_text", [])
        if not rich:
            return ""
        return "".join(x.get("plain_text", "") for x in rich).strip()

    for b in blocks:
        t = b.get("type")
        if t in ("heading_1", "heading_2", "heading_3"):
            txt = extract_rich(b)
            if txt:
                out.append(txt)
                out.append("")  # spacing
        elif t in ("paragraph", "bulleted_list_item", "numbered_list_item", "to_do", "quote", "callout"):
            txt = extract_rich(b)
            if txt:
                out.append(txt)
        elif t == "code":
            # Extract code blocks with language context
            code_data = b.get("code", {})
            code_text = extract_rich(b)
            language = code_data.get("language", "")
            
            if code_text:
                # Format with markdown-style code fence for better embedding context
                if language:
                    out.append(f"```{language}")
                    out.append(code_text)
                    out.append("```")
                else:
                    out.append(f"Code:")
                    out.append(code_text)
                out.append("")  # spacing
        elif t == "toggle":
            # Extract toggle content (collapsible sections)
            txt = extract_rich(b)
            if txt:
                out.append(f"Toggle: {txt}")
        elif t == "table":
            # Basic table handling - extract table rows
            table_data = b.get("table", {})
            has_column_header = table_data.get("has_column_header", False)
            has_row_header = table_data.get("has_row_header", False)
            # Note: Table cells are in children blocks, would need recursive fetch
            out.append("Table:")
        elif t == "table_row":
            # Extract table row cells
            cells = b.get("table_row", {}).get("cells", [])
            row_text = " | ".join(
                "".join(cell.get("plain_text", "") for cell in rich_text_list)
                for rich_text_list in cells
            )
            if row_text:
                out.append(row_text)
        elif t == "equation":
            # Include mathematical equations
            equation = b.get("equation", {}).get("expression", "")
            if equation:
                out.append(f"Equation: {equation}")
        elif t == "divider":
            # Visual separator
            out.append("---")
        elif t == "bookmark":
            # Extract bookmarked URLs with caption
            bookmark = b.get("bookmark", {})
            url = bookmark.get("url", "")
            caption = "".join(
                x.get("plain_text", "") for x in bookmark.get("caption", [])
            ).strip()
            if url:
                out.append(f"Link: {url}" + (f" - {caption}" if caption else ""))
        # Add more handlers as needed:
        # elif t == "image": ... (extract caption)
        # elif t == "video": ... (extract caption/transcript)
        # elif t == "pdf": ...
    return "\n".join(out).strip()


async def fetch_all_block_children(notion: NotionAsyncClient, block_id: str) -> List[Dict[str, Any]]:
    """
    Recursively fetch all block children for a page/block.
    """
    results: List[Dict[str, Any]] = []
    cursor: Optional[str] = None

    while True:
        resp = await notion.blocks.children.list(block_id=block_id, start_cursor=cursor)
        batch = resp.get("results", [])
        results.extend(batch)

        if not resp.get("has_more"):
            break
        cursor = resp.get("next_cursor")

    expanded: List[Dict[str, Any]] = []
    for b in results:
        expanded.append(b)
        if b.get("has_children"):
            expanded.extend(await fetch_all_block_children(notion, b["id"]))
    return expanded


# -----------------------------
# Sync engine
# -----------------------------
@dataclass
class SyncConfig:
    # Notion
    notion_token: str
    openai_api_key: str
    page_ids: Optional[List[str]] = None

    notion_concurrency: int = 3
    # NEW: optional database id / api url
    notion_database_id: Optional[str] = None
    notion_api_url: Optional[str] = None

    # OpenAI
    embed_model: str = "text-embedding-3-small"
    embed_dim: int = 1536

    # Astra
    astra_api_endpoint: str = ""
    astra_token: str = ""
    astra_keyspace: str = "default_keyspace"
    kb_collection: str = "kb_chunks"     # vector collection
    state_collection: str = "kb_state"   # non-vector collection for per-page last_edited_time

    # Metadata
    tenant_id: str = "public"

    # Chunking
    chunk_max_chars: int = 1600
    chunk_overlap: int = 200
    
    # Force re-sync flag
    force_sync: bool = True  # If True, re-process all pages regardless of last_edited_time


class NotionAstraSync:
    def __init__(self, cfg: SyncConfig):
        self.cfg = cfg
        # Initialize Notion client with optional base url
        if cfg.notion_api_url:
            self.notion = NotionAsyncClient(auth=cfg.notion_token, base_url=cfg.notion_api_url)
        else:
            self.notion = NotionAsyncClient(auth=cfg.notion_token)

        self.openai = AsyncOpenAI(api_key=cfg.openai_api_key)

        client = DataAPIClient()
        self.db = client.get_database(
            cfg.astra_api_endpoint,
            token=cfg.astra_token,
            keyspace=cfg.astra_keyspace,
        )

        self.kb_col = self.db.get_collection(cfg.kb_collection)
        self.state_col = self.db.get_collection(cfg.state_collection)

    async def ensure_collections(self) -> None:
        # list_collections may be async in some versions of the client; handle both
        maybe_collections = self.db.list_collections()
        if asyncio.iscoroutine(maybe_collections):
            collections = await maybe_collections
        else:
            collections = maybe_collections

        existing = {c.name for c in collections}

        if self.cfg.kb_collection not in existing:
            # Build a proper collection definition dict expected by astrapy
            kb_definition = {
                "vector": {
                    "dimension": self.cfg.embed_dim,
                    "metric": VectorMetric.COSINE,
                }
            }
            maybe_create = self.db.create_collection(
                self.cfg.kb_collection,
                definition=kb_definition,
            )
            if asyncio.iscoroutine(maybe_create):
                await maybe_create

        if self.cfg.state_collection not in existing:
            maybe_create_state = self.db.create_collection(self.cfg.state_collection)
            if asyncio.iscoroutine(maybe_create_state):
                await maybe_create_state

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        resp = await self.openai.embeddings.create(
            model=self.cfg.embed_model,
            input=texts,
            encoding_format="float",
        )
        return [d.embedding for d in resp.data]

    def get_state(self, page_id: str) -> Optional[Dict[str, Any]]:
        return self.state_col.find_one({"_id": f"notion:{page_id}"})

    def set_state(self, page_id: str, last_edited_time: str, chunk_ids: List[str]) -> None:
        # Use an upsert to create or replace the state document
        self.state_col.update_one({"_id": f"notion:{page_id}"}, {"$set": {
            "page_id": page_id,
            "last_edited_time": last_edited_time,
            "chunk_ids": chunk_ids,
            "tenant_id": self.cfg.tenant_id,
        }}, upsert=True)

    def delete_existing_chunks(self, chunk_ids: List[str]) -> int:
        if not chunk_ids:
            return 0
        # deterministic delete by id list
        deleted = 0
        # batch deletes to avoid large payloads
        batch_size = 50
        for i in range(0, len(chunk_ids), batch_size):
            batch = chunk_ids[i:i+batch_size]
            res = self.kb_col.delete_many({"_id": {"$in": batch}})
            deleted += getattr(res, "deleted_count", 0) or 0
        return deleted

    async def sync_one_page(self, page_id: str) -> Dict[str, Any]:
        # 1) Retrieve page metadata
        page = await self.notion.pages.retrieve(page_id=page_id)
        last_edited_time = page.get("last_edited_time")
        url = page.get("url")

        if not last_edited_time:
            return {"page_id": page_id, "status": "skipped", "reason": "missing_last_edited_time"}

        # 2) Check incremental sync state
        prev = self.get_state(page_id)
        if not self.cfg.force_sync and prev and prev.get("last_edited_time") == last_edited_time:
            return {"page_id": page_id, "status": "unchanged"}

        # 3) Fetch blocks + render to text
        blocks = await fetch_all_block_children(self.notion, page_id)
        text = blocks_to_text(blocks)
        if not text.strip():
            return {"page_id": page_id, "status": "skipped", "reason": "empty_content"}

        # 4) Chunk (using smart token-aware chunking)
        # AstraDB has 8000 byte limit for indexed strings
        # Use conservative limits to stay well under the cap
        max_tokens = min(300, self.cfg.chunk_max_chars // 4)  # Cap at 300 tokens (~1200 chars)
        overlap_tokens = min(50, self.cfg.chunk_overlap // 4)
        
        chunks = chunk_text_smart(
            text, 
            max_tokens=max_tokens,
            overlap_tokens=overlap_tokens,
            model=self.cfg.embed_model,
            max_bytes=7500  # AstraDB limit is 8000, use 7500 for safety margin
        )
        
        if not chunks:
            return {"page_id": page_id, "status": "skipped", "reason": "no_chunks"}

        # 5) Embed
        vectors = await self.embed_texts(chunks)

        # 6) Delete old chunks (if any)
        old_chunk_ids = (prev or {}).get("chunk_ids", [])
        deleted = self.delete_existing_chunks(old_chunk_ids)

        # 7) Insert new chunks
        new_chunk_ids: List[str] = []
        docs = []
        for idx, (chunk, vec) in enumerate(zip(chunks, vectors)):
            _id = chunk_id(page_id, idx, chunk)
            new_chunk_ids.append(_id)
            docs.append({
                "_id": _id,
                "text": chunk,
                "metadata": {
                    "tenant_id": self.cfg.tenant_id,
                    "source": "notion",
                    "page_id": page_id,
                    "url": url,
                    "last_edited_time": last_edited_time,
                    "chunk_index": idx,
                },
                "$vector": vec,
            })

        self.kb_col.insert_many(docs)

        # 8) Update state
        self.set_state(page_id, last_edited_time, new_chunk_ids)

        return {
            "page_id": page_id,
            "status": "updated",
            "chunks": len(new_chunk_ids),
            "deleted_old": deleted,
            "last_edited_time": last_edited_time,
        }

    async def get_page_ids_from_database(self, database_id: str) -> List[str]:
        """
        Query a Notion database and return a list of page ids. Handles pagination.
        """
        page_ids: List[str] = []
        cursor: Optional[str] = None
        # Notion API allows specifying page_size; keep a moderate value
        page_size = 100
        max_retries = 3
        base_backoff = 1.0
        while True:
            attempt = 0
            while True:
                try:
                    # Some versions of the notion_client don't expose a `query` helper
                    # on the DatabasesEndpoint. Use the client's request API to call
                    # POST /databases/{database_id}/query which returns the rows.
                    body: Dict[str, Any] = {"page_size": page_size}
                    if cursor:
                        body["start_cursor"] = cursor

                    resp = await self.notion.data_sources.query(
                        data_source_id=database_id,
                        start_cursor=cursor,
                        page_size=page_size,
                        max_retries=max_retries,
                        base_backoff=base_backoff
                    )
                    break
                except Exception as e:
                    # Try to detect a 429 status on the raised exception; the Notion SDK
                    # or underlying HTTP library may expose status code on different attrs.
                    status = getattr(e, "status", None) or getattr(e, "status_code", None)
                    # Some HTTP libraries attach `response` with a status_code
                    if status is None:
                        resp_obj = getattr(e, "response", None)
                        status = getattr(resp_obj, "status_code", None) or getattr(resp_obj, "status", None)

                    attempt += 1
                    if attempt >= max_retries or status not in (429, None):
                        # If we've exhausted retries or it's not a rate-limit error, bubble up.
                        raise
                    # otherwise backoff and retry
                    backoff = base_backoff * (2 ** (attempt - 1))
                    await asyncio.sleep(backoff)

            results = resp.get("results", [])
            for r in results:
                pid = r.get("id")
                if pid:
                    page_ids.append(pid)

            if not resp.get("has_more"):
                break
            cursor = resp.get("next_cursor")
        return page_ids

    async def run(self) -> Dict[str, Any]:
        await self.ensure_collections()

        # If no explicit page_ids were provided but a database id is present,
        # fetch the pages from the database.
        page_ids = list(self.cfg.page_ids or [])
        if not page_ids and self.cfg.notion_database_id:
            page_ids = await self.get_page_ids_from_database(self.cfg.notion_database_id)

        if not page_ids:
            return {"summary": {"total": 0, "updated": 0, "unchanged": 0, "skipped": 0}, "results": []}

        sem = asyncio.Semaphore(self.cfg.notion_concurrency)

        async def guarded(pid: str):
            async with sem:
                return await self.sync_one_page(pid)

        results = await asyncio.gather(*(guarded(pid) for pid in page_ids))

        updated = sum(1 for r in results if r.get("status") == "updated")
        unchanged = sum(1 for r in results if r.get("status") == "unchanged")
        skipped = sum(1 for r in results if r.get("status") == "skipped")

        return {
            "summary": {"total": len(results), "updated": updated, "unchanged": unchanged, "skipped": skipped},
            "results": results,
        }


def load_config_from_env() -> SyncConfig:
    # Page IDs as comma-separated string or JSON list
    raw_ids = os.getenv("NOTION_PAGE_IDS") or None # settings.NOTION_PAGE_IDS
    page_ids = None

    if raw_ids:
        if raw_ids.strip().startswith("["):
            import json
            page_ids = json.loads(raw_ids)
        else:
            page_ids = [x.strip() for x in raw_ids.split(",") if x.strip()]

    return SyncConfig(
        notion_token=os.getenv("NOTION_TOKEN"), #settings.NOTION_TOKEN,
        openai_api_key=os.getenv("OPENAI_API_KEY"), #settings.OPENAI_API_KEY,
        page_ids=page_ids,
        # optional database id and api url
        notion_database_id=os.getenv("NOTION_DATABASE_ID"),#settings.NOTION_DATABASE_ID,,
        notion_api_url=os.getenv("NOTION_API_URL"),#settings.NOTION_API_URL

        embed_model=os.getenv("EMBED_MODEL"),#settings.EMBED_MODEL,
        embed_dim=int(os.getenv("EMBED_DIM", "1536")), #settings.EMBED_DIM

        astra_api_endpoint=os.getenv("ASTRA_DB_ENDPOINT"), #settings.ASTRA_DB_ENDPOINT,
        astra_token=os.getenv("ASTRA_DB_TOKEN"),#settings.ASTRA_DB_TOKEN
        astra_keyspace=os.getenv("ASTRA_DB_NAMESPACE", "default_keyspace"),
        kb_collection=os.getenv("ASTRA_KB_COLLECTION", "kb_chunks"),
        state_collection=os.getenv("ASTRA_STATE_COLLECTION", "kb_state"),
        tenant_id=os.getenv("TENANT_ID", "public"),
        chunk_max_chars=int(os.getenv("CHUNK_MAX_CHARS", "1600")), #settings.CHUNK_MAX_CHARS
        chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "200")), #settings.CHUNK_OVERLAP
        notion_concurrency=int(os.getenv("NOTION_CONCURRENCY", "3")), #settings.NOTION_CONCURRENCY)
        force_sync=os.getenv("FORCE_SYNC", "false").lower() in ("true", "1", "yes"),
    )

async def run_sync_threaded() -> Dict[str, Any]:
    from utils.run_in_thread_util import get_threading_util

    cfg = load_config_from_env()
    sync = NotionAstraSync(cfg)

    def _runner():
        import asyncio as _asyncio
        return _asyncio.run(sync.run())

    result = await get_threading_util().run_in_thread(_runner)
    return result


