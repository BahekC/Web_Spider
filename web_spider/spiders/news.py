from datetime import datetime, timedelta, timezone

import scrapy

from web_spider.items import RecordLoader
from web_spider.pipelines import clean_text


class NewsSpider(scrapy.Spider):
    name = 'news'
    allowed_domains = ['news.ycombinator.com']
    # The site's robots.txt requests a 30-second interval.
    custom_settings = {'DOWNLOAD_DELAY': 30}

    def __init__(self, keywords='', days=7, max_pages=5, start_url=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.keywords = [clean_text(k) for k in (keywords or '').split(',') if k.strip()]
        self.days = int(days)
        self.max_pages = int(max_pages)
        self.start_url = start_url or 'https://news.ycombinator.com/news'
        self.collected_at = datetime.now(timezone.utc).isoformat()
        self.cutoff = datetime.now(timezone.utc) - timedelta(days=self.days)

    async def start(self):
        yield scrapy.Request(self.start_url, callback=self.parse, errback=self.on_error, cb_kwargs={'page_number': 1})

    def parse(self, response, page_number=1):
        rows = response.css('tr.athing')
        if not rows:
            self.logger.error('News layout changed or empty response: %s', response.url)
            self.crawler.stats.inc_value('quality/layout_errors')
            return
        self.crawler.stats.inc_value('source/pages_parsed')
        for row in rows:
            title = row.css('.titleline > a::text').get()
            link = row.css('.titleline > a::attr(href)').get()
            raw_date = row.xpath('following-sibling::tr[1]//span[@class="age"]/@title').get()
            if not title or not link:
                self.crawler.stats.inc_value('quality/missing_required')
                self.logger.warning('Skipped news item without title or URL')
                continue
            try:
                date = datetime.fromisoformat((raw_date or '').split(' ')[0].replace('Z', '+00:00'))
                if date.tzinfo is None:
                    date = date.replace(tzinfo=timezone.utc)
            except ValueError:
                self.crawler.stats.inc_value('quality/invalid_date')
                continue
            if self.days and date < self.cutoff:
                self.crawler.stats.inc_value('filter/date')
                continue
            if self.keywords and not any(k in clean_text(title) for k in self.keywords):
                self.crawler.stats.inc_value('filter/keywords')
                continue
            loader = RecordLoader(selector=row)
            loader.add_value('title', title)
            loader.add_value('url', response.urljoin(link))
            loader.add_value('date', date.isoformat())
            loader.add_value('source', 'hacker_news')
            loader.add_value('collected_at', self.collected_at)
            item = loader.load_item()
            # Listing pages have no article summaries. Do not invent one.
            item['summary'] = ''
            yield item
        next_page = response.css('a.morelink::attr(href)').get()
        if next_page and page_number < self.max_pages:
            yield response.follow(next_page, callback=self.parse, errback=self.on_error,
                                  cb_kwargs={'page_number': page_number + 1})

    def on_error(self, failure):
        self.crawler.stats.inc_value('source/failed_requests')
        self.logger.error('News request failed after retries: %s', failure)
