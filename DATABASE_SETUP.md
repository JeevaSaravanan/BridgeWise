# AWS RDS PostgreSQL Database Setup for BridgeWise

## Overview
BridgeWise uses **AWS RDS PostgreSQL** for production-ready database hosting with automatic backups, scaling, and high availability.

## Prerequisites

- AWS Account with RDS access
- AWS RDS PostgreSQL instance configured
- Security groups properly configured to allow connections

## Quick Setup

### 1. AWS RDS Configuration

Your AWS RDS PostgreSQL instance should be configured with:
- **Engine**: PostgreSQL 15+
- **Instance Class**: db.t3.micro or higher
- **Storage**: 20GB minimum
- **Security Group**: Allow inbound port 5432 from your development machine
- **Public Access**: Enabled (for development) or VPC access configured

### 2. Environment Configuration

Copy the environment template and configure with your AWS RDS credentials:

```bash
cp github-analyzer-api/.env.example github-analyzer-api/.env
```

Update the `.env` file with your AWS RDS information:
```bash
# AWS RDS PostgreSQL Database Configuration
DATABASE_URL=postgresql://username:password@database-apb-instance-1.cmfwqqwe0oei.us-east-1.rds.amazonaws.com:5432/bridgewise_db
DB_HOST=database-apb-instance-1.cmfwqqwe0oei.us-east-1.rds.amazonaws.com
DB_PORT=5432
DB_NAME=bridgewise_db
DB_USER=your_db_username
DB_PASSWORD=your_db_password

# Azure OpenAI Configuration
AZURE_OPENAI_KEY=your_azure_openai_api_key_here

# GitHub Token (optional, for higher rate limits)
GITHUB_TOKEN=your_github_token_here

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
```

### 3. Install Dependencies

```bash
# Install Node.js dependencies
npm install

# Install Python dependencies for the API
cd github-analyzer-api
pip install -r requirements.txt
```

### 4. Create Database (if not exists)

Connect to your AWS RDS instance and create the database:

```bash
# Connect to RDS (replace with your actual credentials)
psql "postgresql://username:password@database-apb-instance-1.cmfwqqwe0oei.us-east-1.rds.amazonaws.com:5432/postgres"

# Create database
CREATE DATABASE bridgewise_db;
\q
```

### 5. Run Database Migrations

```bash
npm run db:migrate
```

### 6. Seed Sample Data (Optional)

```bash
npm run db:seed
```

### 7. Start the Application

```bash
# Start the backend API
cd github-analyzer-api
python main.py

# In a new terminal, start the frontend
npm run dev
```

## Database Schema

The application uses the following tables:

### Portfolio Items
- `id` - Primary key (UUID)
- `title` - Portfolio item title
- `type` - Item type (github, file, url)
- `url` - Repository/file URL
- `summary` - AI-generated summary
- `skills` - JSON array of skills
- `thumbnail` - Emoji thumbnail
- `analysis_result` - Full GitHub analysis JSON
- `created_at` - Creation timestamp
- `updated_at` - Last update timestamp

### Network Connections
- `id` - Primary key (UUID)
- `name` - Contact name
- `email` - Contact email
- `company` - Company name
- `position` - Job title
- `relationship` - Connection strength
- `skills` - JSON array of skills
- `created_at` - Creation timestamp

### User Preferences
- `id` - Primary key (UUID)
- `github_token` - GitHub API token
- `preferences` - JSON object with user settings
- `created_at` - Creation timestamp
- `updated_at` - Last update timestamp

## API Endpoints

### Portfolio Management
- `GET /api/portfolio` - Get all portfolio items
- `POST /api/portfolio` - Create new portfolio item
- `PUT /api/portfolio/:id` - Update portfolio item
- `DELETE /api/portfolio/:id` - Delete portfolio item

### Network Management
- `GET /api/network` - Get network connections
- `POST /api/network` - Add new connection
- `PUT /api/network/:id` - Update connection
- `DELETE /api/network/:id` - Delete connection

## Development Commands

```bash
# Database operations
npm run db:migrate     # Run migrations
npm run db:seed        # Seed with sample data
npm run db:reset       # Reset database
npm run db:backup      # Backup database
npm run db:restore     # Restore from backup

# Development
npm run dev            # Start development server
npm run build          # Build for production
npm run start          # Start production server
```

## Production Setup

### Using Docker Compose

```yaml
# docker-compose.yml
version: '3.8'
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: bridgewise_db
      POSTGRES_USER: bridgewise_user
      POSTGRES_PASSWORD: your_secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
  
  app:
    build: .
    environment:
      DATABASE_URL: postgresql://bridgewise_user:your_secure_password@postgres:5432/bridgewise_db
    ports:
      - "3000:3000"
    depends_on:
      - postgres

volumes:
  postgres_data:
```

### Using Cloud Services

**Render.com:**
- Add PostgreSQL add-on
- Use provided DATABASE_URL in environment variables

**Vercel + PlanetScale:**
- Create PlanetScale database
- Add connection string to Vercel environment variables

**Heroku:**
- Add Heroku Postgres add-on
- DATABASE_URL will be automatically set

## Backup and Restore

### Create Backup
```bash
pg_dump -h localhost -U bridgewise_user -d bridgewise_db > backup.sql
```

### Restore Backup
```bash
psql -h localhost -U bridgewise_user -d bridgewise_db < backup.sql
```

## Security Best Practices

1. **Use environment variables** for all sensitive data
2. **Enable SSL** in production environments
3. **Use connection pooling** for better performance
4. **Regular backups** to prevent data loss
5. **Monitor database performance** and optimize queries
6. **Use parameterized queries** to prevent SQL injection

## Troubleshooting

### Connection Issues
```bash
# Check PostgreSQL status
brew services list | grep postgresql  # macOS
sudo systemctl status postgresql      # Linux

# Test connection
psql -h localhost -U bridgewise_user -d bridgewise_db
```

### Permission Issues
```bash
# Reset user permissions
psql postgres
GRANT ALL PRIVILEGES ON DATABASE bridgewise_db TO bridgewise_user;
GRANT ALL ON SCHEMA public TO bridgewise_user;
```

### Performance Issues
```bash
# Check active connections
SELECT * FROM pg_stat_activity;

# Check database size
SELECT pg_size_pretty(pg_database_size('bridgewise_db'));
```
