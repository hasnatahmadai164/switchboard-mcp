"""
Pinecone tools: semantic search, index discovery, and document upsert/delete.

`semantic_search` and `upsert_documents` take plain text, not raw vectors
-- both call Pinecone's own hosted embedding model (see
settings.pinecone_embedding_model) to convert text to vectors internally,
so this server needs no separate embedding provider or API key. The demo
index must be created with a matching dimension (1024 for the default
multilingual-e5-large model) -- see the Stage 4 setup notes for how.

These functions are plain, undecorated async functions on purpose --
server.py registers them as tools and attaches annotations there.
"""

from typing import Any

from mcp.server.fastmcp import Context
from pinecone import AsyncPinecone

from switchboard.core.config import settings


async def _embed(pinecone_client: AsyncPinecone, texts: list[str], input_type: str) -> list[list[float]]:
    """Converts text to vectors using Pinecone's hosted embedding model.

    `input_type` is "passage" for text being stored, "query" for text
    being searched with -- the model is asymmetric, so passing the wrong
    one silently hurts search relevance rather than raising an error.
    """
    result = await pinecone_client.inference.embed(
        model=settings.pinecone_embedding_model,
        inputs=texts,
        parameters={"input_type": input_type},
    )
    return [record.values for record in result.data]


async def list_indexes(ctx: Context) -> list[str]:
    """List every Pinecone index in this project."""
    pc = ctx.request_context.lifespan_context.pinecone_client
    # pc.indexes.list() is a coroutine in this SDK version (unlike the
    # non-coroutine async-iterator it became in the docs' newer version) --
    # await it, then read the names off the returned IndexList.
    index_list = await pc.indexes.list()
    return index_list.names()


async def semantic_search(index_name: str, query: str, ctx: Context, top_k: int = 10) -> list[dict[str, Any]]:
    """Search an index for records semantically similar to a natural-language query.

    Args:
        index_name: Which Pinecone index to search.
        query: Natural-language search text -- embedded automatically,
               never sent to Pinecone as a raw vector.
        top_k: Maximum number of matches to return.
    """
    pc = ctx.request_context.lifespan_context.pinecone_client
    [vector] = await _embed(pc, [query], input_type="query")

    idx = await pc.index(name=index_name)
    async with idx:
        results = await idx.query(vector=vector, top_k=top_k, include_metadata=True)

    return [{"id": match.id, "score": match.score, "metadata": match.metadata} for match in results.matches]


async def upsert_documents(index_name: str, documents: list[dict[str, Any]], ctx: Context) -> str:
    """Embed and upsert documents into an index. Adds new records or
    overwrites existing ones with the same id -- not destructive to
    anything else in the index.

    Args:
        index_name: Which Pinecone index to write to.
        documents: Each document needs an "id" and a "text" field. `text`
                   is embedded automatically; every other field is stored
                   as retrievable metadata alongside the embedding.
    """
    pc = ctx.request_context.lifespan_context.pinecone_client
    texts = [doc["text"] for doc in documents]
    vectors = await _embed(pc, texts, input_type="passage")

    idx = await pc.index(name=index_name)
    async with idx:
        await idx.upsert(
            vectors=[
                {
                    "id": doc["id"],
                    "values": vector,
                    # Keeping the original text in metadata -- otherwise
                    # a search result is just an id and a score, with
                    # nothing readable to show for it.
                    "metadata": {k: v for k, v in doc.items() if k != "id"},
                }
                for doc, vector in zip(documents, vectors)
            ]
        )
    return f"Upserted {len(documents)} document(s) into '{index_name}'."


async def delete_vectors(index_name: str, ids: list[str], ctx: Context) -> str:
    """Delete records from an index by id. Destructive.

    Args:
        index_name: Which Pinecone index to delete from.
        ids: Record ids to delete.
    """
    pc = ctx.request_context.lifespan_context.pinecone_client
    idx = await pc.index(name=index_name)
    async with idx:
        await idx.delete(ids=ids)
    return f"Deleted {len(ids)} vector(s) from '{index_name}'."