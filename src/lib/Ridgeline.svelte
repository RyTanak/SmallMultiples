<script lang="ts">
    import * as d3 from "d3";
    import type { TMovie } from "../types";

    type TProps = {
        movies: TMovie[];
        width?: number;
        selectedGenre?: string;
    };

    type Ridge = {
        decade: number;
        count: number;
        density: { runtime: number; value: number }[];
    };

    const { movies, width = 900, selectedGenre }: TProps = $props();
    const margin = { top: 35, right: 25, bottom: 55, left: 85 };
    const rowStep = 60;
    const ridgeHeight = 78;
    const bandwidth = 12;


    const validMovies = $derived(
        movies.filter((movie) => Number.isFinite(movie.runtime_minutes) && movie.runtime_minutes > 0),
    );
    const genres = $derived(
        [...new Set(validMovies.flatMap((movie) => movie.genres.map((genre) => genre.trim()).filter(Boolean)))].sort(d3.ascending),
    );
    const activeGenre = $derived(
        selectedGenre && genres.includes(selectedGenre) ? selectedGenre : (genres[0] ?? ""),
    );
    const maxRuntime = $derived(
        Math.max(20, Math.ceil((d3.max(validMovies, (movie) => movie.runtime_minutes) ?? 0) / 20) * 20),
    );
    const xScale = $derived(
        d3.scaleLinear().domain([0, maxRuntime]).range([margin.left, width - margin.right]),
    );
    const runtimes = $derived(d3.range(0, maxRuntime + 1, maxRuntime / 120));

    const ridges: Ridge[] = $derived.by(() => {
        const byDecade = d3.group(
            validMovies.filter((movie) => movie.genres.some((genre) => genre.trim() === activeGenre)),
            (movie) => Math.floor(movie.year.getFullYear() / 10) * 10,
        );

        return [...byDecade.entries()]
            .sort(([a], [b]) => d3.ascending(a, b))
            .map(([decade, decadeMovies]) => {
                const values = decadeMovies.map((movie) => movie.runtime_minutes);
                const density = runtimes.map((runtime) => ({
                    runtime,
                    value: d3.mean(values, (value) => {
                        const distance = (runtime - value) / bandwidth;
                        return Math.exp(-0.5 * distance * distance) / (bandwidth * Math.sqrt(2 * Math.PI));
                    }) ?? 0,
                }));
                return { decade, count: values.length, density };
            });
    });

    const peakDensity = $derived(d3.max(ridges.flatMap((ridge) => ridge.density), (point) => point.value) ?? 0);
    const height = $derived(margin.top + ridges.length * rowStep + margin.bottom);
    const axisY = $derived(margin.top + ridges.length * rowStep + 12);

    function ridgePath(ridge: Ridge, index: number) {
        const baseline = margin.top + (index + 1) * rowStep;
        return d3.area<(typeof ridge.density)[number]>()
            .x((point) => xScale(point.runtime))
            .y0(baseline)
            .y1((point) => baseline - (peakDensity ? point.value / peakDensity * ridgeHeight : 0))
            .curve(d3.curveBasis)(ridge.density) ?? "";
    }
</script>

<section class="ridgeline">
    <h3>Movie Runtime Distribution by Decade</h3>
    {#if genres.length > 0}
        <p class="selected-genre">Genre: <strong>{activeGenre}</strong></p>

        <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${activeGenre} movie runtime distributions by decade`}>
            {#each ridges as ridge, index (ridge.decade)}
                {@const baseline = margin.top + (index + 1) * rowStep}
                <g class="ridge">
                    <line x1={margin.left} x2={width - margin.right} y1={baseline} y2={baseline} class="baseline" />
                    <path
                        d={ridgePath(ridge, index)}
                        fill={d3.interpolateBlues(0.4 + 0.5 * (index + 1) / ridges.length)}
                    >
                        <title>{ridge.decade}s: {ridge.count} movies</title>
                    </path>
                    <text x={margin.left - 12} y={baseline + 4} text-anchor="end">{ridge.decade}s</text>
                    <text x={width - margin.right - 4} y={baseline - 5} text-anchor="end" class="count">n={ridge.count}</text>
                </g>
            {/each}
            <g class="axis">
                <line x1={margin.left} x2={width - margin.right} y1={axisY} y2={axisY} />
                {#each xScale.ticks(8) as tick}
                    <line x1={xScale(tick)} x2={xScale(tick)} y1={axisY} y2={axisY + 5} />
                    <text x={xScale(tick)} y={axisY + 20} text-anchor="middle">{tick}</text>
                {/each}
                <text x={width / 2} y={height - 5} text-anchor="middle">Runtime (minutes)</text>
            </g>
        </svg>
    {:else}
        <p>No movies with valid runtimes match the selected year range.</p>
    {/if}
</section>

<style>
    .ridgeline { margin: 1.5rem 0; }
    .selected-genre { margin: 0.5rem 0; }
    svg { display: block; width: 100%; max-width: 900px; height: auto; margin-top: 1rem; overflow: visible; }
    .baseline, .axis line { stroke: #aaa; stroke-width: 1; }
    .ridge path { stroke: #315b84; stroke-width: 1.5; fill-opacity: 0.8; }
    .ridge text, .axis text { fill: #444; font-size: 12px; }
    .ridge .count { font-size: 11px; }
</style>
