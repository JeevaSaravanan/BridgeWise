import asyncpg
import os
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
        database_url = os.getenv('DATABASE_URL')
        if database_url:
            self.connection_string = database_url
        else:
            self.connection_string = (
                f"postgresql://{os.getenv('DB_USER')}:"
                f"{os.getenv('DB_PASSWORD')}@"
                f"{os.getenv('DB_HOST')}:"
                f"{os.getenv('DB_PORT', '5432')}/"
                f"{os.getenv('DB_NAME')}"
            )
        self.pool = None

    async def initialize(self):
        """Initialize database connection pool"""
        try:
            print(f"🔄 Attempting to connect to: {self.connection_string.split('@')[1] if '@' in self.connection_string else 'database'}")
            
            self.pool = await asyncpg.create_pool(
                self.connection_string,
                min_size=1,
                max_size=10,
                command_timeout=60,  # 60 seconds command timeout
                server_settings={
                    'application_name': 'bridgewise_app',
                    'jit': 'off'
                }
            )
            print("✅ Database connection pool initialized")
            
            # Test the connection
            async with self.pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                print(f"✅ Database connection test successful: {result}")
                
        except Exception as e:
            error_msg = str(e).lower()
            print(f"❌ Failed to initialize database: {e}")
            
            if "does not exist" in error_msg:
                print("💡 Database does not exist - please create the 'bridgewise_db' database first")
            elif "authentication" in error_msg or "password" in error_msg:
                print("💡 Authentication failed - please check your username and password")
            elif "connection" in error_msg and ("refused" in error_msg or "timeout" in error_msg):
                print("💡 Connection failed - please check:")
                print("   - AWS RDS instance is running")
                print("   - Security groups allow port 5432 from your IP")
                print("   - VPC settings allow public access")
                print("   - Your network allows outbound connections to AWS")
            
            print(f"💡 Connection details: postgresql://***:***@{self.connection_string.split('@')[1] if '@' in self.connection_string else 'unknown'}")
            raise

    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()

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
                    "createdAt": row["created_at"].isoformat() if row["created_at"] else None,
                    "updatedAt": row["updated_at"].isoformat() if row["updated_at"] else None
                }
                for row in rows
            ]

    async def create_portfolio_item(self, item_data: Dict) -> Dict:
        """Create a new portfolio item"""
        async with self.pool.acquire() as conn:
            item_id = str(uuid.uuid4())
            
            row = await conn.fetchrow("""
                INSERT INTO portfolio_items (
                    id, title, type, url, summary, skills, thumbnail, analysis_result
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING 
                    id,
                    title,
                    type,
                    url,
                    summary,
                    skills,
                    thumbnail,
                    analysis_result,
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
                json.dumps(item_data.get("analysisResult")) if item_data.get("analysisResult") else None
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
                    "createdAt": row["created_at"].isoformat() if row["created_at"] else None,
                    "updatedAt": row["updated_at"].isoformat() if row["updated_at"] else None
                }
                for row in rows
            ]

# Global database manager instance
db_manager = DatabaseManager()
