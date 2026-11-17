<script lang="ts">
  import * as d3 from 'd3';
  import type { SteamGame } from '../../types';

  type Props = { games: SteamGame[]; width?: number; height?: number };
  type GameType = 'all' | 'indie' | 'non-indie';
  type SelectedPoint = { game: SteamGame; chart: 'reviews' | 'sentiment' | 'playtime' };

  let { games, width = 1240, height = 420 }: Props = $props();
  let minimumReviews = $state(0);
  let selectedPoint = $state<SelectedPoint | null>(null);
  let gameType = $state<GameType>('all');
  let densityMode = $state(true);
  let focusEnabled = $state(false);
  let focusPercent = $state(95);
  const chartId = $props.id();

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
      return shuffle(group).slice(0, Math.round(group.length * 0.4));
    };
    return [...sample(true), ...sample(false)];
  });
  const positiveReviewPercent = (game: SteamGame) => game.positive_reviews / reviewCount(game) * 100;
  const maxReviews = $derived(d3.max(visiblePoints, ({ game }) => reviewCount(game)) ?? 1);
  // Compute shared percentile caps before the threshold and game-type filters.
  const focusQuantile = (value: (game: SteamGame) => number) =>
    d3.quantile(visiblePoints.map(({ game }) => value(game)), focusPercent / 100) ?? 1;
  const priceLimit = $derived(focusEnabled ? Math.max(0.01, focusQuantile((game) => game.price_no_sales)) : 100);
  const reviewLimit = $derived(focusEnabled ? Math.max(1.01, focusQuantile(reviewCount)) : 100_000);
  const playtimeLimit = $derived(focusEnabled ? Math.max(1, focusQuantile((game) => game.avg_playtime_forever)) : 166.7 * 60);
  const sentimentLimit = $derived(focusEnabled ? Math.max(1, focusQuantile(positiveReviewPercent)) : 100);
  type PlotZoom = { x: [number, number]; y: [number, number] };
  let reviewsZoom = $state<PlotZoom | null>(null);
  let playtimeZoom = $state<PlotZoom | null>(null);
  let sentimentZoom = $state<PlotZoom | null>(null);
  function resetPlotZoom() {
    reviewsZoom = null;
    playtimeZoom = null;
    sentimentZoom = null;
    selectedPoint = null;
  }
  function setFocusPercent(value: number) {
    if (!Number.isFinite(value)) return;
    focusPercent = Math.max(1, Math.min(100, Math.round(value)));
    resetPlotZoom();
  }
  function wheelZoom(node: SVGGElement, chart: SelectedPoint['chart']) {
    const onWheel = (event: WheelEvent) => {
      const [px, py] = d3.pointer(event, node);
      if (px < 0 || px > plotWidth || py < 0 || py > plotHeight || event.deltaY === 0) return;
      const bounds: [number, number] = chart === 'sentiment' ? sentimentBaseX.domain() as [number, number] : [0, priceLimit];
      if (bounds[1] <= bounds[0]) return;
      event.preventDefault();
      const sx = chart === 'reviews' ? reviewsX : chart === 'playtime' ? playtimePriceX : reviewCountX;
      const sy = chart === 'reviews' ? reviewsY : chart === 'playtime' ? playtimeY : sentimentY;
      const delta = event.deltaY * (event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? plotHeight : 1);
      const factor = Math.exp(Math.max(-1, Math.min(1, delta * 0.002)));
      const zoomDomain = (domain: number[], anchor: number, limits: [number, number]): [number, number] => {
        const fullSpan = limits[1] - limits[0];
        const span = domain[1] - domain[0];
        const nextSpan = Math.max(fullSpan / 10000, Math.min(fullSpan, span * factor));
        const low = Math.max(limits[0], Math.min(limits[1] - nextSpan, anchor - (anchor - domain[0]) / span * nextSpan));
        return [low, low + nextSpan];
      };
      const zoom: PlotZoom = {
        x: chart === 'sentiment'
          ? zoomDomain(sx.domain().map(Math.log), Math.log(sx.invert(px)), bounds.map(Math.log) as [number, number]).map(Math.exp) as [number, number]
          : zoomDomain(sx.domain(), sx.invert(px), bounds),
        y: zoomDomain(sy.domain(), sy.invert(py), [0, chart === 'reviews' ? reviewLimit : chart === 'playtime' ? playtimeLimit : sentimentLimit])
      };
      if (chart === 'reviews') reviewsZoom = zoom;
      else if (chart === 'playtime') playtimeZoom = zoom;
      else sentimentZoom = zoom;
      selectedPoint = null;
    };
    node.addEventListener('wheel', onWheel, { passive: false });
    return { destroy() { node.removeEventListener('wheel', onWheel); } };
  }
  // Keep the threshold range independent of zoom and the active threshold.
  const thresholdMax = $derived(Math.max(1, Math.round(d3.quantile(visiblePoints.map(({ game }) => reviewCount(game)), 0.75) ?? 1)));
  const reviewsX = $derived(d3.scaleLinear().domain(reviewsZoom?.x ?? [0, priceLimit]).range([0, plotWidth]));
  const playtimePriceX = $derived(d3.scaleLinear().domain(playtimeZoom?.x ?? [0, priceLimit]).range([0, plotWidth]));
  const reviewsY = $derived(d3.scaleLinear().domain(reviewsZoom?.y ?? [0, reviewLimit]).range([plotHeight, 0]));
  const sentimentBaseX = $derived(focusEnabled
    ? d3.scaleLog().domain([1, reviewLimit])
    : d3.scaleLog().domain([1, Math.max(10, maxReviews)]).nice());
  const reviewCountX = $derived(d3.scaleLog().domain(sentimentZoom?.x ?? sentimentBaseX.domain()).range([0, plotWidth]));
  const sentimentY = $derived(d3.scaleLinear().domain(sentimentZoom?.y ?? [0, sentimentLimit]).range([plotHeight, 0]));
  const reviewCountTicks = $derived(reviewCountX.ticks(5));
  const playtimeY = $derived(d3.scaleLinear().domain(playtimeZoom?.y ?? [0, playtimeLimit]).range([plotHeight, 0]));
  const reviewPriceTicks = $derived(reviewsX.ticks(5));
  const playtimePriceTicks = $derived(playtimePriceX.ticks(5));
  const reviewTicks = $derived(reviewsY.ticks(5));
  const sentimentTicks = $derived(sentimentY.ticks(5));
  const playtimeTicks = $derived(playtimeY.ticks(5));

  const meetsReviewThreshold = (game: SteamGame) => reviewCount(game) >= minimumReviews;
  const rangePoints = $derived(visiblePoints.filter(({ game }) => meetsReviewThreshold(game) && matchesGameType(game)));
  function setMinimumReviews(value: number) {
    if (!Number.isFinite(value)) return;
    minimumReviews = Math.round(Math.max(0, Math.min(value, thresholdMax)));
    reviewsZoom = null;
    playtimeZoom = null;
    sentimentZoom = null;
    selectedPoint = null;
  }
  const formatPlaytime = (minutes: number) => minutes >= 60 ? `${(minutes / 60).toFixed(1)}h` : `${minutes.toFixed(0)}m`;
  const formatReviews = d3.format('.2s');
  const color = (game: SteamGame) => isIndie(game) ? '#ea580c' : '#0284c7';
  const priceLabel = (game: SteamGame) => game.is_free || game.price_no_sales === 0 ? 'Free' : `$${game.price_no_sales.toFixed(2)}`;
  const tooltipWidth = 190;
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
  const inPlot = (game: SteamGame, sx: d3.ScaleLinear<number, number>, sy: d3.ScaleLinear<number, number>, value: number) =>
    sx(game.price_no_sales) >= -1e-8 && sx(game.price_no_sales) <= plotWidth + 1e-8 && sy(value) >= -1e-8 && sy(value) <= plotHeight + 1e-8;
  const reviewPoints = $derived(orderedPoints.filter(({ game }) => reviewCount(game) <= reviewLimit && inPlot(game, reviewsX, reviewsY, reviewCount(game))));
  const playtimePoints = $derived(orderedPoints.filter(({ game }) => game.avg_playtime_forever <= playtimeLimit && inPlot(game, playtimePriceX, playtimeY, game.avg_playtime_forever)));
  const plotTooltipX = (chart: 'reviews' | 'playtime') => selectedPoint
    ? Math.min(Math.max((chart === 'reviews' ? reviewsX : playtimePriceX)(selectedPoint.game.price_no_sales) + 10, 0), Math.max(0, plotWidth - tooltipWidth)) : 0;
  const sentimentPoints = $derived(orderedPoints.filter(({ game }) =>
    reviewCountX(reviewCount(game)) >= -1e-8 && reviewCountX(reviewCount(game)) <= plotWidth + 1e-8 &&
    sentimentY(positiveReviewPercent(game)) >= -1e-8 && sentimentY(positiveReviewPercent(game)) <= plotHeight + 1e-8));
  const sentimentTooltipX = $derived(selectedPoint
    ? Math.min(Math.max(reviewCountX(reviewCount(selectedPoint.game)) + 10, 0), Math.max(0, plotWidth - tooltipWidth)) : 0);
  type DensityPoint = { x: number; y: number; indie: boolean };
  function densityLayers(points: DensityPoint[]) {
    if (!densityMode || points.length === 0) return [];
    const estimator = d3.contourDensity<DensityPoint>()
      .x((point) => point.x).y((point) => point.y)
      .size([Math.ceil(plotWidth), Math.ceil(plotHeight)]).cellSize(4).bandwidth(16).thresholds(6);
    const groups = [true, false].map((indie) => ({ indie, points: points.filter((point) => point.indie === indie) }));
    // Use common density levels for both groups within each panel.
    const peak = d3.max(groups.flatMap((group) => estimator(group.points)), (contour) => contour.value) ?? 0;
    if (peak <= 0) return [];
    const levels = d3.ticks(0, peak, 6).filter((value) => value > 0);
    const path = d3.geoPath();
    return groups.map((group) => ({
      indie: group.indie,
      count: group.points.length,
      contours: estimator.thresholds(levels)(group.points).map((contour) => ({
        path: path(contour) ?? '', value: contour.value
      }))
    }));
  }
  const reviewDensity = $derived(densityLayers(reviewPoints.map(({ game }) => ({ x: reviewsX(game.price_no_sales), y: reviewsY(reviewCount(game)), indie: isIndie(game) }))));
  const playtimeDensity = $derived(densityLayers(playtimePoints.map(({ game }) => ({ x: playtimePriceX(game.price_no_sales), y: playtimeY(game.avg_playtime_forever), indie: isIndie(game) }))));
  const sentimentDensity = $derived(densityLayers(sentimentPoints.map(({ game }) => ({ x: reviewCountX(reviewCount(game)), y: sentimentY(positiveReviewPercent(game)), indie: isIndie(game) }))));
