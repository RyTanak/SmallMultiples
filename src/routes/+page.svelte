<script lang="ts">
  import * as d3 from "d3";
  import { onMount } from "svelte";
  import Bar from "$lib/RyotaVis/Bar.svelte";
  import Bump from "$lib/RyotaVis/Bump.svelte";
  import Heatmap from "$lib/RyotaVis/Heatmap.svelte";
  import GPHeatmap from "$lib/RyotaVis/GPHeatmap.svelte";
  import PLPScatter from "$lib/RyotaVis/PLPScatter.svelte";
  import Ridgeline from "$lib/CarlVis/Ridgeline.svelte";
  import ParallelCoords from "$lib/CarlVis/ParallelCoords.svelte";
  import SplitGenreReviews from "$lib/CarlVis/SplitGenreReviews.svelte";
  import PriceTrend from "$lib/CarlVis/PriceTrend.svelte";
  import Glyphs from "$lib/EricVis/Glyphs.svelte";
  import type { SteamGame } from "../types";

  let games: SteamGame[] = $state([]);

  const parseList = (value: string | undefined) =>
    value
      ?.split(",")
      .map((item) => item.trim())
      .filter(Boolean) ?? [];

  const parseBoolean = (value: string | undefined) =>
    value?.toLowerCase() === "true";

  const parseNumber = (value: string | undefined) => {
    if (!value?.trim()) return null;
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  };

  const parseRequiredNumber = (value: string | undefined) =>
    parseNumber(value) ?? 0;

  const parseDate = (value: string | undefined) => {
    if (!value?.trim()) return null;
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
  };

  onMount(async () => {
    games = await d3.csv('/steam_top_games_2026-selected-columns.csv', (row) => ({
      app_id: parseRequiredNumber(row.app_id),
      name: row.name ?? 'Unnamed game',
      release_date: parseDate(row.release_date),
      coming_soon: parseBoolean(row.coming_soon),
      price_usd: parseRequiredNumber(row.price_usd),
      is_free: parseBoolean(row.is_free),
      discount_pct: parseRequiredNumber(row.discount_pct),
      developer: row.developer ?? 'Unknown developer',
      publisher: row.publisher ?? 'Unknown publisher',
      genres: parseList(row.genres),
      categories: parseList(row.categories),
      tags: parseList(row.tags),
      platforms_win: parseBoolean(row.platforms_win),
      platforms_mac: parseBoolean(row.platforms_mac),
      platforms_linux: parseBoolean(row.platforms_linux),
      metacritic_score: parseNumber(row.metacritic_score),
      recommendations: parseRequiredNumber(row.recommendations),
      positive_reviews: parseRequiredNumber(row.positive_reviews),
      negative_reviews: parseRequiredNumber(row.negative_reviews),
      estimated_owners: row.estimated_owners ?? '',
      avg_playtime_forever: parseRequiredNumber(row.avg_playtime_forever),
      avg_playtime_2weeks: parseRequiredNumber(row.avg_playtime_2weeks),
      median_playtime: parseRequiredNumber(row.median_playtime),
      peak_ccu: parseRequiredNumber(row.peak_ccu),
      required_age: parseRequiredNumber(row.required_age),
      dlc_count: parseRequiredNumber(row.dlc_count),
      achievements: parseRequiredNumber(row.achievements),
      short_description: row.short_description ?? '',
      header_image: row.header_image ?? '',
      price_no_sales: parseRequiredNumber(row.price_usd)  / (1 - parseRequiredNumber(row.discount_pct) / 100)
    })) as SteamGame[];
  });
</script>

<main class="grid">
  <Bar {games} />
  <Bump {games} />
  <Heatmap {games} />
  <Ridgeline {games} />
  <ParallelCoords {games} />
  <SplitGenreReviews {games} />
  <PriceTrend {games} />
  <GPHeatmap {games} />
  <PLPScatter {games} />
  <Glyphs {games} />
</main>
