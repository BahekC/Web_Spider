import subprocess
import sys

import pytest


@pytest.mark.parametrize('extra', [
    ['--output', 'bad.txt'],
    ['--output', 'data.json', '--days', '-1'],
    ['--output', 'data.csv', '--max-pages', '0'],
])
def test_cli_rejects_invalid_arguments(extra):
    result = subprocess.run([sys.executable, 'run_spider.py', '--spider', 'news', *extra], capture_output=True)
    assert result.returncode == 2


def test_cli_rejects_unimplemented_store():
    result = subprocess.run([sys.executable, 'run_spider.py', '--spider', 'ecommerce',
                             '--stores', 'ozon', '--output', 'data.json'], capture_output=True)
    assert result.returncode == 2
