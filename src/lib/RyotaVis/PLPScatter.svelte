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
  type PlotMode = 'points' | 'hexbin';
  const plotModes: { value: PlotMode; label: string }[] = [
    { value: 'points', label: 'Points' },
    { value: 'hexbin', label: 'Hexbin' }
  ];
  let plotMode = $state<PlotMode>('hexbin');
  const hexbinMode = $derived(plotMode === 'hexbin');
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
  const sampledPoints = $derived.by(() => {
    const eligibleGames = games.filter((game) =>
      Number.isFinite(game.price_no_sales) && game.price_no_sales >= 0 && game.price_no_sales <= 100 &&
      Number.isFinite(reviewCount(game)) && reviewCount(game) >= 1 &&
      Number.isFinite(game.avg_playtime_forever) && game.avg_playtime_forever > 0);
    const shuffle = d3.shuffler(d3.randomLcg(0.314159));
    const sample = (indie: boolean) => {
      const group = eligibleGames.filter((game) => isIndie(game) === indie);
      return shuffle(group).slice(0, Math.round(group.length * 0.4));
    };
    return [...sample(true), ...sample(false)].map((game) => ({ game }));
  });
  const positiveReviewPercent = (game: SteamGame) => game.positive_reviews / reviewCount(game) * 100;
  const maxReviews = $derived(d3.max(sampledPoints, ({ game }) => reviewCount(game)) ?? 1);
  const priceLimit = 100;
  const reviewLimit = 100_000;
  const playtimeLimit = 166.7 * 60;
  const sentimentLimit = 100;
  type PlotZoom = { x: [number, number]; y: [number, number] };
  const reviewHexbinDomain: PlotZoom = { x: [2.3, 47.2], y: [5_200, 50_000] };
  const playtimeHexbinDomain: PlotZoom = { x: [12.45, 32.55], y: [325, 2_345] };
  let reviewsZoom = $state<PlotZoom | null>(null);
  let playtimeZoom = $state<PlotZoom | null>(null);
  let sentimentZoom = $state<PlotZoom | null>(null);
  function resetPlotZoom() {
    reviewsZoom = null;
    playtimeZoom = null;
    sentimentZoom = null;
    selectedPoint = null;
  }
  function showFullRange() {
    reviewsZoom = { x: [0, priceLimit], y: [0, reviewLimit] };
    playtimeZoom = { x: [0, priceLimit], y: [0, playtimeLimit] };
    sentimentZoom = null;
    selectedPoint = null;
  }
  function changePlotMode(mode: PlotMode) {
    if (mode === plotMode) return;
    reviewsZoom = null;
    playtimeZoom = null;
    plotMode = mode;
    selectedPoint = null;
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
  const thresholdMax = $derived(Math.max(1, Math.round(d3.quantile(sampledPoints.map(({ game }) => reviewCount(game)), 0.75) ?? 1)));
  const reviewsX = $derived(d3.scaleLinear().domain(reviewsZoom?.x ?? (hexbinMode ? reviewHexbinDomain.x : [0, priceLimit])).range([0, plotWidth]));
  const playtimePriceX = $derived(d3.scaleLinear().domain(playtimeZoom?.x ?? (hexbinMode ? playtimeHexbinDomain.x : [0, priceLimit])).range([0, plotWidth]));
  const reviewsY = $derived(d3.scaleLinear().domain(reviewsZoom?.y ?? (hexbinMode ? reviewHexbinDomain.y : [0, reviewLimit])).range([plotHeight, 0]));
  const sentimentBaseX = $derived(d3.scaleLog().domain([1, Math.max(10, maxReviews)]).nice());
  const reviewCountX = $derived(d3.scaleLog().domain(sentimentZoom?.x ?? sentimentBaseX.domain()).range([0, plotWidth]));
  const sentimentY = $derived(d3.scaleLinear().domain(sentimentZoom?.y ?? [0, sentimentLimit]).range([plotHeight, 0]));
  const reviewCountTicks = $derived(reviewCountX.ticks(5));
  const playtimeY = $derived(d3.scaleLinear().domain(playtimeZoom?.y ?? (hexbinMode ? playtimeHexbinDomain.y : [0, playtimeLimit])).range([plotHeight, 0]));
  const reviewPriceTicks = $derived(reviewsX.ticks(5));
  const playtimePriceTicks = $derived(playtimePriceX.ticks(5));
  const reviewTicks = $derived(reviewsY.ticks(5));
  const sentimentTicks = $derived(sentimentY.ticks(5));
  const playtimeTicks = $derived(playtimeY.ticks(5));

  const meetsReviewThreshold = (game: SteamGame) => reviewCount(game) >= minimumReviews;
  const rangePoints = $derived(sampledPoints.filter(({ game }) => meetsReviewThreshold(game) && matchesGameType(game)));
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
  type ProjectedPoint = { x: number; y: number; yValue: number; indie: boolean };
  const sentimentPositions = $derived(sentimentPoints.map(({ game }) => ({
    x: reviewCountX(reviewCount(game)), y: sentimentY(positiveReviewPercent(game)), yValue: positiveReviewPercent(game), indie: isIndie(game)
  })));

  const hexRadius = 10;
  const hexStepX = Math.sqrt(3) * hexRadius;
  const hexStepY = 1.5 * hexRadius;
  const hexagon = Array.from({ length: 6 }, (_, index) => {
    const angle = (index * 60 - 90) * Math.PI / 180;
    return `${hexRadius * Math.cos(angle)},${hexRadius * Math.sin(angle)}`;
  }).join(' ');

  type Hexbin = { x: number; y: number; indie: number; nonIndie: number; indieSum: number; nonIndieSum: number };
  function hexbin(points: ProjectedPoint[]) {
    const bins = new Map<string, Hexbin>();
    for (const { x, y, yValue, indie } of points) {
      // Round fractional axial coordinates to the nearest hex center.
      const q = x / hexStepX - y / (2 * hexStepY);
      const r = y / hexStepY;
      const third = -q - r;
      let column = Math.round(q);
      let row = Math.round(r);
      const other = Math.round(third);
      const columnError = Math.abs(column - q);
      const rowError = Math.abs(row - r);
      const otherError = Math.abs(other - third);
      if (columnError > rowError && columnError > otherError) column = -row - other;
      else if (rowError > otherError) row = -column - other;

      const key = `${column},${row}`;
      let bin = bins.get(key);
      if (!bin) {
        bin = { x: hexStepX * (column + row / 2), y: hexStepY * row, indie: 0, nonIndie: 0, indieSum: 0, nonIndieSum: 0 };
        bins.set(key, bin);
      }
      if (indie) {
        bin.indie += 1;
        bin.indieSum += yValue;
      } else {
        bin.nonIndie += 1;
        bin.nonIndieSum += yValue;
      }
    }
    return [...bins.values()];
  }
  const reviewHexbins = $derived(hexbinMode ? hexbin(reviewPoints.map(({ game }) => ({
    x: reviewsX(game.price_no_sales), y: reviewsY(reviewCount(game)), yValue: reviewCount(game), indie: isIndie(game)
  }))) : []);
  const playtimeHexbins = $derived(hexbinMode ? hexbin(playtimePoints.map(({ game }) => ({
    x: playtimePriceX(game.price_no_sales), y: playtimeY(game.avg_playtime_forever), yValue: game.avg_playtime_forever, indie: isIndie(game)
  }))) : []);
  const sentimentHexbins = $derived(hexbinMode ? hexbin(sentimentPositions) : []);
  let mergedRows = $state({ reviews: false, playtime: false, sentiment: false });
  type Chart = keyof typeof mergedRows;
  let hoveredBin = $state.raw<{ chart: Chart; indie: boolean; bin: Hexbin } | null>(null);
  const formatBinAverage: Record<Chart, (value: number) => string> = {
    reviews: (value) => `${value.toLocaleString(undefined, { maximumFractionDigits: 1 })} reviews`,
    playtime: (value) => `${(value / 60).toFixed(1)} hours`,
    sentiment: (value) => `${value.toFixed(1)}%`
  };
  function binSummary(chart: Chart, bin: Hexbin, indie: boolean) {
    const count = indie ? bin.indie : bin.nonIndie;
    const average = (indie ? bin.indieSum : bin.nonIndieSum) / count;
    return `${indie ? 'Indie' : 'Non-indie'}: ${count.toLocaleString()} ${count === 1 ? 'game' : 'games'}, avg. ${formatBinAverage[chart](average)}`;
  }
  const hexHalfWidth = hexStepX / 2;
  const leftHexHalf = `0,${-hexRadius} 0,${hexRadius} ${-hexHalfWidth},${hexRadius / 2} ${-hexHalfWidth},${-hexRadius / 2}`;
  const rightHexHalf = `0,${-hexRadius} ${hexHalfWidth},${-hexRadius / 2} ${hexHalfWidth},${hexRadius / 2} 0,${hexRadius}`;
  const maxBinCount = (bins: Hexbin[]) => d3.max(bins, (bin) => Math.max(bin.indie, bin.nonIndie)) ?? 0;
  const reviewBinMax = $derived(maxBinCount(reviewHexbins));
  const playtimeBinMax = $derived(maxBinCount(playtimeHexbins));
  const sentimentBinMax = $derived(maxBinCount(sentimentHexbins));
  const binOpacity = (count: number, maxCount: number) => 0.25 + 0.75 * Math.sqrt(count / maxCount);
  function densitySpectrum(color: string, maxCount: number) {
    const stops = Array.from({ length: 9 }, (_, index) => {
      const count = 1 + (maxCount - 1) * index / 8;
      return d3.rgb(color).copy({ opacity: binOpacity(count, maxCount) }).formatRgb();
    });
    return `linear-gradient(to right, ${stops.join(', ')})`;
  }
  const gameGroups = [
    { indie: true, label: 'Indie', id: 'indie', color: '#ea580c' },
    { indie: false, label: 'Non-indie', id: 'non-indie', color: '#0284c7' }
  ];
</script>

{#snippet hexbinPlot(bins: Hexbin[], id: string, group: (typeof gameGroups)[number], chart: Chart, maxCount: number)}
  {@const merged = mergedRows[chart]}
  <defs><clipPath {id}><rect width={plotWidth} height={plotHeight} /></clipPath></defs>
  <g clip-path={`url(#${id})`}>
    {#each bins.filter((bin) => group.indie ? bin.indie > 0 : bin.nonIndie > 0) as bin}
      {@const count = group.indie ? bin.indie : bin.nonIndie}
      <polygon
        points={merged && bin.indie && bin.nonIndie ? (group.indie ? leftHexHalf : rightHexHalf) : hexagon}
        transform={`translate(${bin.x} ${bin.y})`}
        fill={group.color}
        fill-opacity={binOpacity(count, maxCount)}
        stroke="#fff"
        stroke-width="0.75"
        role="img"
        aria-label={binSummary(chart, bin, group.indie)}
        onpointerenter={() => hoveredBin = { chart, indie: group.indie, bin }}
        onpointerleave={() => {
          if (hoveredBin?.bin === bin && hoveredBin.indie === group.indie) hoveredBin = null;
        }}
      />
    {/each}
  </g>
  {#if hoveredBin?.chart === chart && bins.includes(hoveredBin.bin) && (merged ? !group.indie : group.indie === hoveredBin.indie)}
    {@const bin = hoveredBin.bin}
    {@const shared = merged && bin.indie > 0 && bin.nonIndie > 0}
    {@const width = 230}
    {@const height = shared ? 60 : 42}
    {@const x = Math.max(0, Math.min(bin.x + hexRadius + 4, plotWidth - width))}
    {@const y = Math.max(0, Math.min(bin.y - height - 4, plotHeight - height))}
    <g class="tooltip" transform={`translate(${x} ${y})`}>
      <rect {width} {height} rx="4" />
      <text x="9" y="17">Games in cell</text>
      <text x="9" y="34">{binSummary(chart, bin, shared || hoveredBin.indie)}</text>
      {#if shared}<text x="9" y="51">{binSummary(chart, bin, false)}</text>{/if}
    </g>
  {/if}
{/snippet}

{#snippet mergeControls(chart: keyof typeof mergedRows, maxCount: number)}
  <div class="row-controls">
    {#if hexbinMode && maxCount > 0}
      <div class="density-legend" role="group" aria-label="Density legend, games per hexagon">
        <span>Games per hexagon</span>
        <div class="legend-spectrum">
          {#each gameGroups as group (group.id)}
            <span class="legend-ramp" style:background={densitySpectrum(group.color, maxCount)} aria-hidden="true"></span>
          {/each}
          <div class="legend-range">
            <span>1</span>
            {#if maxCount > 1}<span>{maxCount.toLocaleString()}</span>{/if}
          </div>
        </div>
      </div>
      {#if mergedRows[chart]}
        <div class="shared-hex-key">
          <svg viewBox="-11 -11 22 22" aria-hidden="true">
            <polygon points={leftHexHalf} fill={gameGroups[0].color} />
            <polygon points={rightHexHalf} fill={gameGroups[1].color} />
          </svg>
          <span><strong>Shared hexagon</strong><br />Indie left, non-indie right</span>
        </div>
      {/if}
    {/if}
    <button type="button" onclick={() => {
      hoveredBin = null;
      mergedRows[chart] = !mergedRows[chart];
    }}>
      {mergedRows[chart] ? 'Split' : 'Merge'}
    </button>
  </div>
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
    <span class="point-count">{rangePoints.length.toLocaleString()} of {sampledPoints.length.toLocaleString()} games</span>
  </div>

  <p class="selection-help">{#if hexbinMode}Each hexagon groups nearby games. Darker hexagons contain more games. Each row uses a shared count scale. Hover over a hexagon for counts and averages.{:else}Click a point to compare that game across all plots. Click it again or clear the selection to deselect.{/if}</p>
  <p class="selection-help">All three plots use the same sample of 40% of eligible indie games and 40% of eligible non-indie games.{#if hexbinMode} Choose Show full range to use the same axis limits as Points view.{/if}</p>
  <p class="selection-help">Scroll over either panel to zoom both panels in that row.</p>
  <div class="plot-controls">
    {#if hexbinMode}<button onclick={showFullRange}>Show full range</button>{/if}
    <button onclick={resetPlotZoom}>Reset all plots zoom</button>
    {#each plotModes as mode (mode.value)}
      <button aria-pressed={plotMode === mode.value} onclick={() => changePlotMode(mode.value)}>{mode.label}</button>
    {/each}
  </div>
  {#if selectedPoint}
    <div class="selection-info" role="status">
      <strong>{selectedPoint.game.name}</strong>
      <span>{priceLabel(selectedPoint.game)} &middot; {reviewCount(selectedPoint.game).toLocaleString()} reviews &middot; {formatPlaytime(selectedPoint.game.avg_playtime_forever)} average playtime &middot; {positiveReviewPercent(selectedPoint.game).toFixed(1)}% positive reviews</span>
      <button onclick={() => selectedPoint = null}>Clear selection</button>
    </div>
  {/if}

  {#if sampledPoints.length === 0}
    <p>No games have valid data for any plot.</p>
  {:else}
    {#if rangePoints.length === 0}
      <p role="status">No games match the selected game type and minimum review count.</p>
    {/if}
    <div class="charts">
      <section class="chart-row" aria-labelledby={`${chartId}-reviews-heading`}>
        <h3 id={`${chartId}-reviews-heading`}>Price vs. Review Count</h3>
        <div class="chart-pair" class:merged={mergedRows.reviews}>
          {#each gameGroups as group (group.id)}
            {@const panelPoints = reviewPoints.filter(({ game }) => isIndie(game) === group.indie)}
            <svg class:non-indie={!group.indie} viewBox={`0 0 ${panelWidth} ${height}`} role="img" aria-label={`Price vs. Review Count, ${group.label}`}>
              <g use:wheelZoom={'reviews'} transform={`translate(${margin.left} ${margin.top})`}>
                <text class="chart-title panel-heading" x={plotWidth / 2} y={-14} text-anchor="middle" fill={group.color}>{group.label}</text>
                <rect class="zoom-target" width={plotWidth} height={plotHeight} fill="transparent" />
                <g class="panel-axes">
                  {#each reviewTicks as tick}
                    <line class="grid-line" x1="0" x2={plotWidth} y1={reviewsY(tick)} y2={reviewsY(tick)} />
                    <text class="tick-label" x={-10} y={reviewsY(tick)} text-anchor="end" dominant-baseline="middle">{formatReviews(tick)}</text>
                  {/each}
                  {#each reviewPriceTicks as tick}
                    <line class="grid-line" y1="0" y2={plotHeight} x1={reviewsX(tick)} x2={reviewsX(tick)} />
                    <text class="tick-label" x={reviewsX(tick)} y={plotHeight + 18} text-anchor="middle">${d3.format("~g")(tick)}</text>
                  {/each}
                </g>
                {#if hexbinMode}
                  {@render hexbinPlot(reviewHexbins, `${chartId}-reviews-${group.id}-hexbin`, group, 'reviews', reviewBinMax)}
                {:else}
                  {#each panelPoints as point}
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
                {#if selectedPoint && panelPoints.some(({ game }) => game.app_id === selectedPoint?.game.app_id)}
                  <g class="tooltip" transform={`translate(${plotTooltipX('reviews')} ${tooltipY('reviews')})`}>
                    <rect width={tooltipWidth} height="60" rx="4" />
                    <text x="9" y="18">{selectedPoint.game.name}</text>
                    <text x="9" y="36">Price: {priceLabel(selectedPoint.game)}</text>
                    <text x="9" y="54">Reviews: {reviewCount(selectedPoint.game).toLocaleString()}</text>
                  </g>
                {/if}
                <g class="panel-axes">
                  <line class="axis" x1="0" x2={plotWidth} y1={plotHeight} y2={plotHeight} />
                  <line class="axis" x1="0" x2="0" y1="0" y2={plotHeight} />
                  <text class="axis-label" x={plotWidth / 2} y={plotHeight + 44} text-anchor="middle">Price (USD)</text>
                  <text class="axis-label" transform={`translate(${-58} ${plotHeight / 2}) rotate(-90)`} text-anchor="middle">Review count</text>
                </g>
              </g>
            </svg>
          {/each}
        </div>
        {@render mergeControls('reviews', reviewBinMax)}
      </section>

      <section class="chart-row" aria-labelledby={`${chartId}-playtime-heading`}>
        <h3 id={`${chartId}-playtime-heading`}>Price vs. Playtime</h3>
        <div class="chart-pair" class:merged={mergedRows.playtime}>
          {#each gameGroups as group (group.id)}
            {@const panelPoints = playtimePoints.filter(({ game }) => isIndie(game) === group.indie)}
            <svg class:non-indie={!group.indie} viewBox={`0 0 ${panelWidth} ${height}`} role="img" aria-label={`Price vs. Playtime, ${group.label}`}>
              <g use:wheelZoom={'playtime'} transform={`translate(${margin.left} ${margin.top})`}>
                <text class="chart-title panel-heading" x={plotWidth / 2} y={-14} text-anchor="middle" fill={group.color}>{group.label}</text>
                <rect class="zoom-target" width={plotWidth} height={plotHeight} fill="transparent" />
                <g class="panel-axes">
                  {#each playtimeTicks as tick}
                    <line class="grid-line" x1="0" x2={plotWidth} y1={playtimeY(tick)} y2={playtimeY(tick)} />
                    <text class="tick-label" x={-10} y={playtimeY(tick)} text-anchor="end" dominant-baseline="middle">{d3.format('~g')(tick / 60)}</text>
                  {/each}
                  {#each playtimePriceTicks as tick}
                    <line class="grid-line" y1="0" y2={plotHeight} x1={playtimePriceX(tick)} x2={playtimePriceX(tick)} />
                    <text class="tick-label" x={playtimePriceX(tick)} y={plotHeight + 18} text-anchor="middle">${d3.format("~g")(tick)}</text>
                  {/each}
                </g>
                {#if hexbinMode}
                  {@render hexbinPlot(playtimeHexbins, `${chartId}-playtime-${group.id}-hexbin`, group, 'playtime', playtimeBinMax)}
                {:else}
                  {#each panelPoints as point}
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
                {#if selectedPoint && panelPoints.some(({ game }) => game.app_id === selectedPoint?.game.app_id)}
                  <g class="tooltip" transform={`translate(${plotTooltipX('playtime')} ${tooltipY('playtime')})`}>
                    <rect width={tooltipWidth} height="60" rx="4" />
                    <text x="9" y="18">{selectedPoint.game.name}</text>
                    <text x="9" y="36">Price: {priceLabel(selectedPoint.game)}</text>
                    <text x="9" y="54">Playtime: {formatPlaytime(selectedPoint.game.avg_playtime_forever)}</text>
                  </g>
                {/if}
                <g class="panel-axes">
                  <line class="axis" x1="0" x2={plotWidth} y1={plotHeight} y2={plotHeight} />
                  <line class="axis" x1="0" x2="0" y1="0" y2={plotHeight} />
                  <text class="axis-label" x={plotWidth / 2} y={plotHeight + 44} text-anchor="middle">Price (USD)</text>
                  <text class="axis-label" transform={`translate(${-58} ${plotHeight / 2}) rotate(-90)`} text-anchor="middle">Average playtime (hours)</text>
                </g>
              </g>
            </svg>
          {/each}
        </div>
        {@render mergeControls('playtime', playtimeBinMax)}
      </section>

      <section class="chart-row" aria-labelledby={`${chartId}-sentiment-heading`}>
        <h3 id={`${chartId}-sentiment-heading`}>Review Count vs. Positive Reviews</h3>
        <div class="chart-pair" class:merged={mergedRows.sentiment}>
          {#each gameGroups as group (group.id)}
            {@const panelPoints = sentimentPoints.filter(({ game }) => isIndie(game) === group.indie)}
            <svg class:non-indie={!group.indie} viewBox={`0 0 ${panelWidth} ${height}`} role="img" aria-label={`Review Count vs. Positive Reviews, ${group.label}`}>
              <g use:wheelZoom={'sentiment'} transform={`translate(${margin.left} ${margin.top})`}>
                <rect class="zoom-target" width={plotWidth} height={plotHeight} fill="transparent" />
                <text class="chart-title panel-heading" x={plotWidth / 2} y={-14} text-anchor="middle" fill={group.color}>{group.label}</text>
                <g class="panel-axes">
                  {#each sentimentTicks as tick}
                    <line class="grid-line" x1="0" x2={plotWidth} y1={sentimentY(tick)} y2={sentimentY(tick)} />
                    <text class="tick-label" x={-10} y={sentimentY(tick)} text-anchor="end" dominant-baseline="middle">{tick}%</text>
                  {/each}
                  {#each reviewCountTicks as tick}
                    <line class="grid-line" y1="0" y2={plotHeight} x1={reviewCountX(tick)} x2={reviewCountX(tick)} />
                    <text class="tick-label" x={reviewCountX(tick)} y={plotHeight + 18} text-anchor="middle">{formatReviews(tick)}</text>
                  {/each}
                </g>
                {#if hexbinMode}
                  {@render hexbinPlot(sentimentHexbins, `${chartId}-sentiment-${group.id}-hexbin`, group, 'sentiment', sentimentBinMax)}
                {:else}
                  {#each panelPoints as point}
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
                {#if selectedPoint && panelPoints.some(({ game }) => game.app_id === selectedPoint?.game.app_id)}
                  <g class="tooltip" transform={`translate(${sentimentTooltipX} ${tooltipY('sentiment')})`}>
                    <rect width={tooltipWidth} height="60" rx="4" />
                    <text x="9" y="18">{selectedPoint.game.name}</text>
                    <text x="9" y="36">Reviews: {reviewCount(selectedPoint.game).toLocaleString()}</text>
                    <text x="9" y="54">Positive: {positiveReviewPercent(selectedPoint.game).toFixed(1)}%</text>
                  </g>
                {/if}
                <g class="panel-axes">
                  <line class="axis" x1="0" x2={plotWidth} y1={plotHeight} y2={plotHeight} />
                  <line class="axis" x1="0" x2="0" y1="0" y2={plotHeight} />
                  <text class="axis-label" x={plotWidth / 2} y={plotHeight + 44} text-anchor="middle">Review count (log scale)</text>
                  <text class="axis-label" transform={`translate(${-58} ${plotHeight / 2}) rotate(-90)`} text-anchor="middle">Positive reviews (%)</text>
                </g>
              </g>
            </svg>
          {/each}
        </div>
        {@render mergeControls('sentiment', sentimentBinMax)}
      </section>
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
  .plot-controls { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin: 12px 0; }
  .plot-controls button { padding: 6px 12px; border: 1px solid #94a3b8; border-radius: 5px; background: white; color: #243247; font: inherit; cursor: pointer; }
  .plot-controls button:focus-visible { outline: 3px solid #0284c7; outline-offset: 2px; }

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
  .charts { display: grid; gap: 24px; }
  .chart-row { min-width: 0; }
  .chart-row h3 { margin: 12px 0 0; color: #243247; font-size: 1rem; text-align: center; }
  .chart-pair { display: grid; grid-template-columns: repeat(2, minmax(280px, 1fr)); column-gap: 12px; overflow-x: auto; }
  svg { display: block; width: 100%; height: auto; font-family: inherit; }
  .chart-pair > svg { transform-box: border-box; transition: transform 504ms ease; }
  .chart-pair.merged > svg { transform: translateX(calc(50% + 6px)); }
  .chart-pair.merged > svg.non-indie { transform: translateX(calc(-50% - 6px)); }
  .panel-axes, .panel-heading { pointer-events: none; }
  .panel-axes, .panel-heading { transition: opacity 308ms ease; }
  .merged .panel-heading, .merged .non-indie .panel-axes { opacity: 0; }
  .chart-pair.merged > svg.non-indie { pointer-events: none; }
  .merged .non-indie polygon, .merged .non-indie circle { pointer-events: auto; }
  .merged .non-indie .zoom-target { pointer-events: none; }
  .row-controls { display: flex; justify-content: center; align-items: center; flex-wrap: wrap; gap: 12px; }
  .row-controls button { padding: 6px 12px; border: 1px solid #94a3b8; border-radius: 5px; background: white; color: #243247; font: inherit; cursor: pointer; }
  .density-legend { display: flex; align-items: center; gap: 12px; color: #475569; font-size: 0.8rem; }
  .shared-hex-key { display: flex; align-items: center; gap: 6px; color: #475569; font-size: 0.75rem; }
  .shared-hex-key svg { width: 22px; height: 22px; flex: none; }
  .legend-spectrum { display: grid; gap: 2px; width: 132px; }
  .legend-ramp { height: 7px; border-radius: 2px; }
  .legend-range { display: flex; justify-content: space-between; }
  @media (prefers-reduced-motion: reduce) {
    .chart-pair > svg, .panel-axes, .panel-heading { transition: none; }
  }
  .chart-title { font-size: 12px; font-weight: 700; }
  .grid-line { stroke: #e2e8f0; stroke-width: 1; }
  .axis { stroke: #64748b; stroke-width: 1; }
  .tick-label { fill: #64748b; font-size: 10px; }
  .axis-label { fill: #243247; font-size: 11px; }
  .tooltip { pointer-events: none; }
  .tooltip rect { fill: #172033; stroke: white; stroke-width: 1; }
  .tooltip text { fill: white; font-size: 11px; }
  .tooltip text:first-of-type { font-weight: 700; }
  @media (max-width: 900px) {
    .point-count { margin-left: 0; }
  }
</style>
