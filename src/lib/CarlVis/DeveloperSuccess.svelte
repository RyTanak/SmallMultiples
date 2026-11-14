<script lang="ts">
  import * as d3 from 'd3';
  import type { SteamGame } from '../../types';

  type Props = { games: SteamGame[]; width?: number };
  type Developer = { games: SteamGame[]; indieGames: SteamGame[]; successfulIndieGames: SteamGame[]; successfulGames: SteamGame[] };
  type BarDatum = { key: 'indie' | 'successfulIndie' | 'nonIndie' | 'successfulNonIndie'; label: string; value: number; studios: number; color: string };
  type PieDatum = { label: string; value: number; description: string };

  let { games, width = 1040 }: Props = $props();
  // Change this constant to adjust what counts as a successful game.
  const SUCCESS_REVIEW_THRESHOLD = 75_000;
  const barHeight = 350;
  const pieSize = 300;
  const margin = { top: 48, right: 28, bottom: 66, left: 72 };
  const totalReviews = (game: SteamGame) => game.positive_reviews + game.negative_reviews;
  const isIndie = (game: SteamGame) => [...game.genres, ...game.tags].some((value) => value.trim().toLowerCase() === 'indie');
  const isSuccessful = (game: SteamGame) => totalReviews(game) >= SUCCESS_REVIEW_THRESHOLD;

  const developers = $derived.by(() => {
    const grouped = new Map<string, Developer>();
    games.forEach((game) => {
      const key = (game.developer.trim() || 'Unknown developer').toLocaleLowerCase();
      const developer = grouped.get(key) ?? { games: [], indieGames: [], successfulIndieGames: [], successfulGames: [] };
      developer.games.push(game);
      if (isIndie(game)) developer.indieGames.push(game);
      if (isSuccessful(game)) developer.successfulGames.push(game);
      if (isIndie(game) && isSuccessful(game)) developer.successfulIndieGames.push(game);
      grouped.set(key, developer);
    });
    return [...grouped.values()];
  });
  const cohorts = $derived.by(() => {
    const indie = developers.filter((developer) => developer.indieGames.length > 0);
    return { indie, successfulIndie: indie.filter((developer) => developer.successfulIndieGames.length > 0), nonIndie: developers.filter((developer) => developer.indieGames.length === 0), successfulNonIndie: developers.filter((developer) => developer.indieGames.length === 0 && developer.successfulGames.length > 0) };
  });
  const averageGames = (cohort: Developer[]) => cohort.length === 0 ? 0 : d3.sum(cohort, (developer) => developer.games.length) / cohort.length;
  const bars = $derived<BarDatum[]>([
    { key: 'indie', label: 'Indie developers', value: averageGames(cohorts.indie), studios: cohorts.indie.length, color: '#7c3aed' },
    { key: 'successfulIndie', label: 'Successful indie developers', value: averageGames(cohorts.successfulIndie), studios: cohorts.successfulIndie.length, color: '#db2777' },
    { key: 'nonIndie', label: 'Non-indie developers', value: averageGames(cohorts.nonIndie), studios: cohorts.nonIndie.length, color: '#0f766e' },
    { key: 'successfulNonIndie', label: 'Successful non-indie developers', value: averageGames(cohorts.successfulNonIndie), studios: cohorts.successfulNonIndie.length, color: '#ea580c' }
  ]);

  const followOnBins = ['0', '1', '2–3', '4–6', '7+'];
  const followOnBin = (count: number) => count === 0 ? '0' : count === 1 ? '1' : count <= 3 ? '2–3' : count <= 6 ? '4–6' : '7+';
  const followOnData = (developersInCohort: Developer[]) => {
    const counts = new Map(followOnBins.map((bin) => [bin, 0]));
    developersInCohort.forEach((developer) => {
      const successfulGames = developer.successfulGames.filter((game) => game.release_date !== null).sort((a, b) => (a.release_date?.getTime() ?? 0) - (b.release_date?.getTime() ?? 0));
      const label = followOnBin(Math.max(0, successfulGames.length - 1));
      counts.set(label, (counts.get(label) ?? 0) + 1);
    });
    return followOnBins.map((label): PieDatum => ({ label, value: counts.get(label) ?? 0, description: label === '0' ? 'No additional successful games' : `${label} additional successful games` }));
  };
  const pieData = $derived(followOnData(cohorts.successfulIndie));
  const nonIndiePieData = $derived(followOnData(cohorts.successfulNonIndie));
  const innerWidth = $derived(Math.max(260, width * 0.58 - margin.left - margin.right));
  const x = $derived(d3.scaleBand<string>().domain(bars.map((bar) => bar.key)).range([margin.left, margin.left + innerWidth]).padding(0.3));
  const maxAverage = $derived(Math.max(1, d3.max(bars, (bar) => bar.value) ?? 1));
  const y = $derived(d3.scaleLinear().domain([0, maxAverage]).nice().range([barHeight - margin.bottom, margin.top]));
  const ticks = $derived(y.ticks(5));
  const pieCenterY = pieSize / 2 + 8;
  const pieRadius = $derived(Math.min(125, pieSize / 2 - 38));
  const pie = d3.pie<PieDatum>().value((datum) => datum.value).sort(null);
  const slices = $derived(pie(pieData));
  const nonIndieSlices = $derived(pie(nonIndiePieData));
  const arc = $derived(d3.arc<d3.PieArcDatum<PieDatum>>().innerRadius(0).outerRadius(pieRadius));
  const pieColor = d3.scaleOrdinal<string, string>().domain(followOnBins).range(['#c4b5fd', '#a78bfa', '#8b5cf6', '#7c3aed', '#5b21b6']);
  const formatAverage = d3.format('.2f');
  const formatCount = d3.format(',');
  const rocksteadyGames = $derived(games
    .filter((game) => game.developer.toLocaleLowerCase().includes('rocksteady'))
    .sort((a, b) => (a.release_date?.getTime() ?? Number.MAX_SAFE_INTEGER) - (b.release_date?.getTime() ?? Number.MAX_SAFE_INTEGER) || a.name.localeCompare(b.name)));
  const rockstarGames = $derived(games
    .filter((game) => game.developer.toLocaleLowerCase().includes('rockstar'))
    .sort((a, b) => (a.release_date?.getTime() ?? Number.MAX_SAFE_INTEGER) - (b.release_date?.getTime() ?? Number.MAX_SAFE_INTEGER) || a.name.localeCompare(b.name)));
  const formatDate = (game: SteamGame) => game.release_date?.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' }) ?? 'Unknown date';