</script>

{#snippet densityPlot(layers: ReturnType<typeof densityLayers>, id: string)}
  <defs><clipPath {id}><rect width={plotWidth} height={plotHeight} /></clipPath></defs>
  <g class="density-layer" clip-path={`url(#${id})`}>
    {#each layers as layer}
      <g fill={layer.indie ? '#ea580c' : '#0284c7'} stroke={layer.indie ? '#c2410c' : '#0369a1'}>
        {#each layer.contours as contour}
          <path d={contour.path} fill-opacity="0.12" stroke-opacity="0.65" stroke-width="1">
            <title>{layer.indie ? 'Indie' : 'Non-indie'} density ? {layer.count.toLocaleString()} games in view</title>
          </path>
        {/each}
      </g>
    {/each}
  </g>
{/snippet}

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

  <p class="selection-help">{#if densityMode}Orange contours show indie density; blue contours show non-indie density. Darker nested regions contain more games per unit of plot area. Switch to points to select individual games.{:else}Click a point to compare that game across all plots. Click it again or clear the selection to deselect.{/if}</p>
  <p class="selection-help">Minimum: 1 review in the first plot.</p>
  <p class="selection-help">All plots show a random 40% sample of eligible indie games and 40% of eligible non-indie games.</p>
  <p class="selection-help">{#if focusEnabled}Focus caps each axis at the selected percentile ({focusPercent}%) of sampled games, trimming the upper tail. Games beyond either axis limit are hidden; indie and non-indie share the same limits.{:else}The top plots use linear scales, excluding games above 100,000 reviews in the first and 166.7 hours of average playtime in the second.{/if} Scroll up over any plot to zoom in at the cursor, or scroll down to zoom out.</p>
  <div class="plot-controls">
    <button onclick={resetPlotZoom}>Reset all plots zoom</button>
    <button aria-pressed={densityMode} onclick={() => { densityMode = !densityMode; selectedPoint = null; }}>{densityMode ? 'Show points' : 'Show density'}</button>
    <button aria-pressed={focusEnabled} onclick={() => { focusEnabled = !focusEnabled; resetPlotZoom(); }}>{focusEnabled ? 'Use fixed scales' : `Focus on central ${focusPercent}%`}</button>
    <label class="focus-percent">Focus %
      <input type="number" min="1" max="100" step="1" value={focusPercent}
        onchange={(event) => setFocusPercent(event.currentTarget.valueAsNumber)} />
    </label>
    <span aria-live="polite">{densityMode ? 'Density view' : 'Points view'}</span>
  </div>
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
      <p role="status">No games match the selected game type and minimum review count.</p>
    {/if}
    <div class="charts">
      <svg width={panelWidth} {height} role="img" aria-label="Scatterplot of price and review count, colored by indie status">
        <g use:wheelZoom={'reviews'} transform={`translate(${margin.left} ${margin.top})`}>
          <text class="chart-title" x={plotWidth / 2} y={-14} text-anchor="middle">Price vs. Review Count</text>
          <rect width={plotWidth} height={plotHeight} fill="transparent" />
          {#each reviewTicks as tick}
            <line class="grid-line" x1="0" x2={plotWidth} y1={reviewsY(tick)} y2={reviewsY(tick)} />
            <text class="tick-label" x={-10} y={reviewsY(tick)} text-anchor="end" dominant-baseline="middle">{formatReviews(tick)}</text>
          {/each}
          {#each reviewPriceTicks as tick}
            <line class="grid-line" y1="0" y2={plotHeight} x1={reviewsX(tick)} x2={reviewsX(tick)} />
            <text class="tick-label" x={reviewsX(tick)} y={plotHeight + 18} text-anchor="middle">${d3.format("~g")(tick)}</text>
          {/each}
          {#if densityMode}
            {@render densityPlot(reviewDensity, `${chartId}-reviews-density`)}
          {:else}
          {#each reviewPoints as point}
            <circle
              cx={reviewsX(point.game.price_no_sales)}
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
          {/if}
          {#if selectedPoint && reviewPoints.some(({ game }) => game.app_id === selectedPoint?.game.app_id)}
            <g class="tooltip" transform={`translate(${plotTooltipX('reviews')} ${tooltipY('reviews')})`}>
              <rect width={tooltipWidth} height="60" rx="4" />
              <text x="9" y="18">{selectedPoint.game.name}</text>
              <text x="9" y="36">Price: {priceLabel(selectedPoint.game)}</text>
              <text x="9" y="54">Reviews: {reviewCount(selectedPoint.game).toLocaleString()}</text>
            </g>
          {/if}
          <line class="axis" x1="0" x2={plotWidth} y1={plotHeight} y2={plotHeight} />
          <line class="axis" x1="0" x2="0" y1="0" y2={plotHeight} />
          <text class="axis-label" x={plotWidth / 2} y={plotHeight + 44} text-anchor="middle">Price (USD)</text>
          <text class="axis-label" transform={`translate(${-58} ${plotHeight / 2}) rotate(-90)`} text-anchor="middle">Review count</text>
        </g>
      </svg>

      <svg width={panelWidth} {height} role="img" aria-label="Scatterplot of price and playtime, colored by indie status">
        <g use:wheelZoom={'playtime'} transform={`translate(${margin.left} ${margin.top})`}>
          <text class="chart-title" x={plotWidth / 2} y={-14} text-anchor="middle">Price vs. Playtime</text>
          <rect width={plotWidth} height={plotHeight} fill="transparent" />
          {#each playtimeTicks as tick}
            <line class="grid-line" x1="0" x2={plotWidth} y1={playtimeY(tick)} y2={playtimeY(tick)} />
            <text class="tick-label" x={-10} y={playtimeY(tick)} text-anchor="end" dominant-baseline="middle">{d3.format('~g')(tick / 60)}</text>
          {/each}
          {#each playtimePriceTicks as tick}
            <line class="grid-line" y1="0" y2={plotHeight} x1={playtimePriceX(tick)} x2={playtimePriceX(tick)} />
            <text class="tick-label" x={playtimePriceX(tick)} y={plotHeight + 18} text-anchor="middle">${d3.format("~g")(tick)}</text>
          {/each}
          {#if densityMode}
            {@render densityPlot(playtimeDensity, `${chartId}-playtime-density`)}
          {:else}
          {#each playtimePoints as point}
            <circle
              cx={playtimePriceX(point.game.price_no_sales)}
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
          {/if}
          {#if selectedPoint && playtimePoints.some(({ game }) => game.app_id === selectedPoint?.game.app_id)}
            <g class="tooltip" transform={`translate(${plotTooltipX('playtime')} ${tooltipY('playtime')})`}>
              <rect width={tooltipWidth} height="60" rx="4" />
              <text x="9" y="18">{selectedPoint.game.name}</text>
              <text x="9" y="36">Price: {priceLabel(selectedPoint.game)}</text>
              <text x="9" y="54">Playtime: {formatPlaytime(selectedPoint.game.avg_playtime_forever)}</text>
            </g>
          {/if}
          <line class="axis" x1="0" x2={plotWidth} y1={plotHeight} y2={plotHeight} />
          <line class="axis" x1="0" x2="0" y1="0" y2={plotHeight} />
          <text class="axis-label" x={plotWidth / 2} y={plotHeight + 44} text-anchor="middle">Price (USD)</text>
          <text class="axis-label" transform={`translate(${-58} ${plotHeight / 2}) rotate(-90)`} text-anchor="middle">Average playtime (hours)</text>
        </g>
      </svg>

      <svg width={panelWidth} {height} role="img" aria-label="Scatterplot of review count and positive review percentage, colored by indie status">
        <g use:wheelZoom={'sentiment'} transform={`translate(${margin.left} ${margin.top})`}>
          <rect width={plotWidth} height={plotHeight} fill="transparent" />
          <text class="chart-title" x={plotWidth / 2} y={-14} text-anchor="middle">Review Count vs. Positive Reviews</text>
          {#each sentimentTicks as tick}
            <line class="grid-line" x1="0" x2={plotWidth} y1={sentimentY(tick)} y2={sentimentY(tick)} />
            <text class="tick-label" x={-10} y={sentimentY(tick)} text-anchor="end" dominant-baseline="middle">{tick}%</text>
          {/each}
          {#each reviewCountTicks as tick}
            <line class="grid-line" y1="0" y2={plotHeight} x1={reviewCountX(tick)} x2={reviewCountX(tick)} />
            <text class="tick-label" x={reviewCountX(tick)} y={plotHeight + 18} text-anchor="middle">{formatReviews(tick)}</text>
          {/each}
          {#if densityMode}
            {@render densityPlot(sentimentDensity, `${chartId}-sentiment-density`)}
          {:else}
          {#each sentimentPoints as point}
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
          {/if}
          {#if selectedPoint && sentimentPoints.some(({ game }) => game.app_id === selectedPoint?.game.app_id)}
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
    <div class="review-threshold">
      <div class="threshold-heading">
        <label for="minimum-reviews">Minimum review count</label>
        <span aria-live="polite">At least {minimumReviews.toLocaleString()} reviews &middot; {rangePoints.length.toLocaleString()} matching games</span>
        <button onclick={() => setMinimumReviews(0)}>Reset threshold</button>
      </div>
      <p>Move the slider to show games with at least this many total reviews across all three plots. The slider ends at the third quartile (75th percentile) of the sampled games' review counts.</p>
      <input id="minimum-reviews" class="threshold-slider" type="range" min="0" max={thresholdMax} step="1"
        value={minimumReviews} aria-valuetext={`At least ${minimumReviews.toLocaleString()} total reviews`}
        oninput={(event) => setMinimumReviews(event.currentTarget.valueAsNumber)} />
      <div class="threshold-endpoints"><span>0</span><span>{thresholdMax.toLocaleString()} reviews (Q3)</span></div>
    </div>
  {/if}
  <section class="analysis" aria-label="Scatterplot analysis">
    <h3>Analysis</h3>
    <!-- Replace this paragraph with your analysis. Add more <p> elements as needed. -->
    <p>Write your analysis here.</p>
  </section>
</section>

<style>
  .focus-percent { display: inline-flex; align-items: center; gap: 6px; font-size: 0.8rem; color: #475569; }
  .focus-percent input { width: 64px; padding: 5px; border: 1px solid #94a3b8; border-radius: 4px; font: inherit; }
  .plot-controls { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin: 12px 0; }
  .plot-controls button { padding: 6px 12px; border: 1px solid #94a3b8; border-radius: 5px; background: white; color: #243247; font: inherit; cursor: pointer; }
  .plot-controls button:focus-visible { outline: 3px solid #0284c7; outline-offset: 2px; }
  .plot-controls span { font-size: 0.8rem; color: #475569; }

  .grid-line, .tick-label { pointer-events: none; }
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
  .review-threshold { margin-top: 24px; padding: 16px; border: 1px solid #cbd5e1; border-radius: 6px; }
  .threshold-heading { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; }
  .threshold-heading label { font-weight: 700; }
  .threshold-heading span, .review-threshold p, .threshold-endpoints { font-size: 0.8rem; color: #475569; }
  .threshold-heading button { margin-left: auto; padding: 5px 10px; border: 1px solid #94a3b8; border-radius: 4px; background: white; cursor: pointer; }
  .threshold-slider { width: 100%; margin: 12px 0; accent-color: #0284c7; cursor: pointer; }
  .threshold-slider:focus-visible { outline: 2px solid #0284c7; outline-offset: 4px; }
  .threshold-endpoints { display: flex; justify-content: space-between; }
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
