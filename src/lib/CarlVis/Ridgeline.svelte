<script lang="ts">
  import type { SteamGame } from '../../types';

  type DatedGame = SteamGame & { release_date: Date };
  type Props = { games: SteamGame[]; width?: number; height?: number };
  let { games, width = 620, height = 380 }: Props = $props();

  const datedGames = $derived(games.filter((game): game is DatedGame => game.release_date !== null));
  const decades = $derived.by(() => {
    const map = new Map<number, { free: number; paid: number }>();
    datedGames.forEach((game) => {
      const decade = Math.floor(game.release_date.getFullYear() / 10) * 10;
      const entry = map.get(decade) ?? { free: 0, paid: 0 };
      game.is_free ? entry.free++ : entry.paid++;
      map.set(decade, entry);
    });
    return [...map].sort((a, b) => a[0] - b[0]).slice(-12);
  });
  const max = $derived(Math.max(1, ...decades.map(([, value]) => value.free + value.paid)));
  const scale = $derived((count: number) => count / max * (width - 170));
</script>

<section>
  <h2>Free and paid games by decade</h2>
  <svg {width} {height} aria-label="Free and paid games by decade">
    {#each decades as [decade, value], index}
      {@const y = 30 + index * 26}
      <text x="48" y={y + 14} text-anchor="end">{decade}s</text>
      <rect x="55" y={y} width={scale(value.free)} height="18" fill="#22c55e"><title>{value.free} free games</title></rect>
      <rect x={55 + scale(value.free)} y={y} width={scale(value.paid)} height="18" fill="#8b5cf6"><title>{value.paid} paid games</title></rect>
    {/each}
    <text x={width - 30} y={height - 8} text-anchor="end">Free</text>
    <rect x={width - 25} y={height - 20} width="12" height="12" fill="#22c55e" />
    <text x={width - 80} y={height - 8} text-anchor="end">Paid</text>
    <rect x={width - 75} y={height - 20} width="12" height="12" fill="#8b5cf6" />
  </svg>
</section>
