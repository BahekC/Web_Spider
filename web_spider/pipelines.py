import math
import re
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit

import ftfy
from itemadapter import ItemAdapter
from parsel import Selector
from scrapy.exceptions import DropItem
from w3lib.url import canonicalize_url


def clean_text(value):
    if value is None:
        return ''
    text = ftfy.fix_text(str(value))
    if re.search(r'</?[a-zA-Z][^>]*>', text):
        root = Selector(text=text, type='html')
        text = ' '.join(root.xpath('//text()[not(ancestor::script) and not(ancestor::style)]').getall())
    return re.sub(r'\s+', ' ', text).strip().lower()


def parse_price(value):
    if value is None or str(value).strip() == '':
        return None
    text = re.sub(r'[^\d.,+-]', '', str(value))
    if ',' in text and '.' in text:
        text = text.replace(',', '') if text.rfind('.') > text.rfind(',') else text.replace('.', '').replace(',', '.')
    elif ',' in text:
        text = text.replace(',', '.')
    try:
        number = Decimal(text)
        return float(number) if number.is_finite() else None
    except InvalidOperation:
        return None


class CleaningPipeline:
    def process_item(self, item, spider):
        a = ItemAdapter(item)
        for key in ('title', 'summary', 'category', 'store'):
            if key in a:
                a[key] = clean_text(a[key])
        if a.get('url'):
            a['url'] = canonicalize_url(a['url'].strip(), keep_fragments=False)
        if 'price' in a:
            a['price'] = parse_price(a['price'])
        if 'rating' in a:
            try:
                a['rating'] = float(a['rating']) if a['rating'] is not None else None
            except (TypeError, ValueError):
                a['rating'] = None
        return item


class ValidationPipeline:
    def process_item(self, item, spider):
        a = ItemAdapter(item)
        for key in ('title', 'url'):
            if not a.get(key):
                raise DropItem(f'Missing required field: {key}')
        parsed = urlsplit(a['url'])
        if parsed.scheme not in ('http', 'https') or not parsed.netloc:
            raise DropItem('Invalid HTTP URL')
        if spider.name == 'ecommerce':
            price = a.get('price')
            if not isinstance(price, (int, float)) or not math.isfinite(price) or price < 0:
                raise DropItem('Missing or invalid price')
            rating = a.get('rating')
            if rating is not None and (not math.isfinite(rating) or not 0 <= rating <= 5):
                a['rating'] = None
        return item


class DuplicationPipeline:
    def __init__(self):
        self.seen_urls = set()

    def process_item(self, item, spider):
        url = ItemAdapter(item)['url']
        if url in self.seen_urls:
            spider.crawler.stats.inc_value('quality/duplicates_removed')
            raise DropItem(f'Duplicate URL: {url}')
        self.seen_urls.add(url)
        return item
