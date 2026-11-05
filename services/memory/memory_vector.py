"""memory_vector.py — shim that re-exports the canonical implementation.

Historical note: this file used to be a divergent copy of
``src/memory_vector.py`` (with a different ``COLLECTION_NAME``). All
callers under ``services/`` now go through the shared Qdrant-backed
class in ``src.memory_vector`` so we don't fork behavior. Kept as a
module because ``services.memory.service`` / ``__init__`` import
``MemoryVectorStore`` from here.
"""

from src.memory_vector import MemoryVectorStore, COLLECTION_NAME

__all__ = ["MemoryVectorStore", "COLLECTION_NAME"]
