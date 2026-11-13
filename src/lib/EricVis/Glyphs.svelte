<script lang='ts'>
  import type { SteamGame } from '../../types';

  type Props = { games: SteamGame[] };
  type Group = 'AAA' | 'Indie';
  type MetricKey = 'playtimeSkew' | 'criticDisconnect' | 'value' | 'dlc' | 'discount';
  type Metric = { key: MetricKey; label: string; shortLabel: string };
  type MetricValues = Record<MetricKey, number | null>;
  type Glyph = { key: string; company: string; group: Group; game: SteamGame; metrics: MetricValues; slot: number; slotCount: number };
  type Scale = { low: number; high: number; usable: boolean };

  let { games }: Props = $props();
  const AAA_COMPANIES = ['CAPCOM', 'Valve', 'Ubisoft Montreal', 'Square Enix', 'SEGA', 'FromSoftware', 'Techland'];
  const INDIE_COMPANIES = ['Supergiant Games', 'Klei Entertainment', 'Rusty Lake', 'Fireproof Games', 'Croteam', 'Red Barrels', 'Tripwire Interactive'];
  const GROUPS: { name: Group; companies: string[] }[] = [{ name: 'AAA', companies: AAA_COMPANIES }, { name: 'Indie', companies: INDIE_COMPANIES }];
  const ALL_COMPANIES = GROUPS.flatMap((group) => group.companies);
  const COMPANY_GROUP = new Map<string, Group>([
    ...AAA_COMPANIES.map((company) => [company, 'AAA' as Group] as const),
    ...INDIE_COMPANIES.map((company) => [company, 'Indie' as Group] as const),
  ]);
  const METRICS: Metric[] = [
    { key: 'playtimeSkew', label: 'Playtime Skew', shortLabel: 'Skew' },
    { key: 'criticDisconnect', label: 'User-critic Disconnect', shortLabel: 'Disconnect' },
    { key: 'value', label: 'Hours-per-Dollar Value', shortLabel: 'Value' },
    { key: 'dlc', label: 'DLC Count', shortLabel: 'DLC' },
    { key: 'discount', label: 'Discount', shortLabel: 'Discount' },
  ];
  const finite = (value: number | null | undefined) => value !== null && value !== undefined && Number.isFinite(value) ? value : null;
  const totalReviews = (game: SteamGame) => game.positive_reviews + game.negative_reviews;
  const formatNumber = (value: number | null, digits = 1) => value === null || !Number.isFinite(value) ? 'N/A' : value.toLocaleString(undefined, { maximumFractionDigits: digits });
  const formatPercent = (value: number | null) => value === null || !Number.isFinite(value) ? 'N/A' : `${formatNumber(value)}%`;
  const formatPrice = (game: SteamGame) => game.is_free || game.price_usd <= 0 ? '$0.00 (free)' : `$${game.price_usd.toFixed(2)}`;
  const basePriceFor = (game: SteamGame) => game.discount_pct < 100 ? finite(game.price_usd / (1 - game.discount_pct / 100)) : null;
  const hoursPerDollar = (game: SteamGame) => { const base = basePriceFor(game); return game.median_playtime > 0 && game.price_usd > 0 && base !== null ? finite(game.median_playtime / 60 / base) : null; };
  const formatHoursPerDollar = (game: SteamGame) => { const value = hoursPerDollar(game); return value === null ? 'N/A' : `${formatNumber(value, 2)} hours/dollar`; };
  const formatDate = (game: SteamGame) => game.release_date?.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' }) ?? 'Unknown date';
  const normalizedCompany = (value: string) => {
    const normalized = value.trim().toLowerCase();
    if (normalized === 'capcom co., ltd.' || normalized === 'capcom co., ltd' || normalized === 'capcom') return 'CAPCOM';
    if (normalized.startsWith('ubisoft montreal')) return 'Ubisoft Montreal';
    if (normalized.startsWith('square enix')) return 'Square Enix';
    if (normalized.includes('fromsoftware')) return 'FromSoftware';
    return ALL_COMPANIES.find((company) => company.toLowerCase() === normalized) ?? null;
  };
  const gameMetrics = (game: SteamGame): MetricValues => {
    const reviews = totalReviews(game); const base = basePriceFor(game);
    return {
      playtimeSkew: game.median_playtime > 0 ? finite((game.avg_playtime_forever / game.median_playtime) * 100) : null,
      criticDisconnect: game.metacritic_score !== null && reviews > 0 ? finite(100 - (game.metacritic_score - (game.positive_reviews / reviews) * 100)) : null,
      value: game.median_playtime > 0 && game.price_usd > 0 && base !== null ? finite((game.median_playtime / base) * 100) : null,
      dlc: finite(game.dlc_count), discount: finite(game.discount_pct),
    };
  };
  const eligibleMetrics = (game: SteamGame) => {
    const metrics = gameMetrics(game);
    return game.release_date !== null && metrics.playtimeSkew !== null && metrics.value !== null && metrics.dlc !== null && metrics.discount !== null;
  };

  const subset = $derived(games.filter((game) => eligibleMetrics(game) && normalizedCompany(game.developer) !== null).map((game) => ({ game, company: normalizedCompany(game.developer)! })));
  const summaries = $derived.by(() => {
    const candidates = new Map<string, SteamGame[]>();
    subset.forEach(({ game, company }) => candidates.set(company, [...(candidates.get(company) ?? []), game]));
    return ALL_COMPANIES.flatMap((company) => {
      const selectedGames = (candidates.get(company) ?? [])
        .sort((first, second) => totalReviews(second) - totalReviews(first) || (second.release_date?.getTime() ?? 0) - (first.release_date?.getTime() ?? 0) || first.name.localeCompare(second.name))
        .slice(0, 6);
      return selectedGames.map((game, slot): Glyph => ({ key: `${company}|${game.app_id}`, company, group: COMPANY_GROUP.get(company)!, game, metrics: gameMetrics(game), slot, slotCount: selectedGames.length }));
    });
  });
  const summaryByKey = $derived(new Map(summaries.map((summary) => [summary.key, summary])));
  const percentile = (values: number[], probability: number) => {
    if (!values.length) return null;
    const sorted = [...values].sort((first, second) => first - second);
    const index = (sorted.length - 1) * probability;
    const lower = Math.floor(index); const upper = Math.ceil(index);
    return sorted[lower] + (sorted[upper] - sorted[lower]) * (index - lower);
  };
  const scales = $derived.by(() => Object.fromEntries(METRICS.map(({ key }) => {
    const values = summaries.map((summary) => summary.metrics[key]).filter((value): value is number => value !== null);
    const low = percentile(values, 0.05); const high = percentile(values, 0.95);
    return [key, { low: low ?? 0, high: high ?? 0, usable: low !== null && high !== null && high > low }];
  })) as Record<MetricKey, Scale>);

  const width = 1540; const height = 650;
  const margin = { top: 50, right: 24, bottom: 102, left: 74 };
  const plotWidth = width - margin.left - margin.right; const plotHeight = height - margin.top - margin.bottom;
  const columnWidth = plotWidth / ALL_COMPANIES.length; const rowHeight = plotHeight / 6;
  const maxRadius = Math.min(rowHeight * 0.34, columnWidth * 0.3); const minRadius = 6;
  let selectedKeys = $state<string[]>([]); let replacementSlot = $state(0);
  let hoveredKey = $state<string | null>(null); let showFormulas = $state(false);
  const selected = $derived(selectedKeys.map((key) => summaryByKey.get(key)).filter((value): value is Glyph => value !== undefined));
  const hasMatches = $derived(subset.length > 0);
  const radiusFor = (glyph: Glyph, key: MetricKey, radius = maxRadius) => {
    const value = glyph.metrics[key]; const scale = scales[key];
    if (value === null || !scale.usable) return null;
    const normalized = Math.max(0, Math.min(1, (value - scale.low) / (scale.high - scale.low)));
    return minRadius + normalized * (radius - minRadius);
  };
  const pointsFor = (glyph: Glyph, radius = maxRadius) => METRICS.map((metric, index) => {
    const pointRadius = radiusFor(glyph, metric.key, radius); if (pointRadius === null) return null;
    const angle = (-90 + index * 72) * Math.PI / 180;
    return `${Math.cos(angle) * pointRadius},${Math.sin(angle) * pointRadius}`;
  }).filter((point): point is string => point !== null).join(' ');
  const isSelected = (key: string) => selectedKeys.includes(key);
  const activate = (glyph: Glyph) => {
    const existingIndex = selectedKeys.indexOf(glyph.key);
    if (existingIndex >= 0) { selectedKeys = selectedKeys.filter((key) => key !== glyph.key); return; }
    if (selectedKeys.length < 2) { selectedKeys = [...selectedKeys, glyph.key]; return; }
    const nextKeys = [...selectedKeys]; nextKeys[replacementSlot] = glyph.key;
    selectedKeys = nextKeys; replacementSlot = replacementSlot === 0 ? 1 : 0;
  };
  const onKeydown = (event: KeyboardEvent, glyph: Glyph) => {
    if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); activate(glyph); }
  };
  const clearSelection = () => { selectedKeys = []; replacementSlot = 0; };
  const toggleFormulaReference = () => { showFormulas = !showFormulas; };
  const companyX = (index: number) => margin.left + index * columnWidth + columnWidth / 2;
  const slotY = (slot: number, slotCount = 6) => margin.top + (6 - slotCount + slot) * rowHeight + rowHeight / 2;
  const metricDisplay = (value: number | null, key: MetricKey) => key === 'discount' || key === 'criticDisconnect' || key === 'playtimeSkew' ? formatPercent(value) : formatNumber(value, 1);
