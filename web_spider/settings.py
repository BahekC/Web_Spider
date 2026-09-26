BOT_NAME = 'web_spider_lab'
SPIDER_MODULES = ['web_spider.spiders']
NEWSPIDER_MODULE = 'web_spider.spiders'
ROBOTSTXT_OBEY = True
USER_AGENT = 'WebSpiderLab/1.0 (educational data collection)'
CONCURRENT_REQUESTS = 4
CONCURRENT_REQUESTS_PER_DOMAIN = 1
DOWNLOAD_DELAY = 2
RANDOMIZE_DOWNLOAD_DELAY = False
DOWNLOAD_TIMEOUT = 60
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [429, 500, 502, 503, 504]
TWISTED_REACTOR = 'twisted.internet.asyncioreactor.AsyncioSelectorReactor'
DOWNLOAD_HANDLERS = {
    'http': 'scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler',
    'https': 'scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler',
}
PLAYWRIGHT_BROWSER_TYPE = 'chromium'
PLAYWRIGHT_LAUNCH_OPTIONS = {'headless': True}
PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 60000
PLAYWRIGHT_MAX_CONTEXTS = 1
PLAYWRIGHT_MAX_PAGES_PER_CONTEXT = 1
RETRY_EXCEPTIONS = [
    'twisted.internet.defer.TimeoutError',
    'twisted.internet.error.TimeoutError',
    'twisted.internet.error.DNSLookupError',
    'twisted.internet.error.ConnectionRefusedError',
    'twisted.internet.error.ConnectionDone',
    'twisted.internet.error.ConnectError',
    'twisted.internet.error.ConnectionLost',
    'twisted.web.client.ResponseFailed',
    'scrapy.core.downloader.handlers.http11.TunnelError',
    'builtins.IOError',
    'playwright.async_api.TimeoutError',
]
ITEM_PIPELINES = {
    'web_spider.pipelines.CleaningPipeline': 100,
    'web_spider.pipelines.ValidationPipeline': 200,
    'web_spider.pipelines.DuplicationPipeline': 300,
}
FEED_EXPORT_ENCODING = 'utf-8'
LOG_LEVEL = 'INFO'
TELNETCONSOLE_ENABLED = False
