<script lang="ts">
  import { interpolateBlues } from 'd3';
  import type { SteamGame } from '../../types';

  type Props = { games: SteamGame[]; width?: number; height?: number };
  let { games, width = 620, height = 420 }: Props = $props();
  let indie = $state(true);
  let metric = $state<'reviews' | 'sales'>('reviews');
  const priceRanges = ['Free', 'Below $20', '$20 and above'];
  const priceBucket = (game: SteamGame) => game.is_free || game.price_usd === 0 ? 0 : game.price_usd < 20 ? 1 : 2;
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
  const selectedGames = $derived(games.filter((game) => isIndie(game) === indie));
  const rows = $derived.by(() => genres.map((genre) => {
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
  }));
  const left = 155;
  const top = 48;
  const chartWidth = $derived(Math.max(width, 480));
  const rowHeight = 32;
  const chartHeight = $derived(Math.max(height, top + rows.length * rowHeight + 12));
  const cellWidth = $derived((chartWidth - left - 12) / 3);
  const percent = (value: number) => `${(value * 100).toFixed(1)}%`;
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
      <label><input type="radio" name="gp-heatmap-metric" value="sales" bind:group={metric} />Sales share</label>
    </fieldset>
    <div class="game-type" role="group" aria-label="Game type">
      <button class:active={indie} aria-pressed={indie} onclick={() => indie = true}>Indie games</button>
      <button class:active={!indie} aria-pressed={!indie} onclick={() => indie = false}>Non-indie games</button>
    </div>
  </div>
  <!-- <p class="description">
    {#if metric === 'reviews'}Positive reviews &divide; all reviews in each cell, weighted by review count.
    {:else}Share of estimated owners across price ranges within each genre. Owner-range midpoints are a proxy for sales, including free-game ownership.{/if}
  </p> -->
  <br/>
  <div class="legend" aria-label="Color scale from zero to one hundred percent">
    <span>0%</span><span class="gradient"></span><span>100%</span><span class="missing"></span><span>No data</span>
  </div>
  {#if games.length === 0}
    <p>No game data available.</p>
  {:else}
    <!-- <p class="count" aria-live="polite">{selectedGames.length.toLocaleString()} {indie ? 'indie' : 'non-indie'} games · {metric === 'reviews' ? 'Positive review %' : 'Sales share'}</p> -->
    <div class="chart-scroll">
      <svg width={chartWidth} height={chartHeight} role="img" aria-label={`${indie ? 'Indie' : 'Non-indie'} genre price heatmap: ${metric === 'reviews' ? 'positive review percentage' : 'estimated sales share'}`}>
        <title>Genres by price range</title>
        {#each priceRanges as label, index}
          <text x={left + (index + 0.5) * cellWidth} y={28} text-anchor="middle" class="column-label">{label}</text>
        {/each}
        {#each rows as row, rowIndex}
          <text x={left - 10} y={top + rowIndex * rowHeight + rowHeight / 2} dominant-baseline="middle" text-anchor="end" class="row-label">{row.genre}</text>
          {#each row.cells as cell, columnIndex}
            <g>
              <title>{row.genre} · {cell.label}: {cell.value === null ? 'No data' : percent(cell.value)}; {cell.count} games; {metric === 'reviews' ? `${cell.reviews.toLocaleString()} reviews` : `${cell.estimatedOwners.toLocaleString()} estimated owners`}</title>
              <rect x={left + columnIndex * cellWidth} y={top + rowIndex * rowHeight} width={cellWidth - 3} height={rowHeight - 3} rx="3" fill={cell.value === null ? '#e5e7eb' : interpolateBlues(cell.value)} />
              <text x={left + (columnIndex + 0.5) * cellWidth - 1.5} y={top + rowIndex * rowHeight + (rowHeight - 3) / 2} dominant-baseline="middle" text-anchor="middle" fill={cell.value !== null && cell.value > 0.6 ? 'white' : '#172033'}>{cell.value === null ? '—' : percent(cell.value)}</text>
            </g>
          {/each}
        {/each}
      </svg>
    </div>
  {/if}
   <!-- <p class="description">Indie status follows the Indie genre. Games can appear in multiple genre rows. Prices use the listed USD price; $20 belongs to the highest range.</p> -->
</section>

<style>
  .genre-price { min-width: 0; }
  .chart-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 0.75rem; width: 100%; max-width: 100%; }
  h2 { margin: 0 0 1rem; }
  .control-row { display: flex; align-items: flex-start; justify-content: space-between; gap: 0.75rem; width: 100%; max-width: 100%; }
  .game-type { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 0.25rem; }
  .game-type button { padding: 0.3rem 0.5rem; font-size: 0.75rem; }
  button { padding: 0.5rem 0.7rem; border: 1px solid #94a3b8; border-radius: 5px; background: white; color: #243247; cursor: pointer; font: inherit; font-size: 0.85rem; }
  button.active { background: blue; border-color: black; color: white; }
  button:focus-visible { outline: 3px solid #f59e0b; outline-offset: 2px; }
  .metric-control { display: flex; flex-direction: row; align-items: center; gap: 16px; margin: 0; padding: 0; border: 0; }
  .metric-control legend { padding: 0; margin-bottom: 8px; color: #707174; font-size: 13px; }
  .metric-control label { display: flex; align-items: center; gap: 10px; font-size: 14px; cursor: pointer; }
  .metric-control input { appearance: none; width: 20px; height: 20px; margin: 0; border: 1px solid #ddd; border-radius: 50%; background: white; flex-shrink: 0; cursor: pointer; }
  .metric-control input:checked { border: 7px solid #202124; }
  .metric-control input:focus-visible { outline: 2px solid #202124; outline-offset: 3px; }
  .description, .count { font-size: 0.8rem; line-height: 1.5; color: #475569; }
  .legend { display: flex; align-items: center; gap: 0.5rem; font-size: 0.75rem; }
  .gradient { width: 120px; height: 12px; background: linear-gradient(to right, #f7fbff, #6baed6, #08306b); }
  .missing { width: 12px; height: 12px; margin-left: 0.5rem; background: #e5e7eb; }
  .chart-scroll { overflow-x: auto; }
  svg { display: block; font-family: inherit; font-size: 12px; }
  .column-label { font-weight: 600; fill: #243247; }
  .row-label { fill: #243247; }
  @media (max-width: 560px) {
    .chart-header, .control-row { flex-wrap: wrap; }
  }
</style>