</script>

<section class=glyphs aria-labelledby=glyph-title>
  <h2 id=glyph-title>Selected games by AAA and indie company</h2>
  <p class=subtitle>Each column shows up to six complete games, ordered from most reviewed at the top to least reviewed at the bottom.</p>
  {#if games.length === 0}<p class=empty-state>Loading Steam game data...</p>{:else if !hasMatches}<p class=empty-state>No eligible games from the selected companies were found in the dataset.</p>{:else}
    <div class='visual-row'><div class='chart-panel'>
      <svg viewBox='0 0 1540 650' role='img' aria-label='Pentagon glyph chart comparing selected games per company'>
        <title>Selected games by AAA and indie company</title>
        <text class='axis-label' transform='translate(18 315) rotate(-90)' text-anchor='middle'>Games ordered by total reviews</text>
        {#each Array(6) as _, slot}<line class='row-guide' x1={margin.left} x2={width - margin.right} y1={slotY(slot) + rowHeight / 2} y2={slotY(slot) + rowHeight / 2} />{/each}
        {#each ALL_COMPANIES as company, index}
          {@const x = companyX(index)}
          <line class='column-guide' x1={x} x2={x} y1={margin.top} y2={margin.top + plotHeight} />
          <text class={`company-label ${COMPANY_GROUP.get(company)?.toLowerCase()}`} transform={`translate(${x - 3} ${height - 48}) rotate(-52)`} text-anchor='end'>{company}</text>
          {#if index === AAA_COMPANIES.length - 1}<line class='group-divider' x1={x + columnWidth / 2} x2={x + columnWidth / 2} y1={margin.top - 12} y2={margin.top + plotHeight + 12} />{/if}
        {/each}
        {#each summaries as glyph}
          {@const index = ALL_COMPANIES.indexOf(glyph.company)}{@const x = companyX(index)}{@const y = slotY(glyph.slot, glyph.slotCount)}{@const key = glyph.key}{@const points = pointsFor(glyph)}
          <g class:active={isSelected(key) || hoveredKey === key} class:dimmed={selectedKeys.length > 0 && !isSelected(key)}>
            <title>{glyph.game.name}, {glyph.company}, {formatDate(glyph.game)}</title>
            {#if points.split(' ').length >= 3}<polygon class={`glyph ${glyph.group.toLowerCase()}`} points={points} transform={`translate(${x} ${y})`} />{/if}
            {#each METRICS as metric, metricIndex}{@const radius = radiusFor(glyph, metric.key)}{#if radius !== null}{@const angle = (-90 + metricIndex * 72) * Math.PI / 180}<circle class='vertex' cx={x + Math.cos(angle) * radius} cy={y + Math.sin(angle) * radius} r='1.8' />{/if}{/each}
            <rect class='hit-target' x={x - columnWidth * 0.42} y={y - rowHeight / 2} width={columnWidth * 0.84} height={rowHeight} tabindex='0' role='button' aria-pressed={isSelected(key)} aria-label={glyph.game.name + ', ' + glyph.company + ', game slot ' + (glyph.slot + 1)} onclick={() => activate(glyph)} onkeydown={(event) => onKeydown(event, glyph)} onmouseenter={() => hoveredKey = key} onmouseleave={() => hoveredKey = null} onfocus={() => hoveredKey = key} onblur={() => hoveredKey = null} />
          </g>
        {/each}
      </svg>
    </div><div class='reference-panel'>
      <button class='reference-trigger' type='button' aria-expanded={showFormulas} aria-controls='glyph-formulas' onclick={toggleFormulaReference}>
        <span class='reference-heading'>Glyph metrics</span>
        <svg viewBox='0 0 280 215' role='img' aria-label='Reference glyph with metric labels'>
          <polygon class='reference-polygon' points='105,35 153,70 135,126 75,126 57,70' />
          <circle class='reference-point' cx='105' cy='35' r='3.5' /><circle class='reference-point' cx='153' cy='70' r='3.5' /><circle class='reference-point' cx='135' cy='126' r='3.5' /><circle class='reference-point' cx='75' cy='126' r='3.5' /><circle class='reference-point' cx='57' cy='70' r='3.5' />
          <text class='reference-label' x='105' y='19' text-anchor='middle'>Playtime Skew</text><text class='reference-label' x='164' y='68'>Disconnect</text><text class='reference-label' x='144' y='146'>Value</text><text class='reference-label' x='66' y='146' text-anchor='end'>DLC</text><text class='reference-label' x='45' y='68' text-anchor='end'>Discount</text>
        </svg>
        <span class='reference-hint'>Click to {showFormulas ? 'hide' : 'show'} formulas</span>
      </button>
      {#if showFormulas}<div id='glyph-formulas' class='formula-window' aria-live='polite'><p><strong>Playtime Skew:</strong> average / median playtime * 100.</p><p><strong>Disconnect:</strong> 100 - (metacritic - positive review share).</p><p><strong>Value:</strong> median playtime / base price.</p><p><strong>DLC:</strong> reported downloadable content count.</p><p><strong>Discount:</strong> current discount percentage.</p></div>{/if}
    </div></div>
    <div class='legend' aria-label='Company group legend'><span class='legend-item'><span class='swatch aaa'></span> AAA</span><span class='legend-item'><span class='swatch indie'></span> Indie</span><span>Click or focus a glyph to select it. Two selections open a comparison.</span></div>
    <div class='selection-status' aria-live='polite'>{#if selected.length === 0}No games selected.{:else if selected.length === 1}Selected {selected[0].game.name} from {selected[0].company}.{:else}Comparing {selected[0].game.name} and {selected[1].game.name}.{/if}</div>
    {#snippet gameDetail(glyph: Glyph, enlarged = false)}
      {@const game = glyph.game}
      <article class:enlarged-detail={enlarged} class='game-detail'>
        {#if enlarged}
          {@const points = pointsFor(glyph, 90)}
          <svg class='detail-glyph' viewBox='-110 -110 220 220' role='img' aria-label='Enlarged metric glyph'>
            {#if points.split(' ').length >= 3}<polygon class={`glyph ${glyph.group.toLowerCase()}`} points={points} />{/if}
            {#each METRICS as metric, metricIndex}{@const radius = radiusFor(glyph, metric.key, 90)}{#if radius !== null}{@const angle = (-90 + metricIndex * 72) * Math.PI / 180}<circle class='vertex' cx={Math.cos(angle) * radius} cy={Math.sin(angle) * radius} r='3' />{/if}{/each}
          </svg>
        {/if}
        <h4>{game.name}</h4>
        <p class='detail-meta'>{glyph.company} ({glyph.group}) · Released {formatDate(game)} · {formatNumber(totalReviews(game), 0)} total reviews</p>
        <span>Playtime Skew: {metricDisplay(glyph.metrics.playtimeSkew, 'playtimeSkew')} ({formatNumber(game.avg_playtime_forever / 60, 2)} hours average / {formatNumber(game.median_playtime / 60, 2)} hours median)</span>
        <span>User-critic Disconnect: {metricDisplay(glyph.metrics.criticDisconnect, 'criticDisconnect')} ({game.metacritic_score === null ? 'N/A' : formatNumber(game.metacritic_score, 0) + ' metacritic'} · {formatNumber(game.positive_reviews, 0)} positive / {formatNumber(game.negative_reviews, 0)} negative reviews)</span>
        <span>Hours-per-Dollar Value: {formatHoursPerDollar(game)} ({formatNumber(game.median_playtime / 60, 2)} hours median / {basePriceFor(game) === null ? 'N/A' : '$' + formatNumber(basePriceFor(game), 2) + ' base price'})</span>
        <span>DLC Count: {metricDisplay(glyph.metrics.dlc, 'dlc')}</span><span>Discounted Price: {formatPrice(game)} · Discount: {formatPercent(glyph.metrics.discount)}</span>
      </article>
    {/snippet}
    {#if selected.length === 1}
      <aside class='details' aria-labelledby='selected-heading'><div class='details-heading-row'><div><h3 id='selected-heading'>Selected game details</h3><p>All five plotted metrics and their raw inputs are shown below.</p></div><button class='clear-button' type='button' onclick={clearSelection}>Clear selection</button></div>{@render gameDetail(selected[0])}</aside>
    {:else if selected.length === 2}
      <aside class='details comparison' aria-labelledby='comparison-heading'><div class='details-heading-row'><div><h3 id='comparison-heading'>Glyph comparison</h3><p>Selected games are shown side by side using the same metric scales.</p></div><button class='clear-button' type='button' onclick={clearSelection}>Clear comparison</button></div><div class='comparison-grid'>{@render gameDetail(selected[0], true)}{@render gameDetail(selected[1], true)}</div></aside>
    {/if}
  {/if}
</section>

<style>
  .glyphs{min-width:0}h2{margin-bottom:.2rem}.subtitle,.details p,.legend,.selection-status{color:#64748b;font-size:.82rem}svg{display:block;max-width:100%;height:auto;overflow:visible}.axis-label,.group-label{fill:#475569;font-size:11px;font-weight:600}.tick-label,.company-label{fill:#64748b;font-size:10px}.company-label{font-weight:600}.company-label.aaa,.aaa-group{fill:#075985}.company-label.indie,.indie-group{fill:#9a3412}.column-guide,.row-guide{stroke:#e2e8f0;stroke-width:1}.group-divider{stroke:#64748b;stroke-width:2}.glyph{fill-opacity:.65;stroke:#1e293b;stroke-width:1.25;transition:opacity 120ms ease,stroke-width 120ms ease}.glyph.aaa{fill:#0284c7}.glyph.indie{fill:#ea580c}.vertex{fill:#fff;stroke:#1e293b;stroke-width:1;pointer-events:none}.hit-target{fill:transparent;cursor:pointer;outline:none}g.active .glyph{fill-opacity:.9;stroke-width:2.5}g.active .hit-target:focus{stroke:#0f172a;stroke-width:2;stroke-dasharray:3 2}g.dimmed{opacity:.25}
  .legend{display:flex;flex-wrap:wrap;gap:.5rem 1rem;align-items:center;margin-top:.45rem}.legend-item{display:inline-flex;align-items:center;gap:.3rem}.swatch{width:.75rem;height:.75rem;border:1px solid #1e293b;display:inline-block}.swatch.aaa{background:#0284c7}.swatch.indie{background:#ea580c}.visual-row{display:grid;grid-template-columns:minmax(0,1fr) minmax(15rem,18rem);gap:1rem;align-items:start}.chart-panel{min-width:0;overflow:visible}.chart-panel svg{width:100%;max-width:100%;height:auto}.reference-panel{min-width:0;padding:.65rem;border:1px solid #e2e8f0;background:#fff}.reference-trigger{display:block;width:100%;padding:0;border:0;background:transparent;color:inherit;cursor:pointer;text-align:left}.reference-trigger:focus-visible{outline:2px solid #0f172a;outline-offset:3px}.reference-heading{display:block;margin-bottom:.3rem;color:#0f172a;font-size:.9rem;font-weight:700}.reference-trigger svg{display:block;width:100%;height:auto}.reference-polygon{fill:#dbeafe;stroke:#1e293b;stroke-width:2}.reference-point{fill:#0284c7;stroke:#fff;stroke-width:2}.reference-label{fill:#475569;font-size:10px}.reference-hint{display:block;margin-top:.25rem;color:#64748b;font-size:.75rem}.formula-window{margin-top:.55rem;padding:.5rem;border-top:1px solid #e2e8f0;color:#475569;font-size:.72rem}.formula-window p{margin:.25rem 0}.formula-window strong{color:#0f172a}
  .selection-status{margin-top:.6rem}.details{margin-top:.75rem;padding:.65rem .8rem;border-left:3px solid #94a3b8;background:#f8fafc;min-height:4rem}.details h3{margin:0;color:#0f172a}.details p{margin:.2rem 0 .55rem}.details-heading-row{display:flex;justify-content:space-between;gap:1rem;align-items:start}.clear-button{flex:none;padding:.35rem .55rem;border:1px solid #94a3b8;background:#fff;color:#334155;cursor:pointer}.clear-button:focus-visible{outline:2px solid #0f172a;outline-offset:2px}.comparison-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.75rem}.game-detail{display:grid;gap:.12rem;padding:.5rem;background:#fff;border:1px solid #e2e8f0;color:#475569;font-size:.78rem}.game-detail h4{margin:0 0 .15rem;color:#0f172a;font-size:.88rem}.detail-meta{color:#64748b}.detail-glyph{width:210px;height:210px;margin:0 auto .25rem}.empty-state{padding:1rem;background:#f8fafc;color:#64748b}@media(max-width:760px){.visual-row{grid-template-columns:1fr}.reference-panel{max-width:22rem}.comparison-grid{grid-template-columns:1fr}.details-heading-row{flex-direction:column}}
</style>
