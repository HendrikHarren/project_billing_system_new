# Deployment Guide

This guide covers deploying the Billing System in various environments using Docker and other deployment methods.

## Table of Contents

1. [Deployment Options](#deployment-options)
2. [Docker Deployment](#docker-deployment)
3. [Production Deployment](#production-deployment)
4. [Monitoring and Logging](#monitoring-and-logging)
5. [Backup and Recovery](#backup-and-recovery)
6. [Scaling Considerations](#scaling-considerations)
7. [Troubleshooting Deployment](#troubleshooting-deployment)

---

## Deployment Options

### Available Deployment Methods

1. **Docker** - Recommended for production (containerized, portable)
2. **Docker Compose** - Best for local development and testing
3. **Direct Python** - Simple deployment on single server
4. **Cloud Platforms** - AWS, Google Cloud, Azure (future)

### Which Method to Choose?

| Method | Best For | Pros | Cons |
|--------|----------|------|------|
| Docker | Production, staging | Portable, isolated, reproducible | Requires Docker knowledge |
| Docker Compose | Development, testing | Easy setup, multi-service | Not for high-scale production |
| Direct Python | Simple deployments | Simple, lightweight | Manual dependency management |
| Cloud Platforms | Enterprise, scale | Managed, scalable, reliable | Cost, complexity |

---

## Docker Deployment

### Prerequisites

- Docker 20.10+
- Docker Compose 1.29+ (for compose deployments)
- 2GB RAM minimum
- 10GB disk space

### Quick Start with Docker

**1. Build the image**

```bash
docker build -t billing-system:latest .
```

**2. Run the container**

```bash
docker run -d \
  --name billing-system \
  -v $(pwd)/.env:/app/.env:ro \
  -v billing-cache:/app/.cache \
  billing-system:latest \
  python -m src.cli generate-report --month $(date +%Y-%m)
```

### Docker Compose Deployment

**1. Prepare environment**

```bash
# Create .env file
cp .env.example .env

# Edit configuration
nano .env
```

**2. Deploy with compose**

```bash
# Build and start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

**3. Run commands**

```bash
# Generate report
docker-compose run billing-system python -m src.cli generate-report --month 2024-10

# List timesheets
docker-compose run billing-system python -m src.cli list-timesheets

# Validate data
docker-compose run billing-system python -m src.cli validate-data
```

### Automated Deployment Script

Use the provided deployment script:

```bash
# Run deployment script
./scripts/deploy.sh production

# Script performs:
# ✓ Prerequisites check
# ✓ Configuration validation
# ✓ Docker image build
# ✓ Image testing
# ✓ Container deployment
```

---

## Production Deployment

### Production Checklist

Before deploying to production:

- [ ] Configure production `.env` file
- [ ] Set `ENVIRONMENT=production`
- [ ] Set `DEBUG=false`
- [ ] Configure log level (`LOG_LEVEL=INFO`)
- [ ] Enable caching for performance
- [ ] Set up persistent volumes for cache
- [ ] Configure backup strategy
- [ ] Test Google API connection
- [ ] Set up monitoring and alerts
- [ ] Document rollback procedure

### Production Configuration

**Environment Variables**

```env
# Production settings
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Performance settings
BATCH_SIZE=20
MAX_RETRIES=5
RETRY_DELAY=2.0

# Cache settings
ENABLE_SHEETS_CACHE=true
CACHE_FILE_PATH=/var/cache/billing-system/sheets_cache.json
CACHE_MAX_SIZE=200
CACHE_AUTO_SAVE=true
```

### Production Docker Compose

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  billing-system:
    image: billing-system:1.0.0
    container_name: billing-system-prod
    restart: always
    env_file:
      - .env.production
    volumes:
      - /var/cache/billing-system:/app/.cache
      - /var/log/billing-system:/app/logs
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 1G
    healthcheck:
      test: ["CMD", "python", "-c", "from src.config.settings import get_config; get_config()"]
      interval: 60s
      timeout: 10s
      retries: 3
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "5"
```

Deploy:

```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Scheduled Report Generation

**Using cron**

```bash
# Edit crontab
crontab -e

# Add monthly report generation (1st of each month at 6 AM)
0 6 1 * * cd /path/to/billing-system && docker-compose run billing-system python -m src.cli generate-report --month $(date -d "last month" +%Y-%m)
```

**Using systemd timer** (Linux)

Create `/etc/systemd/system/billing-report.service`:

```ini
[Unit]
Description=Billing System Monthly Report
Wants=billing-report.timer

[Service]
Type=oneshot
WorkingDirectory=/opt/billing-system
ExecStart=/usr/bin/docker-compose run billing-system python -m src.cli generate-report --month %m

[Install]
WantedBy=multi-user.target
```

Create `/etc/systemd/system/billing-report.timer`:

```ini
[Unit]
Description=Monthly Billing Report Timer
Requires=billing-report.service

[Timer]
OnCalendar=monthly
Persistent=true

[Install]
WantedBy=timers.target
```

Enable and start:

```bash
sudo systemctl enable billing-report.timer
sudo systemctl start billing-report.timer

# Check status
sudo systemctl status billing-report.timer
```

---

## Monitoring and Logging

### Logging Configuration

**Log Levels**

- `DEBUG`: Detailed debugging information
- `INFO`: General information (default for production)
- `WARNING`: Warning messages
- `ERROR`: Error messages
- `CRITICAL`: Critical failures

**View Logs**

```bash
# Docker Compose
docker-compose logs -f

# Docker container
docker logs -f billing-system

# Host logs (if volume mounted)
tail -f /var/log/billing-system/app.log
```

### Health Checks

**Container Health**

```bash
# Check container health
docker inspect billing-system | grep -A 10 Health

# Expected output:
# "Health": {
#     "Status": "healthy",
#     ...
# }
```

**Manual Health Check**

```bash
# Run health check script
docker exec billing-system python -c "from src.config.settings import get_config; get_config()"

# Should exit with code 0 if healthy
echo $?  # Should print 0
```

### Monitoring Metrics

**Key Metrics to Monitor**

1. **Container metrics**
   - CPU usage
   - Memory usage
   - Disk I/O

2. **Application metrics**
   - Report generation time
   - API call frequency
   - Error rate
   - Cache hit rate

**Using Docker stats**

```bash
docker stats billing-system
```

**Using Prometheus** (advanced)

Add prometheus exporter to `docker-compose.yml`:

```yaml
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    ports:
      - "9090:9090"
```

---

## Backup and Recovery

### Backup Strategy

**What to Back Up**

1. **Cache data** - `.cache/sheets_cache.json`
2. **Configuration** - `.env` file (encrypted!)
3. **Logs** - Application logs (optional)

**Backup Script**

Create `scripts/backup.sh`:

```bash
#!/bin/bash
# Backup script for Billing System

BACKUP_DIR="/backup/billing-system"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup cache
docker cp billing-system:/app/.cache "$BACKUP_DIR/cache_$DATE"

# Backup configuration (encrypted)
gpg --encrypt --recipient your-email@example.com \
    -o "$BACKUP_DIR/env_$DATE.gpg" .env

# Backup logs
docker cp billing-system:/app/logs "$BACKUP_DIR/logs_$DATE"

# Clean old backups (keep last 30 days)
find "$BACKUP_DIR" -type f -mtime +30 -delete

echo "Backup completed: $BACKUP_DIR"
```

**Automated Backups**

```bash
# Add to crontab (daily at 2 AM)
0 2 * * * /path/to/billing-system/scripts/backup.sh
```

### Recovery Procedure

**1. Stop the running container**

```bash
docker-compose down
```

**2. Restore cache data**

```bash
# Restore cache from backup
cp -r /backup/billing-system/cache_YYYYMMDD_HHMMSS/* .cache/
```

**3. Restore configuration**

```bash
# Decrypt and restore .env
gpg --decrypt /backup/billing-system/env_YYYYMMDD_HHMMSS.gpg > .env
```

**4. Restart container**

```bash
docker-compose up -d
```

**5. Verify**

```bash
# Check health
docker exec billing-system python test_connection.py

# Test report generation
docker-compose run billing-system python -m src.cli list-timesheets
```

---

## Scaling Considerations

### Single Server Limits

The current architecture supports:
- **Timesheets**: 50-100 freelancers
- **Entries**: ~10,000 entries per month
- **Processing time**: ~10-30 seconds per report
- **Memory**: ~500MB-1GB per instance

### Scaling Options

**Vertical Scaling** (increase resources)

```yaml
# Increase container resources
deploy:
  resources:
    limits:
      cpus: '4.0'
      memory: 8G
```

**Horizontal Scaling** (multiple instances)

For very large deployments:

1. **Split by timeframe** - Multiple containers for different months
2. **Split by project** - Separate containers per project
3. **Batch processing** - Process in smaller batches

**Example multi-instance setup**:

```yaml
services:
  billing-proj-a:
    image: billing-system:latest
    environment:
      - PROJECT_FILTER=PROJ-A

  billing-proj-b:
    image: billing-system:latest
    environment:
      - PROJECT_FILTER=PROJ-B
```

### Performance Optimization

**Cache Optimization**

```env
# Increase cache size for large deployments
CACHE_MAX_SIZE=500

# Use dedicated cache volume
CACHE_FILE_PATH=/var/cache/billing-system/sheets_cache.json
```

**Batch Size Tuning**

```env
# Increase batch size for faster processing (uses more memory)
BATCH_SIZE=50

# Or decrease for stability
BATCH_SIZE=10
```

---

## Troubleshooting Deployment

### Common Issues

#### Container Won't Start

**Symptoms:**
```bash
docker-compose ps
# billing-system   Exit 1
```

**Solutions:**

1. **Check logs**
   ```bash
   docker-compose logs billing-system
   ```

2. **Verify configuration**
   ```bash
   docker-compose run billing-system python scripts/validate_config.py
   ```

3. **Check .env file permissions**
   ```bash
   ls -la .env  # Should be readable
   ```

#### Health Check Failures

**Symptoms:**
```bash
docker inspect billing-system | grep Health
# "Status": "unhealthy"
```

**Solutions:**

1. **Check configuration loading**
   ```bash
   docker exec billing-system python -c "from src.config.settings import get_config; get_config()"
   ```

2. **Review logs**
   ```bash
   docker logs billing-system
   ```

#### Out of Memory

**Symptoms:**
- Container killed
- `OOMKilled` in docker logs

**Solutions:**

1. **Increase memory limit**
   ```yaml
   deploy:
     resources:
       limits:
         memory: 4G  # Increase from 2G
   ```

2. **Reduce batch size**
   ```env
   BATCH_SIZE=5  # Reduce from 20
   ```

#### Permission Errors

**Symptoms:**
```
Permission denied: '.cache/sheets_cache.json'
```

**Solutions:**

1. **Fix volume permissions**
   ```bash
   sudo chown -R 1000:1000 .cache
   ```

2. **Use named volumes**
   ```yaml
   volumes:
     - cache-data:/app/.cache  # Use named volume instead of bind mount
   ```

### Getting Help

For deployment issues:

1. Check [Troubleshooting Guide](TROUBLESHOOTING.md)
2. Review container logs
3. Verify configuration with `scripts/validate_config.py`
4. Create issue on [GitHub](https://github.com/HendrikHarren/project_billing_system_new/issues)

---

## Next Steps

After successful deployment:

1. **Test report generation**
   ```bash
   docker-compose run billing-system python -m src.cli generate-report --month $(date +%Y-%m)
   ```

2. **Set up monitoring** - Configure health checks and alerts

3. **Schedule automated reports** - Set up cron or systemd timers

4. **Document procedures** - Create runbooks for your team

5. **Plan backups** - Implement regular backup schedule

For more information:
- [User Guide](USER_GUIDE.md) - Usage and commands
- [Configuration Reference](CONFIGURATION.md) - All settings
- [Troubleshooting Guide](TROUBLESHOOTING.md) - Common issues

---

**Happy deploying! 🚀**
