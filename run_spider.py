"""CLI with two simultaneous exports and machine-readable run evidence."""
import argparse
import json
import os
from pathlib import Path


def positive(value):
    result = int(value)
    if result <= 0:
        raise argparse.ArgumentTypeError('must be positive')
    return result


def nonnegative(value):
    result = int(value)
    if result < 0:
        raise argparse.ArgumentTypeError('must be nonnegative')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description='Лабораторная 4: сбор и очистка веб-данных')
    parser.add_argument('--spider', required=True, choices=['news', 'ecommerce'])
    parser.add_argument('--keywords', default='', help='Ключевые слова через запятую, логика ИЛИ')
    parser.add_argument('--days', type=nonnegative, default=7, help='Давность новостей; 0 = без ограничения')
    parser.add_argument('--category', default='laptops')
    parser.add_argument('--stores', default='webscraper')
    parser.add_argument('--max-pages', type=positive)
    parser.add_argument('--min-items', type=nonnegative, default=100, help='Минимум записей для успешного запуска')
    parser.add_argument('--output', required=True, type=Path, help='JSON или CSV; второй формат создаётся рядом')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO')
    args = parser.parse_args(argv)
    if args.output.suffix.lower() not in ('.json', '.csv'):
        parser.error('--output must end in .json or .csv')
    if args.spider == 'ecommerce' and args.keywords:
        parser.error('--keywords applies only to news; use --category for ecommerce')
    if args.spider == 'ecommerce':
        if args.category.lower() not in ('laptops', 'tablets', 'ноутбуки', 'планшеты'):
            parser.error('Supported categories: laptops, tablets, ноутбуки, планшеты')
        if {s.strip().lower() for s in args.stores.split(',')} != {'webscraper'}:
            parser.error('Supported store: webscraper')

    root = Path(__file__).resolve().parent
    if (root / '.browsers').exists():
        os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH', str(root / '.browsers'))
    from scrapy.crawler import CrawlerProcess
    from scrapy.settings import Settings
    from web_spider.spiders.news import NewsSpider
    from web_spider.spiders.ecommerce import EcommerceSpider

    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    settings = Settings()
    settings.setmodule('web_spider.settings', priority='project')
    fields = ['title', 'url', 'source', 'collected_at'] + (
        ['date', 'summary'] if args.spider == 'news' else ['price', 'currency', 'rating', 'category', 'store', 'summary'])
    settings.set('FEEDS', {str(output.with_suffix('.' + fmt)): {
        'format': fmt, 'overwrite': True, 'encoding': 'utf-8', 'fields': fields,
    } for fmt in ('json', 'csv')}, priority='cmdline')
    settings.set('LOG_FILE', str(output.with_suffix('.log')), priority='cmdline')
    settings.set('LOG_LEVEL', args.log_level, priority='cmdline')
    process = CrawlerProcess(settings)
    crawler = process.create_crawler(NewsSpider if args.spider == 'news' else EcommerceSpider)
    kwargs = {'max_pages': args.max_pages or (5 if args.spider == 'news' else 30)}
    kwargs.update({'keywords': args.keywords, 'days': args.days} if args.spider == 'news' else
                  {'category': args.category, 'stores': args.stores})
    failures = []
    deferred = process.crawl(crawler, **kwargs)
    deferred.addErrback(lambda failure: failures.append(str(failure)))
    process.start()
    stats = crawler.stats.get_stats() if crawler.stats else {}
    count = stats.get('item_scraped_count', 0)
    success = (not failures and count >= args.min_items and stats.get('finish_reason') == 'finished'
               and not stats.get('source/failed_requests') and not stats.get('quality/layout_errors')
               and not stats.get('spider_exceptions/count') and not stats.get('log_count/ERROR')
               and not any(k.startswith('feedexport/failed_count') and v for k, v in stats.items()))
    result = {'success': success, 'spider': args.spider, 'min_items': args.min_items,
              'item_count': count, 'arguments': vars(args), 'failures': failures, 'stats': stats}
    output.with_suffix('.stats.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    print(f'{args.spider}: {count} records; success={success}; {output.with_suffix(".json")} + CSV')
    return 0 if success else 1


if __name__ == '__main__':
    raise SystemExit(main())
