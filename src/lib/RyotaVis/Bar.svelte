<script lang="ts">
  import * as d3 from 'd3';
  import type { SteamGame } from '../../types';
  type Props = { games: SteamGame[]; width?: number; height?: number };
  let { games, width = 600, height = 360 }: Props = $props();
  const counts = $derived.by(() => {
    const map = new Map<string, number>();
    games.forEach((game) => game.genres.forEach((genre) => map.set(genre, (map.get(genre) ?? 0) + 1)));
    return [...map].sort((a, b) => b[1] - a[1]).slice(0, 12);
  });
  const x = $derived(d3.scaleLinear().domain([0, d3.max(counts, (d) => d[1]) ?? 1]).range([150, width - 25]));
  const y = $derived(d3.scaleBand().domain(counts.map((d) => d[0])).range([35, height - 25]).padding(0.18));
</script>
<section><h2>Games by genre</h2><svg {width} {height} aria-label="Number of games by genre">{#each counts as [genre, count]}<text x="145" y={y(genre)! + y.bandwidth() / 2 + 4} text-anchor="end">{genre}</text><rect x={150} y={y(genre)} width={x(count) - 150} height={y.bandwidth()} fill="#4f46e5" rx="3"/><text x={x(count) + 6} y={y(genre)! + y.bandwidth() / 2 + 4}>{count}</text>{/each}</svg></section>
