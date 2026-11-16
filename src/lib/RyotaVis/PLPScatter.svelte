<script lang="ts">
  import * as d3 from 'd3';
  import type { SteamGame } from '../../types';

  type Props = { games: SteamGame[]; width?: number; height?: number };
  type GameType = 'all' | 'indie' | 'non-indie';
  type SelectedPoint = { game: SteamGame; chart: 'reviews' | 'sentiment' | 'playtime' };

  let { games, width = 1240, height = 420 }: Props = $props();
  let selectedPrices = $state<[number, number] | null>([0, 100]);
  let selectedPoint = $state<SelectedPoint | null>(null);
  let gameType = $state<GameType>('all');

  const gap = 44;
  const margin = { top: 36, right: 24, bottom: 58, left: 76 };
  const panelWidth = $derived(Math.max(280, (width - gap) / 2));
  const plotWidth = $derived(Math.max(1, panelWidth - margin.left - margin.right));
  const plotHeight = $derived(Math.max(1, height - margin.top - margin.bottom));

  const isIndie = (game: SteamGame) => game.genres.some((genre) => genre.toLowerCase() === 'indie');
  const matchesGameType = (game: SteamGame) => gameType === 'all' || isIndie(game) === (gameType === 'indie');
  function changeGameType(value: GameType) {
    gameType = value;
    selectedPoint = null;
  }
  const reviewCount = (game: SteamGame) => game.positive_reviews + game.negative_reviews;
  const eligiblePoints = $derived(
    games
      .filter((game) => Number.isFinite(game.price_no_sales) && game.price_no_sales >= 0 && game.price_no_sales <= 100 &&
        Number.isFinite(reviewCount(game)) && reviewCount(game) >= 1 &&
        Number.isFinite(game.avg_playtime_forever) && game.avg_playtime_forever > 0)
      .map((game) => ({ game }))
  );
  // Sample each group independently and reuse the sample across plots and controls.
  // A fixed random seed keeps the sample consistent across reloads and hydration.
  const visiblePoints = $derived.by(() => {
    const shuffle = d3.shuffler(d3.randomLcg(0.314159));
    const sample = (indie: boolean) => {
      const group = eligiblePoints.filter(({ game }) => isIndie(game) === indie);
      return shuffle(group).slice(0, Math.round(group.length * 0.3));
    };
    return [...sample(true), ...sample(false)];
  });
  const maxReviews = $derived(d3.max(visiblePoints, ({ game }) => reviewCount(game)) ?? 1);
  const maxPlaytime = $derived(d3.max(visiblePoints, ({ game }) => game.avg_playtime_forever) ?? 1);
  // Keep the overview domain independent of the zoomed scatterplot axes.
  const brushMax = 100;
  const x = $derived(d3.scaleLinear().domain(selectedPrices ?? [0, brushMax]).range([0, plotWidth]));
  const reviewsY = $derived(d3.scaleLog().domain([1, Math.max(1, maxReviews)]).nice().range([plotHeight, 0]));
  const positiveReviewPercent = (game: SteamGame) => game.positive_reviews / reviewCount(game) * 100;
  const reviewCountX = $derived(d3.scaleLog().domain([1, Math.max(1, maxReviews)]).nice().range([0, plotWidth]));
  const sentimentY = $derived(d3.scaleLinear().domain([0, 100]).range([plotHeight, 0]));
  const reviewCountTicks = $derived(reviewCountX.ticks(5));
  const playtimeY = $derived(d3.scaleLog().domain([1, Math.max(1, maxPlaytime)]).nice().range([plotHeight, 0]));
  const xTicks = $derived(x.ticks(5));
  const reviewTicks = $derived(reviewsY.ticks(5));
  const sentimentTicks = $derived(sentimentY.ticks(5));
  const playtimeTicks = $derived(playtimeY.ticks(5));

  const isInRange = (game: SteamGame) => selectedPrices === null ||
    (game.price_no_sales >= selectedPrices[0] - 1e-8 && game.price_no_sales <= selectedPrices[1] + 1e-8);
  const brushWidth = $derived(Math.max(240, width - 48));
  const brushScale = $derived(d3.scaleLinear().domain([0, brushMax]).range([0, brushWidth]));
  const rangePoints = $derived(visiblePoints.filter(({ game }) => isInRange(game) && matchesGameType(game)));
  let brushNode: SVGGElement | undefined;
  let brushBehavior: d3.BrushBehavior<unknown> | undefined;

  // The action runs in the browser; resizing or new data rebuilds the brush extent.
  function priceBrush(node: SVGGElement, settings: { width: number; max: number }) {
    brushNode = node;
    const setup = ({ width: barWidth, max }: typeof settings) => {
      const scale = d3.scaleLinear().domain([0, max]).range([0, barWidth]);
      const behavior = d3.brushX<unknown>()
        .extent([[0, 0], [barWidth, 32]])
        .on('brush end', (event: d3.D3BrushEvent<unknown>) => {
          const selection = event.selection as [number, number] | null;
          selectedPrices = selection ? [scale.invert(selection[0]), scale.invert(selection[1])] : null;
          selectedPoint = null;
        });
      brushBehavior = behavior;
      const range = selectedPrices
        ? [Math.min(selectedPrices[0], max), Math.min(selectedPrices[1], max)]
        : [0, max];
      d3.select(node).call(behavior).call(behavior.move, range.map(scale) as [number, number]);
    };
    setup(settings);
    return {
      update: setup,
      destroy() {
        d3.select(node).on('.brush', null);
        brushNode = undefined;
        brushBehavior = undefined;
      }
    };
  }

  function movePriceRange(low: number, high: number) {
    const range: [number, number] = [Math.max(0, Math.min(low, brushMax)), Math.max(0, Math.min(high, brushMax))];
    range.sort((a, b) => a - b);
    selectedPrices = range;
    selectedPoint = null;
    if (brushNode && brushBehavior) {
      d3.select(brushNode).call(brushBehavior.move, range.map(brushScale) as [number, number]);
    }
  }
  const formatPlaytime = (minutes: number) => minutes >= 60 ? `${(minutes / 60).toFixed(1)}h` : `${minutes.toFixed(0)}m`;
  const formatReviews = d3.format('.2s');
  const color = (game: SteamGame) => isIndie(game) ? '#ea580c' : '#0284c7';
  const priceLabel = (game: SteamGame) => game.is_free || game.price_no_sales === 0 ? 'Free' : `$${game.price_no_sales.toFixed(2)}`;
  const tooltipWidth = 190;
  const tooltipX = $derived(selectedPoint ? Math.min(Math.max(x(selectedPoint.game.price_no_sales) + 10, 0), Math.max(0, plotWidth - tooltipWidth)) : 0);
  const tooltipY = (chart: SelectedPoint['chart']) => {
    if (!selectedPoint) return 0;
    const game = selectedPoint.game;
    const position = chart === 'reviews' ? reviewsY(reviewCount(game))
      : chart === 'playtime' ? playtimeY(game.avg_playtime_forever)
      : sentimentY(positiveReviewPercent(game));
    return Math.max(0, Math.min(plotHeight - 60, position - 52));
  };

  const isSelected = (game: SteamGame) => selectedPoint?.game.app_id === game.app_id;
  const selectPoint = (game: SteamGame, chart: SelectedPoint['chart']) => {
    selectedPoint = isSelected(game) && selectedPoint?.chart === chart ? null : { game, chart };
  };
  const pointKeydown = (event: KeyboardEvent, game: SteamGame, chart: SelectedPoint['chart']) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      selectPoint(game, chart);
    } else if (event.key === 'Escape') selectedPoint = null;
  };
  // Draw the selected game last so nearby points cannot cover it.
  const orderedPoints = $derived([...rangePoints].sort((a, b) => Number(isSelected(a.game)) - Number(isSelected(b.game))));
  const sentimentTooltipX = $derived(selectedPoint
    ? Math.min(Math.max(reviewCountX(reviewCount(selectedPoint.game)) + 10, 0), Math.max(0, plotWidth - tooltipWidth)) : 0);
