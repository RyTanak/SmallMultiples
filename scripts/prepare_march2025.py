"""Create the browser dataset from games_march2025_cleaned.csv (no row filtering).

Run: python scripts/prepare_march2025.py
Python literal lists/dictionaries are decoded here rather than in the browser.
"""
import ast
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'static/games_march2025_cleaned.csv'
TARGET = ROOT / 'static/games_march2025_visualizations.csv'

FIELDS = [
    'app_id', 'name', 'release_date', 'coming_soon', 'price_usd', 'is_free',
    'discount_pct', 'developer', 'publisher', 'genres', 'categories', 'tags',
    'platforms_win', 'platforms_mac', 'platforms_linux', 'metacritic_score',
    'recommendations', 'positive_reviews', 'negative_reviews', 'estimated_owners',
    'avg_playtime_forever', 'avg_playtime_2weeks', 'median_playtime', 'peak_ccu',
    'required_age', 'dlc_count', 'achievements', 'short_description', 'header_image',
    'price_no_sales'
]
RENAMED = {
    'app_id': 'appid', 'price_usd': 'price', 'discount_pct': 'discount',
    'platforms_win': 'windows', 'platforms_mac': 'mac', 'platforms_linux': 'linux',
    'positive_reviews': 'positive', 'negative_reviews': 'negative',
    'avg_playtime_forever': 'average_playtime_forever',
    'avg_playtime_2weeks': 'average_playtime_2weeks', 'median_playtime': 'median_playtime_forever'
}

def items(value):
    parsed = ast.literal_eval(value or '[]')
    return list(parsed)  # Tag dictionaries become lists of tag names.


def prepare():
    count = 0
    with SOURCE.open(encoding='utf-8-sig', newline='') as source, TARGET.open('w', encoding='utf-8', newline='') as target:
        writer = csv.DictWriter(target, fieldnames=FIELDS)
        writer.writeheader()
        for row in csv.DictReader(source):
            result = {field: row.get(RENAMED.get(field, field), '') for field in FIELDS}
            for field in ['genres', 'categories', 'tags']:
                result[field] = ', '.join(items(row[field]))
            result['developer'] = ', '.join(items(row['developers']))
            result['publisher'] = ', '.join(items(row['publishers']))
            result['estimated_owners'] = row['estimated_owners'].replace(' - ', ' .. ')
            price, discount = float(row['price']), float(row['discount'])
            result['is_free'] = price == 0
            # The source has no coming-soon flag. All charts use release_date instead.
            result['coming_soon'] = False
            result['price_no_sales'] = round(price / (1 - discount / 100), 2) if discount < 100 else price
            # Zero is the source's sentinel for an unavailable critic score.
            result['metacritic_score'] = row['metacritic_score'] if float(row['metacritic_score']) > 0 else ''
            writer.writerow(result)
            count += 1
    print(f'Prepared {count:,} games: {TARGET.name} ({TARGET.stat().st_size / 1e6:.1f} MB)')


if __name__ == '__main__':
    prepare()
