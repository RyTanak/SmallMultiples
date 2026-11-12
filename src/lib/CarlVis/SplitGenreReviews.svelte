<script lang="ts">
  import * as d3 from 'd3';
  import type { SteamGame } from '../../types';

  type Props = { games: SteamGame[]; width?: number };
  type GenreRow = {
    genre: string;
    indieReviews: number;
    nonIndieReviews: number;
    topIndie: SteamGame[];
    topNonIndie: SteamGame[];
  };
  type PieLabel = {
    lineStart: [number, number];
    lineMiddle: [number, number];
    lineEnd: [number, number];
    textX: number;
    textAnchor: 'start' | 'end';
  };

  let { games, width = 1040 }: Props = $props();

  const TOP_GENRE_COUNT = 10;
  const barHeight = 390;
  const barMargin = { top: 28, right: 24, bottom: 48, left: 130 };
  const pieSize = 220;
  const pieRadius = 82;
  const pieColumnWidth = 280;
  const pieGap = 32;
  const barChartWidth = $derived(width - pieColumnWidth * 2 - pieGap - 24);
  const barInnerWidth = $derived(barChartWidth - barMargin.left - barMargin.right);
  const totalReviews = (game: SteamGame) => game.positive_reviews + game.negative_reviews;
  const isIndieGenre = (genre: string) => genre.trim().toLowerCase() === 'indie';
  const isIndie = (game: SteamGame) =>
    [...game.genres, ...game.tags].some((value) => value.trim().toLowerCase() === 'indie');

  const topGenres = $derived.by(() => {
    const counts = new Map<string, number>();
    games.forEach((game) => {
      new Set(game.genres.filter((genre) => !isIndieGenre(genre))).forEach((genre) =>
        counts.set(genre, (counts.get(genre) ?? 0) + 1)
      );
    });
    return [...counts.entries()]
      .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
      .slice(0, TOP_GENRE_COUNT)
      .map(([genre]) => genre);
  });

  // A game with multiple top genres contributes its review total to each matching genre.
  const genreRows = $derived.by(() =>
    topGenres.map((genre): GenreRow => {
      const genreGames = games.filter((game) => game.genres.includes(genre));
      const indieGames = genreGames.filter(isIndie).sort((a, b) => totalReviews(b) - totalReviews(a));
      const nonIndieGames = genreGames
        .filter((game) => !isIndie(game))
        .sort((a, b) => totalReviews(b) - totalReviews(a));

      return {
        genre,
        indieReviews: indieGames.reduce((sum, game) => sum + totalReviews(game), 0),
        nonIndieReviews: nonIndieGames.reduce((sum, game) => sum + totalReviews(game), 0),
        topIndie: indieGames.slice(0, 3),
        topNonIndie: nonIndieGames.slice(0, 3)
      };
    })
  );

  let hoveredGenre = $state<string | null>(null);
  const activeGenre = $derived(hoveredGenre);
  const activeRow = $derived(activeGenre ? genreRows.find((row) => row.genre === activeGenre) ?? null : null);
  const maxReviews = $derived(
    Math.max(1, d3.max(genreRows, (row) => row.indieReviews + row.nonIndieReviews) ?? 1)
  );
  const yScale = $derived(
    d3.scaleBand<string>().domain(topGenres).range([barMargin.top, barHeight - barMargin.bottom]).padding(0.24)
  );
  const xScale = $derived(d3.scaleLinear().domain([0, maxReviews]).nice().range([0, barInnerWidth]));
  const color = $derived(d3.scaleOrdinal<string, string>().domain(topGenres).range(d3.schemeTableau10));
  const pie = d3.pie<GenreRow>().sort(null);
  const indieSlices = $derived(pie.value((row) => row.indieReviews)(genreRows));
  const nonIndieSlices = $derived(pie.value((row) => row.nonIndieReviews)(genreRows));
  const arc = d3.arc<d3.PieArcDatum<GenreRow>>().innerRadius(0).outerRadius(pieRadius);
  const labelArc = d3
    .arc<d3.PieArcDatum<GenreRow>>()
    .innerRadius(pieRadius + 10)
    .outerRadius(pieRadius + 10);

  const formatReviews = d3.format('.3s');
  const segmentWidth = (value: number) => xScale(value);
  const rowY = (genre: string) => yScale(genre) ?? barMargin.top;
  const piePath = (slice: d3.PieArcDatum<GenreRow>) => arc(slice) ?? '';
  const pieLabel = (slice: d3.PieArcDatum<GenreRow>) => {
    const [x, y] = labelArc.centroid(slice);
    const side = x >= 0 ? 1 : -1;
    return {
      lineStart: arc.centroid(slice),
      lineMiddle: [x, y],
      lineEnd: [side * (pieRadius + 24), y],
      textX: side * (pieRadius + 28),
      textAnchor: side === 1 ? 'start' : 'end'
    };
  };
  const layoutPieLabels = (slices: d3.PieArcDatum<GenreRow>[]) => {
    const labels = slices.map((slice) => ({ slice, label: pieLabel(slice) }));
    const minY = -pieSize / 2 + 12;
    const maxY = pieSize / 2 - 12;
    const minimumGap = 15;

    for (const side of [-1, 1]) {
      const sideLabels = labels
        .filter(({ label }) => Math.sign(label.lineMiddle[0]) === side)
        .sort((a, b) => a.label.lineMiddle[1] - b.label.lineMiddle[1]);

      let previousY = minY - minimumGap;
      sideLabels.forEach(({ label }) => {
        const y = Math.max(label.lineMiddle[1], previousY + minimumGap);
        label.lineEnd = [side * (pieRadius + 24), y];
        previousY = y;
      });

      for (let index = sideLabels.length - 1; index >= 0; index -= 1) {
        const label = sideLabels[index].label;
        label.lineEnd[1] = Math.min(label.lineEnd[1], maxY - (sideLabels.length - 1 - index) * minimumGap);
      }
    }

    return new Map(labels.map(({ slice, label }) => [slice.data.genre, label]));
  };
  const percentOf = (value: number, total: number) => (total > 0 ? d3.format('.1%')(value / total) : '0%');
  const pieTotal = (slices: d3.PieArcDatum<GenreRow>[]) => d3.sum(slices, (slice) => slice.data.indieReviews);
  const nonIndiePieTotal = (slices: d3.PieArcDatum<GenreRow>[]) =>
    d3.sum(slices, (slice) => slice.data.nonIndieReviews);
  const indieLabels = $derived(layoutPieLabels(indieSlices));
  const nonIndieLabels = $derived(layoutPieLabels(nonIndieSlices));
