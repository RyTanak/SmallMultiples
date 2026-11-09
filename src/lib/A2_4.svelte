<script lang="ts">
    import * as d3 from "d3";
    import type { TMovie } from "../types";

    type TProps = {
        movies: TMovie[];
        width?: number;
        height?: number;
        selectedGenre?: string;
    };

    type HeatmapCell = {
        year: number;
        genre: string;
        averageRuntime: number;
    };

    let {
        movies,
        width = 900,
        height = 600,
        selectedGenre = $bindable<string | undefined>(),
    }: TProps = $props();

    const margin = { top: 85, bottom: 85, left: 110, right: 25 };
    const usableArea = {
        top: margin.top,
        right: width - margin.right,
        bottom: height - margin.bottom,
        left: margin.left,
    };

    function getHeatmapData(movies: TMovie[]) {
        const runtimeTotals = new Map<string, { total: number; count: number }>();
        const years = new Set<number>();
        const genres = new Set<string>();

        for (const movie of movies) {
            if (!Number.isFinite(movie.runtime_minutes)) continue;
            const year = Math.floor(movie.year.getFullYear() / 10) * 10;
            years.add(year);
            for (const rawGenre of movie.genres) {
                const genre = rawGenre.trim();
                if (!genre) continue;
                genres.add(genre);
                const key = `${year}\u0000${genre}`;
                const current = runtimeTotals.get(key) ?? { total: 0, count: 0 };
                current.total += movie.runtime_minutes;
                current.count += 1;
                runtimeTotals.set(key, current);
            }
        }

        const sortedYears = [...years].sort(d3.ascending);
        const sortedGenres = [...genres].sort(d3.ascending);
        const cells: HeatmapCell[] = [];
        for (const year of sortedYears) {
            for (const genre of sortedGenres) {
                const value = runtimeTotals.get(`${year}\u0000${genre}`);
                if (value) {
                    cells.push({ year, genre, averageRuntime: value.total / value.count });
                }
            }
        }
        return { cells, years: sortedYears, genres: sortedGenres };
    }

    const heatmapData = $derived(getHeatmapData(movies));
    const cells = $derived(heatmapData.cells);
    const years = $derived(heatmapData.years);
    const genres = $derived(heatmapData.genres);

    let selectedCellKey: string | undefined = $state();
    const selectedCell = $derived(
        cells.find((cell) => `${cell.year}\u0000${cell.genre}` === selectedCellKey),
    );

    function handleCellClick(cell: HeatmapCell) {
        const key = `${cell.year}\u0000${cell.genre}`;
        selectedCellKey = selectedCellKey === key ? undefined : key;
        selectedGenre = selectedCellKey === undefined ? undefined : cell.genre;
    }

    const xScale = $derived(
        d3.scaleBand<string>()
            .domain(years.map(String))
            .range([usableArea.left, usableArea.right])
            .padding(0.05),
    );
    const yScale = $derived(
        d3.scaleBand<string>()
            .domain(genres)
            .range([usableArea.top, usableArea.bottom])
            .padding(0.05),
    );

    const runtimeExtent = $derived(d3.extent(cells, (d) => d.averageRuntime));
    const colorScale = $derived(
        d3.scaleSequential(d3.interpolateYlOrBr).domain(
            runtimeExtent[0] === undefined || runtimeExtent[1] === undefined
                ? [0, 1]
                : runtimeExtent[0] === runtimeExtent[1]
                  ? [runtimeExtent[0] - 1, runtimeExtent[1] + 1]
                  : runtimeExtent,
        ),
    );
    const legendWidth = 180;
    const legendHeight = 12;
    const legendScale = $derived(
        d3.scaleLinear<number, number>().domain(colorScale.domain()).range([0, legendWidth]),
    );

    let xAxis: SVGGElement | undefined = $state();
    let yAxis: SVGGElement | undefined = $state();
    let legendAxis: SVGGElement | undefined = $state();

    function updateAxis() {
        if (!xAxis || !yAxis || !legendAxis) return;
        d3.select(xAxis)
            .call(d3.axisBottom(xScale))
            .selectAll("text")
            .attr("transform", "rotate(45)")
            .style("text-anchor", "start");
        d3.select(yAxis).call(d3.axisLeft(yScale));
        d3.select(legendAxis)
            .call(d3.axisBottom(legendScale).ticks(5).tickFormat(d3.format(".0f")));
    }

    $effect(() => updateAxis());
