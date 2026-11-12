<script lang="ts">
  import type { SteamGame } from '../../types';

  type Props = { games: SteamGame[] };
  type Group = 'AAA' | 'Indie';
  type MetricKey = 'playtimeSkew' | 'criticDisconnect' | 'value' | 'dlc' | 'discount';
  type Metric = { key: MetricKey; label: string; shortLabel: string };
  type MetricValues = Record<MetricKey, number | null>;
  type GameMetrics = MetricValues & { game: SteamGame };
  type Summary = {
    key: string;
    company: string;
    group: Group;
    year: number;
    games: SteamGame[];
    metrics: MetricValues;
    slot: number;
    slotCount: number;
  };
  type Scale = { low: number; high: number; usable: boolean };

  let { games }: Props = $props();

  const AAA_COMPANIES = ['Valve', 'Ubisoft Montreal', 'Square Enix', 'CAPCOM', 'SEGA'];
  const INDIE_COMPANIES = ['Supergiant Games', 'Klei Entertainment', 'Scott Cawthon', 'Motion Twin', 'Rusty Lake'];
  const GROUPS: { name: Group; companies: string[] }[] = [
    { name: 'AAA', companies: AAA_COMPANIES },
    { name: 'Indie', companies: INDIE_COMPANIES },
  ];
  const METRICS: Metric[] = [
    { key: 'playtimeSkew', label: 'Playtime Skew', shortLabel: 'Skew' },
    { key: 'criticDisconnect', label: 'User-critic Disconnect', shortLabel: 'Disconnect' },
    { key: 'value', label: 'Hours-per-Dollar Value', shortLabel: 'Value' },
    { key: 'dlc', label: 'DLC Count', shortLabel: 'DLC' },
    { key: 'discount', label: 'Discount', shortLabel: 'Discount' },
  ];
  const ALL_COMPANIES = GROUPS.flatMap((group) => group.companies);
  const COMPANY_GROUP = new Map<string, Group>([
    ...AAA_COMPANIES.map((company) => [company, 'AAA' as Group] as const),
    ...INDIE_COMPANIES.map((company) => [company, 'Indie' as Group] as const),
  ]);
  const normalizedCompany = (value: string) => {
    const normalized = value.trim().toLowerCase();
    if (normalized === 'capcom co., ltd.' || normalized === 'capcom co., ltd' || normalized === 'capcom') return 'CAPCOM';
    return ALL_COMPANIES.find((company) => company.toLowerCase() === normalized) ?? null;
  };
  const finite = (value: number | null | undefined) => (value !== null && value !== undefined && Number.isFinite(value) ? value : null);
  const totalReviews = (game: SteamGame) => game.positive_reviews + game.negative_reviews;
  const formatNumber = (value: number | null, digits = 1) => value === null || !Number.isFinite(value) ? 'N/A' : value.toLocaleString(undefined, { maximumFractionDigits: digits });
  const formatPercent = (value: number | null) => value === null || !Number.isFinite(value) ? 'N/A' : `${formatNumber(value)}%`;
  const formatPrice = (game: SteamGame) => game.is_free || game.price_usd <= 0 ? '$0.00 (free)' : `$${game.price_usd.toFixed(2)}`;
  const basePriceFor = (game: SteamGame) => game.discount_pct < 100 ? finite(game.price_usd / (1 - game.discount_pct / 100)) : null;
  const hoursPerDollar = (game: SteamGame) => {
    const basePrice = basePriceFor(game);
    return game.median_playtime > 0 && game.price_usd > 0 && basePrice !== null
      ? finite(game.median_playtime / 60 / basePrice)
      : null;
  };
  const formatHoursPerDollar = (game: SteamGame) => {
    const value = hoursPerDollar(game);
    return value === null ? 'N/A' : `${formatNumber(value, 2)} hours/dollar`;
  };
  const yearOf = (game: SteamGame) => game.release_date?.getFullYear() ?? null;

  const gameMetrics = (game: SteamGame): GameMetrics => {
    const reviews = totalReviews(game);
    const basePrice = basePriceFor(game);
    return {
      game,
      playtimeSkew: game.median_playtime > 0 ? finite((game.avg_playtime_forever / game.median_playtime) * 100) : null,
      criticDisconnect: game.metacritic_score !== null && reviews > 0
        ? finite(100 - (game.metacritic_score - (game.positive_reviews / reviews) * 100))
        : null,
      value: game.median_playtime > 0 && game.price_usd > 0 && basePrice !== null
        ? finite((game.median_playtime / basePrice) * 100)
        : null,
      dlc: finite(game.dlc_count),
      discount: finite(game.discount_pct),
    };
  };

  const subset = $derived(
    games
      .filter((game) => yearOf(game) !== null && yearOf(game)! >= 2010 && normalizedCompany(game.developer) !== null)
      .map((game) => ({ game, company: normalizedCompany(game.developer)! }))
  );
  const latestYear = $derived(Math.max(2010, ...games.map((game) => yearOf(game) ?? 2010)));
  const years = $derived(Array.from({ length: Math.max(0, latestYear - 2010 + 1) }, (_, index) => 2010 + index));
  const summaries = $derived.by(() => {
    const byCell = new Map<string, SteamGame[]>();
    subset.forEach(({ game, company }) => {
      const year = yearOf(game)!;
      const key = `${company}|${year}`;
      byCell.set(key, [...(byCell.get(key) ?? []), game]);
    });
    return ALL_COMPANIES.flatMap((company) => years.flatMap((year): Summary[] => {
      const cellGames = byCell.get(`${company}|${year}`) ?? [];
      return cellGames.map((game, slot): Summary => ({
        key: `${company}|${year}|${game.app_id}`,
        company,
        group: COMPANY_GROUP.get(company)!,
        year,
        games: [game],
        metrics: gameMetrics(game),
        slot,
        slotCount: cellGames.length,
      }));
    }));
  });
  const summaryByKey = $derived(new Map(summaries.map((summary) => [summary.key, summary])));
  const percentile = (values: number[], probability: number) => {
    if (!values.length) return null;
    const sorted = [...values].sort((a, b) => a - b);
    const index = (sorted.length - 1) * probability;
    const lower = Math.floor(index);
    const upper = Math.ceil(index);
    return sorted[lower] + (sorted[upper] - sorted[lower]) * (index - lower);
  };
  const scales = $derived.by(() => Object.fromEntries(METRICS.map(({ key }) => {
    const values = summaries.map((summary) => summary.metrics[key]).filter((value): value is number => value !== null);
    const low = percentile(values, 0.05);
    const high = percentile(values, 0.95);
    return [key, { low: low ?? 0, high: high ?? 0, usable: low !== null && high !== null && high > low }];
  })) as Record<MetricKey, Scale>);

  const width = 1180;
  const height = 570;
  const margin = { top: 65, right: 22, bottom: 52, left: 155 };
  const plotWidth = width - margin.left - margin.right;
  const rowHeight = 38;
  const plotHeight = rowHeight * ALL_COMPANIES.length;
  const cellWidth = $derived(plotWidth / Math.max(years.length, 1));
  const maxRadius = $derived(Math.min(rowHeight * 0.42, cellWidth * 0.38));
  const minRadius = 5;
  let selectedKey = $state<string | null>(null);
  let hoveredKey = $state<string | null>(null);
  let showFormulas = $state(false);
  const selected = $derived(selectedKey ? summaryByKey.get(selectedKey) ?? null : null);
  const hasMatches = $derived(subset.length > 0);
  const radiusFor = (summary: Summary, key: MetricKey) => {
    const value = summary.metrics[key];
    const scale = scales[key];
    if (value === null || !scale.usable) return null;
    const normalized = Math.max(0, Math.min(1, (value - scale.low) / (scale.high - scale.low)));
    return minRadius + normalized * (maxRadius - minRadius);
  };
  const pointsFor = (summary: Summary) => METRICS
    .map((metric, index) => {
      const radius = radiusFor(summary, metric.key);
      if (radius === null) return null;
      const angle = (-90 + index * 72) * Math.PI / 180;
      return `${Math.cos(angle) * radius},${Math.sin(angle) * radius}`;
    })
    .filter((point): point is string => point !== null)
    .join(' ');
  const activate = (summary: Summary) => {
    if (summary.games.length) {
      selectedKey = selectedKey === summary.key ? null : summary.key;
    }
  };
  const onKeydown = (event: KeyboardEvent, summary: Summary) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      activate(summary);
    }
  };
  const toggleFormulaReference = () => {
    showFormulas = !showFormulas;
  };
  const yearX = (year: number) => margin.left + (year - 2010) * cellWidth + cellWidth / 2;
  const companyY = (index: number) => margin.top + index * rowHeight + rowHeight / 2;
  const glyphX = (summary: Summary) => {
    const spacing = Math.min(cellWidth / Math.max(summary.slotCount, 1), maxRadius * 2.1);
    return yearX(summary.year) + (summary.slot - (summary.slotCount - 1) / 2) * spacing;
  };
  const hitWidth = (summary: Summary) => Math.min(cellWidth / Math.max(summary.slotCount, 1), maxRadius * 2.1);
  const metricDisplay = (value: number | null, key: MetricKey) => key === 'discount' || key === 'criticDisconnect' || key === 'playtimeSkew' ? formatPercent(value) : formatNumber(value, 1);
