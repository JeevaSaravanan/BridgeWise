#!/usr/bin/env node

import { Pool } from 'pg';
import dotenv from 'dotenv';

dotenv.config({ path: 'github-analyzer-api/.env' });

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

async function checkDatabaseStatus() {
  try {
    console.log('🔍 Checking database status...\n');
    
    // Test connection
    const client = await pool.connect();
    console.log('✅ Database connection: OK');
    
    // Check tables
    const tablesResult = await client.query(`
      SELECT table_name 
      FROM information_schema.tables 
      WHERE table_schema = 'public' 
      ORDER BY table_name
    `);
    
    console.log('\n📊 Tables:');
    if (tablesResult.rows.length === 0) {
      console.log('   No tables found (run migrations first)');
    } else {
      tablesResult.rows.forEach(row => {
        console.log(`   - ${row.table_name}`);
      });
    }
    
    // Check portfolio items count
    try {
      const portfolioResult = await client.query('SELECT COUNT(*) FROM portfolio_items');
      console.log(`\n💼 Portfolio items: ${portfolioResult.rows[0].count}`);
    } catch (error) {
      console.log('\n💼 Portfolio items: Table not found (run migrations)');
    }
    
    // Check executed migrations
    try {
      const migrationsResult = await client.query('SELECT filename FROM migrations ORDER BY id');
      console.log('\n🚀 Executed migrations:');
      if (migrationsResult.rows.length === 0) {
        console.log('   No migrations executed');
      } else {
        migrationsResult.rows.forEach(row => {
          console.log(`   - ${row.filename}`);
        });
      }
    } catch (error) {
      console.log('\n🚀 Migrations: Table not found (first migration not run)');
    }
    
    // Database size
    const sizeResult = await client.query(`
      SELECT pg_size_pretty(pg_database_size('${process.env.DB_NAME || 'bridgewise_db'}')) as size
    `);
    console.log(`\n💾 Database size: ${sizeResult.rows[0].size}`);
    
    // Active connections
    const connectionsResult = await client.query(`
      SELECT count(*) as active_connections 
      FROM pg_stat_activity 
      WHERE state = 'active'
    `);
    console.log(`🔗 Active connections: ${connectionsResult.rows[0].active_connections}`);
    
    client.release();
    console.log('\n✨ Database status check complete!');
    
  } catch (error) {
    console.error('❌ Database connection failed:', error.message);
    console.log('\n💡 Try checking:');
    console.log('   - AWS RDS instance is running and accessible');
    console.log('   - Security groups allow connections on port 5432');
    console.log('   - Database credentials in .env file are correct');
    console.log('   - npm run db:migrate (to run migrations)');
    console.log('   - npm run db:seed (to add sample data)');
  } finally {
    await pool.end();
  }
}

// Run if this is the main module
if (import.meta.url === `file://${process.argv[1]}`) {
  checkDatabaseStatus();
}

export { checkDatabaseStatus };
