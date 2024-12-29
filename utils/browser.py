import asyncio
import os
import time
import re
from urllib.parse import urlparse
from playwright.async_api import async_playwright
from utils.proxy import create_proxy, create_user_agent
from dotenv import load_dotenv

load_dotenv()

CACHE_DIR = os.getenv('CACHE_DIR', 'cache')
BROWSER_POOL_SIZE = int(os.getenv('BROWSER_POOL_SIZE', '5'))
PAGE_TIMEOUT = int(os.getenv('PAGE_TIMEOUT', '300000'))
ENABLE_CACHING = os.getenv('ENABLE_CACHING', 'true').lower() == 'true'
DETAILED_LOGGING= os.getenv('DETAILED_LOGGING', 'false').lower() == 'true'

if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

class PlaywrightManager:
    def __init__(self, pool_size=BROWSER_POOL_SIZE):
        self.pool_size = pool_size
        self.browsers = {
            'proxy': [],
            'no_proxy': []
        }
        self.lock = asyncio.Lock()
        self.indices = {
            'proxy': 0,
            'no_proxy': 0
        }
        self.track_requests = True
        self.track_cache = ENABLE_CACHING
        self.detailed_logging = DETAILED_LOGGING

    def format_bytes(self, size):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"

    async def initialize_browser_pool(self):
        tasks = []
        for _ in range(self.pool_size):
            tasks.append(self.add_browser('proxy'))
        for _ in range(max(1, self.pool_size // 3)):
            tasks.append(self.add_browser('no_proxy'))
        
        await asyncio.gather(*tasks)

    async def add_browser(self, browser_type):
        browser = await self.create_browser(browser_type)
        if browser:
            async with self.lock:
                self.browsers[browser_type].append(browser)

    async def create_browser(self, browser_type):
        p = await async_playwright().start()
        
        launch_options = {
            'headless': True,
            'args': [
                '--disable-gpu',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
            ]
        }

        if browser_type == 'proxy' and os.getenv('USE_PROXIES', 'false').lower() == 'true':
            proxy = create_proxy()
            if proxy:
                launch_options['proxy'] = proxy

        try:
            browser = await p.chromium.launch(**launch_options)
            return browser
        except Exception as e:
            print(f"Browser creation error: {str(e)}")
            return None

    async def get_browser(self, use_proxy=True):
        async with self.lock:
            browser_type = 'proxy' if use_proxy else 'no_proxy'
            pool = self.browsers[browser_type]
            
            if not pool:
                new_browser = await self.create_browser(browser_type)
                if new_browser:
                    pool.append(new_browser)
                else:
                    browser_type = 'no_proxy'
                    pool = self.browsers['no_proxy']
                    if not pool:
                        new_browser = await self.create_browser('no_proxy')
                        if new_browser:
                            pool.append(new_browser)

            if not pool:
                raise Exception("No browsers available")

            index = self.indices[browser_type]
            browser = pool[index]
            self.indices[browser_type] = (index + 1) % len(pool)
            return browser, browser_type

    def get_latest_cache_file(self, cache_dir):
        """Get the most recent file from the cache directory"""
        try:
            files = os.listdir(cache_dir)
            if not files:
                return None
            return max([os.path.join(cache_dir, f) for f in files], key=os.path.getmtime)
        except Exception as e:
            print(f"Error accessing cache: {str(e)}")
            return None

    async def intercept_route(self, route, request, page):
        """Handle request interception for caching"""
        try:
            cache_patterns = [
                r'\.js$',
                r'\.css$',
                r'\.woff2$',
                r'\.png$',
                r'\.jpg$',
                r'\.gif$'
            ]

            should_cache = any(re.search(pattern, request.url) for pattern in cache_patterns)

            if should_cache and self.track_cache:
                parsed_url = urlparse(request.url)
                file_name = os.path.basename(parsed_url.path)
                resource_type = next((p.strip('.$^') for p in cache_patterns if re.search(p, file_name)), 'misc')
                cache_dir = os.path.join(CACHE_DIR, resource_type)

                if not os.path.exists(cache_dir):
                    os.makedirs(cache_dir)

                cache_file = os.path.join(cache_dir, file_name)

                if os.path.exists(cache_file):
                    with open(cache_file, 'rb') as f:
                        content = f.read()
                    await route.fulfill(
                        status=200,
                        body=content,
                        headers={'Cache-Control': 'max-age=31536000'}
                    )
                    if hasattr(page, 'cache_hits'):
                        page.cache_hits += 1
                else:
                    response = await route.fetch()
                    if response:
                        content = await response.body()
                        try:
                            with open(cache_file, 'wb') as f:
                                f.write(content)
                        except Exception as e:
                            print(f"Error writing cache: {str(e)}")
                        await route.fulfill(
                            status=response.status,
                            headers=response.headers,
                            body=content
                        )
                    else:
                        await route.continue_()
            else:
                await route.continue_()

        except Exception as e:
            if self.detailed_logging:
                print(f"Resource fetch failed for {request.url}: {str(e)}")
                
            await route.continue_()

    async def new_context_page(self, use_proxy=True):
        browser, browser_type = await self.get_browser(use_proxy)
        context = await browser.new_context(
            user_agent=create_user_agent(),
            bypass_csp=True,
            ignore_https_errors=True
        )

        page = await context.new_page()
        page.requests = []
        page.cache_hits = 0
        page.browser_type = browser_type
        
        if self.track_requests:
            async def log_request(request):
                request_info = {
                    'url': request.url,
                    'method': request.method,
                    'resource_type': request.resource_type,
                    'start_time': time.time(),
                    'browser_type': page.browser_type
                }
                page.requests.append(request_info)

            async def log_response(response):
                for req in page.requests:
                    if req['url'] == response.url:
                        req['status'] = response.status
                        req['end_time'] = time.time()
                        req['duration'] = req['end_time'] - req['start_time']
                        break

            page.on('request', log_request)
            page.on('response', log_response)

        if self.track_cache:
            await page.route("**/*", lambda route, request: self.intercept_route(route, request, page))

        context.set_default_timeout(PAGE_TIMEOUT)
        return page

    async def print_network_summary(self, page):
        """Print a summary of network activity and cache performance"""
        
        if not self.detailed_logging:
            return
        
        if not self.track_requests:
            return

        total_requests = len(page.requests)
        successful_requests = sum(1 for req in page.requests if req.get('status', 0) == 200)
        cache_hits = getattr(page, 'cache_hits', 0)
        proxy_requests = sum(1 for req in page.requests if req.get('browser_type') == 'proxy')
        no_proxy_requests = sum(1 for req in page.requests if req.get('browser_type') == 'no_proxy')

        print("\nNetwork Summary:")
        print("=" * 50)
        print(f"Total Requests: {total_requests}")
        print(f"Successful Requests: {successful_requests}")
        print(f"Cache Hits: {cache_hits}")
        if total_requests > 0:
            cache_hit_rate = (cache_hits / total_requests) * 100
            print(f"Cache Hit Rate: {cache_hit_rate:.2f}%")
        print(f"Requests using proxy: {proxy_requests}")
        print(f"Requests without proxy: {no_proxy_requests}")

        print("\nDetailed Request Information:")
        print("=" * 50)
        for req in page.requests:
            status = req.get('status', 'N/A')
            duration = req.get('duration', 0)
            proxy_info = "PROXY" if req.get('browser_type') == 'proxy' else "NO PROXY"
            print(f"{req['method']} {req['url']} - Status: {status} - Duration: {duration:.2f}s - {proxy_info}")

        if hasattr(page, 'requests'):
            total_duration = sum(req.get('duration', 0) for req in page.requests)
            print(f"\nTotal Request Duration: {total_duration:.2f}s")

    async def close_page(self, page):
        await page.context.close()

    async def close_all_browsers(self):
        async with self.lock:
            for pool in self.browsers.values():
                for browser in pool:
                    await browser.close()
            self.browsers = {key: [] for key in self.browsers}

    async def __del__(self):
        await self.close_all_browsers()