</script>

<section class="visualization" aria-labelledby="developer-success-title">
  <div class="heading"><div><p class="eyebrow">Developer trajectories</p><h2 id="developer-success-title">Indie studios and repeat success</h2><p class="subtitle">Average games per developer, plus how often an indie developer follows one successful game with more.</p></div><div class="threshold">Success threshold <strong>{formatCount(SUCCESS_REVIEW_THRESHOLD)} reviews</strong></div></div>
  {#if games.length === 0}<p class="empty">Loading Steam game data…</p>{:else if developers.length === 0}<p class="empty">No developer data is available.</p>{:else}
    <div class="charts">
      <div class="bar-panel"><h3>Games per studio</h3><svg viewBox={`0 0 ${Math.max(width * 0.58, 420)} ${barHeight}`} role="img" aria-label="Average number of games per studio for indie, successful indie, non-indie, and successful non-indie developers"><title>Average games per studio by developer cohort</title>{#each ticks as tick}<line class="gridline" x1={margin.left} x2={margin.left + innerWidth} y1={y(tick)} y2={y(tick)} /><text class="tick" x={margin.left - 10} y={y(tick) + 4} text-anchor="end">{tick}</text>{/each}<line class="axis" x1={margin.left} x2={margin.left + innerWidth} y1={barHeight - margin.bottom} y2={barHeight - margin.bottom} /><text class="axis-label" transform={`translate(17 ${barHeight / 2}) rotate(-90)`} text-anchor="middle">Average games per studio</text>{#each bars as bar}{@const barX = x(bar.key) ?? margin.left}{@const barTop = y(bar.value)}<rect class="bar" x={barX} y={barTop} width={x.bandwidth()} height={Math.max(0, barHeight - margin.bottom - barTop)} fill={bar.color} rx="5"><title>{bar.label}: {formatAverage(bar.value)} games across {formatCount(bar.studios)} studios</title></rect><text class="bar-value" x={barX + x.bandwidth() / 2} y={barTop - 10} text-anchor="middle">{formatAverage(bar.value)}</text><text class="bar-label" x={barX + x.bandwidth() / 2} y={barHeight - margin.bottom + 24} text-anchor="middle">{bar.label}</text><text class="bar-count" x={barX + x.bandwidth() / 2} y={barHeight - margin.bottom + 42} text-anchor="middle">{formatCount(bar.studios)} studios</text>{/each}</svg></div>
      <div class="pie-panel"><h3>After a successful indie game</h3><p class="panel-note">Indie developers with at least one indie game above the threshold</p><svg viewBox={`0 0 ${pieSize} ${pieSize + 30}`} role="img" aria-label="Distribution of additional successful games made by successful indie developers"><title>Additional successful games by successful indie developer</title><g transform={`translate(${pieSize / 2} ${pieCenterY})`}>{#each slices as slice}<path d={arc(slice) ?? ''} fill={pieColor(slice.data.label)} stroke="white" stroke-width="2"><title>{slice.data.description}: {formatCount(slice.data.value)} developers</title></path>{/each}</g><g class="legend" transform={`translate(${pieSize / 2 - 63} ${pieSize - 2})`}>{#each pieData as datum, index}<g transform={`translate(${(index % 3) * 72 - 72} ${Math.floor(index / 3) * 20})`}><rect width="10" height="10" rx="2" fill={pieColor(datum.label)} /><text x="15" y="9">{datum.label}: {datum.value}</text></g>{/each}</g></svg></div>
      <div class="pie-panel"><h3>After a successful non-indie game</h3><p class="panel-note">Non-indie developers with at least one game above the threshold</p><svg viewBox={`0 0 ${pieSize} ${pieSize + 30}`} role="img" aria-label="Distribution of additional successful games made by successful non-indie developers"><title>Additional successful games by successful non-indie developer</title><g transform={`translate(${pieSize / 2} ${pieCenterY})`}>{#each nonIndieSlices as slice}<path d={arc(slice) ?? ''} fill={pieColor(slice.data.label)} stroke="white" stroke-width="2"><title>{slice.data.description}: {formatCount(slice.data.value)} developers</title></path>{/each}</g><g class="legend" transform={`translate(${pieSize / 2 - 63} ${pieSize - 2})`}>{#each nonIndiePieData as datum, index}<g transform={`translate(${(index % 3) * 72 - 72} ${Math.floor(index / 3) * 20})`}><rect width="10" height="10" rx="2" fill={pieColor(datum.label)} /><text x="15" y="9">{datum.label}: {datum.value}</text></g>{/each}</g></svg></div>
    </div>
    <div class="debug-panel">
      <div class="debug-heading"><div><h3>Rocksteady games</h3><p class="panel-note">Debug list for developers containing “Rocksteady”</p></div><span class="debug-count">{rockstarGames.length} games</span></div>
      {#if rockstarGames.length === 0}
        <p class="empty-debug">No Rocksteady games found in the loaded CSV.</p>
      {:else}
        <div class="table-wrap"><table><thead><tr><th>Game</th><th>Release date</th><th>Reviews</th><th>Indie</th><th>Successful</th></tr></thead><tbody>{#each rockstarGames as game}<tr><td>{game.name}</td><td>{formatDate(game)}</td><td>{formatCount(totalReviews(game))}</td><td>{isIndie(game) ? 'Yes' : 'No'}</td><td>{isSuccessful(game) ? 'Yes' : 'No'}</td></tr>{/each}</tbody></table></div>
      {/if}
    </div><p class="method">A game is indie when either its genre or tag is exactly “Indie.” Developers are grouped case-insensitively; repeat success is counted after each developer’s first successful indie game by release date, including successful games in any genre.</p>
  {/if}
</section>

<style>
  .visualization { min-width: 0; padding: 1.25rem 1.35rem 1.1rem; border: 1px solid #e5e7eb; border-radius: 18px; background: linear-gradient(135deg, #fff, #faf9ff); color: #1f2937; }
  .heading { display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem; margin-bottom: .5rem; } .eyebrow { margin: 0 0 .25rem; color: #7c3aed; font-size: .72rem; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; } h2, h3 { margin: 0; color: #111827; } h2 { font-size: clamp(1.15rem, 2vw, 1.45rem); } h3 { font-size: .95rem; }
  .subtitle, .panel-note, .method { color: #6b7280; font-size: .82rem; line-height: 1.45; } .subtitle { margin: .35rem 0 0; } .panel-note { margin: .25rem 0 0; } .threshold { padding: .55rem .7rem; border-radius: 8px; background: #f3e8ff; color: #6b21a8; font-size: .76rem; white-space: nowrap; } .threshold strong { display: block; margin-top: .1rem; color: #4c1d95; }
  .charts { display: grid; grid-template-columns: minmax(0, 1.35fr) repeat(2, minmax(190px, .7fr)); gap: .5rem; align-items: center; } .bar-panel, .pie-panel { min-width: 0; } .bar-panel svg { display: block; width: 100%; height: auto; overflow: visible; } .pie-panel { text-align: center; } .pie-panel svg { display: block; width: min(100%, 310px); height: auto; margin: 0 auto; overflow: visible; }
  .gridline { stroke: #e5e7eb; stroke-dasharray: 3 4; } .axis { stroke: #9ca3af; } .tick, .bar-count, .legend text { fill: #6b7280; font-size: 10px; } .axis-label { fill: #4b5563; font-size: 11px; } .bar-label { fill: #374151; font-size: 11px; font-weight: 700; } .bar-value { fill: #111827; font-size: 12px; font-weight: 800; } .bar { transition: opacity 160ms ease; } .bar:hover { opacity: .78; } .method { margin: .25rem 0 0; font-size: .73rem; } .empty { min-height: 8rem; display: grid; place-items: center; color: #6b7280; }
  @media (max-width: 720px) { .heading { flex-direction: column; } .charts { grid-template-columns: 1fr; } .pie-panel { padding-top: .7rem; } }
</style>





