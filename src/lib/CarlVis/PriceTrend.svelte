<script lang="ts">
  import * as d3 from 'd3';
  import type { SteamGame } from '../../types';

  type Props = { games: SteamGame[]; width?: number; height?: number };
  type Category = 'indie' | 'nonIndie';
  type PriceBand = { price: number; game: SteamGame };
  type YearSummary = { year: number; indie: PriceBand[]; nonIndie: PriceBand[] };
  type PricePoint = { year: number; price: number };
  type DotDefinition = { category: Category; rank: number; points: PricePoint[] };
  type DotPoint = PricePoint & { category: Category; rank: number; overlap: boolean };

  let { games, width = 760, height = 430 }: Props = $props();

  // Raise this value to show fewer games, or lower it to include more.
  const MIN_TOTAL_REVIEWS = 3_000;
  // Prices within this amount are grouped into the same price band.
  const PRICE_MATCH_MARGIN = 0.5;
  const TOP_PRICE_BANDS = 3;
  const categories: Category[] = ['indie', 'nonIndie'];
  const ranks = [0, 1, 2];
  const margin = { top: 28, right: 28, bottom: 54, left: 60 };
  const totalReviews = (game: SteamGame) => game.positive_reviews + game.negative_reviews;
  const isIndie = (game: SteamGame) =>
    [...game.genres, ...game.tags].some((value) => value.trim().toLowerCase() === 'indie');
  const sentiment = (game: SteamGame) => {
    const reviews = totalReviews(game);
    return reviews > 0 ? game.positive_reviews / reviews : 0;
  };

  const subset = $derived(
    games.filter((game) => totalReviews(game) >= MIN_TOTAL_REVIEWS && game.release_date !== null)
  );

  const buildPriceBands = (categoryGames: SteamGame[]) => {
    const sortedGames = [...categoryGames].sort((a, b) => a.price_usd - b.price_usd);
    const bands: SteamGame[][] = [];

    sortedGames.forEach((game) => {
      const currentBand = bands[bands.length - 1];
      const currentBandMax = currentBand ? currentBand[currentBand.length - 1].price_usd : null;
      if (currentBand && currentBandMax !== null && game.price_usd - currentBandMax <= PRICE_MATCH_MARGIN + 1e-9) {
        currentBand.push(game);
      } else {
        bands.push([game]);
      }
    });

    const summarizeBand = (band: SteamGame[]): PriceBand => {
        const priceCounts = new Map<number, number>();
        const priceReviews = new Map<number, number>();
        band.forEach((game) => {
          priceCounts.set(game.price_usd, (priceCounts.get(game.price_usd) ?? 0) + 1);
          priceReviews.set(game.price_usd, (priceReviews.get(game.price_usd) ?? 0) + totalReviews(game));
        });
        const price = [...priceCounts.keys()].sort(
          (a, b) =>
            (priceCounts.get(b) ?? 0) - (priceCounts.get(a) ?? 0) ||
            (priceReviews.get(b) ?? 0) - (priceReviews.get(a) ?? 0) ||
            a - b
        )[0];
        const game = band.reduce((mostReviewed, candidate) =>
          totalReviews(candidate) > totalReviews(mostReviewed) ? candidate : mostReviewed
        );
        return { price, game };
    };
    const orderedBands = bands.sort(
      (a, b) =>
        b.length - a.length ||
        d3.sum(b, totalReviews) - d3.sum(a, totalReviews) ||
        d3.min(a, (game) => game.price_usd)! - d3.min(b, (game) => game.price_usd)!
    );
    const selectedBands = orderedBands.slice(0, TOP_PRICE_BANDS).map(summarizeBand);

    if (selectedBands.length >= TOP_PRICE_BANDS) return selectedBands;

    const usedPrices = new Set(selectedBands.map((band) => band.price));
    const fallbackPrices = [...new Set(categoryGames.map((game) => game.price_usd))]
      .filter((price) => !usedPrices.has(price))
      .sort(
        (a, b) =>
          categoryGames.filter((game) => game.price_usd === b).length -
            categoryGames.filter((game) => game.price_usd === a).length ||
          d3.sum(categoryGames.filter((game) => game.price_usd === b), totalReviews) -
            d3.sum(categoryGames.filter((game) => game.price_usd === a), totalReviews) ||
          a - b
      )
      .slice(0, TOP_PRICE_BANDS - selectedBands.length);

    return [
      ...selectedBands,
      ...fallbackPrices.map((price) => summarizeBand(categoryGames.filter((game) => game.price_usd === price)))
    ];
  };

  const yearSummaries = $derived.by(() => {
    const years = [...new Set(subset.map((game) => game.release_date!.getFullYear()))].sort(
      (a, b) => a - b
    );
    return years.map((year): YearSummary => {
      const yearGames = subset.filter((game) => game.release_date!.getFullYear() === year);
      return {
        year,
        indie: buildPriceBands(yearGames.filter(isIndie)),
        nonIndie: buildPriceBands(yearGames.filter((game) => !isIndie(game)))
      };
    });
  });

  const years = $derived(yearSummaries.map((summary) => summary.year));
  const maxPrice = $derived(
    Math.max(
      1,
      d3.max(yearSummaries, (summary) =>
        d3.max([...summary.indie, ...summary.nonIndie], (band) => band.price)
      ) ?? 1
    )
  );
  const xScale = $derived(d3.scalePoint<number>().domain(years).range([margin.left, width - margin.right]));
  const yScale = $derived(
    d3.scaleLinear().domain([0, maxPrice]).nice().range([height - margin.bottom, margin.top])
  );
  const dotDefinitions = $derived.by(() =>
    categories.flatMap((category) =>
      ranks.map((rank): DotDefinition => {
        const points = yearSummaries.flatMap((summary) => {
          const band = summary[category][rank];
          return band ? [{ year: summary.year, price: band.price }] : [];
        });
        return { category, rank, points };
      })
    )
  );
  const dotPoints = $derived.by(() => {
    const points = dotDefinitions.flatMap((definition) =>
      definition.points.map((point) => ({ ...point, category: definition.category, rank: definition.rank }))
    );
    return points
      .map((point): DotPoint => ({
        ...point,
        overlap: points.some(
          (other) =>
            other !== point &&
            other.category !== point.category &&
            other.year === point.year &&
            Math.abs(other.price - point.price) <= PRICE_MATCH_MARGIN + 1e-9
        )
      }))
      .sort((a, b) => a.rank - b.rank);
  });
  const tickYears = $derived(
    years.filter((_, index) => index % Math.max(1, Math.ceil(years.length / 10)) === 0)
  );
  let hoveredYear = $state<number | null>(null);
  const hoveredSummary = $derived(
    hoveredYear === null ? null : yearSummaries.find((summary) => summary.year === hoveredYear) ?? null
  );

  const bandFor = (summary: YearSummary | null, category: Category, rank: number) =>
    summary?.[category][rank] ?? null;
  const handleDotHover = (year: number) => {
    hoveredYear = year;
  };
  const clearHover = () => {
    hoveredYear = null;
  };

  const formatReviews = d3.format(',');
  const formatPrice = d3.format('$,.2f');
  const formatSentiment = d3.format('.1%');
  const categoryLabel = (category: Category) => (category === 'indie' ? 'Indie' : 'Non-indie');
  const dotRadius = (rank: number) => 6 - rank * 1.25;
