<script lang="ts">
  import { interpolateBlues, interpolateRdBu } from 'd3';
  import type { SteamGame } from '../../types';

  type Props = { games: SteamGame[]; width?: number; height?: number };
  let { games, width = 620, height = 420 }: Props = $props();
  let metric = $state<'reviews' | 'sales'>('reviews');
  let merged = $state(false);
  let chartScroll = $state<HTMLDivElement>();
  function toggleMerge() {
    merged = !merged;
    if (merged && chartScroll) {
      chartScroll.scrollTo({
        left: (chartScroll.scrollWidth - chartScroll.clientWidth) / 2,
        behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth'
      });
    }
  }
  const id = $props.id();
  const priceRanges = ['Free', 'Below $20', '$20 and above'];
  const priceBucket = (game: SteamGame) => game.is_free || game.price_no_sales === 0 ? 0 : game.price_no_sales < 20 ? 1 : 2;
  const isIndie = (game: SteamGame) => game.genres.some((genre) => genre.toLowerCase() === 'indie');
  const owners = (game: SteamGame): number | null => {
    const bounds = game.estimated_owners.replaceAll(',', '').split('..').map((part) => Number(part.trim()));
    return bounds.length === 2 && bounds.every((value) => Number.isFinite(value) && value >= 0)
      ? (bounds[0] + bounds[1]) / 2 : null;
  };
  const genres = [
    'Action',
    'Adventure',
    'Casual',
    'Education',
    'Racing',
    'RPG',
    'Simulation',
    'Massively Multiplayer',
    'Sports',
    'Strategy'
  ];
  const panels = $derived.by(() => [true, false].map((indie) => {
    const selectedGames = games.filter((game) => isIndie(game) === indie);
    return { label: indie ? 'Indie games' : 'Non-indie games', rows: genres.map((genre) => {
    const genreGames = selectedGames.filter((game) => game.genres.includes(genre));
    const totalOwners = genreGames.reduce((sum, game) => sum + (owners(game) ?? 0), 0);
    return { genre, cells: priceRanges.map((label, index) => {
      const matching = genreGames.filter((game) => priceBucket(game) === index);
      const positive = matching.reduce((sum, game) => sum + game.positive_reviews, 0);
      const reviews = matching.reduce((sum, game) => sum + game.positive_reviews + game.negative_reviews, 0);
      const estimatedOwners = matching.reduce((sum, game) => sum + (owners(game) ?? 0), 0);
      const hasOwners = matching.some((game) => owners(game) !== null);
      const value = metric === 'reviews'
        ? reviews > 0 ? positive / reviews : null
        : totalOwners > 0 && (matching.length === 0 || hasOwners) ? estimatedOwners / totalOwners : null;
      return { label, count: matching.length, value, reviews, estimatedOwners };
    }) };
    }) };
  }));
  const colorDomain = $derived.by(() => {
    const values = panels.flatMap((panel) => panel.rows.flatMap((row) =>
      row.cells.flatMap((cell) => cell.value === null ? [] : [cell.value])
    ));
    return metric === 'reviews' && values.length > 0
      ? [Math.min(...values), Math.max(...values)]
      : [0, 1];
  });
  const colorPosition = (value: number) => colorDomain[1] === colorDomain[0]
    ? 0
    : Math.max(0, Math.min(1, (value - colorDomain[0]) / (colorDomain[1] - colorDomain[0])));
  const left = 155;
  const top = 48;
  const chartWidth = $derived(Math.max(width, 480));
  const rowHeight = 32;
  const chartHeight = $derived(Math.max(height, top + genres.length * rowHeight + 12));
  const cellWidth = $derived((chartWidth - left - 12) / 3);
  const percent = (value: number) => `${(value * 100).toFixed(1)}%`;
  const differences = $derived(panels[0].rows.map((row, rowIndex) => ({
    genre: row.genre,
    cells: row.cells.map((cell, columnIndex) => {
      const nonIndie = panels[1].rows[rowIndex].cells[columnIndex].value;
      const indie = cell.value;
      return { label: cell.label, indie, nonIndie, delta: indie === null || nonIndie === null ? null : indie - nonIndie };
    })
  })));
  const differenceLimit = $derived(Math.max(
    0.01,
    ...differences.flatMap((row) => row.cells.map((cell) => Math.abs(cell.delta ?? 0)))
  ));
  const differenceColor = (delta: number) => interpolateRdBu(0.5 + delta / (2 * differenceLimit));
  const percentagePoints = (delta: number) => {
    const rounded = Number((delta * 100).toFixed(1));
    return `${rounded > 0 ? '+' : ''}${rounded.toFixed(1)} pp`;
  };
</script>

