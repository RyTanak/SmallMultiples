<script lang="ts">
  import * as d3 from 'd3';
  import type { SteamGame } from '../../types';

  type Props = { games: SteamGame[]; width?: number; height?: number };
  type Dimension = 'price' | 'medianPlaytime' | 'genre' | 'reviews' | 'sentiment';

  let { games, width = 760, height = 500 }: Props = $props();

  // Raise this value to show fewer games, or lower it to include more.
  const MIN_TOTAL_REVIEWS = 10_000;
  const MAX_GAMES = 140;
  const dimensions: Dimension[] = ['price', 'medianPlaytime', 'genre', 'reviews', 'sentiment'];
  const dimensionLabels: Record<Dimension, string> = {
    price: 'Price (USD)',
    medianPlaytime: 'Median playtime (hours)',
    genre: 'Genre',
    reviews: 'Reviews',
    sentiment: 'Positive sentiment'
  };
  const margin = { top: 62, right: 34, bottom: 28, left: 34 };
  const innerHeight = $derived(height - margin.top - margin.bottom);

  const totalReviews = (game: SteamGame) => game.positive_reviews + game.negative_reviews;
  const isIndie = (game: SteamGame) =>
    [...game.genres, ...game.tags].some((value) => value.trim().toLowerCase() === 'indie');
  const primaryGenre = (game: SteamGame) => game.genres[0] ?? game.tags[0] ?? 'Unknown';
  const hours = (minutes: number) => minutes / 60;

  const subset = $derived(
    games
      .filter((game) => totalReviews(game) >= MIN_TOTAL_REVIEWS)
      .sort((a, b) => totalReviews(b) - totalReviews(a))
      .slice(0, MAX_GAMES)
  );
  const genreDomain = $derived(
    [...new Set(subset.map(primaryGenre))].sort((a, b) => a.localeCompare(b))
  );
  const maxPrice = $derived(Math.max(1, d3.max(subset, (game) => game.price_usd) ?? 1));
  const maxPlaytime = $derived(Math.max(1, d3.max(subset, (game) => hours(game.median_playtime)) ?? 1));
  const maxReviews = $derived(Math.max(1, d3.max(subset, totalReviews) ?? MIN_TOTAL_REVIEWS));
  const priceScale = $derived(
    d3.scaleLinear().domain([0, maxPrice]).nice().range([innerHeight, 0])
  );
  const playtimeScale = $derived(
    d3.scaleLinear().domain([0, maxPlaytime]).nice().range([innerHeight, 0])
  );
  const genreScale = $derived(
    d3.scalePoint<string>().domain(genreDomain).range([innerHeight, 0]).padding(0.4)
  );
  const reviewsScale = $derived(
    d3.scaleLog().domain([Math.max(1, MIN_TOTAL_REVIEWS), maxReviews]).range([innerHeight, 0])
  );
  const sentimentScale = $derived(d3.scaleLinear().domain([0, 1]).range([innerHeight, 0]));
  const xScale = $derived(
    d3.scalePoint<Dimension>().domain(dimensions).range([margin.left, width - margin.right])
  );
  let hoveredGame = $state<SteamGame | null>(null);

  const sentiment = (game: SteamGame) => {
    const reviews = totalReviews(game);
    return reviews > 0 ? game.positive_reviews / reviews : 0;
  };

  const yValue = (game: SteamGame, dimension: Dimension) => {
    switch (dimension) {
      case 'price':
        return margin.top + priceScale(game.price_usd);
      case 'medianPlaytime':
        return margin.top + playtimeScale(hours(game.median_playtime));
      case 'genre':
        return margin.top + (genreScale(primaryGenre(game)) ?? innerHeight);
      case 'reviews':
        return margin.top + reviewsScale(Math.max(1, totalReviews(game)));
      case 'sentiment':
        return margin.top + sentimentScale(sentiment(game));
    }
  };

  const pathFor = (game: SteamGame) =>
    d3
      .line<Dimension>()
      .x((dimension) => xScale(dimension) ?? 0)
      .y((dimension) => yValue(game, dimension))(
        dimensions
      ) ?? '';

  const tickValues = (dimension: Dimension): (number | string)[] => {
    switch (dimension) {
      case 'price':
        return priceScale.ticks(5);
      case 'medianPlaytime':
        return playtimeScale.ticks(5);
      case 'genre':
        return genreDomain;
      case 'reviews':
        return reviewsScale.ticks(5);
      case 'sentiment':
        return sentimentScale.ticks(5);
    }
  };

  const tickY = (dimension: Dimension, value: number | string) => {
    switch (dimension) {
      case 'price':
        return margin.top + priceScale(Number(value));
      case 'medianPlaytime':
        return margin.top + playtimeScale(Number(value));
      case 'genre':
        return margin.top + (genreScale(String(value)) ?? innerHeight);
      case 'reviews':
        return margin.top + reviewsScale(Number(value));
      case 'sentiment':
        return margin.top + sentimentScale(Number(value));
    }
  };

  const tickLabel = (dimension: Dimension, value: number | string) => {
    if (dimension === 'genre') return String(value);
    if (dimension === 'price') return `$${Number(value).toFixed(0)}`;
    if (dimension === 'medianPlaytime') return `${Number(value).toFixed(0)}h`;
    if (dimension === 'reviews') return d3.format('.2s')(Number(value));
    return d3.format('.0%')(Number(value));
  };
