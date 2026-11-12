<script lang="ts">
  import * as d3 from 'd3';
  import type { SteamGame } from '../../types';
  type Props = { games: SteamGame[]; width?: number; height?: number };
  let { games, width = 620, height = 380 }: Props = $props();
  const points = $derived(games.filter((game) => Number.isFinite(game.price_usd) && Number.isFinite(game.discount_pct)).slice(0, 900));
  const x = $derived(d3.scaleLinear().domain([0, d3.max(points, (game) => game.price_usd) ?? 1]).nice().range([50, width - 25]));
  const y = $derived(d3.scaleLinear().domain([0, 100]).range([height - 45, 25]));
</script>
<section><h2>Price and discount</h2><svg {width} {height} aria-label="Price and discount scatterplot">{#each points as game}<circle cx={x(game.price_usd)} cy={y(game.discount_pct)} r="3" fill={game.is_free ? '#16a34a' : '#2563eb'} opacity="0.35"><title>{game.name}: ${game.price_usd.toFixed(2)}, {game.discount_pct}% off</title></circle>{/each}<line x1="50" x2={width - 25} y1={height - 45} y2={height - 45} stroke="#555"/><line x1="50" x2="50" y1="25" y2={height - 45} stroke="#555"/><text x={width / 2} y={height - 10} text-anchor="middle">Price (USD)</text><text transform={`translate(14 ${height / 2}) rotate(-90)`} text-anchor="middle">Discount (%)</text></svg></section>
