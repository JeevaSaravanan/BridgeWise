# 🚀 BridgeWise with AWS RDS PostgreSQL - Quick Start

## 🎯 Database Setup

BridgeWise now uses **AWS RDS PostgreSQL** for production-ready database hosting.

### Prerequisites
- AWS RDS PostgreSQL instance configured
- Database credentials available

## ⚙️ Configuration

### 1. Environment Setup
Copy and configure your environment variables:

```bash
cp github-analyzer-api/.env.example github-analyzer-api/.env
```

Update the `.env` file with your AWS RDS credentials:

```bash
# AWS RDS PostgreSQL Database Configuration
DATABASE_URL=postgresql://username:password@your-rds-endpoint.region.rds.amazonaws.com:5432/bridgewise_db
DB_HOST=your-rds-endpoint.region.rds.amazonaws.com
DB_PORT=5432
DB_NAME=bridgewise_db
DB_USER=your_db_username
DB_PASSWORD=your_db_password
```

### 2. Run Database Migrations
```bash
npm run db:migrate
```

### 3. Seed Sample Data (Optional)
```bash
npm run db:seed
```

### 4. Start Development Server
```bash
npm run dev
```

## 🔧 Development Commands

| Command | Description |
|---------|-------------|
| `npm run db:migrate` | Run database migrations |
| `npm run db:seed` | Add sample portfolio data |
| `npm run db:reset` | Reset database (migrate + seed) |
| `npm run db:status` | Check database status |
| `npm run dev` | Start development server |

## 🌐 Access Points

- **Application**: http://localhost:5173
- **pgAdmin**: http://localhost:8080
  - Email: `admin@bridgewise.com`
  - Password: `admin123`

## 📊 Database Features

### Portfolio Management
- ✅ Persistent storage in PostgreSQL
- ✅ GitHub analysis results saved
- ✅ Skills and metadata indexed
- ✅ Full-text search capabilities

### Data Migration
- ✅ Automatic schema migrations
- ✅ Sample data seeding
- ✅ Backup/restore functionality

### Performance
- ✅ Connection pooling
- ✅ Indexed queries
- ✅ JSON fields for flexible data

## 🐳 Docker Services

```yaml
services:
  postgres:    # Database server
  pgadmin:     # Database admin interface
```

## 🔒 Security

- Environment variable configuration
- Connection pooling
- Parameterized queries
- SSL support for production

## 🚨 Troubleshooting

### Connection Issues
```bash
# Test connection to AWS RDS
psql "postgresql://username:password@database-apb-instance-1.cmfwqqwe0oei.us-east-1.rds.amazonaws.com:5432/bridgewise_db"

# Check environment variables
cat github-analyzer-api/.env
```

### Migration Failures
```bash
# Check database status
npm run db:status

# Reset database
npm run db:reset
```

### Network Issues
```bash
# Test connectivity to RDS endpoint
telnet database-apb-instance-1.cmfwqqwe0oei.us-east-1.rds.amazonaws.com 5432

# Check VPC security groups in AWS Console
```

## 📈 Production Configuration

### Environment Variables
```bash
DATABASE_URL=postgresql://user:password@database-apb-instance-1.cmfwqqwe0oei.us-east-1.rds.amazonaws.com:5432/bridgewise_db
AZURE_OPENAI_KEY=your_azure_openai_key
GITHUB_TOKEN=your_github_token
```

### AWS RDS Best Practices
- **Security Groups**: Restrict access to known IP addresses
- **Encryption**: Enable encryption at rest and in transit
- **Backups**: Configure automated backups with appropriate retention
- **Monitoring**: Enable CloudWatch monitoring and alerts

### Backup Strategy
```bash
# Create backup from RDS
pg_dump "postgresql://user:password@database-apb-instance-1.cmfwqqwe0oei.us-east-1.rds.amazonaws.com:5432/bridgewise_db" > backup.sql

# Restore backup
psql "postgresql://user:password@database-apb-instance-1.cmfwqqwe0oei.us-east-1.rds.amazonaws.com:5432/bridgewise_db" < backup.sql
```

## 🎉 What's New

- **AWS RDS PostgreSQL**: Production-ready managed database hosting
- **Persistent Storage**: Portfolio items saved to cloud database
- **High Availability**: AWS RDS provides automatic failover and backups
- **Scalability**: Easy scaling with AWS RDS instance types
- **Security**: VPC isolation and encryption at rest/in transit
- **Migration System**: Version-controlled schema changes
- **Azure OpenAI Integration**: AI-powered portfolio analysis

Your BridgeWise application now runs on enterprise-grade cloud infrastructure! 🚀
