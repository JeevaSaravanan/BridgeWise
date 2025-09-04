import asyncpg
import os
import asyncio
from dotenv import load_dotenv
from typing import List, Dict, Optional
import json
from datetime import datetime
import uuid

# Load environment variables
load_dotenv()

class DatabaseManager:
    def __init__(self):
        # Use DATABASE_URL if provided, otherwise construct from individual components
        db_host = os.getenv('DB_HOST')
        db_name = os.getenv('DB_NAME')
        db_user = os.getenv('DB_USER')
        db_password = os.getenv('DB_PASSWORD')
        database_url = os.getenv('DATABASE_URL')

        if db_host and db_name and db_user and db_password:
            self.connection_string = (
                f"postgresql://{db_user}:{db_password}@{db_host}:{os.getenv('DB_PORT', '5432')}/{db_name}"
            )
        elif database_url:
            self.connection_string = database_url
        else:
            self.connection_string = "postgresql://postgres:postgres@localhost:5432/postgres"
        self.pool = None

    async def initialize(self):
        """Initialize database connection pool"""
        attempts = int(os.getenv('DB_CONNECT_RETRIES', '5'))
        initial_delay = float(os.getenv('DB_CONNECT_INITIAL_DELAY', '1'))
        max_delay = float(os.getenv('DB_CONNECT_MAX_DELAY', '15'))
        delay = initial_delay
        target = self.connection_string.split('@')[1] if '@' in self.connection_string else self.connection_string
        print(f"🔄 Attempting DB connect: {target} (max {attempts} attempts)")
        last_error = None
        for attempt in range(1, attempts + 1):
            try:
                self.pool = await asyncpg.create_pool(
                    self.connection_string,
                    min_size=1,
                    max_size=10,
                    command_timeout=60,
                    server_settings={'application_name': 'bridgewise_app', 'jit': 'off'}
                )
                print("✅ DB pool initialized")
                async with self.pool.acquire() as conn:
                    result = await conn.fetchval("SELECT 1")
                print(f"✅ DB test query returned: {result}")
                return
            except Exception as e:
                last_error = e
                msg = str(e).lower()
                print(f"❌ DB connection attempt {attempt}/{attempts} failed: {e}")
                if attempt == 1:
                    if "does not exist" in msg:
                        print("💡 Database missing - create it (CREATE DATABASE ...)")
                    elif any(k in msg for k in ["auth", "password"]):
                        print("💡 Auth issue - verify DB_USER / DB_PASSWORD")
                    elif any(k in msg for k in ["refused", "timeout", "unreachable", "could not connect"]):
                        print("💡 Network issue - verify host/port, security groups, firewall, server status")
                if attempt < attempts:
                    print(f"⏳ Retrying in {delay:.1f}s...")
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, max_delay)
        print("💥 All DB connection attempts failed. Proceeding without database (read-only AI features still available).")
        print(f"💡 Last error: {last_error}")
        print(f"💡 Connection details (masked): postgresql://***:***@{target}")
        self.pool = None  # Degraded mode
        return

    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            print("🔌 DB pool closed")

    def is_ready(self) -> bool:
        return self.pool is not None

    async def get_all_portfolio_items(self) -> List[Dict]:
        """Get all portfolio items"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT 
                    id,
                    title,
                    type,
                    url,
                    summary,
                    skills,
                    thumbnail,
                    analysis_result,
                    skill_visibility,
                    created_at,
                    updated_at
                FROM portfolio_items 
                ORDER BY created_at DESC
            """)
            
            return [
                {
                    "id": str(row["id"]),
                    "title": row["title"],
                    "type": row["type"],
                    "url": row["url"],
                    "summary": row["summary"],
                    "skills": row["skills"] if isinstance(row["skills"], list) else (json.loads(row["skills"]) if row["skills"] else []),
                    "thumbnail": row["thumbnail"],
                    "analysisResult": row["analysis_result"] if row["analysis_result"] is None else (
                        row["analysis_result"] if isinstance(row["analysis_result"], dict) else json.loads(row["analysis_result"])
                    ),
                    "skillVisibility": {} if row["skill_visibility"] is None else (
                        row["skill_visibility"] if isinstance(row["skill_visibility"], dict) else json.loads(row["skill_visibility"])
                    ),
                    "createdAt": row["created_at"].isoformat() if row["created_at"] else None,
                    "updatedAt": row["updated_at"].isoformat() if row["updated_at"] else None
                }
                for row in rows
            ]

    async def create_portfolio_item(self, item_data: Dict) -> Dict:
        """Create a new portfolio item"""
        async with self.pool.acquire() as conn:
            # Optional lightweight deduplication (guards against immediate double POSTs from dev tools / React StrictMode)
            if os.getenv('ENFORCE_PORTFOLIO_DEDUP', '1') == '1':
                natural_keys = [
                    item_data.get("title"),
                    item_data.get("type"),
                    item_data.get("url"),
                    item_data.get("summary")
                ]
                if all(natural_keys[:2]):  # require at least title & type
                    existing = await conn.fetchrow(
                        """
                        SELECT id, title, type, url, summary, skills, thumbnail, analysis_result, created_at, updated_at
                        FROM portfolio_items
                        WHERE title = $1 AND type = $2 AND COALESCE(url,'') = COALESCE($3,'') AND summary = $4
                        ORDER BY created_at DESC
                        LIMIT 1
                        """,
                        item_data.get("title"),
                        item_data.get("type"),
                        item_data.get("url"),
                        item_data.get("summary")
                    )
                    if existing:
                        # Return existing to keep endpoint idempotent for identical payload
                        return {
                            "id": str(existing["id"]),
                            "title": existing["title"],
                            "type": existing["type"],
                            "url": existing["url"],
                            "summary": existing["summary"],
                            "skills": json.loads(existing["skills"]) if existing["skills"] else [],
                            "thumbnail": existing["thumbnail"],
                            "analysisResult": json.loads(existing["analysis_result"]) if existing["analysis_result"] else None,
                            "createdAt": existing["created_at"].isoformat() if existing["created_at"] else None,
                            "updatedAt": existing["updated_at"].isoformat() if existing["updated_at"] else None
                        }
            item_id = str(uuid.uuid4())
            
            # Debug logging for skill visibility
            item_type = item_data["type"]
            skill_visibility_data = item_data.get("skillVisibility", {})
            print(f"Creating portfolio item type: {item_type}")
            print(f"skill_visibility data: {skill_visibility_data}")
            if item_type in ['file', 'github'] and (not skill_visibility_data or len(skill_visibility_data) == 0):
                print("WARNING: Empty skill_visibility for file/github type!")
                print(f"Item data: {item_data}")
            
            row = await conn.fetchrow("""
                INSERT INTO portfolio_items (
                    id, title, type, url, summary, skills, thumbnail, analysis_result, skill_visibility
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING 
                    id,
                    title,
                    type,
                    url,
                    summary,
                    skills,
                    thumbnail,
                    analysis_result,
                    skill_visibility,
                    created_at,
                    updated_at
            """, 
                item_id,
                item_data["title"],
                item_data["type"],
                item_data.get("url"),
                item_data["summary"],
                json.dumps(item_data.get("skills", [])),
                item_data.get("thumbnail", "📄"),
                json.dumps(item_data.get("analysisResult")) if item_data.get("analysisResult") else None,
                json.dumps(item_data.get("skillVisibility", {})) # New field for skill visibility
            )
            
            return {
                "id": str(row["id"]),
                "title": row["title"],
                "type": row["type"],
                "url": row["url"],
                "summary": row["summary"],
                "skills": json.loads(row["skills"]) if row["skills"] else [],
                "thumbnail": row["thumbnail"],
                "analysisResult": json.loads(row["analysis_result"]) if row["analysis_result"] else None,
                "skillVisibility": json.loads(row["skill_visibility"]) if row["skill_visibility"] else {},
                "createdAt": row["created_at"].isoformat() if row["created_at"] else None,
                "updatedAt": row["updated_at"].isoformat() if row["updated_at"] else None
            }

    async def update_portfolio_item(self, item_id: str, updates: Dict) -> Optional[Dict]:
        """Update an existing portfolio item"""
        async with self.pool.acquire() as conn:
            # Build dynamic update query
            set_clauses = []
            values = []
            param_count = 1

            if "title" in updates:
                set_clauses.append(f"title = ${param_count}")
                values.append(updates["title"])
                param_count += 1

            if "summary" in updates:
                set_clauses.append(f"summary = ${param_count}")
                values.append(updates["summary"])
                param_count += 1

            if "skills" in updates:
                set_clauses.append(f"skills = ${param_count}")
                values.append(json.dumps(updates["skills"]))
                param_count += 1

            if "url" in updates:
                set_clauses.append(f"url = ${param_count}")
                values.append(updates["url"])
                param_count += 1

            if "analysisResult" in updates:
                set_clauses.append(f"analysis_result = ${param_count}")
                values.append(json.dumps(updates["analysisResult"]) if updates["analysisResult"] else None)
                param_count += 1

            if "skillVisibility" in updates:
                set_clauses.append(f"skill_visibility = ${param_count}")
                values.append(json.dumps(updates["skillVisibility"]))
                param_count += 1

            if not set_clauses:
                raise ValueError("No valid updates provided")

            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            values.append(item_id)

            query = f"""
                UPDATE portfolio_items 
                SET {', '.join(set_clauses)}
                WHERE id = ${param_count}
                RETURNING 
                    id,
                    title,
                    type,
                    url,
                    summary,
                    skills,
                    thumbnail,
                    analysis_result,
                    skill_visibility,
                    created_at,
                    updated_at
            """

            row = await conn.fetchrow(query, *values)
            
            if not row:
                return None

            return {
                "id": str(row["id"]),
                "title": row["title"],
                "type": row["type"],
                "url": row["url"],
                "summary": row["summary"],
                "skills": json.loads(row["skills"]) if row["skills"] else [],
                "thumbnail": row["thumbnail"],
                "analysisResult": json.loads(row["analysis_result"]) if row["analysis_result"] else None,
                "skillVisibility": json.loads(row["skill_visibility"]) if row["skill_visibility"] else {},
                "createdAt": row["created_at"].isoformat() if row["created_at"] else None,
                "updatedAt": row["updated_at"].isoformat() if row["updated_at"] else None
            }

    async def delete_portfolio_item(self, item_id: str) -> bool:
        """Delete a portfolio item"""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM portfolio_items WHERE id = $1",
                item_id
            )
            return result != "DELETE 0"

    async def get_portfolio_stats(self) -> Dict:
        """Get portfolio statistics"""
        async with self.pool.acquire() as conn:
            # Get total count
            total_count = await conn.fetchval("SELECT COUNT(*) FROM portfolio_items")
            
            # Get skills
            skills_rows = await conn.fetch("""
                SELECT DISTINCT jsonb_array_elements_text(skills::jsonb) as skill 
                FROM portfolio_items 
                WHERE skills IS NOT NULL AND skills != 'null'
            """)
            unique_skills = [row["skill"] for row in skills_rows]
            
            # Get type breakdown
            type_rows = await conn.fetch("""
                SELECT type, COUNT(*) as count 
                FROM portfolio_items 
                GROUP BY type
            """)
            type_breakdown = {row["type"]: row["count"] for row in type_rows}
            
            return {
                "totalItems": total_count,
                "skillCount": len(unique_skills),
                "typeBreakdown": type_breakdown,
                "uniqueSkills": unique_skills
            }

    async def search_portfolio_items(self, query: str) -> List[Dict]:
        """Search portfolio items by title, summary, or skills"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT 
                    id,
                    title,
                    type,
                    url,
                    summary,
                    skills,
                    thumbnail,
                    analysis_result,
                    skill_visibility,
                    created_at,
                    updated_at
                FROM portfolio_items 
                WHERE 
                    title ILIKE $1 
                    OR summary ILIKE $1 
                    OR skills::text ILIKE $1
                ORDER BY created_at DESC
            """, f"%{query}%")
            
            return [
                {
                    "id": str(row["id"]),
                    "title": row["title"],
                    "type": row["type"],
                    "url": row["url"],
                    "summary": row["summary"],
                    "skills": json.loads(row["skills"]) if row["skills"] else [],
                    "thumbnail": row["thumbnail"],
                    "analysisResult": json.loads(row["analysis_result"]) if row["analysis_result"] else None,
                    "skillVisibility": json.loads(row["skill_visibility"]) if row["skill_visibility"] else {},
                    "createdAt": row["created_at"].isoformat() if row["created_at"] else None,
                    "updatedAt": row["updated_at"].isoformat() if row["updated_at"] else None
                }
                for row in rows
            ]

# Global database manager instance
db_manager = DatabaseManager()
