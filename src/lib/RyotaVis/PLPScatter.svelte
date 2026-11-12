<script lang="ts">
  import * as d3 from 'd3';
  import type { SteamGame } from '../../types';

  type Props = { games: SteamGame[]; width?: number; height?: number };
  type PriceFilter = 'all' | 'free' | 'under20' | '20to4099' | '41to4999' | 'over50';

  let { games, width = 620, height = 420 }: Props = $props();
  let priceFilter = $state<PriceFilter>('all');
  let yMetric = $state<'owners' | 'reviews'>('reviews');
  let hoveredPoint = $state<{ game: SteamGame; owners: number | null } | null>(null);

  const margin = { top: 24, right: 24, bottom: 58, left: 76 };
  const plotWidth = $derived(Math.max(1, width - margin.left - margin.right));
  const plotHeight = $derived(Math.max(1, height - margin.top - margin.bottom));

  const owners = (game: SteamGame): number | null => {
    const bounds = game.estimated_owners.replaceAll(',', '').split('..').map((part) => Number(part.trim()));
    return bounds.length === 2 && bounds.every((value) => Number.isFinite(value) && value > 0)
      ? (bounds[0] + bounds[1]) / 2
      : null;
  };

  const isIndie = (game: SteamGame) => game.genres.some((genre) => genre.toLowerCase() === 'indie');
  const priceRange = (game: SteamGame): Exclude<PriceFilter, 'all'> => {
    if (game.is_free || game.price_usd === 0) return 'free';
    if (game.price_usd < 20) return 'under20';
    if (game.price_usd <= 40.99) return '20to4099';
    if (game.price_usd < 50) return '41to4999';
    return 'over50';
  };

  const points = $derived(
    games
      .map((game) => ({ game, owners: owners(game) }))
      .filter(({ game, owners: ownerCount }) =>
        Number.isFinite(game.avg_playtime_forever) && game.avg_playtime_forever > 0 &&
        (ownerCount !== null || game.positive_reviews + game.negative_reviews > 0)
      )
      .slice(0, 1400)
  );

  const visiblePoints = $derived(points.filter(({ owners: ownerCount }) =>
    yMetric === 'reviews' || (ownerCount ?? 0) > 10000
  ));
  const maxPlaytime = $derived(d3.max(visiblePoints, ({ game }) => game.avg_playtime_forever) ?? 1);
  const yValue = (point: { game: SteamGame; owners: number | null }): number | null =>
    yMetric === 'owners' ? point.owners : point.game.positive_reviews + point.game.negative_reviews;
  const maxY = $derived(d3.max(visiblePoints, (point) => yValue(point) ?? 1) ?? 1);
  const x = $derived(d3.scaleLog().domain([1, Math.max(1, maxPlaytime)]).nice().range([0, plotWidth]));
  const y = $derived(d3.scaleLog().domain([1, Math.max(1, maxY)]).nice().range([plotHeight, 0]));
  const xTicks = $derived(x.ticks(5));
  const yTicks = $derived(y.ticks(5));

  const isHighlighted = (game: SteamGame) => priceFilter === 'all' || priceRange(game) === priceFilter;
  const formatNumber = d3.format('.2s');
  const formatPlaytime = (minutes: number) => minutes >= 60 ? `${(minutes / 60).toFixed(1)}h` : `${minutes.toFixed(0)}m`;
  const color = (game: SteamGame) => isIndie(game) ? '#2563eb' : '#eab308';
  const priceLabel = (game: SteamGame) => game.is_free || game.price_usd === 0 ? 'Free' : `${game.price_usd.toFixed(2)}`;
  const tooltipWidth = 190;
  const tooltipX = $derived(hoveredPoint ? Math.min(Math.max(x(hoveredPoint.game.avg_playtime_forever) + 10, 0), Math.max(0, plotWidth - tooltipWidth)) : 0);
  const tooltipY = $derived(hoveredPoint ? Math.max(0, y(yValue(hoveredPoint) ?? 1) - 52) : 0);
</script>