</script>

<section class="split-genre-reviews">
  <h2>Indie and non-indie review share by genre</h2>
  <p class="subtitle">
    The {TOP_GENRE_COUNT} most common genres are shown; bar segments show review volume, while each pie shows its group's genre distribution.
  </p>

  <div class="charts">
    <div class="bar-chart">
      <h3>Review split within each genre</h3>
      <svg width={barChartWidth} height={barHeight} aria-label="Review volume split by genre and indie status">
        <line
          class="baseline"
          x1={barMargin.left}
          x2={barChartWidth - barMargin.right}
          y1={barHeight - barMargin.bottom}
          y2={barHeight - barMargin.bottom}
        />
        {#each xScale.ticks(4) as tick}
          {@const tickX = barMargin.left + xScale(tick)}
          <line class="grid-line" x1={tickX} x2={tickX} y1={barMargin.top} y2={barHeight - barMargin.bottom} />
          <text class="tick-label" x={tickX} y={barHeight - barMargin.bottom + 18} text-anchor="middle">
            {formatReviews(tick)}
          </text>
        {/each}
        {#each genreRows as row}
          {@const y = rowY(row.genre)}
          {@const band = yScale.bandwidth()}
          {@const indieWidth = segmentWidth(row.indieReviews)}
          <text class:active-label={activeGenre === row.genre} class="genre-label" x={barMargin.left - 10} y={y + band / 2 + 4} text-anchor="end">
            {row.genre}
          </text>
          <rect
            class:active-segment={activeGenre === row.genre}
            class:inactive-segment={activeGenre !== null && activeGenre !== row.genre}
            class="non-indie-segment"
            x={barMargin.left}
            y={y}
            width={segmentWidth(row.nonIndieReviews)}
            height={band}
            onmouseenter={() => (hoveredGenre = row.genre)}
            onmouseleave={() => (hoveredGenre = null)}
            role="img"
            aria-label={`${row.genre}: non-indie reviews`}
          >
            <title>{row.genre}: {formatReviews(row.nonIndieReviews)} non-indie reviews</title>
          </rect>
          <rect
            class:active-segment={activeGenre === row.genre}
            class:inactive-segment={activeGenre !== null && activeGenre !== row.genre}
            class="indie-segment"
            x={barMargin.left + segmentWidth(row.nonIndieReviews)}
            y={y}
            width={indieWidth}
            height={band}
            onmouseenter={() => (hoveredGenre = row.genre)}
            onmouseleave={() => (hoveredGenre = null)}
            role="img"
            aria-label={`${row.genre}: indie reviews`}
          >
            <title>{row.genre}: {formatReviews(row.indieReviews)} indie reviews</title>
          </rect>
          {#if activeGenre === row.genre}
            <text class="bar-value" x={barMargin.left + segmentWidth(row.indieReviews + row.nonIndieReviews) + 7} y={y + band / 2 + 4}>
              {formatReviews(row.indieReviews + row.nonIndieReviews)} total
            </text>
          {/if}
        {/each}
        <text class="axis-label" x={barMargin.left + barInnerWidth / 2} y={barHeight - 5} text-anchor="middle">Total reviews</text>
      </svg>
      <div class="bar-legend"><span class="swatch non-indie"></span> Non-indie <span class="swatch indie"></span> Indie</div>
    </div>

    <div class="pies">
      <div class="pie-chart">
        <h3>Indie reviews</h3>
        <svg width={pieSize} height={pieSize} viewBox={`0 0 ${pieSize} ${pieSize}`} aria-label="Genre distribution of indie reviews">
          <g transform={`translate(${pieSize / 2} ${pieSize / 2})`}>
            {#each indieSlices as slice (slice.data.genre)}
              {@const label = indieLabels.get(slice.data.genre) ?? pieLabel(slice)}
              <path
                class:active-slice={activeGenre === slice.data.genre}
                class:inactive-slice={activeGenre !== null && activeGenre !== slice.data.genre}
                d={piePath(slice)}
                fill={color(slice.data.genre)}
                onmouseenter={() => (hoveredGenre = slice.data.genre)}
                onmouseleave={() => (hoveredGenre = null)}
                role="img"
                aria-label={`${slice.data.genre}: ${percentOf(slice.data.indieReviews, pieTotal(indieSlices))} of indie reviews`}
              >
                <title>{slice.data.genre}: {percentOf(slice.data.indieReviews, pieTotal(indieSlices))}</title>
              </path>
              <polyline
                class:active-leader={activeGenre === slice.data.genre}
                class:inactive-leader={activeGenre !== null && activeGenre !== slice.data.genre}
                points={`${label.lineStart.join(',')} ${label.lineMiddle.join(',')} ${label.lineEnd.join(',')}`}
              />
              <text
                class:active-pie-label={activeGenre === slice.data.genre}
                class:inactive-pie-label={activeGenre !== null && activeGenre !== slice.data.genre}
                x={label.textX}
                y={label.lineEnd[1] + 3}
                text-anchor={label.textAnchor}
              >{slice.data.genre}</text>
            {/each}
          </g>
        </svg>
      </div>

      <div class="pie-chart">
        <h3>Non-indie reviews</h3>
        <svg width={pieSize} height={pieSize} viewBox={`0 0 ${pieSize} ${pieSize}`} aria-label="Genre distribution of non-indie reviews">
          <g transform={`translate(${pieSize / 2} ${pieSize / 2})`}>
            {#each nonIndieSlices as slice (slice.data.genre)}
              {@const label = nonIndieLabels.get(slice.data.genre) ?? pieLabel(slice)}
              <path
                class:active-slice={activeGenre === slice.data.genre}
                class:inactive-slice={activeGenre !== null && activeGenre !== slice.data.genre}
                d={piePath(slice)}
                fill={color(slice.data.genre)}
                onmouseenter={() => (hoveredGenre = slice.data.genre)}
                onmouseleave={() => (hoveredGenre = null)}
                role="img"
                aria-label={`${slice.data.genre}: ${percentOf(slice.data.nonIndieReviews, nonIndiePieTotal(nonIndieSlices))} of non-indie reviews`}
              >
                <title>{slice.data.genre}: {percentOf(slice.data.nonIndieReviews, nonIndiePieTotal(nonIndieSlices))}</title>
              </path>
              <polyline
                class:active-leader={activeGenre === slice.data.genre}
                class:inactive-leader={activeGenre !== null && activeGenre !== slice.data.genre}
                points={`${label.lineStart.join(',')} ${label.lineMiddle.join(',')} ${label.lineEnd.join(',')}`}
              />
              <text
                class:active-pie-label={activeGenre === slice.data.genre}
                class:inactive-pie-label={activeGenre !== null && activeGenre !== slice.data.genre}
                x={label.textX}
                y={label.lineEnd[1] + 3}
                text-anchor={label.textAnchor}
              >{slice.data.genre}</text>
            {/each}
          </g>
        </svg>
      </div>
    </div>
  </div>

  <div class="details" aria-live="polite">
    {#if activeRow}
      <h3>{activeRow.genre}</h3>
      <div class="detail-columns">
        <div>
          <h4>Top indie games</h4>
          {#if activeRow.topIndie.length}
            <ol>
              {#each activeRow.topIndie as game}
                <li><span>{game.name}</span><small>{formatReviews(totalReviews(game))} reviews</small></li>
              {/each}
            </ol>
          {:else}
            <p class="empty">No indie games in this genre.</p>
          {/if}
        </div>
        <div>
          <h4>Top non-indie games</h4>
          {#if activeRow.topNonIndie.length}
            <ol>
              {#each activeRow.topNonIndie as game}
                <li><span>{game.name}</span><small>{formatReviews(totalReviews(game))} reviews</small></li>
              {/each}
            </ol>
          {:else}
            <p class="empty">No non-indie games in this genre.</p>
          {/if}
        </div>
      </div>
    {/if}
  </div>
</section>

<style>
  .split-genre-reviews {
    min-width: 0;
  }

  h2,
  h3,
  h4 {
    margin-top: 0;
  }

  h2 {
    margin-bottom: 0.2rem;
  }

  h3 {
    font-size: 0.95rem;
    margin-bottom: 0.4rem;
  }

  .subtitle {
    color: #64748b;
    font-size: 0.82rem;
    margin: 0 0 0.8rem;
  }

  .charts {
    align-items: start;
    display: flex;
    gap: 0.35rem;
    justify-content: center;
  }

  .bar-chart {
    flex: 0 1 auto;
    min-width: 0;
  }

  .pies {
    display: flex;
    flex: 0 0 auto;
    gap: 2rem;
    justify-content: center;
  }

  .pie-chart {
    box-sizing: border-box;
    padding: 0 4.0rem;
    text-align: center;
    width: 280px;
  }

  svg {
    display: block;
    max-width: 100%;
    overflow: visible;
  }

  .baseline,
  .grid-line {
    stroke: #cbd5e1;
    stroke-width: 1;
  }

  .grid-line {
    stroke-dasharray: 2 3;
  }

  .tick-label,
  .axis-label {
    fill: #64748b;
    font-size: 10px;
  }

  .genre-label,
  .bar-value {
    fill: #475569;
    font-size: 11px;
  }

  .active-label,
  .bar-value {
    fill: #0f172a;
    font-weight: 700;
  }

  rect,
  path {
    cursor: pointer;
    transition: opacity 120ms ease, stroke 120ms ease, stroke-width 120ms ease;
  }

  .non-indie-segment {
    fill: #94a3b8;
  }

  .indie-segment {
    fill: #f97316;
  }

  .active-segment {
    stroke: #0f172a;
    stroke-width: 1.5;
  }

  .inactive-segment,
  .inactive-slice {
    opacity: 0.22;
  }

  .active-slice {
    opacity: 1;
    stroke: #0f172a;
    stroke-width: 2.5;
  }

  polyline {
    fill: none;
    pointer-events: none;
    stroke: #94a3b8;
    stroke-width: 1;
  }

  .active-leader {
    stroke: #0f172a;
    stroke-width: 1.5;
  }

  .inactive-leader,
  .inactive-pie-label {
    opacity: 0.28;
  }

  text.active-pie-label,
  text.inactive-pie-label {
    fill: #475569;
    font-size: 8.5px;
    pointer-events: none;
  }

  text.active-pie-label {
    fill: #0f172a;
    font-weight: 700;
  }

  .bar-legend {
    color: #64748b;
    font-size: 0.78rem;
    text-align: center;
  }

  .swatch {
    display: inline-block;
    height: 0.65rem;
    margin: 0 0.25rem 0 0.7rem;
    vertical-align: -0.05rem;
    width: 0.65rem;
  }

  .swatch:first-child {
    margin-left: 0;
  }

  .swatch.non-indie {
    background: #94a3b8;
  }

  .swatch.indie {
    background: #f97316;
  }

  .details {
    border-top: 1px solid #e2e8f0;
    box-sizing: border-box;
    height: 10rem;
    margin-top: 0.6rem;
    overflow: hidden;
    padding-top: 0.8rem;
  }

  .details h3 {
    color: #0f172a;
    margin-bottom: 0.45rem;
  }

  .detail-columns {
    display: grid;
    gap: 1rem;
    grid-template-columns: 1fr 1fr;
  }

  .detail-columns h4 {
    color: #475569;
    font-size: 0.8rem;
    margin-bottom: 0.25rem;
  }

  ol {
    margin: 0;
    padding-left: 1.3rem;
  }

  li {
    color: #334155;
    font-size: 0.8rem;
    margin-bottom: 0.18rem;
    padding-left: 0.15rem;
  }

  li small {
    color: #64748b;
    margin-left: 0.35rem;
  }

  .empty {
    color: #64748b;
    font-size: 0.8rem;
    margin: 0;
  }

  @media (max-width: 850px) {
    .charts {
      display: block;
    }

    .pies {
      justify-content: center;
      margin-top: 0.8rem;
    }
  }
</style>
