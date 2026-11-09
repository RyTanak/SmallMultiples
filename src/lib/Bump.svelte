<script lang="ts">
  import type { TMovie } from "../types";
  import * as d3 from "d3";

  // define the props of the Bar component
  type Props = {
    movies: TMovie[];
    progress?: number;
    width?: number;
    height?: number;
  };

  // progress is 100 by default unless specified
  let {
    movies,
    progress = 100,
    width = 1000,
    height = 400
  }: Props = $props();

  let selectedGenre: string = $state("");

  // processing the data; $derived is used to create a reactive variable that updates whenever the dependent variables change
  const yearRange = $derived(
    d3.extent(movies.map((d) => d.year))
  );

  function getUpYear(
    yearRange: [undefined, undefined] | [Date, Date]
  ) {
    if (!yearRange[0]) return new Date();

    const timeScale = d3
      .scaleTime()
      .domain(yearRange)
      .range([0, 100]);

    return timeScale.invert(progress);
  }

  const upYear: Date = $derived(
    getUpYear(yearRange!)
  );

  function getGenreNums(
    movies: TMovie[],
    upYear: Date
  ) {
    let res: {
      year: Date;
      genre: string;
      count: number;
      rank: number;
    }[] = [];

    let yearGenreNums: {
      [year: number]: {
        [genre: string]: number;
      };
    } = {};

    // Count the number of movies for each genre for each year
    movies
      .filter((movie) => movie.year <= upYear)
      .forEach((movie) => {
        const year = movie.year.getFullYear();

        if (!yearGenreNums[year]) {
          yearGenreNums[year] = {};
        }

        movie.genres.forEach((genre: string) => {
          yearGenreNums[year][genre] =
            (yearGenreNums[year][genre] || 0) + 1;
        });
      });

    // Rank the genres for each year
    Object.entries(yearGenreNums).forEach(
      ([year, genres]) => {

        const rankedGenres = Object.entries(genres)
          .sort((a, b) => b[1] - a[1])
          .slice(0, 3);

        rankedGenres.forEach(
          ([genre, count], index) => {
            res.push({
              year: new Date(Number(year), 0, 1),
              genre: genre,
              count: count,
              rank: index + 1
            });
          }
        );
      }
    );

    return res;
  }

  const genreNums = $derived(
    getGenreNums(movies, upYear)
  );

  // Group the data by genre so each genre can have its own line
  const genreGroups = $derived(
    d3.group(genreNums, (d) => d.genre)
  );

  // drawing the bar chart

  const margin = {
    top: 30,
    bottom: 50,
    left: 60,
    right: 140,
  };

  let usableArea = {
    top: margin.top,
    right: width - margin.right,
    bottom: height - margin.bottom,
    left: margin.left,
  };

  const xScale = $derived(
    // tip: use d3.scaleBand() to create a band scale for the x-axis
    // d3
    //   .scaleBand()
    //   .range(xx)
    //   .domain(xx)
    //   .padding(xx),

    d3
      .scaleTime()
      .range([
        usableArea.left,
        usableArea.right
      ])
      .domain(
        yearRange[0] && yearRange[1]
          ? [yearRange[0], yearRange[1]]
          : [new Date(), new Date()]
      )
  );

  const yScale = $derived(
    // tip: use d3.scaleLinear() to create a linear scale for the y-axis
    // d3
    //   .scaleLinear()
    //   .range(xx)
    //   .domain(xxx),

    d3
      .scaleLinear()
      .range([
        usableArea.top,
        usableArea.bottom
      ])
      .domain([1, 3])
  );

  // Get every genre that appears in the top 3
  const genres = $derived(
    Array.from(
      new Set(
        genreNums.map((d) => d.genre)
      )
    )
  );

  // Assign a color to each genre
  const colorScale = $derived(
    d3
      .scaleOrdinal<string, string>()
      .domain(genres)
      .range(d3.schemeTableau10)
  );

  // Create the line for each genre
  const lineGenerator = $derived(
    d3
      .line<{
        year: Date;
        genre: string;
        count: number;
        rank: number;
      }>()
      .x((d) => xScale(d.year))
      .y((d) => yScale(d.rank))
  );

  let xAxis: any = $state(),
    yAxis: any = $state();

  function updateAxis() {
    d3.select(xAxis)
      .call(
        d3
          .axisBottom(xScale)
          .ticks(10)
          .tickFormat((d) =>
            d3.timeFormat("%Y")(d as Date)
          )
      )
      .selectAll("text")
      .attr("transform", "rotate(45)")
      .style("text-anchor", "start");

    // tip:
    // similar to the x-axis, create a y-axis using d3.axisLeft() and bind it to the yAxis variable
    d3.select(yAxis)
      .call(
        d3
          .axisLeft(yScale)
          .tickValues([1, 2, 3])
          .tickFormat((d) => `${d}`)
      )
      .selectAll("text")
      .attr("transform", "rotate(0)")
      .style("text-anchor", "end");
  }

  // the $effect function is used to run a function whenever the reactive variables change, also known as a side effect
  $effect(() => {
    if (genreNums.length > 0) {
      updateAxis();
    }
  });