<section class="genre-price">
  <header class="chart-header" style={`width: ${chartWidth}px`}>
    <div>
      <h2>Genre &times; price</h2>
    </div>
  </header>
  <div class="control-row" style={`width: ${chartWidth}px`}>
    <fieldset class="metric-control">
      <!-- <legend>Color represents</legend> -->
      <label><input type="radio" name="gp-heatmap-metric" value="reviews" bind:group={metric} />Positive review %</label>
      <label><input type="radio" name="gp-heatmap-metric" value="sales" bind:group={metric} />Ownership share</label>
    </fieldset>

  </div>
  <!-- <p class="description">
    {#if metric === 'reviews'}Positive reviews &divide; all reviews in each cell, weighted by review count.
    {:else}Share of estimated owners across price ranges within each genre. Owner-range midpoints are a proxy for sales, including free-game ownership.{/if}
  </p> -->
  <br/>
  {#if merged}
    <div class="legend" aria-label="Percentage-point difference, indie minus non-indie">
      <span>Indie minus non-indie</span>
      <span>{percentagePoints(-differenceLimit)}</span>
      <span class="gradient" style:background={`linear-gradient(to right, ${differenceColor(-differenceLimit)}, ${differenceColor(0)}, ${differenceColor(differenceLimit)})`}></span>
      <span>{percentagePoints(differenceLimit)}</span><span class="missing"></span><span>No data</span>
    </div>
  {:else}
  <div class="legend" aria-label={`Color scale from ${percent(colorDomain[0])} to ${percent(colorDomain[1])}`}>
    <span>{percent(colorDomain[0])}</span><span class="gradient"></span><span>{percent(colorDomain[1])}</span><span class="missing"></span><span>No data</span>
  </div>
  {/if}
  {#if games.length === 0}
    <p>No game data available.</p>
  {:else}
    <div class="chart-scroll" bind:this={chartScroll}>
      <div class="heatmaps" class:merged id={`${id}-heatmaps`}>
      {#each panels as panel, panelIndex}
      <div class="heatmap-panel" class:non-indie={panelIndex === 1} aria-hidden={merged}>
      <h3>{panel.label}</h3>
      <svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} role="img" aria-label={`${panel.label} genre price heatmap: ${metric === 'reviews' ? 'positive review percentage' : 'estimated ownership share'}`}>
        <title>Genres by price range</title>
        {#each priceRanges as label, index}
          <text x={left + (index + 0.5) * cellWidth} y={28} text-anchor="middle" class="column-label">{label}</text>
        {/each}
        {#each panel.rows as row, rowIndex}
          <text x={left - 10} y={top + rowIndex * rowHeight + rowHeight / 2} dominant-baseline="middle" text-anchor="end" class="row-label">{row.genre}</text>
          {#each row.cells as cell, columnIndex}
            <g>
              <title>{row.genre} · {cell.label}: {cell.value === null ? 'No data' : percent(cell.value)}; {cell.count} games; {metric === 'reviews' ? `${cell.reviews.toLocaleString()} reviews` : `${cell.estimatedOwners.toLocaleString()} estimated owners`}</title>
              <rect x={left + columnIndex * cellWidth} y={top + rowIndex * rowHeight} width={cellWidth - 3} height={rowHeight - 3} rx="3" fill={cell.value === null ? '#e5e7eb' : interpolateBlues(colorPosition(cell.value))} />
              <text x={left + (columnIndex + 0.5) * cellWidth - 1.5} y={top + rowIndex * rowHeight + (rowHeight - 3) / 2} dominant-baseline="middle" text-anchor="middle" fill={cell.value !== null && colorPosition(cell.value) > 0.6 ? 'white' : '#172033'}>{cell.value === null ? '—' : percent(cell.value)}</text>
            </g>
          {/each}
        {/each}
      </svg>
      </div>
      {/each}
      <div class="difference-panel" aria-hidden={!merged}>
        <h3 style:padding-inline-start={`${(left - 15) / chartWidth * 100}%`}>Indie minus non-indie</h3>
        <svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} role="img" aria-label={`Genre price heatmap of differences in ${metric === 'reviews' ? 'positive review percentage' : 'ownership share'}`}>
          {#each priceRanges as label, index}
            <text x={left + (index + 0.5) * cellWidth} y={28} text-anchor="middle" class="column-label">{label}</text>
          {/each}
          {#each differences as row, rowIndex}
            <text x={left - 10} y={top + rowIndex * rowHeight + rowHeight / 2} dominant-baseline="middle" text-anchor="end" class="row-label">{row.genre}</text>
            {#each row.cells as cell, columnIndex}
              <g>
                <title>{`${row.genre}, ${cell.label}. Indie: ${cell.indie === null ? 'No data' : percent(cell.indie)}. Non-indie: ${cell.nonIndie === null ? 'No data' : percent(cell.nonIndie)}. Difference: ${cell.delta === null ? 'No data' : percentagePoints(cell.delta)}.`}</title>
                <rect x={left + columnIndex * cellWidth} y={top + rowIndex * rowHeight} width={cellWidth - 3} height={rowHeight - 3} rx="3" fill={cell.delta === null ? '#e5e7eb' : differenceColor(cell.delta)} />
                <text x={left + (columnIndex + 0.5) * cellWidth - 1.5} y={top + rowIndex * rowHeight + (rowHeight - 3) / 2} dominant-baseline="middle" text-anchor="middle" fill={cell.delta !== null && Math.abs(cell.delta) / differenceLimit > 0.65 ? 'white' : '#172033'}>{cell.delta === null ? '?' : percentagePoints(cell.delta)}</text>
              </g>
            {/each}
          {/each}
        </svg>
      </div>
      </div>
    </div>
    <div class="merge-control">
      <button type="button" aria-controls={`${id}-heatmaps`} onclick={toggleMerge}>{merged ? 'Split' : 'Merge'}</button>
    </div>
  {/if}
  <section class="analysis" aria-label="Heatmap analysis">
    <h3>Analysis</h3>
    <p>Across all the genres, indie games shows a higher positive review percentage for all price ranges than non-indie games. For both indie and non-indies, games that are
      $0.01~19.99 (below $20) have the highest positive reviews in all genres. For sales share, for indie games, games priced under $20 have a much higher share of ownership 
    in all genres except sports and mmos. In non-indie games, the share is more distributed evenly across all price ranges, showing that indies depend on games between $0.01~$19.99 for their sales.</p>
  </section>
   <!-- <p class="description">Indie status follows the Indie genre. Games can appear in multiple genre rows. Prices use the undiscounted USD price; $20 belongs to the highest range.</p> -->
</section>

<style>
  .genre-price { min-width: 0; }
  .chart-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 0.75rem; width: 100%; max-width: 100%; }
  h2 { margin: 0 0 1rem; }
  .control-row { display: flex; align-items: flex-start; justify-content: space-between; gap: 0.75rem; width: 100%; max-width: 100%; }
  .metric-control { display: flex; flex-direction: row; align-items: center; gap: 16px; margin: 0; padding: 0; border: 0; }
  .metric-control label { display: flex; align-items: center; gap: 10px; font-size: 14px; cursor: pointer; }
  .metric-control input { appearance: none; width: 20px; height: 20px; margin: 0; border: 1px solid #ddd; border-radius: 50%; background: white; flex-shrink: 0; cursor: pointer; }
  .metric-control input:checked { border: 7px solid #202124; }
  .metric-control input:focus-visible { outline: 2px solid #202124; outline-offset: 3px; }
  .legend { display: flex; align-items: center; gap: 0.5rem; font-size: 0.75rem; }
  .gradient { width: 120px; height: 12px; background: linear-gradient(to right, #f7fbff, #6baed6, #08306b); }
  .missing { width: 12px; height: 12px; margin-left: 0.5rem; background: #e5e7eb; }
  .chart-scroll { overflow-x: auto; }
  .heatmaps { position: relative; display: grid; grid-template-columns: repeat(2, minmax(360px, 1fr)); gap: 12px; min-width: 732px; }
  .heatmap-panel { transition: transform 504ms ease, opacity 120ms ease; }
  .merged .heatmap-panel { transform: translateX(calc(50% + 6px)); opacity: 0; transition-delay: 0ms, 384ms; pointer-events: none; }
  .merged .heatmap-panel.non-indie { transform: translateX(calc(-50% - 6px)); }
  .difference-panel { position: absolute; top: 0; left: 50%; width: calc(50% - 6px); transform: translateX(-50%); opacity: 0; visibility: hidden; }
  .merged .difference-panel { opacity: 1; visibility: visible; transition: opacity 120ms ease 384ms; }
  .merge-control { display: flex; justify-content: center; margin-top: 8px; }
  .merge-control button { padding: 6px 12px; border: 1px solid #94a3b8; border-radius: 5px; background: white; color: #243247; font: inherit; cursor: pointer; }
  @media (prefers-reduced-motion: reduce) {
    .heatmap-panel, .merged .difference-panel { transition: none; }
  }
  .analysis { width: 100%; margin: 24px 0 0; padding-top: 16px; border-top: 1px solid #e2e8f0; box-sizing: border-box; }
  .analysis h3 { margin: 0 0 8px; text-align: left; }
  .analysis p { margin: 0 0 12px; line-height: 1.7; color: #334155; }
  h3 { margin: 16px 0 0; text-align: center; font-size: 1rem; }
  svg { display: block; width: 100%; height: auto; font-family: inherit; font-size: 12px; }
  .column-label { font-weight: 600; fill: #243247; }
  .row-label { fill: #243247; }
  @media (max-width: 560px) {
    .chart-header, .control-row { flex-wrap: wrap; }
  }
</style>



