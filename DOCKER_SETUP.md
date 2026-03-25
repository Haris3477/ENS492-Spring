# Docker Setup for Redmine

## Install Docker Desktop

1. **Download Docker Desktop for Mac (Apple Silicon)**
   - Visit: https://www.docker.com/products/docker-desktop/
   - Download the version for Apple Silicon (arm64)
   - Install the `.dmg` file

2. **Start Docker Desktop**
   - Open Docker Desktop from Applications
   - Wait for it to start (whale icon in menu bar)

3. **Verify Installation**
   ```bash
   docker --version
   docker-compose --version
   ```

## Start Redmine with Docker

Once Docker is installed, run:

```bash
cd "/Users/adnanbugrametli/Desktop/Sabancı/ENS 491"
docker-compose up -d
```

This will:
- Download the Redmine image (if not already present)
- Start MySQL database
- Start Redmine on http://localhost:3000
- Set up persistent volumes for data

## Access Redmine

- **Web Interface**: http://localhost:3000
- **Default Admin Login**: 
  - Username: `admin`
  - Password: `admin` (change on first login)

## Useful Commands

```bash
# Start Redmine
docker-compose up -d

# Stop Redmine
docker-compose down

# View logs
docker-compose logs -f redmine

# Restart Redmine
docker-compose restart redmine

# Check status
docker-compose ps
```

## Update Test Configuration

After starting Redmine in Docker, update your test environment:

```bash
export REDMINE_URL=http://localhost:3000
```

The notebook will automatically use `http://localhost:3000` if `REDMINE_URL` is not set, but you can also set it explicitly.


