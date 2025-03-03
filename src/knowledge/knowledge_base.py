"""
Knowledge Base Module

This module implements a comprehensive knowledge base system that manages both
short-term and long-term data storage with efficient retrieval and caching.

Features:
1. Data Management
   - Short-term memory (Redis)
   - Long-term storage (SQLite)
   - Data validation
   - Schema management

2. Knowledge Organization
   - Hierarchical structure
   - Topic categorization
   - Relationship mapping
   - Version control

3. Performance Optimizations
   - Multi-level caching
   - Batch operations
   - Concurrent access
   - Resource management
"""

from typing import Dict, List, Optional, Any, Set, Tuple, Union
from datetime import datetime
import redis
import sqlite3
from pydantic import BaseModel, Field
import asyncio
from dataclasses import dataclass
from enum import Enum
import hashlib
import time
import json
from pathlib import Path
import pickle
from collections import defaultdict

class StorageType(Enum):
    """Enum for storage types."""
    SHORT_TERM = "short_term"  # Redis
    LONG_TERM = "long_term"    # SQLite
    CACHE = "cache"           # Memory cache

class DataType(Enum):
    """Enum for data types."""
    TEXT = "text"
    NUMERIC = "numeric"
    BOOLEAN = "boolean"
    JSON = "json"
    BINARY = "binary"
    LIST = "list"
    SET = "set"
    HASH = "hash"

@dataclass
class DataMetadata:
    """Data class for data metadata."""
    created_at: datetime
    updated_at: datetime
    version: int
    data_type: DataType
    size: int
    tags: Set[str]
    relationships: Dict[str, List[str]]

class KnowledgeEntry(BaseModel):
    """Model for knowledge entries."""
    key: str = Field(..., description="Unique identifier")
    value: Any = Field(..., description="Data value")
    metadata: DataMetadata = Field(..., description="Entry metadata")
    storage_type: StorageType = Field(..., description="Storage location")
    schema_version: str = Field(..., description="Schema version")
    hash: str = Field(..., description="Content hash")

