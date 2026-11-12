<script lang="ts">
  import * as d3 from 'd3';
  import type { SteamGame } from '../../types';
  type Props = { games: SteamGame[]; width?: number; height?: number };
  let { games, width = 620, height = 380 }: Props = $props();
  const developers = $derived.by(() => { const map = new Map<string, SteamGame[]>(); games.forEach((game) => map.set(game.developer, [...(map.get(game.developer) ?? []), game])); return [...map].map(([developer, values]) => ({ developer, average: d3.mean(values, (game) => game.price_usd) ?? 0, count: values.length })).sort((a, b) => b.count - a.count).slice(0, 12); });
  const x = $derived(d3.scaleBand().domain(developers.map((item) => item.developer)).range([45, width - 20]).padding(0.15));
  const y = $derived(d3.scaleLinear().domain([0, d3.max(developers, (item) => item.average) ?? 1]).nice().range([height - 45, 30]));
</script>
<section><h2>Average price by leading developer</h2><svg {width} {height} aria-label="Average price by developer">{#each developers as item}<rect x={x(item.developer)} y={y(item.average)} width={x.bandwidth()} height={height - 45 - y(item.average)} fill="#f97316"><title>{item.developer}: ${item.average.toFixed(2)} average</title></rect><text x={x(item.developer)! + x.bandwidth() / 2} y={height - 28} transform={`rotate(-45 ${x(item.developer)! + x.bandwidth() / 2} ${height - 28})`} text-anchor="end" font-size="10">{item.developer}</text>{/each}<text x={width / 2} y={height - 4} text-anchor="middle">Average price (USD)</text></svg></section>
