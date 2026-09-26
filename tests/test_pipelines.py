from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from scrapy.exceptions import DropItem

from web_spider.pipelines import CleaningPipeline, ValidationPipeline, DuplicationPipeline, clean_text, parse_price


def spider(name='news'):
    return SimpleNamespace(name=name, crawler=SimpleNamespace(stats=Mock()))


@pytest.mark.parametrize('raw,expected', [
    ('  HELLO\n\t world ', 'hello world'),
    ('<p>Hello <b>WORLD</b></p><script>bad()</script>', 'hello world'),
    ('FranÃ§ais', 'français'),
    (None, ''),
    ('ПНИПУ\u00a0 Магистратура', 'пнипу магистратура'),
])
def test_text(raw, expected):
    assert clean_text(raw) == expected


@pytest.mark.parametrize('raw,expected', [
    ('$1,299.99', 1299.99), ('1 299,99 ₽', 1299.99), ('€1.299,99', 1299.99),
    ('$0.00', 0), (None, None), ('unknown', None), ('NaN', None),
])
def test_prices(raw, expected):
    assert parse_price(raw) == expected


def test_pipeline_deduplicates_canonical_urls_and_preserves_distinct_products():
    cleaner, validator, deduper = CleaningPipeline(), ValidationPipeline(), DuplicationPipeline()
    s = spider('ecommerce')
    for url in ['https://shop.test/item?b=2&a=1#part', 'https://shop.test/item?a=1&b=2']:
        item = cleaner.process_item({'title': ' Model ', 'url': url, 'price': '$123.45'}, s)
        validator.process_item(item, s)
        if deduper.seen_urls:
            with pytest.raises(DropItem, match='Duplicate'):
                deduper.process_item(item, s)
        else:
            deduper.process_item(item, s)
    # Same title can represent different configurations and must not be dropped.
    other = {'title': 'model', 'url': 'https://shop.test/other', 'price': 123.45}
    assert deduper.process_item(other, s) is other


@pytest.mark.parametrize('item', [
    {'title': '', 'url': 'https://example.org'},
    {'title': 'a', 'url': ''},
    {'title': 'a', 'url': 'javascript:alert(1)'},
    {'title': 'a', 'url': 'https://example.org', 'price': -1},
    {'title': 'a', 'url': 'https://example.org', 'price': float('nan')},
])
def test_validation_rejects_invalid_records(item):
    with pytest.raises(DropItem):
        ValidationPipeline().process_item(item, spider('ecommerce'))


def test_missing_optional_rating_is_not_invented():
    item = {'title': 'a', 'url': 'https://example.org', 'price': 1, 'rating': 99}
    assert ValidationPipeline().process_item(item, spider('ecommerce'))['rating'] is None
