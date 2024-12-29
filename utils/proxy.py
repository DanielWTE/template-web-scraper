import random
import requests
import os
from dotenv import load_dotenv

load_dotenv()

PROXY_FILE_PATH = os.getenv('PROXY_FILE_PATH', 'proxies/proxies.txt')

def create_proxy():
    """
    Creates a proxy configuration from the proxy file.
    Expected format in proxy file: hostname:port:username:password
    """
    try:
        with open(PROXY_FILE_PATH, "r") as f:
            proxies = f.readlines()
    except FileNotFoundError:
        print(f"Proxy file not found: {PROXY_FILE_PATH}")
        return None

    proxies = [proxy.strip() for proxy in proxies if proxy.strip()]
    if not proxies:
        print("No proxies found in proxy file.")
        return None

    random.shuffle(proxies)
    for proxy in proxies:
        if check_proxy(proxy):
            return parse_proxy(proxy)
    
    return None

def parse_proxy(proxy):
    """Parse proxy string into configuration dict"""
    components = proxy.split(':')
    if len(components) == 4:
        hostname, port, username, password = components
        return {
            "server": f"http://{hostname}:{port}",
            "username": username,
            "password": password
        }
    else:
        raise ValueError("Invalid proxy format")

def check_proxy(proxy):
    """Test if proxy is working"""
    try:
        parsed_proxy = parse_proxy(proxy)
        proxy_url = f"http://{parsed_proxy['username']}:{parsed_proxy['password']}@{parsed_proxy['server'][7:]}"
        response = requests.get(
            "https://google.com", 
            proxies={"http": proxy_url, "https": proxy_url}, 
            timeout=5,
            headers={"User-Agent": create_user_agent()}
        )
        print(f"Proxy check successful: {parsed_proxy['server']}")
        return response.status_code == 200
    except Exception as e:
        print(f"Proxy check failed: {str(e)}")
        return False

def create_user_agent():
    """Generate a random user agent string"""
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:123.0) Gecko/20100101 Firefox/123.0",
        "Mozilla/5.0 (X11; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0"
    ]
    return random.choice(user_agents)