#!/usr/bin/env python3
"""
scripts/migrate_minio_paths.py

Migrate existing MinIO objects from the legacy `userdata/{user_id}/...` structure
to the new session/library separation:
  - Session files: {owner}/sessions/{session_id}/uploads/{upload_id}
  - Library files: {owner}/library/{doc_id}

This script:
1. Scans the MinIO bucket for existing objects under userdata/ prefix
2. Determines the appropriate scope based on metadata or heuristics
3. Moves/renames objects to the new structure
4. Updates database records with new storage_path values

Usage:
    python scripts/migrate_minio_paths.py [--dry-run] [--force]

Options:
    --dry-run   Show what would be migrated without making changes
    --force     Skip confirmation prompt
"""

import argparse
import logging
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import text
from core.database import SessionLocal, Document, FileScope
from src.object_store import store as object_store, _BUCKET

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)


def list_all_user_objects() -> List[str]:
    """List all objects under userdata/ prefix."""
    if not object_store.healthy:
        logger.warning("Object store not healthy, cannot list objects")
        return []
    
    objects = []
    try:
        for obj in object_store._client.list_objects(_BUCKET, prefix="userdata/", recursive=True):
            objects.append(obj.object_name)
    except Exception as e:
        logger.error(f"Failed to list objects: {e}")
    return objects


def parse_user_object_key(key: str) -> Optional[Tuple[str, str]]:
    """Parse a MinIO object key into (user_id, relative_path).
    
    Expected format: userdata/{user_id}/{relative_path}
    """
    if not key.startswith("userdata/"):
        return None
    
    parts = key.split("/", 2)
    if len(parts) < 3:
        return None
    
    return parts[1], parts[2]


def determine_file_scope(doc_id: Optional[str], session_id: Optional[str]) -> str:
    """Determine file scope based on document metadata.
    
    Returns 'session' if session_id is present, 'library' otherwise.
    """
    if session_id:
        return FileScope.SESSION.value
    return FileScope.LIBRARY.value


def get_document_by_upload_id(upload_id: str) -> Optional[Document]:
    """Find a document by its upload ID (stored in metadata or title)."""
    with SessionLocal() as db:
        # Try to find by storage_path containing the upload_id
        doc = db.query(Document).filter(
            Document.storage_path.like(f"%{upload_id}%")
        ).first()
        return doc


def migrate_object(
    old_key: str,
    owner: str,
    relative_path: str,
    doc: Optional[Document] = None,
    dry_run: bool = False
) -> Dict:
    """Migrate a single object to the new structure.
    
    Returns migration result dictionary.
    """
    result = {
        "old_key": old_key,
        "new_key": None,
        "success": False,
        "error": None,
    }
    
    # Determine scope and compute new path
    file_scope = determine_file_scope(doc.id if doc else None, doc.session_id if doc else None)
    
    # Extract upload/doc ID from relative path
    # Legacy format: uploads/YYYY/MM/DD/upload_id.ext or just upload_id.ext
    path_parts = relative_path.split("/")
    filename = path_parts[-1]
    
    if file_scope == FileScope.SESSION.value and doc and doc.session_id:
        # Session file: {owner}/sessions/{session_id}/uploads/{filename}
        new_relative = f"sessions/{doc.session_id}/uploads/{filename}"
    else:
        # Library file: {owner}/library/{filename}
        new_relative = f"library/{filename}"
    
    new_key = f"{owner}/{new_relative}"
    result["new_key"] = new_key
    result["file_scope"] = file_scope
    
    if dry_run:
        logger.info(f"[DRY-RUN] Would migrate: {old_key} -> {new_key} (scope: {file_scope})")
        result["success"] = True
        return result
    
    # Perform the migration
    try:
        # Get the object
        obj_data = object_store.get_user_object(owner, relative_path)
        if obj_data is None:
            result["error"] = "Failed to read source object"
            return result
        
        # Delete old object
        object_store.delete_user_object(owner, relative_path)
        
        # Put new object with correct path
        from io import BytesIO
        import mimetypes
        
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        
        if file_scope == FileScope.SESSION.value and doc and doc.session_id:
            object_store.put_session_file(owner, doc.session_id, filename, obj_data, content_type)
        else:
            object_store.put_library_file(owner, filename, obj_data, content_type)
        
        result["success"] = True
        logger.info(f"Migrated: {old_key} -> {new_key}")
        
        # Update database record
        if doc:
            with SessionLocal() as db:
                db_doc = db.query(Document).filter(Document.id == doc.id).first()
                if db_doc:
                    db_doc.file_scope = file_scope
                    db_doc.storage_path = new_key
                    db.commit()
                    logger.info(f"Updated database for document {doc.id}")
        
        return result
        
    except Exception as e:
        result["error"] = str(e)
        logger.error(f"Failed to migrate {old_key}: {e}")
        return result