</script>

<section class="price-comparisons">
  <div class="header">
    <div>
      <h2>Price Comparisons</h2>
      <br />
    </div>
  </div>

  <div class="game-type-filter" role="group" aria-label="Filter scatterplots by game type">
    <button class:active={gameType === 'all'} aria-pressed={gameType === 'all'} onclick={() => changeGameType('all')}>All games</button>
    <button class:active={gameType === 'indie'} aria-pressed={gameType === 'indie'} onclick={() => changeGameType('indie')}>Indie only</button>
    <button class:active={gameType === 'non-indie'} aria-pressed={gameType === 'non-indie'} onclick={() => changeGameType('non-indie')}>Non-indie only</button>
  </div>
  <div class="legend" aria-label="Point color legend">
    <span><i class="swatch indie"></i>Indie</span>
    <span><i class="swatch non-indie"></i>Non-indie</span>
    <span class="point-count">{rangePoints.length.toLocaleString()} of {visiblePoints.length.toLocaleString()} games</span>
  </div>

  <p class="selection-help">Click a point to compare that game across all plots. Click it again or clear the selection to deselect.</p>
  <p class="selection-help">Minimum: 1 review in the first plot.</p>
  <p class="selection-help">All plots show a random 30% sample of eligible indie games and 30% of eligible non-indie games.</p>
  {#if selectedPoint}
    <div class="selection-info" role="status">
      <strong>{selectedPoint.game.name}</strong>
      <span>{priceLabel(selectedPoint.game)} &middot; {reviewCount(selectedPoint.game).toLocaleString()} reviews &middot; {formatPlaytime(selectedPoint.game.avg_playtime_forever)} average playtime &middot; {positiveReviewPercent(selectedPoint.game).toFixed(1)}% positive reviews</span>
      <button onclick={() => selectedPoint = null}>Clear selection</button>
    </div>
  {/if}

  {#if visiblePoints.length === 0}
    <p>No games with valid price, review-count, and playtime data are available.</p>
  {:else}
    {#if rangePoints.length === 0}
      <p role="status">No games match the selected game type and price range.</p>
    {/if}
    <div class="charts">
      <svg width={panelWidth} {height} role="img" aria-label="Scatterplot of price and review count, colored by indie status">
        <g transform={`translate(${margin.left} ${margin.top})`}>
          <text class="chart-title" x={plotWidth / 2} y={-14} text-anchor="middle">Price vs. Review Count</text>
          {#each reviewTicks as tick}
            <line class="grid-line" x1="0" x2={plotWidth} y1={reviewsY(tick)} y2={reviewsY(tick)} />
            <text class="tick-label" x={-10} y={reviewsY(tick)} text-anchor="end" dominant-baseline="middle">{formatReviews(tick)}</text>
          {/each}
          {#each xTicks as tick}
            <line class="grid-line" y1="0" y2={plotHeight} x1={x(tick)} x2={x(tick)} />
            <text class="tick-label" x={x(tick)} y={plotHeight + 18} text-anchor="middle">${d3.format("~g")(tick)}</text>
          {/each}
          {#each orderedPoints as point}
            <circle
              cx={x(point.game.price_no_sales)}
              cy={reviewsY(reviewCount(point.game))}
              r={isSelected(point.game) ? 7 : 4}
              fill={color(point.game)}
              opacity={selectedPoint ? isSelected(point.game) ? 1 : 0.12 : 0.75}
              stroke={isSelected(point.game) ? '#172033' : 'white'}
              stroke-width={isSelected(point.game) ? 2 : 0.7}
              role="button"
              tabindex="0"
              aria-label={`Select ${point.game.name}, ${priceLabel(point.game)}`}
              aria-pressed={isSelected(point.game)}
              onclick={() => selectPoint(point.game, 'reviews')}
              onkeydown={(event) => pointKeydown(event, point.game, 'reviews')}
            >
            </circle>
          {/each}
          {#if selectedPoint && isInRange(selectedPoint.game)}
            <g class="tooltip" transform={`translate(${tooltipX} ${tooltipY('reviews')})`}>
              <rect width={tooltipWidth} height="60" rx="4" />
              <text x="9" y="18">{selectedPoint.game.name}</text>
              <text x="9" y="36">Price: {priceLabel(selectedPoint.game)}</text>
              <text x="9" y="54">Reviews: {reviewCount(selectedPoint.game).toLocaleString()}</text>
            </g>
          {/if}
          <line class="axis" x1="0" x2={plotWidth} y1={plotHeight} y2={plotHeight} />
          <line class="axis" x1="0" x2="0" y1="0" y2={plotHeight} />
          <text class="axis-label" x={plotWidth / 2} y={plotHeight + 44} text-anchor="middle">Price (USD)</text>
          <text class="axis-label" transform={`translate(${-58} ${plotHeight / 2}) rotate(-90)`} text-anchor="middle">Review count (log scale)</text>
        </g>
      </svg>

      <svg width={panelWidth} {height} role="img" aria-label="Scatterplot of price and playtime, colored by indie status">
        <g transform={`translate(${margin.left} ${margin.top})`}>
          <text class="chart-title" x={plotWidth / 2} y={-14} text-anchor="middle">Price vs. Playtime</text>
          {#each playtimeTicks as tick}
            <line class="grid-line" x1="0" x2={plotWidth} y1={playtimeY(tick)} y2={playtimeY(tick)} />
            <text class="tick-label" x={-10} y={playtimeY(tick)} text-anchor="end" dominant-baseline="middle">{formatPlaytime(tick)}</text>
          {/each}
          {#each xTicks as tick}
            <line class="grid-line" y1="0" y2={plotHeight} x1={x(tick)} x2={x(tick)} />
            <text class="tick-label" x={x(tick)} y={plotHeight + 18} text-anchor="middle">${d3.format("~g")(tick)}</text>
          {/each}
          {#each orderedPoints as point}
            <circle
              cx={x(point.game.price_no_sales)}
              cy={playtimeY(point.game.avg_playtime_forever)}
              r={isSelected(point.game) ? 7 : 4}
              fill={color(point.game)}
              opacity={selectedPoint ? isSelected(point.game) ? 1 : 0.12 : 0.75}
              stroke={isSelected(point.game) ? '#172033' : 'white'}
              stroke-width={isSelected(point.game) ? 2 : 0.7}
              role="button"
              tabindex="0"
              aria-label={`Select ${point.game.name}, ${priceLabel(point.game)}`}
              aria-pressed={isSelected(point.game)}
              onclick={() => selectPoint(point.game, 'playtime')}
              onkeydown={(event) => pointKeydown(event, point.game, 'playtime')}
            >
            </circle>
          {/each}
          {#if selectedPoint && isInRange(selectedPoint.game)}
            <g class="tooltip" transform={`translate(${tooltipX} ${tooltipY('playtime')})`}>
              <rect width={tooltipWidth} height="60" rx="4" />
              <text x="9" y="18">{selectedPoint.game.name}</text>
              <text x="9" y="36">Price: {priceLabel(selectedPoint.game)}</text>
              <text x="9" y="54">Playtime: {formatPlaytime(selectedPoint.game.avg_playtime_forever)}</text>
            </g>
          {/if}
          <line class="axis" x1="0" x2={plotWidth} y1={plotHeight} y2={plotHeight} />
          <line class="axis" x1="0" x2="0" y1="0" y2={plotHeight} />
          <text class="axis-label" x={plotWidth / 2} y={plotHeight + 44} text-anchor="middle">Price (USD)</text>
          <text class="axis-label" transform={`translate(${-58} ${plotHeight / 2}) rotate(-90)`} text-anchor="middle">Average playtime (minutes, log scale)</text>
        </g>
      </svg>

      <svg width={panelWidth} {height} role="img" aria-label="Scatterplot of review count and positive review percentage, colored by indie status">
        <g transform={`translate(${margin.left} ${margin.top})`}>
          <text class="chart-title" x={plotWidth / 2} y={-14} text-anchor="middle">Review Count vs. Positive Reviews</text>
          {#each sentimentTicks as tick}
            <line class="grid-line" x1="0" x2={plotWidth} y1={sentimentY(tick)} y2={sentimentY(tick)} />
            <text class="tick-label" x={-10} y={sentimentY(tick)} text-anchor="end" dominant-baseline="middle">{tick}%</text>
          {/each}
          {#each reviewCountTicks as tick}
            <line class="grid-line" y1="0" y2={plotHeight} x1={reviewCountX(tick)} x2={reviewCountX(tick)} />
            <text class="tick-label" x={reviewCountX(tick)} y={plotHeight + 18} text-anchor="middle">{formatReviews(tick)}</text>
          {/each}
          {#each orderedPoints as point}
            <circle
              cx={reviewCountX(reviewCount(point.game))}
              cy={sentimentY(positiveReviewPercent(point.game))}
              r={isSelected(point.game) ? 7 : 4}
              fill={color(point.game)}
              opacity={selectedPoint ? isSelected(point.game) ? 1 : 0.12 : 0.75}
              stroke={isSelected(point.game) ? '#172033' : 'white'}
              stroke-width={isSelected(point.game) ? 2 : 0.7}
              role="button"
              tabindex="0"
              aria-label={`Select ${point.game.name}, ${priceLabel(point.game)}`}
              aria-pressed={isSelected(point.game)}
              onclick={() => selectPoint(point.game, 'sentiment')}
              onkeydown={(event) => pointKeydown(event, point.game, 'sentiment')}
            >
            </circle>
          {/each}
          {#if selectedPoint && isInRange(selectedPoint.game)}
            <g class="tooltip" transform={`translate(${sentimentTooltipX} ${tooltipY('sentiment')})`}>
              <rect width={tooltipWidth} height="60" rx="4" />
              <text x="9" y="18">{selectedPoint.game.name}</text>
              <text x="9" y="36">Reviews: {reviewCount(selectedPoint.game).toLocaleString()}</text>
              <text x="9" y="54">Positive: {positiveReviewPercent(selectedPoint.game).toFixed(1)}%</text>
            </g>
          {/if}
          <line class="axis" x1="0" x2={plotWidth} y1={plotHeight} y2={plotHeight} />
          <line class="axis" x1="0" x2="0" y1="0" y2={plotHeight} />
          <text class="axis-label" x={plotWidth / 2} y={plotHeight + 44} text-anchor="middle">Review count (log scale)</text>
          <text class="axis-label" transform={`translate(${-58} ${plotHeight / 2}) rotate(-90)`} text-anchor="middle">Positive reviews (%)</text>
        </g>
      </svg>


    </div>
    <div class="price-brush">
      <div class="brush-heading">
        <strong>Brush price range</strong>
        <span aria-live="polite">${(selectedPrices?.[0] ?? 0).toFixed(2)} &ndash; ${(selectedPrices?.[1] ?? brushMax).toFixed(2)} &middot; {rangePoints.length.toLocaleString()} visible games</span>
        <button onclick={() => movePriceRange(0, brushMax)}>Reset range</button>
      </div>
      <p>Drag across the bar to zoom the price axes and filter games in all three plots. Drag the selection to move it, or its edges to resize.</p>
      <svg class="brush-svg" width="100%" viewBox={`0 0 ${brushWidth + 48} 76`} role="group" aria-label="Select a continuous price range for all scatterplots">
        <g transform="translate(24 8)">
          <rect class="brush-track" width={brushWidth} height="32" rx="3" />
          <g class="brush" use:priceBrush={{ width: brushWidth, max: brushMax }}></g>
          {#each brushScale.ticks(8) as tick}
            <line class="axis" x1={brushScale(tick)} x2={brushScale(tick)} y1="36" y2="41" />
            <text class="tick-label" x={brushScale(tick)} y="56" text-anchor="middle">${d3.format("~g")(tick)}</text>
          {/each}
        </g>
      </svg>
      <div class="range-inputs">
        <label>Minimum price ($)
          <input type="number" min="0" max={brushMax} step="0.01" value={(selectedPrices?.[0] ?? 0).toFixed(2)}
            onchange={(event) => { const value = event.currentTarget.valueAsNumber; if (Number.isFinite(value)) movePriceRange(Math.min(value, selectedPrices?.[1] ?? brushMax), selectedPrices?.[1] ?? brushMax); }} />
        </label>
        <label>Maximum price ($)
          <input type="number" min="0" max={brushMax} step="0.01" value={(selectedPrices?.[1] ?? brushMax).toFixed(2)}
            onchange={(event) => { const value = event.currentTarget.valueAsNumber; if (Number.isFinite(value)) movePriceRange(selectedPrices?.[0] ?? 0, Math.max(value, selectedPrices?.[0] ?? 0)); }} />
        </label>
      </div>
    </div>
  {/if}
  <section class="analysis" aria-label="Scatterplot analysis">
    <h3>Analysis</h3>
    <!-- Replace this paragraph with your analysis. Add more <p> elements as needed. -->
    <p>Write your analysis here.</p>
  </section>
</section>

<style>
  .analysis { width: 100%; margin: 24px 0 0; padding-top: 16px; border-top: 1px solid #e2e8f0; box-sizing: border-box; }
  .analysis h3 { margin: 0 0 8px; text-align: left; font-size: 1rem; }
  .analysis p { margin: 0 0 12px; line-height: 1.7; color: #334155; }
  .game-type-filter { display: flex; flex-wrap: wrap; gap: 6px; }
  .game-type-filter button { padding: 6px 12px; border: 1px solid #94a3b8; border-radius: 5px; background: white; color: #243247; font: inherit; font-size: 0.85rem; cursor: pointer; }
  .game-type-filter button.active { background: #243247; border-color: #243247; color: white; }
  .game-type-filter button:focus-visible { outline: 3px solid #0284c7; outline-offset: 2px; }
  circle[role="button"] { cursor: pointer; }
  circle[role="button"]:focus-visible { outline: 2px solid #172033; }
  .selection-help { font-size: 0.8rem; color: #475569; }
  .selection-info { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; padding: 12px; margin: 12px 0; border: 1px solid #94a3b8; border-radius: 6px; font-size: 0.85rem; }
  .selection-info button { margin-left: auto; cursor: pointer; padding: 5px 10px; }
  .price-comparisons { min-width: 0; }
  .header { display: block; }
  h2 { margin: 0 0 0.25rem; }
  .legend span { display: inline-flex; align-items: center; gap: 0.3rem; color: #243247; font-size: 0.78rem; white-space: nowrap; }
  .price-brush { margin-top: 24px; padding: 16px; border: 1px solid #cbd5e1; border-radius: 6px; }
  .brush-heading, .range-inputs { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; }
  .brush-heading span, .price-brush p { font-size: 0.8rem; color: #475569; }
  .brush-heading button { margin-left: auto; padding: 5px 10px; border: 1px solid #94a3b8; border-radius: 4px; background: white; cursor: pointer; }
  .brush-track { fill: #e2e8f0; }
  .brush-svg { touch-action: none; }
  .brush :global(.selection) { fill: #0284c7; fill-opacity: 0.25; stroke: #0369a1; }
  .brush :global(.handle) { fill: #0369a1; }
  .range-inputs label { display: flex; align-items: center; gap: 8px; font-size: 0.8rem; }
  .range-inputs input { width: 100px; padding: 5px; border: 1px solid #94a3b8; border-radius: 4px; }
  .legend { display: flex; flex-wrap: wrap; align-items: center; gap: 0.75rem; margin: 0.75rem 0 0.25rem; }
  .swatch { width: 0.7rem; height: 0.7rem; border-radius: 50%; }
  .swatch.indie { background: #ea580c; }
  .swatch.non-indie { background: #0284c7; }
  .point-count { margin-left: auto; color: #64748b !important; }
  .charts { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 44px; align-items: start; }
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