</script>

<section class="price-trend">
  <h2>Top game price bands by release year</h2>
  <p class="subtitle">
    {subset.length} games with at least {formatReviews(MIN_TOTAL_REVIEWS)} total reviews; similar prices within {formatPrice(PRICE_MATCH_MARGIN)} are grouped.
  </p>

  <svg {width} {height} aria-label="Dot chart of the top three indie and non-indie price bands by year">
    {#each yScale.ticks(5) as tick}
      <line class="grid-line" x1={margin.left} x2={width - margin.right} y1={yScale(tick)} y2={yScale(tick)} />
      <text class="tick-label" x={margin.left - 8} y={yScale(tick) + 4} text-anchor="end">{formatPrice(tick)}</text>
    {/each}
    {#each tickYears as year}
      {@const x = xScale(year) ?? 0}
      <line class="year-tick" x1={x} x2={x} y1={height - margin.bottom} y2={height - margin.bottom + 5} />
      <text class="tick-label" x={x} y={height - margin.bottom + 20} text-anchor="middle">{year}</text>
    {/each}
    <line class="axis" x1={margin.left} x2={width - margin.right} y1={height - margin.bottom} y2={height - margin.bottom} />
    <line class="axis" x1={margin.left} x2={margin.left} y1={margin.top} y2={height - margin.bottom} />

    {#each dotPoints as dot (`${dot.category}-${dot.rank}-${dot.year}`)}
        <circle
          class:dimmed-dot={hoveredYear !== null && hoveredYear !== dot.year}
          class:selected-dot={hoveredYear === dot.year}
          class:overlap-dot={dot.overlap}
          class={`dot ${dot.category}-dot rank-${dot.rank + 1}`}
          cx={xScale(dot.year)}
          cy={yScale(dot.price)}
          r={dotRadius(dot.rank)}
          onmouseenter={() => handleDotHover(dot.year)}
          onmouseleave={clearHover}
          role="img"
          aria-label={`${categoryLabel(dot.category)}, price band ${dot.rank + 1}, ${dot.year}`}
        >
          <title>{dot.overlap ? 'Overlapping indie and non-indie dots: ' : ''}{categoryLabel(dot.category)}, price band {dot.rank + 1}, {dot.year}: {formatPrice(dot.price)}</title>
        </circle>
    {/each}

    <text class="axis-label" x={width / 2} y={height - 5} text-anchor="middle">Release year</text>
    <text class="axis-label" transform={`translate(14 ${height / 2}) rotate(-90)`} text-anchor="middle">Price (USD)</text>
  </svg>

  <div class="legend">
    <span class="legend-dot indie-dot rank-1"></span> Indie
    <span class="legend-dot nonIndie-dot rank-1"></span> Non-indie
    <span class="legend-dot overlap-dot rank-1"></span> Overlap
    <span class="rank-key">Large = 1st · medium = 2nd · small = 3rd</span>
  </div>

  <div class="selection" aria-live="polite">
    {#if hoveredYear !== null && hoveredSummary}
      <strong>{hoveredYear}</strong>
      {#each categories as category}
        <div class={`selection-category ${category}-text`}>
          <b>{categoryLabel(category)}</b>
          {#each ranks as rank}
            {@const band = bandFor(hoveredSummary, category, rank)}
            {#if band}
              <div>
                <span>{rank + 1}. {band.game.name}</span> · {formatPrice(band.price)} · {formatReviews(totalReviews(band.game))} reviews · {formatSentiment(sentiment(band.game))} positive
              </div>
            {:else}
              <div>{rank + 1}. No qualifying price band</div>
            {/if}
          {/each}
        </div>
      {/each}
    {/if}
  </div>
</section>

<style>
  .price-trend { min-width: 0; }
  h2 { margin-bottom: 0.2rem; }
  .subtitle { color: #64748b; font-size: 0.82rem; margin: 0; }
  svg { display: block; height: auto; max-width: 100%; overflow: visible; }
  .axis, .year-tick { stroke: #475569; stroke-width: 1; }
  .grid-line { stroke: #cbd5e1; stroke-dasharray: 2 3; }
  .tick-label, .axis-label { fill: #64748b; font-size: 10px; }
  .axis-label { font-size: 11px; }
  .dot { cursor: pointer; stroke: #fff; stroke-width: 1.5; transition: opacity 120ms ease, r 120ms ease, stroke-width 120ms ease; }
  .indie-dot { fill: #f97316; }
  .nonIndie-dot { fill: #64748b; }
  .overlap-dot { fill: #8b5cf6; }
  .dimmed-dot { opacity: 0.18; }
  .selected-dot { opacity: 1; stroke: #0f172a; stroke-width: 2.5; }
  .legend { color: #64748b; font-size: 0.78rem; text-align: center; }
  .legend-dot { border-radius: 50%; display: inline-block; height: 0.65rem; margin: 0 0.3rem 0 0.8rem; vertical-align: middle; width: 0.65rem; }
  .legend-dot:first-child { margin-left: 0; }
  .legend-dot.indie-dot { background: #f97316; }
  .legend-dot.nonIndie-dot { background: #64748b; }
  .rank-key { margin-left: 0.8rem; }
  .selection { align-items: flex-start; background: #f8fafc; border-left: 3px solid #94a3b8; box-sizing: border-box; color: #475569; display: flex; flex-wrap: wrap; gap: 0.35rem 0.8rem; height: 9.5rem; line-height: 1.4; overflow: hidden; padding: 0.45rem 0.65rem; }
  .selection strong { color: #0f172a; }
  .selection-category { flex: 1 1 18rem; min-width: 0; }
  .selection-category b { display: block; margin-bottom: 0.15rem; }
  .indie-text b { color: #ea580c; }
  .nonIndie-text b { color: #475569; }
  .focused-selection { color: #0f172a; font-weight: 700; }
</style>
