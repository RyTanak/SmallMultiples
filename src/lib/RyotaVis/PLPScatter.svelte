<script lang="ts">
  import * as d3 from 'd3';
  import type { SteamGame } from '../../types';

  type Props = { games: SteamGame[]; width?: number; height?: number };
  type PriceFilter = 'all' | 'free' | 'under20' | '20to4099' | '41to4999' | 'over50';
  type HoveredPoint = { game: SteamGame; chart: 'reviews' | 'peak' | 'playtime' };

  let { games, width = 1240, height = 420 }: Props = $props();
  let priceFilter = $state<PriceFilter>('all');
  let hoveredPoint = $state<HoveredPoint | null>(null);

  const gap = 44;
  const margin = { top: 36, right: 24, bottom: 58, left: 76 };
  const panelWidth = $derived(Math.max(280, (width - gap) / 2));
  const plotWidth = $derived(Math.max(1, panelWidth - margin.left - margin.right));
  const plotHeight = $derived(Math.max(1, height - margin.top - margin.bottom));

  const isIndie = (game: SteamGame) => game.genres.some((genre) => genre.toLowerCase() === 'indie');
  const reviewCount = (game: SteamGame) => game.positive_reviews + game.negative_reviews;
  const priceRange = (game: SteamGame): Exclude<PriceFilter, 'all'> => {
    if (game.is_free || game.price_no_sales === 0) return 'free';
    if (game.price_no_sales < 20) return 'under20';
    if (game.price_no_sales <= 40.99) return '20to4099';
    if (game.price_no_sales < 50) return '41to4999';
    return 'over50';
  };

  const visiblePoints = $derived(
    games
      .filter((game) => Number.isFinite(game.price_no_sales) && game.price_no_sales >= 0 &&
        Number.isFinite(reviewCount(game)) && reviewCount(game) > 0 &&
        Number.isFinite(game.avg_playtime_forever) && game.avg_playtime_forever > 0)
      .slice(0, 1400)
      .map((game) => ({ game }))
  );
  const maxPrice = $derived(d3.max(visiblePoints, ({ game }) => game.price_no_sales) ?? 1);
  const maxReviews = $derived(d3.max(visiblePoints, ({ game }) => reviewCount(game)) ?? 1);
  const peakPoints = $derived(visiblePoints.filter(({ game }) => Number.isFinite(game.peak_ccu) && game.peak_ccu > 0));
  const maxPeak = $derived(d3.max(peakPoints, ({ game }) => game.peak_ccu) ?? 1);
  const maxPlaytime = $derived(d3.max(visiblePoints, ({ game }) => game.avg_playtime_forever) ?? 1);
  const x = $derived(d3.scaleLinear().domain([0, Math.max(1, maxPrice)]).nice().range([0, plotWidth]));
  const reviewsY = $derived(d3.scaleLog().domain([1, Math.max(1, maxReviews)]).nice().range([plotHeight, 0]));
  const peakY = $derived(d3.scaleLog().domain([1, Math.max(1, maxPeak)]).nice().range([plotHeight, 0]));
  const playtimeY = $derived(d3.scaleLog().domain([1, Math.max(1, maxPlaytime)]).nice().range([plotHeight, 0]));
  const xTicks = $derived(x.ticks(5));
  const reviewTicks = $derived(reviewsY.ticks(5));
  const peakTicks = $derived(peakY.ticks(5));
  const playtimeTicks = $derived(playtimeY.ticks(5));

  const isHighlighted = (game: SteamGame) => priceFilter === 'all' || priceRange(game) === priceFilter;
  const formatPlaytime = (minutes: number) => minutes >= 60 ? `${(minutes / 60).toFixed(1)}h` : `${minutes.toFixed(0)}m`;
  const formatReviews = d3.format('.2s');
  const color = (game: SteamGame) => isIndie(game) ? '#ea580c' : '#0284c7';
  const priceLabel = (game: SteamGame) => game.is_free || game.price_no_sales === 0 ? 'Free' : `$${game.price_no_sales.toFixed(2)}`;
  const tooltipWidth = 190;
  const tooltipX = $derived(hoveredPoint ? Math.min(Math.max(x(hoveredPoint.game.price_no_sales) + 10, 0), Math.max(0, plotWidth - tooltipWidth)) : 0);
  const tooltipY = $derived(hoveredPoint
    ? Math.max(0, (hoveredPoint.chart === 'reviews' ? reviewsY(reviewCount(hoveredPoint.game)) : hoveredPoint.chart === 'peak' ? peakY(hoveredPoint.game.peak_ccu) : playtimeY(hoveredPoint.game.avg_playtime_forever)) - 52)
    : 0);

  const selectPoint = (game: SteamGame, chart: HoveredPoint['chart']) => {
    hoveredPoint = isHighlighted(game) ? { game, chart } : null;
  };
