#!/usr/bin/env node

import { Pool } from 'pg';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import dotenv from 'dotenv';

dotenv.config({ path: 'github-analyzer-api/.env' });

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Database configuration - prioritize DATABASE_URL for AWS RDS
const getDatabaseConfig = () => {
  const databaseUrl = process.env.DATABASE_URL;
  
  if (databaseUrl) {
    // Parse DATABASE_URL for AWS RDS
    const url = new URL(databaseUrl);
    return {
      host: url.hostname,
      port: parseInt(url.port || '5432'),
      database: url.pathname.slice(1), // Remove leading '/'
      user: url.username,
      password: url.password,
    };
  }
  
  // Fallback to individual environment variables
  return {
    host: process.env.DB_HOST,
    port: parseInt(process.env.DB_PORT || '5432'),
    database: process.env.DB_NAME,
    user: process.env.DB_USER,
    password: process.env.DB_PASSWORD,
  };
};

const pool = new Pool(getDatabaseConfig());

// Create migrations table if it doesn't exist
async function createMigrationsTable() {
  const client = await pool.connect();
  try {
    await client.query(`
      CREATE TABLE IF NOT EXISTS migrations (
        id SERIAL PRIMARY KEY,
        filename VARCHAR(255) NOT NULL UNIQUE,
        executed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
      )
    `);
    console.log('✅ Migrations table ready');
  } finally {
    client.release();
  }
}

// Get executed migrations
async function getExecutedMigrations() {
  const client = await pool.connect();
  try {
    const result = await client.query('SELECT filename FROM migrations ORDER BY id');
    return result.rows.map(row => row.filename);
  } finally {
    client.release();
  }
}

// Execute a migration
async function executeMigration(filename, sql) {
  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    
    // Execute the migration SQL
    await client.query(sql);
    
    // Record the migration
    await client.query(
      'INSERT INTO migrations (filename) VALUES ($1)',
      [filename]
    );
    
    await client.query('COMMIT');
    console.log(`✅ Executed migration: ${filename}`);
  } catch (error) {
    await client.query('ROLLBACK');
    console.error(`❌ Failed to execute migration ${filename}:`, error.message);
    throw error;
  } finally {
    client.release();
  }
}

// Run migrations
async function runMigrations() {
  try {
    console.log('🚀 Starting database migrations...');
    
    // Test connection
    const client = await pool.connect();
    await client.query('SELECT NOW()');
    client.release();
    console.log('✅ Database connection successful');
    
    // Create migrations table
    await createMigrationsTable();
    
    // Get migration files
    const migrationsDir = path.join(__dirname, '../migrations');
    const migrationFiles = fs.readdirSync(migrationsDir)
      .filter(file => file.endsWith('.sql'))
      .sort();
    
    if (migrationFiles.length === 0) {
      console.log('📁 No migration files found');
      return;
    }
    
    // Get executed migrations
    const executedMigrations = await getExecutedMigrations();
    
    // Execute pending migrations
    let executedCount = 0;
    for (const filename of migrationFiles) {
      if (!executedMigrations.includes(filename)) {
        const filePath = path.join(migrationsDir, filename);
        const sql = fs.readFileSync(filePath, 'utf8');
        await executeMigration(filename, sql);
        executedCount++;
      } else {
        console.log(`⏭️  Skipping already executed migration: ${filename}`);
      }
    }
    
    if (executedCount === 0) {
      console.log('✨ All migrations are up to date!');
    } else {
      console.log(`✨ Successfully executed ${executedCount} migration(s)`);
    }
    
  } catch (error) {
    console.error('❌ Migration failed:', error.message);
    process.exit(1);
  } finally {
    await pool.end();
  }
}

// Seed database with sample data
async function seedDatabase() {
  try {
    console.log('🌱 Seeding database with sample data...');
    
    const client = await pool.connect();
    
    // Check if data already exists
    const result = await client.query('SELECT COUNT(*) FROM portfolio_items');
    const count = parseInt(result.rows[0].count);
    
    if (count > 0) {
      console.log('📊 Database already contains data, skipping seed');
      client.release();
      return;
    }
    
    // Insert sample portfolio items
    const sampleItems = [
      {
        title: "React Dashboard Project",
        type: "github",
        url: "https://github.com/user/react-dashboard",
        summary: "A comprehensive analytics dashboard built with React, TypeScript, and D3.js featuring real-time data visualization and user management.",
        skills: ["React", "TypeScript", "D3.js", "API Design"],
        thumbnail: "📊"
      },
      {
        title: "Product Strategy Deck",
        type: "file",
        summary: "Strategic roadmap for launching a new mobile product feature, including market analysis, user personas, and go-to-market strategy.",
        skills: ["Product Strategy", "Market Analysis", "User Research"],
        thumbnail: "📋"
      },
      {
        title: "ML Model Documentation",
        type: "url",
        url: "https://docs.example.com/ml-model",
        summary: "Complete documentation for a machine learning model that predicts customer churn with 89% accuracy using Python and scikit-learn.",
        skills: ["Machine Learning", "Python", "Data Analysis"],
        thumbnail: "🤖"
      }
    ];
    
    for (const item of sampleItems) {
      await client.query(`
        INSERT INTO portfolio_items (title, type, url, summary, skills, thumbnail)
        VALUES ($1, $2, $3, $4, $5, $6)
      `, [
        item.title,
        item.type,
        item.url || null,
        item.summary,
        JSON.stringify(item.skills),
        item.thumbnail
      ]);
    }
    
    client.release();
    console.log('✅ Sample data seeded successfully');
    
  } catch (error) {
    console.error('❌ Seeding failed:', error.message);
    process.exit(1);
  } finally {
    await pool.end();
  }
}

// Main function
async function main() {
  const command = process.argv[2];
  
  switch (command) {
    case 'migrate':
      await runMigrations();
      break;
    case 'seed':
      await seedDatabase();
      break;
    case 'reset':
      console.log('🗑️  Resetting database...');
      await runMigrations();
      await seedDatabase();
      break;
    default:
      console.log(`
Usage: node scripts/migrate.js <command>

Commands:
  migrate  - Run pending migrations
  seed     - Seed database with sample data
  reset    - Reset database (migrate + seed)
      `);
  }
}

// Run if this is the main module
if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch(console.error);
}

export { runMigrations, seedDatabase };