class KnowledgeBase:
    """
    Knowledge base system that manages data storage and retrieval with support
    for both short-term and long-term storage.
    
    Features:
    - Multi-level storage (Redis, SQLite, Memory)
    - Data validation and schema management
    - Efficient caching and retrieval
    - Relationship tracking
    - Version control
    
    Attributes:
        redis_client: Redis client for short-term storage
        db_path: Path to SQLite database
        cache_dir: Directory for caching
        max_cache_size: Maximum size of cache in MB
        _memory_cache: LRU cache for frequently accessed data
        _processing_lock: Lock for concurrent operations
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0",
                 db_path: str = "data/knowledge.db",
                 cache_dir: str = "cache/knowledge",
                 max_cache_size: int = 100):
        # Initialize Redis client
        self.redis_client = redis.from_url(redis_url)
        
        # Setup SQLite database
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        
        # Setup caching
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_cache_size = max_cache_size * 1024 * 1024  # Convert to bytes
        self._memory_cache = {}
        
        # Setup processing
        self._processing_lock = asyncio.Lock()
        self._relationship_graph = defaultdict(set)
        self._schema_version = "1.0.0"
    
    def _init_database(self) -> None:
        """Initialize SQLite database with required tables."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create entries table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS entries (
                        key TEXT PRIMARY KEY,
                        value BLOB,
                        metadata BLOB,
                        storage_type TEXT,
                        schema_version TEXT,
                        hash TEXT,
                        created_at TIMESTAMP,
                        updated_at TIMESTAMP
                    )
                """)
                
                # Create relationships table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS relationships (
                        source_key TEXT,
                        target_key TEXT,
                        relationship_type TEXT,
                        metadata BLOB,
                        created_at TIMESTAMP,
                        PRIMARY KEY (source_key, target_key, relationship_type),
                        FOREIGN KEY (source_key) REFERENCES entries(key),
                        FOREIGN KEY (target_key) REFERENCES entries(key)
                    )
                """)
                
                # Create indices
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_entries_updated_at ON entries(updated_at)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_relationships_source ON relationships(source_key)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_relationships_target ON relationships(target_key)")
                
                conn.commit()
        except Exception as e:
            raise RuntimeError(f"Error initializing database: {str(e)}")
    
    async def store(self, key: str, value: Any, storage_type: StorageType = StorageType.SHORT_TERM,
                   tags: Optional[Set[str]] = None, relationships: Optional[Dict[str, List[str]]] = None) -> None:
        """
        Store data in the knowledge base.
        
        Args:
            key: Unique identifier
            value: Data to store
            storage_type: Storage location
            tags: Optional tags for categorization
            relationships: Optional relationships with other entries
            
        Raises:
            ValueError: If storage fails
            RuntimeError: If storage system is unavailable
        """
        try:
            async with self._processing_lock:
                # Generate content hash
                value_hash = self._generate_hash(value)
                
                # Create metadata
                metadata = DataMetadata(
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    version=1,
                    data_type=self._determine_data_type(value),
                    size=self._calculate_size(value),
                    tags=tags or set(),
                    relationships=relationships or {}
                )
                
                # Create entry
                entry = KnowledgeEntry(
                    key=key,
                    value=value,
                    metadata=metadata,
                    storage_type=storage_type,
                    schema_version=self._schema_version,
                    hash=value_hash
                )
                
                # Store based on type
                if storage_type == StorageType.SHORT_TERM:
                    await self._store_in_redis(entry)
                elif storage_type == StorageType.LONG_TERM:
                    await self._store_in_sqlite(entry)
                
                # Update relationships
                if relationships:
                    await self._update_relationships(key, relationships)
                
                # Update memory cache
                self._memory_cache[key] = entry
                
        except Exception as e:
            raise ValueError(f"Error storing data: {str(e)}")
    
    async def retrieve(self, key: str) -> Optional[KnowledgeEntry]:
        """
        Retrieve data from the knowledge base.
        
        Args:
            key: Unique identifier
            
        Returns:
            KnowledgeEntry if found, None otherwise
            
        Raises:
            ValueError: If retrieval fails
        """
        try:
            # Check memory cache first
            if key in self._memory_cache:
                return self._memory_cache[key]
            
            # Try Redis
            redis_data = await self._retrieve_from_redis(key)
            if redis_data:
                self._memory_cache[key] = redis_data
                return redis_data
            
            # Try SQLite
            sqlite_data = await self._retrieve_from_sqlite(key)
            if sqlite_data:
                self._memory_cache[key] = sqlite_data
                return sqlite_data
            
            return None
            
        except Exception as e:
            raise ValueError(f"Error retrieving data: {str(e)}")
    
    async def update(self, key: str, value: Any, tags: Optional[Set[str]] = None,
                    relationships: Optional[Dict[str, List[str]]] = None) -> None:
        """
        Update existing data in the knowledge base.
        
        Args:
            key: Unique identifier
            value: New value
            tags: Optional new tags
            relationships: Optional new relationships
            
        Raises:
            ValueError: If update fails
        """
        try:
            async with self._processing_lock:
                # Get existing entry
                entry = await self.retrieve(key)
                if not entry:
                    raise ValueError(f"Entry not found: {key}")
                
                # Update value and metadata
                entry.value = value
                entry.metadata.updated_at = datetime.now()
                entry.metadata.version += 1
                entry.metadata.size = self._calculate_size(value)
                entry.hash = self._generate_hash(value)
                
                # Update tags if provided
                if tags is not None:
                    entry.metadata.tags = tags
                
                # Update relationships if provided
                if relationships is not None:
                    await self._update_relationships(key, relationships)
                    entry.metadata.relationships = relationships
                
                # Store updated entry
                await self.store(key, entry.value, entry.storage_type,
                               entry.metadata.tags, entry.metadata.relationships)
                
        except Exception as e:
            raise ValueError(f"Error updating data: {str(e)}")
    
    async def delete(self, key: str) -> None:
        """
        Delete data from the knowledge base.
        
        Args:
            key: Unique identifier
            
        Raises:
            ValueError: If deletion fails
        """
        try:
            async with self._processing_lock:
                # Get entry to determine storage type
                entry = await self.retrieve(key)
                if not entry:
                    raise ValueError(f"Entry not found: {key}")
                
                # Delete based on storage type
                if entry.storage_type == StorageType.SHORT_TERM:
                    await self._delete_from_redis(key)
                elif entry.storage_type == StorageType.LONG_TERM:
                    await self._delete_from_sqlite(key)
                
                # Remove from memory cache
                self._memory_cache.pop(key, None)
                
                # Remove relationships
                await self._remove_relationships(key)
                
        except Exception as e:
            raise ValueError(f"Error deleting data: {str(e)}")
    
    async def search(self, query: str, tags: Optional[Set[str]] = None,
                    storage_type: Optional[StorageType] = None) -> List[KnowledgeEntry]:
        """
        Search for data in the knowledge base.
        
        Args:
            query: Search query
            tags: Optional tags to filter by
            storage_type: Optional storage type to filter by
            
        Returns:
            List of matching KnowledgeEntry objects
            
        Raises:
            ValueError: If search fails
        """
        try:
            results = []
            
            # Search in Redis
            if storage_type in (None, StorageType.SHORT_TERM):
                redis_results = await self._search_in_redis(query, tags)
                results.extend(redis_results)
            
            # Search in SQLite
            if storage_type in (None, StorageType.LONG_TERM):
                sqlite_results = await self._search_in_sqlite(query, tags)
                results.extend(sqlite_results)
            
            return results
            
        except Exception as e:
            raise ValueError(f"Error searching data: {str(e)}")
    
    async def get_related(self, key: str, relationship_type: Optional[str] = None) -> List[KnowledgeEntry]:
        """
        Get related entries for a given key.
        
        Args:
            key: Unique identifier
            relationship_type: Optional relationship type to filter by
            
        Returns:
            List of related KnowledgeEntry objects
            
        Raises:
            ValueError: If retrieval fails
        """
        try:
            # Get relationships from graph
            relationships = self._relationship_graph.get(key, set())
            
            # Filter by type if specified
            if relationship_type:
                relationships = {r for r in relationships if r[0] == relationship_type}
            
            # Get related entries
            related_entries = []
            for _, target_key in relationships:
                entry = await self.retrieve(target_key)
                if entry:
                    related_entries.append(entry)
            
            return related_entries
            
        except Exception as e:
            raise ValueError(f"Error getting related entries: {str(e)}")
    
    async def get_by_tags(self, tags: Set[str], match_all: bool = True) -> List[KnowledgeEntry]:
        """
        Get entries by tags.
        
        Args:
            tags: Set of tags to match
            match_all: Whether to require all tags to match
            
        Returns:
            List of matching KnowledgeEntry objects
            
        Raises:
            ValueError: If retrieval fails
        """
        try:
            results = []
            
            # Search in Redis
            redis_results = await self._get_by_tags_from_redis(tags, match_all)
            results.extend(redis_results)
            
            # Search in SQLite
            sqlite_results = await self._get_by_tags_from_sqlite(tags, match_all)
            results.extend(sqlite_results)
            
            return results
            
        except Exception as e:
            raise ValueError(f"Error getting entries by tags: {str(e)}")
    
    async def cleanup(self) -> None:
        """Clean up expired data and optimize storage."""
        try:
            async with self._processing_lock:
                # Clean up Redis
                await self._cleanup_redis()
                
                # Clean up SQLite
                await self._cleanup_sqlite()
                
                # Clean up memory cache
                await self._cleanup_memory_cache()
                
        except Exception as e:
            raise ValueError(f"Error cleaning up: {str(e)}")
    
    def _determine_data_type(self, value: Any) -> DataType:
        """Determine the data type of a value."""
        if isinstance(value, str):
            return DataType.TEXT
        elif isinstance(value, (int, float)):
            return DataType.NUMERIC
        elif isinstance(value, bool):
            return DataType.BOOLEAN
        elif isinstance(value, dict):
            return DataType.JSON
        elif isinstance(value, bytes):
            return DataType.BINARY
        elif isinstance(value, list):
            return DataType.LIST
        elif isinstance(value, set):
            return DataType.SET
        else:
            return DataType.JSON
    
    def _calculate_size(self, value: Any) -> int:
        """Calculate the size of a value in bytes."""
        try:
            if isinstance(value, (str, bytes)):
                return len(value)
            elif isinstance(value, (int, float)):
                return 8  # Assuming 64-bit numbers
            elif isinstance(value, (list, set, dict)):
                return len(pickle.dumps(value))
            else:
                return len(pickle.dumps(value))
        except Exception:
            return 0
    
    def _generate_hash(self, value: Any) -> str:
        """Generate hash for a value."""
        try:
            if isinstance(value, (str, bytes)):
                return hashlib.sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()
            else:
                return hashlib.sha256(pickle.dumps(value)).hexdigest()
        except Exception:
            return ""
    
    async def _store_in_redis(self, entry: KnowledgeEntry) -> None:
        """Store entry in Redis."""
        try:
            # Serialize entry
            data = pickle.dumps(entry)
            
            # Store in Redis
            self.redis_client.set(entry.key, data)
            
            # Store tags
            if entry.metadata.tags:
                for tag in entry.metadata.tags:
                    self.redis_client.sadd(f"tag:{tag}", entry.key)
            
        except Exception as e:
            raise ValueError(f"Error storing in Redis: {str(e)}")
    
    async def _store_in_sqlite(self, entry: KnowledgeEntry) -> None:
        """Store entry in SQLite."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Serialize data
                value_blob = pickle.dumps(entry.value)
                metadata_blob = pickle.dumps(entry.metadata)
                
                # Insert or update entry
                cursor.execute("""
                    INSERT OR REPLACE INTO entries
                    (key, value, metadata, storage_type, schema_version, hash, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    entry.key,
                    value_blob,
                    metadata_blob,
                    entry.storage_type.value,
                    entry.schema_version,
                    entry.hash,
                    entry.metadata.created_at,
                    entry.metadata.updated_at
                ))
                
                conn.commit()
                
        except Exception as e:
            raise ValueError(f"Error storing in SQLite: {str(e)}")
    
    async def _retrieve_from_redis(self, key: str) -> Optional[KnowledgeEntry]:
        """Retrieve entry from Redis."""
        try:
            data = self.redis_client.get(key)
            if data:
                return pickle.loads(data)
            return None
        except Exception as e:
            raise ValueError(f"Error retrieving from Redis: {str(e)}")
    
    async def _retrieve_from_sqlite(self, key: str) -> Optional[KnowledgeEntry]:
        """Retrieve entry from SQLite."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT value, metadata, storage_type, schema_version, hash, created_at, updated_at
                    FROM entries
                    WHERE key = ?
                """, (key,))
                
                row = cursor.fetchone()
                if row:
                    value = pickle.loads(row[0])
                    metadata = pickle.loads(row[1])
                    
                    return KnowledgeEntry(
                        key=key,
                        value=value,
                        metadata=metadata,
                        storage_type=StorageType(row[2]),
                        schema_version=row[3],
                        hash=row[4]
                    )
                return None
                
        except Exception as e:
            raise ValueError(f"Error retrieving from SQLite: {str(e)}")
    
    async def _delete_from_redis(self, key: str) -> None:
        """Delete entry from Redis."""
        try:
            # Get entry to get tags
            entry = await self._retrieve_from_redis(key)
            if entry:
                # Delete tags
                for tag in entry.metadata.tags:
                    self.redis_client.srem(f"tag:{tag}", key)
                
                # Delete entry
                self.redis_client.delete(key)
        except Exception as e:
            raise ValueError(f"Error deleting from Redis: {str(e)}")
    
    async def _delete_from_sqlite(self, key: str) -> None:
        """Delete entry from SQLite."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM entries WHERE key = ?", (key,))
                conn.commit()
        except Exception as e:
            raise ValueError(f"Error deleting from SQLite: {str(e)}")
    
    async def _search_in_redis(self, query: str, tags: Optional[Set[str]] = None) -> List[KnowledgeEntry]:
        """Search entries in Redis."""
        try:
            results = []
            
            # Get all keys
            keys = self.redis_client.keys("*")
            
            # Filter by tags if specified
            if tags:
                tag_keys = set()
                for tag in tags:
                    tag_keys.update(self.redis_client.smembers(f"tag:{tag}"))
                keys = [k for k in keys if k in tag_keys]
            
            # Search in entries
            for key in keys:
                entry = await self._retrieve_from_redis(key)
                if entry and self._matches_query(entry, query):
                    results.append(entry)
            
            return results
            
        except Exception as e:
            raise ValueError(f"Error searching in Redis: {str(e)}")
    
    async def _search_in_sqlite(self, query: str, tags: Optional[Set[str]] = None) -> List[KnowledgeEntry]:
        """Search entries in SQLite."""
        try:
            results = []
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Build query
                sql = "SELECT key FROM entries WHERE 1=1"
                params = []
                
                if tags:
                    sql += " AND EXISTS (SELECT 1 FROM json_each(metadata->'tags') WHERE value IN ("
                    sql += ",".join("?" * len(tags))
                    sql += "))"
                    params.extend(tags)
                
                cursor.execute(sql, params)
                
                # Get matching entries
                for (key,) in cursor.fetchall():
                    entry = await self._retrieve_from_sqlite(key)
                    if entry and self._matches_query(entry, query):
                        results.append(entry)
            
            return results
            
        except Exception as e:
            raise ValueError(f"Error searching in SQLite: {str(e)}")
    
    def _matches_query(self, entry: KnowledgeEntry, query: str) -> bool:
        """Check if entry matches search query."""
        try:
            # Convert query to lowercase
            query = query.lower()
            
            # Check value
            if isinstance(entry.value, str):
                if query in entry.value.lower():
                    return True
            
            # Check metadata
            if query in str(entry.metadata.tags).lower():
                return True
            
            return False
            
        except Exception:
            return False
    
    async def _update_relationships(self, key: str, relationships: Dict[str, List[str]]) -> None:
        """Update relationships for an entry."""
        try:
            # Remove old relationships
            await self._remove_relationships(key)
            
            # Add new relationships
            for rel_type, target_keys in relationships.items():
                for target_key in target_keys:
                    self._relationship_graph[key].add((rel_type, target_key))
                    
                    # Store in SQLite
                    with sqlite3.connect(self.db_path) as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO relationships
                            (source_key, target_key, relationship_type, metadata, created_at)
                            VALUES (?, ?, ?, ?, ?)
                        """, (
                            key,
                            target_key,
                            rel_type,
                            pickle.dumps({}),
                            datetime.now()
                        ))
                        conn.commit()
            
        except Exception as e:
            raise ValueError(f"Error updating relationships: {str(e)}")
    
    async def _remove_relationships(self, key: str) -> None:
        """Remove all relationships for an entry."""
        try:
            # Remove from graph
            self._relationship_graph.pop(key, None)
            
            # Remove from SQLite
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM relationships WHERE source_key = ?", (key,))
                conn.commit()
            
        except Exception as e:
            raise ValueError(f"Error removing relationships: {str(e)}")
    
    async def _cleanup_redis(self) -> None:
        """Clean up expired data in Redis."""
        try:
            # Implementation for Redis cleanup
            pass
        except Exception as e:
            raise ValueError(f"Error cleaning up Redis: {str(e)}")
    
    async def _cleanup_sqlite(self) -> None:
        """Clean up and optimize SQLite database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Vacuum database
                cursor.execute("VACUUM")
                
                # Analyze tables
                cursor.execute("ANALYZE")
                
                conn.commit()
        except Exception as e:
            raise ValueError(f"Error cleaning up SQLite: {str(e)}")
    
    async def _cleanup_memory_cache(self) -> None:
        """Clean up memory cache."""
        try:
            # Remove old entries
            current_time = time.time()
            self._memory_cache = {
                k: v for k, v in self._memory_cache.items()
                if current_time - v.metadata.updated_at.timestamp() < 3600  # 1 hour
            }
        except Exception as e:
            raise ValueError(f"Error cleaning up memory cache: {str(e)}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics."""
        try:
            stats = {
                "total_entries": 0,
                "short_term_entries": 0,
                "long_term_entries": 0,
                "total_size": 0,
                "cache_size": 0,
                "relationship_count": 0,
                "tag_count": 0
            }
            
            # Get Redis stats
            redis_info = self.redis_client.info()
            stats["short_term_entries"] = redis_info["db0"]["keys"]
            stats["total_size"] += redis_info["used_memory"]
            
            # Get SQLite stats
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(*) FROM entries")
                stats["long_term_entries"] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM relationships")
                stats["relationship_count"] = cursor.fetchone()[0]
            
            # Calculate total entries
            stats["total_entries"] = stats["short_term_entries"] + stats["long_term_entries"]
            
            # Get cache stats
            stats["cache_size"] = len(self._memory_cache)
            
            # Get tag stats
            tag_keys = self.redis_client.keys("tag:*")
            stats["tag_count"] = len(tag_keys)
            
            return stats
            
        except Exception as e:
            raise ValueError(f"Error getting stats: {str(e)}") 