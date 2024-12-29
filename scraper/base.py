from fastapi import HTTPException
from utils.browser import PlaywrightManager

class BaseScraper:
    def __init__(self, browser_manager: PlaywrightManager):
        self.browser_manager = browser_manager

    async def scrape(self, url: str):
        """
        Base scraping method that demonstrates the scraping workflow.
        Override this method in derived classes for specific scraping logic.
        """
        page = await self.browser_manager.new_context_page()
        try:
            await page.goto(url, timeout=120000)
            
            title = await self._get_element_content(page, "title")
            meta_description = await self._get_element_content(
                page, 
                'meta[name="description"]', 
                attribute="content"
            )
            h1_headers = await self._get_elements_content(page, "h1")
            content = await self._get_page_content(page)
            
            return {
                "url": url,
                "title": title,
                "meta_description": meta_description,
                "h1_headers": h1_headers,
                "content": content
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            await self.browser_manager.print_network_summary(page)
            await self.browser_manager.close_page(page)

    async def _get_element_content(self, page, selector, attribute=None, default=None):
        """Helper method to get content from an element"""
        element = await page.query_selector(selector)
        if element:
            if attribute:
                return await element.get_attribute(attribute)
            return await element.inner_text()
        return default

    async def _get_elements_content(self, page, selector):
        """Helper method to get content from multiple elements"""
        elements = await page.query_selector_all(selector)
        return [await element.inner_text() for element in elements]
    
    async def _get_page_content(self, page):
        """Helper method to get the full page content"""
        return await page.content()