</script>

<h3>
  Top 3 Movie Genres
  {yearRange[0]?.getFullYear()} -
  {yearRange[1]?.getFullYear()}
</h3>

{#if movies.length > 0}
  <svg {width} {height}>

    <g class="bars">

      {#each Array.from(genreGroups) as [genre, points]}

        <g class={genre}>

          <!-- tip: draw bars here using the svg <rect/> component -->

          <path
            d={lineGenerator(
              [...points].sort(
                (a, b) =>
                  a.year.getTime() -
                  b.year.getTime()
              )
            )}
            fill="none"
            stroke={colorScale(genre)}
            stroke-width={selectedGenre === genre ? 4 : 2}
            opacity={
              selectedGenre === "" ||
              selectedGenre === genre
                ? 1
                : 0.15
            }
            onmouseover={() => {
              selectedGenre = genre;
            }}
            onmouseout={() => {
              selectedGenre = "";
            }}
          />

          {#each points as d}

            <circle
              cx={xScale(d.year)}
              cy={yScale(d.rank)}
              r={selectedGenre === genre ? 5 : 3}
              fill={colorScale(genre)}
              opacity={
                selectedGenre === "" ||
                selectedGenre === genre
                  ? 1
                  : 0.15
              }
              onmouseover={() => {
                selectedGenre = genre;
              }}
              onmouseout={() => {
                selectedGenre = "";
              }}
            />

            <text
              x={xScale(d.year)}
              y={yScale(d.rank) - 8}
              font-size="11"
              text-anchor="middle"
            >
              <!-- tip: the text below should change with the hover on interaction -->
              {selectedGenre === genre
                ? genre
                : ""}
            </text>

          {/each}

        </g>

      {/each}

    </g>

    <g
      transform="translate(0, {usableArea.bottom})"
      bind:this={xAxis}
    />

    <g
      transform="translate({usableArea.left}, 0)"
      bind:this={yAxis}
    />

    <!-- Legend -->
    <g
      class="legend"
      transform={`translate(${width - margin.right + 20}, ${margin.top})`}
    >

      {#each genres as genre, i}

        <g
          transform={`translate(0, ${i * 20})`}
          onmouseover={() => {
            selectedGenre = genre;
          }}
          onmouseout={() => {
            selectedGenre = "";
          }}
        >

          <circle
            cx="0"
            cy="0"
            r="5"
            fill={colorScale(genre)}
          />

          <text
            x="10"
            y="4"
            font-size="12"
          >
            {genre}
          </text>

        </g>

      {/each}

    </g>

  </svg>
{/if}

<style>
  .bar {
    transition:
      y 0.1s ease,
      height 0.1s ease,
      width 0.1s ease; /* Smooth transition for height */
  }

  path,
  circle {
    transition:
      opacity 0.15s ease,
      stroke-width 0.15s ease;
  }
</style>