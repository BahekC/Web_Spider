import scrapy
from itemloaders.processors import TakeFirst
from scrapy.loader import ItemLoader


class Record(scrapy.Item):
    title = scrapy.Field()
    url = scrapy.Field()
    source = scrapy.Field()
    collected_at = scrapy.Field()
    date = scrapy.Field()
    summary = scrapy.Field()
    price = scrapy.Field()
    currency = scrapy.Field()
    rating = scrapy.Field()
    category = scrapy.Field()
    store = scrapy.Field()


class RecordLoader(ItemLoader):
    default_item_class = Record
    default_output_processor = TakeFirst()
