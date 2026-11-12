<script lang="ts">
  import * as d3 from 'd3';
  import type { SteamGame } from '../../types';

  type DatedGame = SteamGame & { release_date: Date };
  type Props = { games: SteamGame[]; width?: number; height?: number };
  let { games, width = 620, height = 340 }: Props = $props();

  const datedGames = $derived(games.filter((game): game is DatedGame => game.release_date !== null));
  const data = $derived.by(() => {
    const counts = new Map<number, number>();
    datedGames.forEach((game) => {
      const year = game.release_date.getFullYear();
      counts.set(year, (counts.get(year) ?? 0) + 1);
    });
    return [...counts].sort((a, b) => a[0] - b[0]);
  });
  const x = $derived(d3.scaleLinear().domain(d3.extent(data, (item) => item[0]) as [number, number]).range([50, width - 20]));
  const y = $derived(d3.scaleLinear().domain([0, d3.max(data, (item) => item[1]) ?? 1]).nice().range([height - 45, 30]));
  const path = $derived(d3.line<[number, number]>().x((item) => x(item[0])).y((item) => y(item[1]))(data) ?? '');
</script>

<section>
  <h2>Games released by year</h2>
  <svg {width} {height} aria-label="Games released by year line chart">
    <path d={path} fill="none" stroke="#0891b2" stroke-width="3" />
    {#each data as [year, count]}
      <circle cx={x(year)} cy={y(count)} r="3" fill="#0891b2"><title>{year}: {count} games</title></circle>
    {/each}
    <text x={width / 2} y={height - 8} text-anchor="middle">Release year</text>
  </svg>
</section>
