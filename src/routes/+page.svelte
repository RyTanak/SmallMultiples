<script lang="ts">
  import * as d3 from 'd3';
  import { onMount } from 'svelte';
  import Bar from '$lib/RyotaVis/Bar.svelte';
  import Bump from '$lib/RyotaVis/Bump.svelte';
  import Heatmap from '$lib/RyotaVis/Heatmap.svelte';
  import Scatter from '$lib/EricVis/Scatter.svelte';
  import A2_4 from '$lib/EricVis/A2_4.svelte';
  import Line from '$lib/EricVis/Line.svelte';
  import Ridgeline from '$lib/CarlVis/Ridgeline.svelte';
  import type { SteamGame } from '../types';

  let games: SteamGame[] = $state([]);

  onMount(async () => {
    games = await d3.csv('/steam_top_games_2026-selected-columns.csv', (row) => ({
    app_id: Number(row.app_id),
    name: row.name ?? 'Unnamed game',
    release_date: new Date(row.release_date ?? ''),
    coming_soon: row.coming_soon?.toLowerCase() === 'true',
    price_usd: Number(row.price_usd),
    is_free: row.is_free?.toLowerCase() === 'true',
    discount_pct: Number(row.discount_pct),
    developer: row.developer ?? 'Unknown developer',
    publisher: row.publisher ?? 'Unknown publisher',
    genres: (row.genres ?? '').split(',').map((genre) => genre.trim()).filter(Boolean)
    })) as SteamGame[];
  });
</script>

<main class="grid">
  <Bar {games} />
  <Bump {games} />
  <Heatmap {games} />
  <Scatter {games} />
  <A2_4 {games} />
  <Line {games} />
  <Ridgeline {games} />
</main>


