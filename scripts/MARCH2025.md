The main page and all ten visualizations use the March 2025 cleaned dataset.

Regenerate the browser CSV after changing the source:

```powershell
python scripts/prepare_march2025.py
```

Source: `static/games_march2025_cleaned.csv` (89,618 rows).
Output: `static/games_march2025_visualizations.csv` (same rows, selected columns).
The page loads the output to avoid downloading 469 MB of descriptions and media
metadata. The output is approximately 60 MB, so the first load can still take time.

The converter maps March column names to the existing `SteamGame` interface,
decodes Python literal lists and tag dictionary keys, and normalizes owner ranges
from `100000 - 200000` to `100000 .. 200000` for GPHeatmap.
Prices and discounts come from `price` and `discount`; `price_no_sales` reverses
the discount and rounds to cents. A 100% discount cannot be reversed, so that case
uses the listed price. Zero price determines `is_free` because this source has
no free-game flag. It also has no coming-soon flag; the compatibility field is
false and release-date charts use the source release date. Zero Metacritic
scores become null, meaning unavailable. Review counts use `positive` and
`negative`, and median playtime uses `median_playtime_forever`.

Existing chart-specific review thresholds, company selections, and point limits
remain in effect. Both GPHeatmap and PLPScatter still use undiscounted prices.
