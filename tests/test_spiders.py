from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import scrapy
from scrapy.http import HtmlResponse

from web_spider.spiders.news import NewsSpider
from web_spider.spiders.ecommerce import EcommerceSpider


def test_news_filters_keywords_dates_and_paginates():
    spider = NewsSpider(keywords='AI,ПНИПУ', days=7)
    spider.crawler = SimpleNamespace(stats=Mock())
    now = datetime.now(timezone.utc).isoformat()
    html = ''.join(f'<tr class="athing"><td><span class="titleline"><a href="/{i}">{title}</a></span></td></tr>'
                   f'<tr><td><span class="age" title="{date}"></span></td></tr>'
                   for i, title, date in [(1, 'AI News', now), (2, 'ПНИПУ', now),
                                          (3, 'Other', now), (4, 'AI Old', '2000-01-01T00:00:00'),
                                          (5, 'AI Bad date', 'invalid')])
    response = HtmlResponse('https://news.ycombinator.com/news', body=html + '<a class="morelink" href="?p=2">More</a>', encoding='utf-8')
    results = list(spider.parse(response))
    records = [r for r in results if not isinstance(r, scrapy.Request)]
    requests = [r for r in results if isinstance(r, scrapy.Request)]
    assert [r['title'] for r in records] == ['AI News', 'ПНИПУ']
    assert requests[0].url.endswith('/news?p=2')
    assert requests[0].cb_kwargs == {'page_number': 2}


def test_news_missing_selector_logged():
    spider = NewsSpider()
    spider.crawler = SimpleNamespace(stats=Mock())
    assert list(spider.parse(HtmlResponse('https://example.org', body=b'<html></html>'))) == []
    spider.crawler.stats.inc_value.assert_called_with('quality/layout_errors')


def test_ecommerce_parses_rendered_cards_and_full_title():
    spider = EcommerceSpider()
    spider.crawler = SimpleNamespace(stats=Mock())
    html = '<div class="product-wrapper"><div class="thumbnail"><a class="title" title="Full Model Name" href="/product/1">Full...</a><h4 class="price">$1299.99</h4><p class="description">Description</p><p data-rating="4"></p></div></div>'
    request = scrapy.Request('https://webscraper.io/test', meta={
        'playwright_page_methods': {'collect': SimpleNamespace(result=[html])}})
    items = list(spider.parse(HtmlResponse(request.url, request=request)))
    assert len(items) == 1
    assert items[0]['title'] == 'Full Model Name'
    assert items[0]['price'] == '$1299.99'
    assert items[0]['url'] == 'https://webscraper.io/product/1'


def test_ecommerce_reads_rating_from_rendered_stars():
    spider = EcommerceSpider()
    spider.crawler = SimpleNamespace(stats=Mock())
    html = '<div class="product-wrapper"><a class="title" href="/1">Model</a><h4 class="price">$10</h4><div class="ratings"><span class="ws-icon-star"></span><span class="ws-icon-star"></span></div></div>'
    request = scrapy.Request('https://webscraper.io/test', meta={
        'playwright_page_methods': {'collect': SimpleNamespace(result=[html])}})
    assert list(spider.parse(HtmlResponse(request.url, request=request)))[0]['rating'] == 2