</script>

<section class="price-comparisons">
  <div class="header">
    <div>
      <h2>Price Comparisons</h2>
      <br />
    </div>
  </div>

  <fieldset class="price-filter">
    <legend>Highlight price range</legend>
    <label><input type="radio" name="plp-price-filter" value="all" bind:group={priceFilter} />All</label>
    <label><input type="radio" name="plp-price-filter" value="free" bind:group={priceFilter} />Free</label>
    <label><input type="radio" name="plp-price-filter" value="under20" bind:group={priceFilter} />Below $20</label>
    <label><input type="radio" name="plp-price-filter" value="20to4099" bind:group={priceFilter} />$20–$40.99</label>
    <label><input type="radio" name="plp-price-filter" value="41to4999" bind:group={priceFilter} />$41–$49.99</label>
    <label><input type="radio" name="plp-price-filter" value="over50" bind:group={priceFilter} />$50+</label>
  </fieldset>

  <div class="legend" aria-label="Point color legend">
    <span><i class="swatch indie"></i>Indie</span>
    <span><i class="swatch non-indie"></i>Non-indie</span>
    <span class="point-count">{visiblePoints.length.toLocaleString()} games</span>
  </div>

  {#if visiblePoints.length === 0}
    <p>No games with valid price, review-count, and playtime data are available.</p>
  {:else}
    <div class="charts">
      <div class="left-charts">
      <svg width={panelWidth} {height} role="img" aria-label="Scatterplot of price and review count, colored by indie status">
        <g transform={`translate(${margin.left} ${margin.top})`}>
          <text class="chart-title" x={plotWidth / 2} y={-14} text-anchor="middle">Price vs. Review Count</text>
          {#each reviewTicks as tick}
            <line class="grid-line" x1="0" x2={plotWidth} y1={reviewsY(tick)} y2={reviewsY(tick)} />
            <text class="tick-label" x={-10} y={reviewsY(tick)} text-anchor="end" dominant-baseline="middle">{formatReviews(tick)}</text>
          {/each}
          {#each xTicks as tick}
            <line class="grid-line" y1="0" y2={plotHeight} x1={x(tick)} x2={x(tick)} />
            <text class="tick-label" x={x(tick)} y={plotHeight + 18} text-anchor="middle">${tick.toFixed(0)}</text>
          {/each}
          {#each visiblePoints as point}
            <circle
              cx={x(point.game.price_no_sales)}
              cy={reviewsY(reviewCount(point.game))}
              r={isHighlighted(point.game) ? 4 : 2.5}
              fill={color(point.game)}
              opacity={isHighlighted(point.game) ? 0.75 : 0.12}
              stroke={isHighlighted(point.game) ? 'white' : 'none'}
              stroke-width="0.7"
              role="img"
              pointer-events={isHighlighted(point.game) ? 'auto' : 'none'}
              onmouseenter={() => selectPoint(point.game, 'reviews')}
              onmouseleave={() => hoveredPoint = null}
            >
              {#if isHighlighted(point.game)}
                <title>{point.game.name}: {priceLabel(point.game)}, {formatReviews(reviewCount(point.game))} reviews; {isIndie(point.game) ? 'Indie' : 'Non-indie'}</title>
              {/if}
            </circle>
          {/each}
          {#if hoveredPoint?.chart === 'reviews' && isHighlighted(hoveredPoint.game)}
            <g class="tooltip" transform={`translate(${tooltipX} ${tooltipY})`}>
              <rect width={tooltipWidth} height="60" rx="4" />
              <text x="9" y="18">{hoveredPoint.game.name}</text>
              <text x="9" y="36">Price: {priceLabel(hoveredPoint.game)}</text>
              <text x="9" y="54">Reviews: {formatReviews(reviewCount(hoveredPoint.game))}</text>
            </g>
          {/if}
          <line class="axis" x1="0" x2={plotWidth} y1={plotHeight} y2={plotHeight} />
          <line class="axis" x1="0" x2="0" y1="0" y2={plotHeight} />
          <text class="axis-label" x={plotWidth / 2} y={plotHeight + 44} text-anchor="middle">Price (USD)</text>
          <text class="axis-label" transform={`translate(${-58} ${plotHeight / 2}) rotate(-90)`} text-anchor="middle">Review count (log scale)</text>
        </g>
      </svg>

      <svg width={panelWidth} {height} role="img" aria-label="Scatterplot of price and peak concurrent players, colored by indie status">
        <g transform={`translate(${margin.left} ${margin.top})`}>
          <text class="chart-title" x={plotWidth / 2} y={-14} text-anchor="middle">Price vs. Peak Concurrent Players</text>
          {#each peakTicks as tick}
            <line class="grid-line" x1="0" x2={plotWidth} y1={peakY(tick)} y2={peakY(tick)} />
            <text class="tick-label" x={-10} y={peakY(tick)} text-anchor="end" dominant-baseline="middle">{formatReviews(tick)}</text>
          {/each}
          {#each xTicks as tick}
            <line class="grid-line" y1="0" y2={plotHeight} x1={x(tick)} x2={x(tick)} />
            <text class="tick-label" x={x(tick)} y={plotHeight + 18} text-anchor="middle">${tick.toFixed(0)}</text>
          {/each}
          {#each peakPoints as point}
            <circle
              cx={x(point.game.price_no_sales)}
              cy={peakY(point.game.peak_ccu)}
              r={isHighlighted(point.game) ? 4 : 2.5}
              fill={color(point.game)}
              opacity={isHighlighted(point.game) ? 0.75 : 0.12}
              stroke={isHighlighted(point.game) ? 'white' : 'none'}
              stroke-width="0.7"
              role="img"
              pointer-events={isHighlighted(point.game) ? 'auto' : 'none'}
              onmouseenter={() => selectPoint(point.game, 'peak')}
              onmouseleave={() => hoveredPoint = null}
            >
              {#if isHighlighted(point.game)}
                <title>{point.game.name}: {priceLabel(point.game)}, {formatReviews(point.game.peak_ccu)} peak concurrent players; {isIndie(point.game) ? 'Indie' : 'Non-indie'}</title>
              {/if}
            </circle>
          {/each}
          {#if hoveredPoint?.chart === 'peak' && isHighlighted(hoveredPoint.game)}
            <g class="tooltip" transform={`translate(${tooltipX} ${tooltipY})`}>
              <rect width={tooltipWidth} height="60" rx="4" />
              <text x="9" y="18">{hoveredPoint.game.name}</text>
              <text x="9" y="36">Price: {priceLabel(hoveredPoint.game)}</text>
              <text x="9" y="54">Peak CCU: {formatReviews(hoveredPoint.game.peak_ccu)}</text>
            </g>
          {/if}
          <line class="axis" x1="0" x2={plotWidth} y1={plotHeight} y2={plotHeight} />
          <line class="axis" x1="0" x2="0" y1="0" y2={plotHeight} />
          <text class="axis-label" x={plotWidth / 2} y={plotHeight + 44} text-anchor="middle">Price (USD)</text>
          <text class="axis-label" transform={`translate(${-58} ${plotHeight / 2}) rotate(-90)`} text-anchor="middle">Peak concurrent players (log scale)</text>
        </g>
      </svg>
      </div>
      <svg width={panelWidth} {height} role="img" aria-label="Scatterplot of price and playtime, colored by indie status">
        <g transform={`translate(${margin.left} ${margin.top})`}>
          <text class="chart-title" x={plotWidth / 2} y={-14} text-anchor="middle">Price vs. Playtime</text>
          {#each playtimeTicks as tick}
            <line class="grid-line" x1="0" x2={plotWidth} y1={playtimeY(tick)} y2={playtimeY(tick)} />
            <text class="tick-label" x={-10} y={playtimeY(tick)} text-anchor="end" dominant-baseline="middle">{formatPlaytime(tick)}</text>
          {/each}
          {#each xTicks as tick}
            <line class="grid-line" y1="0" y2={plotHeight} x1={x(tick)} x2={x(tick)} />
            <text class="tick-label" x={x(tick)} y={plotHeight + 18} text-anchor="middle">${tick.toFixed(0)}</text>
          {/each}
          {#each visiblePoints as point}
            <circle
              cx={x(point.game.price_no_sales)}
              cy={playtimeY(point.game.avg_playtime_forever)}
              r={isHighlighted(point.game) ? 4 : 2.5}
              fill={color(point.game)}
              opacity={isHighlighted(point.game) ? 0.75 : 0.12}
              stroke={isHighlighted(point.game) ? 'white' : 'none'}
              stroke-width="0.7"
              role="img"
              pointer-events={isHighlighted(point.game) ? 'auto' : 'none'}
              onmouseenter={() => selectPoint(point.game, 'playtime')}
              onmouseleave={() => hoveredPoint = null}
            >
              {#if isHighlighted(point.game)}
                <title>{point.game.name}: {priceLabel(point.game)}, {formatPlaytime(point.game.avg_playtime_forever)}; {isIndie(point.game) ? 'Indie' : 'Non-indie'}</title>
              {/if}
            </circle>
          {/each}
          {#if hoveredPoint?.chart === 'playtime' && isHighlighted(hoveredPoint.game)}
            <g class="tooltip" transform={`translate(${tooltipX} ${tooltipY})`}>
              <rect width={tooltipWidth} height="60" rx="4" />
              <text x="9" y="18">{hoveredPoint.game.name}</text>
              <text x="9" y="36">Price: {priceLabel(hoveredPoint.game)}</text>
              <text x="9" y="54">Playtime: {formatPlaytime(hoveredPoint.game.avg_playtime_forever)}</text>
            </g>
          {/if}
          <line class="axis" x1="0" x2={plotWidth} y1={plotHeight} y2={plotHeight} />
          <line class="axis" x1="0" x2="0" y1="0" y2={plotHeight} />
          <text class="axis-label" x={plotWidth / 2} y={plotHeight + 44} text-anchor="middle">Price (USD)</text>
          <text class="axis-label" transform={`translate(${-58} ${plotHeight / 2}) rotate(-90)`} text-anchor="middle">Average playtime (minutes, log scale)</text>
        </g>
      </svg>
    </div>
  {/if}
</section>

<style>
  .price-comparisons { min-width: 0; }
  .header { display: block; }
  h2 { margin: 0 0 0.25rem; }
  .price-filter { display: flex; flex-wrap: wrap; gap: 0.45rem 0.75rem; margin: 0; padding: 0; border: 0; }
  .price-filter legend { width: 100%; margin-bottom: 0.15rem; color: #475569; font-size: 0.8rem; font-weight: 600; }
  .price-filter label, .legend span { display: inline-flex; align-items: center; gap: 0.3rem; color: #243247; font-size: 0.78rem; white-space: nowrap; }
  .price-filter input { accent-color: #2563eb; }
  .legend { display: flex; flex-wrap: wrap; align-items: center; gap: 0.75rem; margin: 0.75rem 0 0.25rem; }
  .swatch { width: 0.7rem; height: 0.7rem; border-radius: 50%; }
  .swatch.indie { background: #ea580c; }
  .swatch.non-indie { background: #0284c7; }
  .point-count { margin-left: auto; color: #64748b !important; }
  .charts { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 44px; align-items: start; }
  .left-charts { display: grid; gap: 44px; min-width: 0; }
  svg { display: block; max-width: 100%; overflow: visible; font-family: inherit; }
  .chart-title { fill: #243247; font-size: 12px; font-weight: 700; }
  .grid-line { stroke: #e2e8f0; stroke-width: 1; }
  .axis { stroke: #64748b; stroke-width: 1; }
  .tick-label { fill: #64748b; font-size: 10px; }
  .axis-label { fill: #243247; font-size: 11px; }
  .tooltip { pointer-events: none; }
  .tooltip rect { fill: #172033; stroke: white; stroke-width: 1; }
  .tooltip text { fill: white; font-size: 11px; }
  .tooltip text:first-of-type { font-weight: 700; }
  @media (max-width: 900px) {
    .charts { grid-template-columns: 1fr; }
    .point-count { margin-left: 0; }
  }
</style>