</script>

<section class="parallel-coordinates">
  <div class="heading">
    <div>
      <h2>Popular games across price, playtime, and sentiment</h2>
      <p class="subtitle">
        {subset.length} games with at least {d3.format(',')(MIN_TOTAL_REVIEWS)} total reviews
      </p>
    </div>
    <div class="legend"><span class="legend-line indie"></span> Indie <span class="legend-line"></span> Other</div>
  </div>

  <svg {width} {height} aria-label="Parallel coordinates chart of popular Steam games">
    {#each dimensions as dimension}
      {@const axisX = xScale(dimension) ?? 0}
      <line class="axis" x1={axisX} x2={axisX} y1={margin.top} y2={height - margin.bottom} />
      <text class="axis-label" x={axisX} y={margin.top - 32} text-anchor="middle">
        {dimensionLabels[dimension]}
      </text>
      {#each tickValues(dimension) as value}
        {@const y = tickY(dimension, value)}
        <line class="tick-line" x1={axisX - 4} x2={axisX + 4} y1={y} y2={y} />
        <text class="tick-label" x={axisX + 8} y={y + 3}>{tickLabel(dimension, value)}</text>
      {/each}
    {/each}

    {#each subset as game (game.app_id)}
      <path
        d={pathFor(game)}
        class:indie-line={isIndie(game)}
        class:hovered={hoveredGame?.app_id === game.app_id}
        class:dimmed={hoveredGame !== null && hoveredGame.app_id !== game.app_id}
        onmouseenter={() => (hoveredGame = game)}
        onmouseleave={() => (hoveredGame = null)}
        role="img"
        aria-label={game.name}
      >
        <title>{game.name}</title>
      </path>
    {/each}
  </svg>

  <div class="selection" aria-live="polite">
    {#if hoveredGame}
      <strong>{hoveredGame.name}</strong>
      <span>{primaryGenre(hoveredGame)} · {isIndie(hoveredGame) ? 'Indie' : 'Other'}</span>
      <span>${hoveredGame.price_usd.toFixed(2)} · {hours(hoveredGame.median_playtime).toFixed(1)}h median playtime · {d3.format(',')(totalReviews(hoveredGame))} reviews · {d3.format('.1%')(sentiment(hoveredGame))} positive</span>
    {:else}
      <span>Hover over a line to highlight the game it represents.</span>
    {/if}
  </div>
</section>

<style>
  .parallel-coordinates {
    min-width: 0;
  }

  .heading {
    align-items: end;
    display: flex;
    gap: 1rem;
    justify-content: space-between;
  }

  h2 {
    margin-bottom: 0.2rem;
  }

  .subtitle {
    color: #64748b;
    font-size: 0.82rem;
    margin: 0;
  }

  .legend {
    color: #64748b;
    font-size: 0.78rem;
    white-space: nowrap;
  }

  .legend-line {
    border-top: 1px solid #94a3b8;
    display: inline-block;
    margin: 0 0.25rem 0 0.65rem;
    vertical-align: middle;
    width: 1.4rem;
  }

  .legend-line.indie {
    border-top: 3px solid #f97316;
  }

  svg {
    display: block;
    height: auto;
    max-width: 100%;
    overflow: visible;
  }

  .axis {
    stroke: #475569;
    stroke-width: 1.2;
  }

  .tick-line {
    stroke: #475569;
  }

  .tick-label,
  .axis-label {
    fill: #475569;
    font-size: 10px;
  }

  .axis-label {
    font-size: 11px;
    font-weight: 650;
  }

  path {
    cursor: pointer;
    fill: none;
    opacity: 0.28;
    stroke: #64748b;
    stroke-width: 1;
    transition: opacity 120ms ease, stroke 120ms ease, stroke-width 120ms ease;
  }

  path.indie-line {
    opacity: 0.62;
    stroke: #f97316;
    stroke-width: 2.4;
  }

  path.hovered {
    opacity: 1;
    stroke: #0f172a;
    stroke-width: 3.2;
  }

  path.hovered.indie-line {
    stroke: #ea580c;
    stroke-width: 4;
  }

  path.dimmed {
    opacity: 0.06;
  }

  .selection {
    align-items: baseline;
    background: #f8fafc;
    border-left: 3px solid #94a3b8;
    color: #475569;
    display: flex;
    flex-wrap: wrap;
    gap: 0.25rem 0.7rem;
    min-height: 1.4rem;
    padding: 0.45rem 0.65rem;
  }

  .selection strong {
    color: #0f172a;
  }
</style>
