"""Actual HTTP errors through Scrapy's downloader, without hitting public sites."""
import json
from pathlib import Path
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread


def test_retry_429_503_and_exhaustion(tmp_path):
    counts = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            counts[self.path] = counts.get(self.path, 0) + 1
            attempt = counts[self.path]
            status = (429 if attempt == 1 else 503 if attempt == 2 else 200) if self.path == '/recover' else 503
            self.send_response(status)
            self.end_headers()
            self.wfile.write(b'ok')

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    script = tmp_path / 'retry_probe.py'
    stats_path = tmp_path / 'stats.json'
    script.write_text('''
import json, sys
import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.settings import Settings
class Probe(scrapy.Spider):
    name = 'retry_probe'
    async def start(self):
        for suffix in ('recover', 'fail'):
            yield scrapy.Request(sys.argv[1] + '/' + suffix, errback=self.failed)
    def parse(self, response):
        yield {'status': response.status}
    def failed(self, failure):
        self.crawler.stats.inc_value('probe/failed')
settings = Settings()
settings.setmodule('web_spider.settings')
settings.set('DOWNLOAD_HANDLERS', {})
settings.set('ITEM_PIPELINES', {})
settings.set('ROBOTSTXT_OBEY', False)
settings.set('DOWNLOAD_DELAY', 0)
settings.set('LOG_ENABLED', False)
process = CrawlerProcess(settings)
crawler = process.create_crawler(Probe)
process.crawl(crawler)
process.start()
open(sys.argv[2], 'w').write(json.dumps(crawler.stats.get_stats(), default=str))
''', encoding='utf-8')
    import os
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1]))
    try:
        result = subprocess.run([sys.executable, str(script), f'http://127.0.0.1:{server.server_port}', str(stats_path)],
                                capture_output=True, text=True, timeout=60, env=env)
        assert result.returncode == 0, result.stderr
        stats = json.loads(stats_path.read_text())
        assert counts == {'/recover': 3, '/fail': 4}
        assert stats['retry/count'] == 5
        assert stats['retry/max_reached'] == 1
        assert stats['item_scraped_count'] == 1
        assert stats['probe/failed'] == 1
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
