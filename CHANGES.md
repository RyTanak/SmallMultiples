# Steam Games Migration and Developer Workflow

The application currently expects the movie schema in `static/summer_movies.csv`.
Migrate it to `steam_top_games_2026-selected-columns.csv` and use one central
page that renders independently owned developer visualizations.

## Data files

- `steam_top_games_2026-selected-columns.csv` — relocate or copy into the static
  asset directory so the browser can load it.
- `static/steam_top_games_2026-selected-columns.csv` — add the replacement CSV
  at the URL used by the central page.
- `static/summer_movies.csv` — delete after the application no longer references
  the movie dataset.

## Shared data model

- `src/types.ts` — replace `TMovie` with the shared Steam game type covering
  `app_id`, `name`, `release_date`, `coming_soon`, `price_usd`, `is_free`,
  `discount_pct`, `developer`, `publisher`, and `genres`. Parse release dates,
  booleans, numbers, and genre arrays consistently before passing data to apps.

## Central application

- `src/routes/+page.svelte` — create the central page. Load and parse the CSV
  once, import the developer-owned visualizations, and pass the parsed games to
  them through props such as `<Heatmap {games} />`. Keep this file limited to
  data loading, imports, and component composition.
- `src/app.html` — leave as the SvelteKit document shell. Do not import
  visualizations or put application logic here; SvelteKit inserts the output of
  `src/routes/+page.svelte` into `%sveltekit.body%`.
- `src/routes/+layout.svelte` — retain only shared page-level behavior such as
  the favicon or global shell. It should not contain developer visualization
  logic.

## Developer-owned visualizations

Add these directories:

- `src/lib/RyotaVis/` — Ryota’s visualization components and local helpers.
- `src/lib/EricVis/` — Eric’s visualization components and local helpers.
- `src/lib/CarlVis/` — Carl’s visualization components and local helpers.

Each developer owns the files in their directory. Components should receive the
already parsed `games` array through props, own their calculations and markup,
and avoid fetching the CSV independently or editing another developer’s folder.
For example:

```text
src/lib/RyotaVis/Heatmap.svelte
src/lib/EricVis/Scatterplot.svelte
src/lib/CarlVis/Ridgeline.svelte
```

Move retained visualizations from the current unowned collection into the
appropriate developer directory and update their imports and data types:

- `src/lib/Bar.svelte`
- `src/lib/Bump.svelte`
- `src/lib/Heatmap.svelte`
- `src/lib/Line.svelte`
- `src/lib/Ridgeline.svelte`
- `src/lib/Scatter.svelte`
- `src/lib/A2_4.svelte`

These components must be adapted to the Steam schema. Preserve compatible
genre and release-date analyses; replace movie-only runtime, rating, and vote
analyses with game fields such as price or discount.

## Route cleanup

Remove the old route pages and directories after their useful visualization
logic has been moved:

- `src/routes/A0/+page.svelte`
- `src/routes/A1/+page.svelte`
- `src/routes/A2/+page.svelte`
- `src/routes/A3/+page.svelte`
- `src/routes/A0/`
- `src/routes/A1/`
- `src/routes/A2/`
- `src/routes/A3/`

No additional route is needed for an individual visualization or developer.

## Collaboration rules

- Developers work inside their own `src/lib/<Name>Vis/` directory.
- The central page loads the dataset once and supplies the same parsed data to
  every visualization.
- Developer components own their chart markup, calculations, labels, and
  visualization-specific types.
- The central `src/routes/+page.svelte` is the integration point and should be
  updated only when a visualization is ready to display.
- Keep central-page changes small; designate one person to integrate imports
  and component instances when possible, since that is the primary shared merge
  point.