</script>

<section class="glyphs" aria-labelledby="glyph-title">
  <h2 id="glyph-title">AAA and indie releases over time</h2>
  <p class="subtitle">Each pentagon summarizes a company’s releases in one year using median metric values.</p>
  {#if games.length === 0}
    <p class="empty-state">Loading Steam game data…</p>
  {:else if !hasMatches}
    <p class="empty-state">No releases from the selected companies were found in the dataset.</p>
  {:else}
    <div class="visual-row">
      <div class="chart-panel">
        <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Pentagon glyph chart comparing selected AAA and indie developers from 2010 through {latestYear}">
          <title>AAA and indie releases from 2010 through {latestYear}</title>
          <text class="axis-label" x={margin.left + plotWidth / 2} y="20" text-anchor="middle">Release year</text>
          {#each years as year}
            <line class="year-guide" x1={yearX(year)} x2={yearX(year)} y1={margin.top - 8} y2={margin.top + plotHeight} />
            <text class="tick-label" x={yearX(year)} y={margin.top - 16} text-anchor="middle">{year}</text>
          {/each}
          {#each ALL_COMPANIES as company, index}
            <line class="row-guide" x1={margin.left} x2={width - margin.right} y1={companyY(index) + rowHeight / 2} y2={companyY(index) + rowHeight / 2} />
            <text class={`company-label ${COMPANY_GROUP.get(company)?.toLowerCase()}`} x={margin.left - 12} y={companyY(index) + 4} text-anchor="end">{company}</text>
            {#if index === AAA_COMPANIES.length - 1}
              <line class="group-divider" x1={margin.left - 8} x2={width - margin.right} y1={margin.top + (index + 1) * rowHeight} y2={margin.top + (index + 1) * rowHeight} />
            {/if}
          {/each}
          {#each summaries as summary}
            {@const index = ALL_COMPANIES.indexOf(summary.company)}
            {@const x = glyphX(summary)}
            {@const y = companyY(index)}
            {#if summary.games.length > 0}
              {@const key = summary.key}
              {@const points = pointsFor(summary)}
              <g class:active={selectedKey === key || hoveredKey === key} class:dimmed={selectedKey !== null && selectedKey !== key}>
                <title>{summary.games[0].name}, {summary.company}, {summary.year}</title>
                {#if points.split(' ').length >= 3}<polygon class={`glyph ${summary.group.toLowerCase()}`} points={points} transform={`translate(${x} ${y})`} />{/if}
                {#each METRICS as metric, metricIndex}
                  {@const radius = radiusFor(summary, metric.key)}
                  {#if radius !== null}
                    {@const angle = (-90 + metricIndex * 72) * Math.PI / 180}
                    <circle class="vertex" cx={x + Math.cos(angle) * radius} cy={y + Math.sin(angle) * radius} r="1.8" />
                  {/if}
                {/each}
                <rect class="hit-target" x={x - hitWidth(summary) / 2} y={y - rowHeight / 2} width={hitWidth(summary)} height={rowHeight} tabindex="0" role="button" aria-label={`${summary.games[0].name}, ${summary.company}, ${summary.year}`} onclick={() => activate(summary)} onkeydown={(event) => onKeydown(event, summary)} onmouseenter={() => hoveredKey = key} onmouseleave={() => hoveredKey = null} onfocus={() => hoveredKey = key} onblur={() => hoveredKey = null} />
              </g>
            {/if}
          {/each}
        </svg>
      </div>
      <div class="reference-panel">
        <button class="reference-trigger" type="button" aria-expanded={showFormulas} aria-controls="glyph-formulas" onclick={toggleFormulaReference}>
          <span class="reference-heading">Glyph metrics</span>
          <svg viewBox="0 0 280 215" role="img" aria-label="Reference glyph with each vertex labeled by its metric">
            <polygon class="reference-polygon" points="105,35 153,70 135,126 75,126 57,70" />
            <circle class="reference-point" cx="105" cy="35" r="3.5" />
            <circle class="reference-point" cx="153" cy="70" r="3.5" />
            <circle class="reference-point" cx="135" cy="126" r="3.5" />
            <circle class="reference-point" cx="75" cy="126" r="3.5" />
            <circle class="reference-point" cx="57" cy="70" r="3.5" />
            <text class="reference-label" x="105" y="19" text-anchor="middle">Playtime Skew</text>
            <text class="reference-label" x="164" y="68">User-critic Disconnect</text>
            <text class="reference-label" x="144" y="146">Hours-per-Dollar Value</text>
            <text class="reference-label" x="66" y="146" text-anchor="end">DLC Count</text>
            <text class="reference-label" x="47" y="68" text-anchor="end">Discount</text>
          </svg>
          <span class="reference-hint">Click to {showFormulas ? 'hide' : 'show'} formulas</span>
        </button>
        {#if showFormulas}
          <div id="glyph-formulas" class="formula-window" aria-label="Glyph metric formulas">
            <p><strong>Playtime Skew</strong> = avg_playtime_forever / median_playtime × 100</p>
            <p><strong>User-critic Disconnect</strong> = 100 − (metacritic_score − positive_reviews / total_reviews × 100)</p>
            <p><strong>Hours-per-Dollar Value</strong> = median_playtime / base_price_usd × 100 for glyph scaling; details show hours/dollar</p>
            <p><strong>DLC Count</strong> = dlc_count</p>
            <p><strong>Discount</strong> = discount_pct</p>
          </div>
        {/if}
      </div>
    </div>
    <div class="legend" aria-label="Chart legend">
      <span class="legend-item"><span class="swatch aaa"></span> AAA</span>
      <span class="legend-item"><span class="swatch indie"></span> Indie</span>
    </div>
    <aside class="details" aria-live="polite" aria-label="Selected company-year details">
      {#if selected}
        <h3>{selected.company} · {selected.year}</h3>
        <p>{selected.games.length} release{selected.games.length === 1 ? '' : 's'} · Values below are calculated per game.</p>
        <div class="game-list">
          {#each selected.games as game}
            {@const metrics = gameMetrics(game)}
            <article class="game-detail">
              <h4>{game.name}</h4>
              <span>Release date: {game.release_date?.toLocaleDateString() ?? 'N/A'}</span>
              <span>Playtime Skew: {metricDisplay(metrics.playtimeSkew, 'playtimeSkew')} ({formatNumber(game.avg_playtime_forever, 0)} min avg / {formatNumber(game.median_playtime, 0)} min median)</span>
              <span>User-critic Disconnect: {metricDisplay(metrics.criticDisconnect, 'criticDisconnect')} ({game.metacritic_score === null ? 'N/A' : `${formatNumber(game.metacritic_score, 0)} metacritic`} · {formatNumber(game.positive_reviews, 0)} positive / {formatNumber(game.negative_reviews, 0)} negative reviews)</span>
              <span>Hours-per-Dollar Value: {formatHoursPerDollar(game)} ({formatNumber(game.median_playtime / 60, 2)} hours median / {basePriceFor(game) === null ? 'N/A' : `$${formatNumber(basePriceFor(game), 2)} base price`})</span>
              <span>DLC Count: {metricDisplay(metrics.dlc, 'dlc')}</span>
              <span>Discounted Price: {formatPrice(game)} · Discount: {formatPercent(metrics.discount)}</span>
            </article>
          {/each}
        </div>
      {:else}
        <p>Select a glyph to inspect every game included in its company-year summary.</p>
      {/if}
    </aside>
  {/if}
</section>

<style>
  .glyphs { min-width: 0; }
  h2 { margin-bottom: 0.2rem; }
  .subtitle, .details p, .legend, .metric-key { color: #64748b; font-size: 0.82rem; }
  svg { display: block; max-width: 100%; height: auto; overflow: visible; }
  .axis-label, .group-label { fill: #475569; font-size: 11px; font-weight: 600; }
  .tick-label, .company-label { fill: #64748b; font-size: 10px; }
  .company-label { font-weight: 600; }
  .company-label.aaa { fill: #075985; }
  .company-label.indie { fill: #9a3412; }
  .year-guide { stroke: #e2e8f0; stroke-width: 1; }
  .row-guide { stroke: #e2e8f0; stroke-width: 1; }
  .group-divider { stroke: #64748b; stroke-width: 2; }
  .glyph { fill-opacity: 0.65; stroke: #1e293b; stroke-width: 1.25; transition: opacity 120ms ease, stroke-width 120ms ease; }
  .glyph.aaa { fill: #0284c7; }
  .glyph.indie { fill: #ea580c; }
  .vertex { fill: #fff; stroke: #1e293b; stroke-width: 1; pointer-events: none; }
  .hit-target { fill: transparent; cursor: pointer; outline: none; }
  g.active .glyph { fill-opacity: 0.9; stroke-width: 2.5; }
  g.active .hit-target:focus { stroke: #0f172a; stroke-width: 2; stroke-dasharray: 3 2; }
  g.dimmed { opacity: 0.25; }
  .legend, .metric-key { display: flex; flex-wrap: wrap; gap: 0.5rem 1rem; align-items: center; margin-top: 0.45rem; }
  .legend-item { display: inline-flex; align-items: center; gap: 0.3rem; }
  .swatch { width: 0.75rem; height: 0.75rem; border: 1px solid #1e293b; display: inline-block; }
  .swatch.aaa { background: #0284c7; }
  .swatch.indie { background: #ea580c; }
  .visual-row { display: grid; grid-template-columns: minmax(0, 1fr) minmax(15rem, 18rem); gap: 1rem; align-items: start; }
  .chart-panel { min-width: 0; }
  .chart-panel svg { width: 100%; }
  .reference-panel { min-width: 0; padding: 0.65rem; border: 1px solid #e2e8f0; background: #fff; }
  .reference-trigger { display: block; width: 100%; padding: 0; border: 0; background: transparent; color: inherit; cursor: pointer; text-align: left; }
  .reference-trigger:focus-visible { outline: 2px solid #0f172a; outline-offset: 3px; }
  .reference-heading { display: block; margin-bottom: 0.3rem; color: #0f172a; font-size: 0.9rem; font-weight: 700; }
  .reference-trigger svg { display: block; width: 100%; height: auto; }
  .reference-polygon { fill: #dbeafe; stroke: #1e293b; stroke-width: 2; }
  .reference-point { fill: #0284c7; stroke: #fff; stroke-width: 2; }
  .reference-label { fill: #475569; font-size: 10px; }
  .reference-hint { display: block; margin-top: 0.25rem; color: #64748b; font-size: 0.75rem; }
  .formula-window { margin-top: 0.55rem; padding: 0.5rem; border-top: 1px solid #e2e8f0; color: #475569; font-size: 0.72rem; pointer-events: none; }
  .formula-window p { margin: 0.25rem 0; }
  .formula-window strong { color: #0f172a; }
  .details { margin-top: 0.75rem; padding: 0.65rem 0.8rem; border-left: 3px solid #94a3b8; background: #f8fafc; min-height: 4rem; }
  .details h3 { margin: 0; color: #0f172a; }
  .details p { margin: 0.2rem 0 0.55rem; }
  .game-list { display: grid; grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr)); gap: 0.55rem; }
  .game-detail { display: grid; gap: 0.12rem; padding: 0.5rem; background: #fff; border: 1px solid #e2e8f0; color: #475569; font-size: 0.78rem; }
  .game-detail h4 { margin: 0 0 0.15rem; color: #0f172a; font-size: 0.88rem; }
  .empty-state { padding: 1rem; background: #f8fafc; color: #64748b; }
  @media (max-width: 760px) {
    .visual-row { grid-template-columns: 1fr; }
    .reference-panel { max-width: 22rem; }
  }
</style>
