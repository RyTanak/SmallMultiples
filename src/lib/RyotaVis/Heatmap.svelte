<script lang="ts">
  import type { SteamGame } from '../../types';
  type Props = { games: SteamGame[]; width?: number; height?: number };
  let { games, width = 620, height = 420 }: Props = $props();
  const genres = $derived([...new Set(games.flatMap((game) => game.genres))].sort());
  const cells = $derived.by(() => {
    const counts = new Map<string, Map<string, number>>();
    for (const game of games) {
      const uniqueGenres = [...new Set(game.genres)];
      for (const row of uniqueGenres) {
        const columns = counts.get(row) ?? new Map<string, number>();
        counts.set(row, columns);
        for (const column of uniqueGenres) {
          if (row !== column) columns.set(column, (columns.get(column) ?? 0) + 1);
        }
      }
    }
    return genres.flatMap((row) => genres.map((column) => ({
      row, column, count: counts.get(row)?.get(column) ?? 0
    })));
  });
  const left = 110; const top = 70; const size = $derived(Math.min((width - left - 20) / Math.max(genres.length, 1), (height - top - 20) / Math.max(genres.length, 1)));
  const max = $derived(Math.max(1, ...cells.map((cell) => cell.count)));
</script>
<section><h2>Genre co-occurrence</h2><svg {width} {height} aria-label="Genre co-occurrence heatmap">{#each genres as genre, index}<text x={left + index * size + size / 2} y={top - 8} transform={`rotate(-45 ${left + index * size + size / 2} ${top - 8})`} text-anchor="start" font-size="10">{genre}</text><text x={left - 8} y={top + index * size + size / 2 + 3} text-anchor="end" font-size="10">{genre}</text>{/each}{#each cells as cell}<rect x={left + genres.indexOf(cell.column) * size} y={top + genres.indexOf(cell.row) * size} width={size - 1} height={size - 1} fill={`rgba(37, 99, 235, ${0.08 + cell.count / max * 0.9})`}><title>{cell.row} + {cell.column}: {cell.count}</title></rect>{/each}</svg></section>