<section class="playtime-owners">
  <div class="header">
    <div>
      <h2>Playtime and Review Count</h2>
      <!-- <p class="subtitle">Select a price range to highlight its games.</p> -->
       <br/>
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
  <div class="metric-switch" role="group" aria-label="Y-axis measure">
    <span>Y-axis:</span>
    <button class:active={yMetric === 'owners'} aria-pressed={yMetric === 'owners'} onclick={() => yMetric = 'owners'}>Estimated owners</button>
    <button class:active={yMetric === 'reviews'} aria-pressed={yMetric === 'reviews'} onclick={() => yMetric = 'reviews'}>Review count</button>
  </div>

  <div class="legend" aria-label="Point color legend">
    <span><i class="swatch indie"></i>Indie</span>
    <span><i class="swatch non-indie"></i>Non-indie</span>
    <span class="point-count">{visiblePoints.length.toLocaleString()} games</span>
  </div>

  {#if visiblePoints.length === 0}
    <p>No games with valid playtime and estimated-owner data are available.</p>
  {:else}
    <svg {width} {height} role="img" aria-label={`Scatterplot of playtime and ${yMetric === 'owners' ? 'estimated owners' : 'review count'}, colored by indie status`}>
      <g transform={`translate(${margin.left} ${margin.top})`}>
        {#each yTicks as tick}
          <line class="grid-line" x1="0" x2={plotWidth} y1={y(tick)} y2={y(tick)} />
          <text class="tick-label" x={-10} y={y(tick)} text-anchor="end" dominant-baseline="middle">{formatNumber(tick)}</text>
        {/each}
        {#each xTicks as tick}
          <line class="grid-line" y1="0" y2={plotHeight} x1={x(tick)} x2={x(tick)} />
          <text class="tick-label" x={x(tick)} y={plotHeight + 18} text-anchor="middle">{formatNumber(tick)}</text>
        {/each}
        {#each visiblePoints as point}
          <circle
            cx={x(point.game.avg_playtime_forever)}
            cy={y(yValue(point) ?? 1)}
            r={yValue(point) !== null && isHighlighted(point.game) ? 4 : 2.5}
            fill={color(point.game)}
            opacity={yValue(point) !== null && isHighlighted(point.game) ? 0.75 : 0.12}
            stroke={yValue(point) !== null && isHighlighted(point.game) ? 'white' : 'none'}
            stroke-width="0.7"
            role="img"
            onmouseenter={() => hoveredPoint = point}
            onmouseleave={() => hoveredPoint = null}
          >
            <title>{point.game.name}: {formatPlaytime(point.game.avg_playtime_forever)}, {formatNumber(yValue(point) ?? 0)} {yMetric === 'owners' ? 'estimated owners' : 'reviews'}; {isIndie(point.game) ? 'Indie' : 'Non-indie'}</title>
          </circle>
        {/each}
        {#if hoveredPoint}
          <g class="tooltip" transform={`translate(${tooltipX} ${tooltipY})`}>
            <rect width={tooltipWidth} height="46" rx="4" />
            <text x="9" y="18">{hoveredPoint.game.name}</text>
            <text x="9" y="36">Price: {priceLabel(hoveredPoint.game)}</text>
          </g>
        {/if}
        <line class="axis" x1="0" x2={plotWidth} y1={plotHeight} y2={plotHeight} />
        <line class="axis" x1="0" x2="0" y1="0" y2={plotHeight} />
        <text class="axis-label" x={plotWidth / 2} y={plotHeight + 44} text-anchor="middle">Average playtime (minutes, log scale)</text>
        <text class="axis-label" transform={`translate(${-58} ${plotHeight / 2}) rotate(-90)`} text-anchor="middle">{yMetric === 'owners' ? 'Estimated owners' : 'Review count'} (log scale)</text>
      </g>
    </svg>
  {/if}
</section>

<style>
  .playtime-owners { min-width: 0; }
  .header { display: block; }
  h2 { margin: 0 0 0.25rem; }
  .subtitle { margin: 0; color: #475569; font-size: 0.8rem; }
  .price-filter { display: flex; flex-wrap: wrap; gap: 0.45rem 0.75rem; margin: 0; padding: 0; border: 0; }
  .metric-switch { display: flex; align-items: center; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.5rem; }
  .metric-switch span { color: #475569; font-size: 0.8rem; }
  .metric-switch button { padding: 0.3rem 0.5rem; border: 1px solid #94a3b8; border-radius: 5px; background: white; color: #243247; cursor: pointer; font: inherit; font-size: 0.75rem; }
  .metric-switch button.active { background: #1d4ed8; border-color: #1d4ed8; color: white; }
  .metric-switch button:focus-visible { outline: 3px solid #f59e0b; outline-offset: 2px; }
  .price-filter legend { width: 100%; margin-bottom: 0.15rem; color: #475569; font-size: 0.8rem; font-weight: 600; }
  .price-filter label, .legend span { display: inline-flex; align-items: center; gap: 0.3rem; color: #243247; font-size: 0.78rem; white-space: nowrap; }
  .price-filter input { accent-color: #2563eb; }
  .legend { display: flex; flex-wrap: wrap; align-items: center; gap: 0.75rem; margin: 0.75rem 0 0.25rem; }
  .swatch { width: 0.7rem; height: 0.7rem; border-radius: 50%; }
  .swatch.indie { background: #2563eb; }
  .swatch.non-indie { background: #eab308; }
  .point-count { margin-left: auto; color: #64748b !important; }
  svg { display: block; max-width: 100%; overflow: visible; font-family: inherit; }
  .grid-line { stroke: #e2e8f0; stroke-width: 1; }
  .axis { stroke: #64748b; stroke-width: 1; }
  .tick-label { fill: #64748b; font-size: 10px; }
  .axis-label { fill: #243247; font-size: 11px; }
  .tooltip { pointer-events: none; }
  .tooltip rect { fill: #172033; stroke: white; stroke-width: 1; }
  .tooltip text { fill: white; font-size: 11px; }
  .tooltip text:first-of-type { font-weight: 700; }
  @media (max-width: 700px) {
    .header { flex-direction: column; }
    .point-count { margin-left: 0; }
  }
</style>
