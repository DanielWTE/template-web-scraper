import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import AnyHttpUrl
from dotenv import load_dotenv
from scraper.base import BaseScraper
from utils.browser import PlaywrightManager

load_dotenv()

API_KEY = os.getenv("API_KEY")
assert API_KEY, "API_KEY must be set in environment variables"

app = FastAPI(title="Base Web Scraper API")
browser_manager = PlaywrightManager()

@app.middleware("http")
async def check_authorization(request: Request, call_next):
    auth_header = request.headers.get('Authorization')
    if not auth_header or auth_header != API_KEY:
        return JSONResponse(
            status_code=401,
            content={"message": "Unauthorized"}
        )
    response = await call_next(request)
    return response

@app.on_event("startup")
async def startup_event():
    await browser_manager.initialize_browser_pool()

@app.on_event("shutdown")
async def shutdown_event():
    await browser_manager.close_all_browsers()

@app.get("/")
def read_root():
    return {"status": "healthy"}

@app.get("/scrape")
async def scrape_url(url: AnyHttpUrl):
    try:
        scraper = BaseScraper(browser_manager)
        result = await scraper.scrape(str(url))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    