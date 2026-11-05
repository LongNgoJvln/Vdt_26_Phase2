
import json
import logging
import os
import time
import uuid
import re
from typing import List, Dict, Tuple
from datetime import datetime

from core import feature_flags

logger = logging.getLogger(__name__)

def tokenize(text: str) -> List[str]:
    """Simple tokenizer that splits on whitespace and removes punctuation."""
    return [word.strip('.,!?";') for word in text.split()]

def get_text_similarity(text1: str, text2: str) -> float:
    """Calculate Jaccard similarity between two texts."""
    if not text1 or not text2:
        return 0.0
    
    tokens1 = set(tokenize(text1.lower()))
    tokens2 = set(tokenize(text2.lower()))
    
    if not tokens1 and not tokens2:
        return 1.0
    if not tokens1 or not tokens2:
        return 0.0
        
    intersection = tokens1.intersection(tokens2)
    union = tokens1.union(tokens2)
    
    return len(intersection) / len(union)

class MemoryManager:
    def __init__(self, data_dir: str):
        self.memory_file = os.path.join(data_dir, "memory.json")
        self.ensure_file_exists()
        
    def extract_memory_from_chat(self, chat_history: List[Dict], session_id: str = None) -> List[Dict]:
        """
        Extract memory entries from chat history as a fallback when LLM fails.
        
        Args:
            chat_history: List of chat messages with 'role' and 'content' keys
            session_id: Optional session ID to associate with extracted memories
            
        Returns:
            List of memory entries with text, timestamp, and optional session_id
        """
        memories = []
        
        for msg in chat_history:
            if msg.get("role") == "assistant":
                content = str(msg.get("content", ""))
                lines = content.split('\n')
                
                for line in lines:
                    line = line.strip()
                    # Look for bullet points or numbered lists that might contain memories
                    if re.match(r'^[-*•]|\d+\.', line):
                        # Extract the text after the bullet/number
                        text_match = re.match(r'^[-*•]|\d+\.\s*(.*)', line)
                        if text_match:
                            text = text_match.group(1).strip()
                            if text:
                                memories.append({
                                    "text": text,
                                    "timestamp": int(datetime.now().timestamp()),
                                    "session_id": session_id
                                })
                    # If we see a heading that suggests memories
                    elif re.search(r'memory|fact|note|remember', line, re.I):
                        pass
                    # If we see a clear separator or end
                    elif re.match(r'^={3,}|-{3,}|_{3,}', line):
                        pass
                        
        return memories
        
    def process_inline_memory_command(self, message: str) -> Tuple[bool, str]:
        """
        Check if a message is an inline memory command (e.g. "remember: X").
        
        Args:
            message: The user message to check
            
        Returns:
            Tuple of (is_command, extracted_text) where is_command is True if 
            the message matches the memory command pattern
        """
        # Pattern for memory commands: "remember: X", "memorize: X", "save: X", etc.
        pattern = r'^(?:remember|memorize|save|note|store)[:\-]?\s+(.+)$'
        match = re.match(pattern, message.strip(), re.IGNORECASE)
        
        if match:
            return True, match.group(1).strip()
        else:
            return False, ""
    
    def ensure_file_exists(self):
        """Create memory file if it doesn't exist."""
        if not os.path.exists(self.memory_file):
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
    
    def _db_enabled(self) -> bool:
        return bool(
            feature_flags.features.infra_enabled("memory_in_db")
            and feature_flags.features.infra_enabled("multitenant_postgres")
        )

    def _db_dual_write(self) -> bool:
        return bool(feature_flags.features.infra_enabled("memory_dual_write"))

    @staticmethod
    def _row_to_dict(row) -> Dict:
        return {
            "id": row.id,
            "text": row.text,
            "category": row.category or "fact",
            "source": row.source or "user",
            "owner": row.owner,
            "session_id": row.session_id,
            "timestamp": int(row.timestamp) if row.timestamp is not None else int(time.time()),
        }

    def _db_load_all(self) -> List[Dict]:
        from core.database import Memory, SessionLocal
        out = []
        with SessionLocal() as db:
            rows = db.query(Memory).all()
            for r in rows:
                d = self._row_to_dict(r)
                # Preserve extra client-only fields that have been observed on
                # entries flowing through the in-memory list (pinned, uses).
                # They aren't columns today; read them off the JSON file if
                # present so a flag flip mid-session does not drop them.
                d.setdefault("uses", 0)
                d.setdefault("pinned", False)
                out.append(d)
        return out

    def _db_load_by_owner(self, owner: str) -> List[Dict]:
        from core.database import Memory, SessionLocal
        out = []
        with SessionLocal() as db:
            rows = db.query(Memory).filter(Memory.owner == owner).all()
            for r in rows:
                d = self._row_to_dict(r)
                d.setdefault("uses", 0)
                d.setdefault("pinned", False)
                out.append(d)
        return out

    def _db_upsert_many(self, entries: List[Dict]) -> None:
        if not entries:
            return
        from core import db_upsert
        from core.database import Memory, SessionLocal
        rows = []
        for e in entries:
            e = self._validate_entries([e])[0]
            rows.append({
                "id": e["id"],
                "text": e["text"],
                "category": e.get("category", "fact"),
                "source": e.get("source", "user"),
                "owner": e.get("owner"),
                "session_id": e.get("session_id"),
                "timestamp": int(e.get("timestamp", int(time.time()))),
            })
        with SessionLocal() as db:
            db_upsert.bulk_upsert(db, Memory, ["id"], rows)
            db.commit()

    def _db_delete_ids(self, ids: List[str]) -> int:
        if not ids:
            return 0
        from core.database import Memory, SessionLocal
        with SessionLocal() as db:
            n = db.query(Memory).filter(Memory.id.in_(ids)).delete(synchronize_session=False)
            db.commit()
            return n

    def _db_delete_for_owner_except(self, owner: str, keep: List[str]) -> int:
        from core.database import Memory, SessionLocal
        with SessionLocal() as db:
            q = db.query(Memory).filter(Memory.owner == owner)
            if keep:
                q = q.filter(~Memory.id.in_(keep))
            n = q.delete(synchronize_session=False)
            db.commit()
            return n

    def load_all(self) -> List[Dict]:
        """Load all memory entries from JSON file (unfiltered)."""
        if self._db_enabled():
            return self._db_load_all()

        if not os.path.exists(self.memory_file):
            return []

        try:
            with open(self.memory_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return self._validate_entries(data)
        except (json.JSONDecodeError, PermissionError) as e:
            logger.error("Error loading memory.json: %s", e)
            return self._migrate_from_legacy()

        return []

    def load(self, owner: str = None) -> List[Dict]:
        """Load memory entries, optionally filtered by owner."""
        if owner is not None and self._db_enabled():
            # The DB row is indexed by owner; let PG filter instead of the
            # client. Falling through to load_all would work, but it pulls
            # every tenant's memories into the process per request.
            return self._db_load_by_owner(owner)
        entries = self.load_all()
        if owner is None:
            return entries
        return [e for e in entries if e.get("owner") == owner]

    def claim_ownerless(self, owner: str):
        """Assign all ownerless memory entries to the given owner. Run once to migrate."""
        entries = self.load_all()
        changed = False
        for e in entries:
            if not e.get("owner"):
                e["owner"] = owner
                changed = True
        if changed:
            self.save(entries)
            logger.info("Claimed %d ownerless memories for %s", sum(1 for e in entries if e.get("owner") == owner), owner)

    def delete_entry(self, memory_id: str) -> bool:
        """Row-level delete. Returns True if a row was removed."""
        if self._db_enabled():
            n = self._db_delete_ids([memory_id])
            if not self._db_dual_write():
                return n > 0
        # Legacy / dual-write path: mutate the JSON list.
        entries = self.load_all()
        before = len(entries)
        entries = [e for e in entries if e.get("id") != memory_id]
        if len(entries) == before:
            return False
        tmp_file = self.memory_file + ".tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
        os.replace(tmp_file, self.memory_file)
        return True
    
    def _validate_entries(self, entries: List[Dict]) -> List[Dict]:
        """Ensure all entries have required fields."""
        validated = []
        for entry in entries:
            if "id" not in entry:
                entry["id"] = str(uuid.uuid4())
            if "timestamp" not in entry:
                entry["timestamp"] = int(time.time())
            if "source" not in entry:
                entry["source"] = "unknown"
            if "category" not in entry:
                entry["category"] = "fact"
            validated.append(entry)
        return validated
    
    def _migrate_from_legacy(self) -> List[Dict]:
        """Migrate from old text format to JSON if needed."""
        legacy_path = os.path.join(os.path.dirname(self.memory_file), "memory.txt")
        if not os.path.exists(legacy_path):
            return []
            
        logger.info("Converting legacy memory.txt to new JSON format")
        try:
            with open(legacy_path, "r", encoding="utf-8") as f:
                lines = [ln.strip() for ln in f.readlines() if ln.strip()]
            
            entries = []
            for line in lines:
                entries.append({
                    "id": str(uuid.uuid4()),
                    "text": line,
                    "timestamp": int(time.time()),
                    "source": "user",
                    "category": "fact"
                })
            
            self.save(entries)
            return entries
        except Exception as e:
            logger.error("Failed to convert legacy memory: %s", e)
            return []
    
    def save(self, entries: List[Dict], owner: str = None):
        """Persist memory entries.

        Under the DB flag this is a row-level upsert: every entry in
        ``entries`` is UPSERTed by id. Pass ``owner`` when the save
        represents the complete set for that owner (e.g. delete_memory
        dropped an entry from the list) — the DB row for any id of that
        owner not in ``entries`` is then deleted, so a concurrent
        save from another user is not affected.
        """
        # Validate entries before saving
        for entry in entries:
            if "id" not in entry:
                entry["id"] = str(uuid.uuid4())
            if "timestamp" not in entry:
                entry["timestamp"] = int(time.time())
            if "source" not in entry:
                entry["source"] = "user"
            if "category" not in entry:
                entry["category"] = "fact"

        db_on = self._db_enabled()
        if db_on:
            self._db_upsert_many(entries)
            if owner is not None:
                self._db_delete_for_owner_except(owner, [e["id"] for e in entries])
            if not self._db_dual_write():
                return

        # JSON write (always under flag-off; only under dual-write otherwise)
        tmp_file = self.memory_file + ".tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
        os.replace(tmp_file, self.memory_file)
    
    def add_entry(self, text: str, source: str = "user", category: str = "fact", owner: str = None) -> Dict:
        """Add a new memory entry."""
        if not text.strip():
            raise ValueError("Memory text cannot be empty")

        entry = {
            "id": str(uuid.uuid4()),
            "text": text.strip(),
            "timestamp": int(time.time()),
            "source": source,
            "category": category
        }
        if owner:
            entry["owner"] = owner
        return entry
    
    def find_duplicates(self, text: str, entries: List[Dict] = None) -> List[Dict]:
        """Find duplicate memory entries based on text content."""
        if entries is None:
            entries = self.load()
            
        text_lower = text.strip().lower()
        return [entry for entry in entries if entry["text"].lower() == text_lower]
            
    def categorize_memory_by_relevance(self, message: str, memories: list):
        """Categorize memories by type and relevance"""
        categories = {
            "contacts": [],
            "preferences": [],
            "facts": [],
            "tasks": []
        }
        
        msg_lower = message.lower()
        
        for mem in memories:
            text_lower = mem["text"].lower()
            
            # Contact info
            if any(word in text_lower for word in ["phone", "email", "address", "lives", "works"]):
                if any(word in msg_lower for word in ["contact", "phone", "address", "email"]):
                    categories["contacts"].append(mem)
            
            # Personal preferences
            elif any(word in text_lower for word in ["likes", "dislikes", "prefers", "favorite"]):
                if any(word in msg_lower for word in ["like", "prefer", "favorite", "want"]):
                    categories["preferences"].append(mem)
            
            # Tasks and todos
            elif any(word in text_lower for word in ["todo", "task", "remind", "meeting"]):
                if any(word in msg_lower for word in ["todo", "task", "schedule", "remind"]):
                    categories["tasks"].append(mem)
            
            # General facts - only if very relevant
            else:
                if get_text_similarity(message, mem["text"]) > 0.4:
                    categories["facts"].append(mem)
        
        return categories

    def get_relevant_memories(self, query: str, memories: list, threshold: float = 0.05, max_items: int = 8):
        """Get memories that are relevant to the query based on text similarity and semantic keyword matching."""
        if not memories or not query.strip():
            return []
            
        # Define keyword categories for semantic matching
        identity_words = ["name", "who", "i", "am", "called", "identity", "myself", "me", "my"]
        contact_words = ["phone", "email", "address", "contact", "number", "where", "located", "reach"]
        preference_words = ["like", "prefer", "favorite", "want", "love", "hate", "dislike", "enjoy", "interested"]
        task_words = ["todo", "task", "remind", "meeting", "appointment", "schedule", "deadline"]
        fact_words = ["what", "when", "where", "how", "why", "explain", "describe", "information", "know"]
        
        query_lower = query.lower()
        
        # Determine query type based on keywords
        query_type = None
        if any(word in query_lower for word in identity_words):
            query_type = "identity"
        elif any(word in query_lower for word in contact_words):
            query_type = "contact"
        elif any(word in query_lower for word in preference_words):
            query_type = "preference"
        elif any(word in query_lower for word in task_words):
            query_type = "task"
        elif any(word in query_lower for word in fact_words):
            query_type = "fact"
        
        relevant = []
        identity_memories = []
        other_memories = []
        
        # Separate identity memories from others
        for memory in memories:
            memory_text = memory["text"].lower()
            # Check if this is an identity memory (contains name patterns or identity indicators)
            is_identity = any([
                re.search(r'\b[A-Z][a-z]+ [A-Z][a-z]+\b', memory["text"]),
                any(word in memory_text for word in ["name is", "i'm", "i am", "called", "my name", "named", "call me"])
            ])
            if is_identity:
                identity_memories.append(memory)
            else:
                other_memories.append(memory)
        
        # For identity queries, include all identity memories regardless of similarity
        if query_type == "identity" and identity_memories:
            # Give them high scores to ensure they're included first
            for memory in identity_memories:
                relevant.append((0.9, memory))  # High score for identity memories in identity queries
        
        # Process other memories with similarity scoring
        for memory in other_memories:
            memory_text = memory["text"].lower()
            memory_tokens = set(tokenize(memory_text))
            query_tokens = set(tokenize(query_lower))
            
            # Calculate base Jaccard similarity
            if not query_tokens or not memory_tokens:
                continue
                
            base_similarity = len(query_tokens & memory_tokens) / len(query_tokens | memory_tokens)
            final_score = base_similarity
            
            # Apply boosts based on semantic matching
            if query_type == "contact":
                # Boost memories with contact information
                has_contact_info = any(word in memory_text for word in ["@gmail.com", "@", ".com", 
                                                                     "phone", "number", "address", 
                                                                     "http", "www", "tel:"])
                if has_contact_info:
                    final_score *= 1.4  # 40% boost for contact-related memories
            
            elif query_type == "preference":
                # Boost memories with preference indicators
                has_preference = any(word in memory_text for word in ["like", "love", "hate", "dislike", 
                                                                   "prefer", "favorite", "enjoy", "interested"])
                if has_preference:
                    final_score *= 1.3  # 30% boost for preference-related memories
            
            elif query_type == "task":
                # Boost memories with task indicators
                has_task = any(word in memory_text for word in ["todo", "task", "remind", "meeting", 
                                                              "appointment", "schedule", "deadline", "need to"])
                if has_task:
                    final_score *= 1.3  # 30% boost for task-related memories
            
            # Always consider exact phrase matches as highly relevant
            if query.lower() in memory["text"].lower():
                final_score = max(final_score, 0.8)  # Ensure high relevance for exact matches
            
            # Include memory if it meets threshold after boosts
            if final_score >= threshold:
                relevant.append((final_score, memory))
        
        # Sort by final score (descending) and return top matches
        relevant.sort(key=lambda x: x[0], reverse=True)
        return [mem for _, mem in relevant[:max_items]]
