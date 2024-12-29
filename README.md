# Template Web Scraper

A comprehensive web scraping template built with FastAPI and Playwright. Features multi-level caching, proxy support, and extensive configurability.

## Features

- FastAPI-based API endpoints
- Caching system:
  - Resource caching (JS, CSS, images or custom)
- Configurable proxy support
- Browser session management
- Comprehensive error handling
- Modular scraping architecture
- Detailed network statistics
- Automated metadata extraction

## Requirements

- Python 3.12+
- FastAPI
- Playwright
- Additional dependencies in requirements.txt

## Installation

1. Clone the repository:
```bash
git clone https://github.com/DanielWTE/template-web-scraper.git
cd template-web-scraper
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install Playwright browsers:
```bash
playwright install
```

5. Configure environment variables:
```bash
cp .env.example .env
```

Edit the .env file with your configuration.

## Configuration

Required environment variables:

```plaintext
# API Configuration
API_KEY=your_api_key
PORT=8000
HOST=0.0.0.0

# Browser Configuration
BROWSER_POOL_SIZE=1
PAGE_TIMEOUT=300000

# Resource Cache Configuration
CACHE_DIR=cache
ENABLE_CACHING=true

# Proxy Configuration
PROXY_FILE_PATH=proxies/proxies.txt
USE_PROXIES=false
```

## Usage

Start the API server:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Development mode with auto-reload:
```bash
uvicorn main:app --reload --reload-exclude 'venv'
```

### Docker

Build and run with Docker:

```bash
docker build -t template-web-scraper .
docker run -p 8000:8000 template-web-scraper
```

## API Endpoints

### GET /
Health check endpoint

### GET /scrape
Scrape a webpage with caching
- Required header: `Authorization: your_api_key`
- Required parameter: `url`

Example:
```bash
curl -X GET "http://localhost:8000/scrape?url=https://example.com" \
     -H "Authorization: your_api_key" # From .env
```


## Caching System

The template implements a two-level caching system:

1. **Resource Caching**:
- Caches static resources (JS, CSS, images)
- Reduces bandwidth usage and load times
- Configurable through ENABLE_CACHING