def run_migration(dry_run: bool = False, force: bool = False) -> Dict:
    """Run the full migration process.
    
    Returns migration statistics.
    """
    stats = {
        "total_objects": 0,
        "migrated": 0,
        "failed": 0,
        "skipped": 0,
        "session_files": 0,
        "library_files": 0,
        "errors": [],
    }
    
    if not object_store.healthy:
        logger.error("Object store not healthy. Check MinIO configuration.")
        return stats
    
    logger.info("Scanning for objects to migrate...")
    objects = list_all_user_objects()
    stats["total_objects"] = len(objects)
    
    if not objects:
        logger.info("No objects found under userdata/ prefix")
        return stats
    
    logger.info(f"Found {len(objects)} objects to process")
    
    if dry_run:
        logger.info("Running in DRY-RUN mode - no changes will be made")
    elif not force:
        response = input(f"\nMigrate {len(objects)} objects? (yes/no): ")
        if response.lower() != "yes":
            logger.info("Migration cancelled by user")
            return stats
    
    for old_key in objects:
        parsed = parse_user_object_key(old_key)
        if not parsed:
            logger.warning(f"Skipping unrecognized key format: {old_key}")
            stats["skipped"] += 1
            continue
        
        owner, relative_path = parsed
        
        # Try to find associated document
        doc = None
        try:
            # Extract potential upload ID from path
            filename = relative_path.split("/")[-1]
            doc = get_document_by_upload_id(filename)
        except Exception as e:
            logger.debug(f"Could not find document for {old_key}: {e}")
        
        # Migrate the object
        result = migrate_object(old_key, owner, relative_path, doc, dry_run)
        
        if result["success"]:
            stats["migrated"] += 1
            if result.get("file_scope") == FileScope.SESSION.value:
                stats["session_files"] += 1
            else:
                stats["library_files"] += 1
        else:
            stats["failed"] += 1
            stats["errors"].append({
                "key": old_key,
                "error": result["error"],
            })
    
    return stats


def print_summary(stats: Dict) -> None:
    """Print migration summary."""
    print("\n" + "=" * 60)
    print("MIGRATION SUMMARY")
    print("=" * 60)
    print(f"Total objects scanned: {stats['total_objects']}")
    print(f"Successfully migrated: {stats['migrated']}")
    print(f"  - Session files: {stats['session_files']}")
    print(f"  - Library files: {stats['library_files']}")
    print(f"Failed: {stats['failed']}")
    print(f"Skipped: {stats['skipped']}")
    
    if stats["errors"]:
        print(f"\nErrors ({len(stats['errors'])}):")
        for err in stats["errors"][:10]:  # Show first 10 errors
            print(f"  - {err['key']}: {err['error']}")
        if len(stats["errors"]) > 10:
            print(f"  ... and {len(stats['errors']) - 10} more")
    
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Migrate MinIO objects to new session/library structure")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be migrated without making changes")
    parser.add_argument("--force", action="store_true", help="Skip confirmation prompt")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info("Starting MinIO path migration")
    logger.info(f"Bucket: {_BUCKET}")
    logger.info(f"Object store healthy: {object_store.healthy}")
    
    stats = run_migration(dry_run=args.dry_run, force=args.force)
    print_summary(stats)
    
    if stats["failed"] > 0 and not args.dry_run:
        sys.exit(1)


if __name__ == "__main__":
    main()
