from __future__ import annotations

import asyncio
import hashlib
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from notion_client import AsyncClient as NotionAsyncClient
from openai import AsyncOpenAI
from astrapy import DataAPIClient
from astrapy.constants import VectorMetric
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

def chunk_text(text: str, max_chars: int = 1600, overlap: int = 200) -> List[str]:
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
        # Add more handlers here as your KB grows:
        # elif t == "code": ...
        # elif t == "toggle": ...
        # elif t == "table": ...
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
        if prev and prev.get("last_edited_time") == last_edited_time:
            return {"page_id": page_id, "status": "unchanged"}

        # 3) Fetch blocks + render to text
        blocks = await fetch_all_block_children(self.notion, page_id)
        text = blocks_to_text(blocks)
        if not text.strip():
            return {"page_id": page_id, "status": "skipped", "reason": "empty_content"}

        # 4) Chunk
        chunks = chunk_text(text, self.cfg.chunk_max_chars, self.cfg.chunk_overlap)
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
    )

async def run_sync() -> Dict[str, Any]:
    cfg = load_config_from_env()
    sync = NotionAstraSync(cfg)

    # Run the async sync.run() inside a thread-safe runner so callers that expect a threaded call
    # don't accidentally get a coroutine object passed into the thread helper.
    def _runner():
        import asyncio as _asyncio
        return _asyncio.run(sync.run())

    # result = await get_threading_util().run_in_thread(_runner)
    result = _runner()
    return result or {}


