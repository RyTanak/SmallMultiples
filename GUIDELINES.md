# Repository Guidelines

## Architecture

- `src/routes/+page.svelte` is the only application integration point. It loads `/steam_top_games_2026-selected-columns.csv` once, parses every CSV field, and passes the resulting `SteamGame[]` to visualizations.
- Keep `src/app.html` as the SvelteKit document shell and keep `src/routes/+layout.svelte` limited to shared page behavior such as the favicon.
- The shared data contract is `SteamGame` in `src/types.ts`. Dates are `Date | null`, nullable numeric values are represented as `number | null`, other numeric fields are numbers, booleans are booleans, and comma-separated fields are trimmed string arrays.

## Visualization ownership

- Ryota owns `src/lib/RyotaVis/` (`Bar.svelte`, `Bump.svelte`, and `Heatmap.svelte`).
- Eric owns `src/lib/EricVis/` (`Scatter.svelte`, `A2_4.svelte`, and `Line.svelte`).
- Carl owns `src/lib/CarlVis/` (`Ridgeline.svelte`).
- Components receive `games` through props and must not fetch the CSV themselves.
- A developer should edit only their own visualization directory unless coordinating an integration change in `src/routes/+page.svelte`.

## Data and routes

- The browser-facing CSV is `static/steam_top_games_2026-selected-columns.csv`; do not reintroduce `static/summer_movies.csv` or movie-only fields such as runtime, rating, votes, or title IDs.
- The parser currently covers identity, release status, pricing, taxonomy, platform support, review metrics, ownership, playtime, community counts, descriptions, and image URLs from the CSV.
- Keep the root route as the single page. Do not add individual visualization routes unless the project requirements change.
- If the dataset schema changes, update the parser and `SteamGame` together, then update all affected visualizations.

## Workflow

- Install dependencies with `npm install` when needed.
- Run `npm run check` after TypeScript or Svelte changes and `npm run build` before handoff when practical.
- Keep central-page changes small: add an import and component instance only after a visualization is ready.
- Do not commit changes or create branches unless explicitly requested.
