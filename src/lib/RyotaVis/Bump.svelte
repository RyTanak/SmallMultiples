<script lang="ts">
  import * as d3 from 'd3';
  import type { SteamGame } from '../../types';

  type DatedGame = SteamGame & { release_date: Date };
  type Props = { games: SteamGame[]; width?: number; height?: number };
  let { games, width = 620, height = 360 }: Props = $props();

  const datedGames = $derived(games.filter((game): game is DatedGame => game.release_date !== null));
  const years = $derived([...new Set(datedGames.map((game) => game.release_date.getFullYear()))].sort((a, b) => a - b));
  const series = $derived.by(() => {
    const genres = [...new Set(datedGames.flatMap((game) => game.genres))];
    return genres
      .map((genre) => ({
        genre,
        points: years.map((year) => ({
          year,
          count: datedGames.filter((game) => game.release_date.getFullYear() === year && game.genres.includes(genre)).length
        }))
      }))
      .sort((a, b) => d3.sum(b.points, (point) => point.count) - d3.sum(a.points, (point) => point.count))
      .slice(0, 5);
  });
  const x = $derived(d3.scaleLinear().domain(d3.extent(years) as [number, number]).range([45, width - 20]));
  const y = $derived(d3.scaleLinear().domain([0, d3.max(series, (item) => d3.max(item.points, (point) => point.count)) ?? 1]).range([height - 35, 35]));
  const line = d3.line<{ year: number; count: number }>().x((point) => x(point.year)).y((point) => y(point.count));
</script>

<section>
  <h2>Genre releases over time</h2>
  <svg {width} {height} aria-label="Genre release trends">
    {#each series as item, index}
      <path d={line(item.points) ?? ''} fill="none" stroke={d3.schemeTableau10[index]} stroke-width="2" />
      <text x={width - 15} y={y(item.points[item.points.length - 1]?.count ?? 0)} fill={d3.schemeTableau10[index]} text-anchor="end">{item.genre}</text>
    {/each}
    <line x1="45" x2={width - 20} y1={height - 35} y2={height - 35} stroke="#555" />
    <text x={width / 2} y={height - 8} text-anchor="middle">Release year</text>
  </svg>
</section>
