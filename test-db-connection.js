import { Pool } from 'pg';
import dotenv from 'dotenv';

dotenv.config({ path: 'github-analyzer-api/.env' });

async function testConnection() {
    console.log('🔍 Testing database connection...');
    console.log('Host:', process.env.DB_HOST);
    console.log('Port:', process.env.DB_PORT);
    console.log('User:', process.env.DB_USER);
    console.log('Database:', process.env.DB_NAME);
    
    // First try connecting to default postgres database
    const defaultPool = new Pool({
        host: process.env.DB_HOST,
        port: parseInt(process.env.DB_PORT || '5432'),
        database: 'postgres', // Connect to default postgres database first
        user: process.env.DB_USER,
        password: process.env.DB_PASSWORD,
    });

    try {
        console.log('\n🔄 Testing connection to default postgres database...');
        const client = await defaultPool.connect();
        console.log('✅ Connected to default postgres database');
        
        // Check if bridgewise_db exists
        const result = await client.query("SELECT 1 FROM pg_database WHERE datname = 'bridgewise_db'");
        
        if (result.rows.length === 0) {
            console.log('⚠️  bridgewise_db does not exist. Creating it...');
            await client.query('CREATE DATABASE bridgewise_db');
            console.log('✅ bridgewise_db created successfully');
        } else {
            console.log('✅ bridgewise_db already exists');
        }
        
        client.release();
        await defaultPool.end();
        
        // Now test connection to bridgewise_db
        const targetPool = new Pool({
            host: process.env.DB_HOST,
            port: parseInt(process.env.DB_PORT || '5432'),
            database: process.env.DB_NAME,
            user: process.env.DB_USER,
            password: process.env.DB_PASSWORD,
        });
        
        console.log('\n🔄 Testing connection to bridgewise_db...');
        const targetClient = await targetPool.connect();
        console.log('✅ Connected to bridgewise_db successfully');
        
        // Test a simple query
        const testResult = await targetClient.query('SELECT NOW()');
        console.log('✅ Query test successful:', testResult.rows[0]);
        
        targetClient.release();
        await targetPool.end();
        
    } catch (error) {
        console.error('❌ Connection failed:', error.message);
        console.error('Error details:', error);
    }
}

testConnection();
