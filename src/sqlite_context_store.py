"""
Production Context Store Implementation

SQLite-backed persistent memory for experience frames with query capabilities.
"""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .context_store import ContextQuery, ContextResult, ContextStore, ExperienceFrame

logger = logging.getLogger(__name__)


class SQLiteContextStore(ContextStore):
    """
    SQLite-backed context store for persistent memory.
    
    Features:
    - Persistent storage of experience frames
    - Full-text search on queries and responses
    - Time-based queries
    - Session management
    - Efficient indexing for fast retrieval
    """

    def __init__(self, db_path: str = "smartglass_memory.db", auto_vacuum: bool = True):
        """
        Initialize SQLite context store.
        
        Args:
            db_path: Path to SQLite database file
            auto_vacuum: Enable auto-vacuum for space efficiency
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Enable dict-like access

        if auto_vacuum:
            self.conn.execute("PRAGMA auto_vacuum = FULL")

        self._create_tables()
        logger.info(f"SQLiteContextStore initialized: {self.db_path}")

    def _create_tables(self):
        """Create database schema if not exists."""
        cursor = self.conn.cursor()

        # Main experience frames table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS experience_frames (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                query TEXT NOT NULL,
                visual_context TEXT,
                response TEXT NOT NULL,
                actions TEXT,
                metadata TEXT,
                session_id TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Full-text search virtual table for queries and responses
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS frames_fts USING fts5(
                query,
                response,
                content='experience_frames',
                content_rowid='id'
            )
        """)

        # Triggers to keep FTS table in sync
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS frames_ai AFTER INSERT ON experience_frames BEGIN
                INSERT INTO frames_fts(rowid, query, response)
                VALUES (new.id, new.query, new.response);
            END
        """)

        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS frames_ad AFTER DELETE ON experience_frames BEGIN
                DELETE FROM frames_fts WHERE rowid = old.id;
            END
        """)

        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS frames_au AFTER UPDATE ON experience_frames BEGIN
                UPDATE frames_fts SET query = new.query, response = new.response
                WHERE rowid = new.id;
            END
        """)

        # Indexes for common queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON experience_frames(timestamp)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_session ON experience_frames(session_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_created_at ON experience_frames(created_at)
        """)

        self.conn.commit()
        logger.debug("Database schema created/verified")

    def write(self, frame: ExperienceFrame) -> None:
        """
        Write experience frame to persistent storage.
        
        Args:
            frame: ExperienceFrame to store
        """
        cursor = self.conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO experience_frames
                (timestamp, query, visual_context, response, actions, metadata, session_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    frame.timestamp,
                    frame.query,
                    frame.visual_context,
                    frame.response,
                    json.dumps(frame.actions),
                    json.dumps(frame.metadata),
                    frame.metadata.get("session_id") if frame.metadata else None,
                ),
            )
            self.conn.commit()
            logger.debug(f"Experience frame written: id={cursor.lastrowid}")

        except sqlite3.Error as e:
            logger.error(f"Failed to write experience frame: {e}")
            raise

    def query(self, query: ContextQuery) -> ContextResult:
        """
        Query context store for relevant experience frames.
        
        Args:
            query: ContextQuery with search parameters
        
        Returns:
            ContextResult with matching frames
        """
        cursor = self.conn.cursor()

        # Build SQL query
        sql_parts = ["SELECT * FROM experience_frames WHERE 1=1"]
        params = []

        # Keyword search using FTS
        if query.keywords:
            keyword_query = " OR ".join(query.keywords)
            sql_parts.append("""
                AND id IN (
                    SELECT rowid FROM frames_fts
                    WHERE frames_fts MATCH ?
                )
            """)
            params.append(keyword_query)

        # Time range filter
        if query.time_range_start or query.time_range_end:
            if query.time_range_start:
                sql_parts.append("AND timestamp >= ?")
                params.append(query.time_range_start)
            if query.time_range_end:
                sql_parts.append("AND timestamp <= ?")
                params.append(query.time_range_end)

        # Session filter
        if query.session_id:
            sql_parts.append("AND session_id = ?")
            params.append(query.session_id)

        # Order by timestamp (newest first)
        sql_parts.append("ORDER BY timestamp DESC")

        # Limit results
        if query.limit:
            sql_parts.append("LIMIT ?")
            params.append(query.limit)

        sql = " ".join(sql_parts)

        try:
            cursor.execute(sql, params)
            rows = cursor.fetchall()

            # Convert rows to ExperienceFrames
            frames = []
            for row in rows:
                frame = ExperienceFrame(
                    timestamp=row["timestamp"],
                    query=row["query"],
                    visual_context=row["visual_context"] or "",
                    response=row["response"],
                    actions=json.loads(row["actions"]) if row["actions"] else [],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                )
                frames.append(frame)

            logger.debug(f"Query returned {len(frames)} frames")

            return ContextResult(frames=frames, total_count=len(frames))

        except sqlite3.Error as e:
            logger.error(f"Failed to query context store: {e}")
            return ContextResult(frames=[], total_count=0)

    def session_state(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get session state summary.
        
        Args:
            session_id: Optional session ID to filter by
        
        Returns:
            Dict with session statistics
        """
        cursor = self.conn.cursor()

        try:
            if session_id:
                # Get stats for specific session
                cursor.execute(
                    """
                    SELECT 
                        COUNT(*) as total_interactions,
                        MIN(timestamp) as first_interaction,
                        MAX(timestamp) as latest_interaction
                    FROM experience_frames
                    WHERE session_id = ?
                """,
                    (session_id,),
                )
            else:
                # Get overall stats
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_interactions,
                        MIN(timestamp) as first_interaction,
                        MAX(timestamp) as latest_interaction,
                        COUNT(DISTINCT session_id) as session_count
                    FROM experience_frames
                """)

            row = cursor.fetchone()

            state = {
                "total_interactions": row["total_interactions"],
                "first_interaction": row["first_interaction"],
                "latest_interaction": row["latest_interaction"],
            }

            if not session_id:
                state["session_count"] = row["session_count"]

            return state

        except sqlite3.Error as e:
            logger.error(f"Failed to get session state: {e}")
            return {"total_interactions": 0}

    def get_recent_frames(self, limit: int = 10) -> List[ExperienceFrame]:
        """
        Get most recent experience frames.
        
        Args:
            limit: Maximum number of frames to return
        
        Returns:
            List of recent ExperienceFrames
        """
        query = ContextQuery(limit=limit)
        result = self.query(query)
        return result.frames

    def search_by_text(self, search_text: str, limit: int = 10) -> List[ExperienceFrame]:
        """
        Search for frames containing specific text.
        
        Args:
            search_text: Text to search for
            limit: Maximum number of results
        
        Returns:
            List of matching ExperienceFrames
        """
        query = ContextQuery(keywords=[search_text], limit=limit)
        result = self.query(query)
        return result.frames

    def clear_old_frames(self, days_to_keep: int = 30) -> int:
        """
        Clear experience frames older than specified days.
        
        Args:
            days_to_keep: Number of days to retain
        
        Returns:
            Number of frames deleted
        """
        cursor = self.conn.cursor()

        try:
            cutoff_date = datetime.now().isoformat()
            cursor.execute(
                """
                DELETE FROM experience_frames
                WHERE julianday('now') - julianday(created_at) > ?
            """,
                (days_to_keep,),
            )
            deleted_count = cursor.rowcount
            self.conn.commit()

            logger.info(f"Cleared {deleted_count} frames older than {days_to_keep} days")
            return deleted_count

        except sqlite3.Error as e:
            logger.error(f"Failed to clear old frames: {e}")
            return 0

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get detailed statistics about stored data.
        
        Returns:
            Dict with statistics
        """
        cursor = self.conn.cursor()

        try:
            # Total frames
            cursor.execute("SELECT COUNT(*) as count FROM experience_frames")
            total_frames = cursor.fetchone()["count"]

            # Database size
            cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
            db_size_bytes = cursor.fetchone()["size"]

            # Sessions
            cursor.execute("SELECT COUNT(DISTINCT session_id) as count FROM experience_frames")
            session_count = cursor.fetchone()["count"]

            # Date range
            cursor.execute("SELECT MIN(timestamp) as first, MAX(timestamp) as last FROM experience_frames")
            row = cursor.fetchone()

            return {
                "total_frames": total_frames,
                "database_size_mb": db_size_bytes / (1024 * 1024),
                "session_count": session_count,
                "first_interaction": row["first"],
                "last_interaction": row["last"],
                "db_path": str(self.db_path),
            }

        except sqlite3.Error as e:
            logger.error(f"Failed to get statistics: {e}")
            return {"error": str(e)}

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("SQLiteContextStore connection closed")

    def __del__(self):
        """Cleanup on deletion."""
        self.close()


if __name__ == "__main__":
    # Example usage
    print("SQLite Context Store - Example Usage")
    print("=" * 60)

    # Initialize context store
    store = SQLiteContextStore(db_path="test_memory.db")

    print("\n✓ Context store initialized")
    stats = store.get_statistics()
    print(f"  Total frames: {stats['total_frames']}")
    print(f"  Database size: {stats['database_size_mb']:.2f} MB")

    # Write sample frame
    print("\n" + "=" * 60)
    print("Writing sample experience frame...")

    frame = ExperienceFrame(
        timestamp=datetime.now().isoformat(),
        query="What is this building?",
        visual_context="Large building with glass facade",
        response="This appears to be a modern office building.",
        actions=[{"type": "identification", "result": "office building"}],
        metadata={"session_id": "test_session_001", "confidence": 0.85},
    )

    store.write(frame)
    print("✓ Frame written")

    # Query frames
    print("\n" + "=" * 60)
    print("Querying recent frames...")

    recent_frames = store.get_recent_frames(limit=5)
    print(f"✓ Found {len(recent_frames)} recent frames")

    for i, frame in enumerate(recent_frames, 1):
        print(f"\n  Frame {i}:")
        print(f"    Query: {frame.query}")
        print(f"    Response: {frame.response[:50]}...")

    # Get statistics
    print("\n" + "=" * 60)
    print("Database Statistics:")
    stats = store.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print("\n✓ Context store ready for production use")