</script>

<h3>Average Movie Runtime by Decade and Genre</h3>

{#if cells.length > 0}
    <svg {width} {height} aria-label="Heatmap of average movie runtime by year and genre">
        <defs>
            <linearGradient id="runtime-gradient" x1="0%" x2="100%" y1="0%" y2="0%">
                {#each d3.range(0, 1.01, 0.25) as stop}
                    <stop offset={`${stop * 100}%`} stop-color={colorScale(legendScale.domain()[0] + stop * (legendScale.domain()[1] - legendScale.domain()[0]))} />
                {/each}
            </linearGradient>
        </defs>
        <g class="legend" transform={`translate(${usableArea.right - legendWidth}, 25)`}>
            <text x={legendWidth / 2} y="-8" text-anchor="middle">Average runtime (minutes)</text>
            <rect width={legendWidth} height={legendHeight} fill="url(#runtime-gradient)" />
            <g transform={`translate(0, ${legendHeight})`} bind:this={legendAxis} />
        </g>
        <g class="cells">
            {#each cells as cell (cell.year + cell.genre)}
                <rect
                    class="cell"
                    x={xScale(String(cell.year))}
                    y={yScale(cell.genre)}
                    width={xScale.bandwidth()}
                    height={yScale.bandwidth()}
                    fill={colorScale(cell.averageRuntime)}
                    stroke={selectedCell === cell ? "steelblue" : "none"}
                    stroke-width={selectedCell === cell ? 3 : 0}
                    role="button"
                    tabindex="0"
                    aria-label={`${cell.genre}, ${cell.year}s: ${cell.averageRuntime.toFixed(1)} minutes average`}
                    aria-pressed={selectedCell === cell}
                    onclick={() => handleCellClick(cell)}
                    onkeydown={(event) => {
                        if (event.key === "Enter" || event.key === " ") {
                            event.preventDefault();
                            handleCellClick(cell);
                        }
                    }}
                >
                    <title>{cell.genre}, {cell.year}: {cell.averageRuntime.toFixed(1)} minutes</title>
                </rect>
            {/each}
        </g>
        <g transform="translate(0, {usableArea.bottom})" bind:this={xAxis} />
        <g transform="translate({usableArea.left}, 0)" bind:this={yAxis} />
        <text x={(usableArea.left + usableArea.right) / 2} y={usableArea.bottom + 45} text-anchor="middle">Decades</text>
        <text transform="translate(18, {(usableArea.top + usableArea.bottom) / 2}) rotate(-90)" text-anchor="middle">Genre</text>
    </svg>
    <div class="selectedInfo">
        {selectedCell
            ? JSON.stringify(selectedCell, null, 2)
            : "Click on a cell to see details"}
    </div>
{:else}
    <p>No movies match the selected year range.</p>
{/if}

<style>
    .cell { transition: opacity 0.2s ease; }
    .cell:hover { opacity: 0.75; }
    .cell { cursor: pointer; }
    svg {
        display: inline-block;
        vertical-align: top;
    }
    .selectedInfo {
        display: inline-block;
        vertical-align: top;
        width: 250px;
        color: #555;
        font-family: monospace;
        white-space: pre-wrap;
        background-color: #f9f9f9;
        padding: 10px;
        border: 1px solid #ccc;
        border-radius: 4px;
        overflow: auto;
    }
</style>
