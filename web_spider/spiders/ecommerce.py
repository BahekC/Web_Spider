import asyncio
from datetime import datetime, timezone

import scrapy
from parsel import Selector
from scrapy_playwright.page import PageMethod

from web_spider.items import RecordLoader


async def collect_rendered_pages(page, max_pages):
    """Read only rendered cards, switching the shop's JS pagination in-browser."""
    await page.wait_for_selector('.ecomerce-items .title')
    pages = []
    for index in range(max_pages):
        pages.append(await page.locator('.ecomerce-items').inner_html())
        next_button = page.locator('.pager .next')
        if await next_button.count() == 0 or await next_button.is_disabled():
            break
        if index + 1 >= max_pages:
            break
        old_href = await page.locator('.ecomerce-items .title').first.get_attribute('href')
        await asyncio.sleep(2)
        await next_button.click()
        await page.wait_for_function(
            "old => { const a = document.querySelector('.ecomerce-items .title'); return a && a.getAttribute('href') !== old; }",
            arg=old_href,
        )
    return pages


class EcommerceSpider(scrapy.Spider):
    name = 'ecommerce'
    allowed_domains = ['webscraper.io']

    def __init__(self, category='laptops', stores='webscraper', max_pages=30, start_url=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        aliases = {'ноутбуки': 'laptops', 'планшеты': 'tablets'}
        self.category = aliases.get(category.lower(), category.lower())
        if self.category not in ('laptops', 'tablets'):
            raise ValueError('Supported categories: laptops/ноутбуки, tablets/планшеты')
        if {s.strip().lower() for s in stores.split(',')} != {'webscraper'}:
            raise ValueError('Only the webscraper training store is supported')
        self.max_pages = int(max_pages)
        self.start_url = start_url or f'https://webscraper.io/test-sites/e-commerce/ajax/computers/{self.category}'
        self.collected_at = datetime.now(timezone.utc).isoformat()

    async def start(self):
        yield scrapy.Request(
            self.start_url, callback=self.parse, errback=self.on_error,
            meta={'playwright': True, 'playwright_page_methods': {
                'collect': PageMethod(collect_rendered_pages, self.max_pages),
            }},
        )

    def parse(self, response):
        fragments = response.meta['playwright_page_methods']['collect'].result
        self.crawler.stats.set_value('source/rendered_pages', len(fragments))
        for fragment in fragments:
            root = Selector(text=fragment)
            cards = root.css('.product-wrapper')
            if not cards:
                cards = root.css('.thumbnail')
            if not cards:
                self.logger.error('No product cards in rendered DOM')
                self.crawler.stats.inc_value('quality/layout_errors')
            for card in cards:
                loader = RecordLoader(selector=card)
                loader.add_css('title', 'a.title::attr(title)')
                if not loader.get_output_value('title'):
                    loader.add_css('title', 'a.title::text')
                link = card.css('a.title::attr(href)').get()
                if link:
                    loader.add_value('url', response.urljoin(link))
                loader.add_css('price', '.price::text')
                loader.add_css('rating', '[data-rating]::attr(data-rating)')
                if loader.get_output_value('rating') is None and card.css('.ratings'):
                    stars = card.css('.ratings .ws-icon-star')
                    if stars:
                        loader.add_value('rating', len(stars))
                loader.add_css('summary', '.description::text')
                loader.add_value('category', self.category)
                loader.add_value('store', 'webscraper')
                loader.add_value('source', 'webscraper_test_site')
                loader.add_value('currency', 'USD')
                loader.add_value('collected_at', self.collected_at)
                item = loader.load_item()
                item.setdefault('rating', None)
                item.setdefault('summary', '')
                yield item

    def on_error(self, failure):
        self.crawler.stats.inc_value('source/failed_requests')
        self.logger.error('Browser request failed after retries: %s', failure)
