<script lang="ts">
  import type { TMovie } from "../types";
  import * as d3 from "d3";
  // define the props of the Bar component
  type Props = {
    movies: TMovie[];
    width?: number;
    height?: number;
  };

  let {
    movies,
    width = 700,
    height = 700
  }: Props = $props();

  // processing the data; $derived is used to create a reactive variable that updates whenever the dependent variables change
  function getGenreRelations(movies: TMovie[]) {
    let pairCounts: {
      [pair: string]: number;
    } = {};

    let genreSet = new Set<string>();

    movies.forEach((movie) => {
      const genres = movie.genres;

      genres.forEach((genre) => {
        genreSet.add(genre);
      });

      for (let i = 0; i < genres.length; i++) {
        for (let j = i + 1; j < genres.length; j++) {
          const genre1 = genres[i];
          const genre2 = genres[j];

          const pair = [genre1, genre2].sort().join("|");

          pairCounts[pair] = (pairCounts[pair] || 0) + 1;
        }
      }
    });

    const genres = Array.from(genreSet).sort();

    let relations: {
      genre1: string;
      genre2: string;
      count: number;
    }[] = [];

    genres.forEach((genre1) => {
      genres.forEach((genre2) => {
        if (genre1 === genre2) {
          relations.push({
            genre1,
            genre2,
            count: 0
          });
        } else {
          const pair = [genre1, genre2].sort().join("|");

          relations.push({
            genre1,
            genre2,
            count: pairCounts[pair] || 0
          });
        }
      });
    });

    return {
      genres,
      relations
    };
  }

  const relationData = $derived(
    getGenreRelations(movies)
  );

  const genres = $derived(
    relationData.genres
  );

  const relations = $derived(
    relationData.relations
  );

  // drawing the bar chart

  const margin = {
    top: 40,
    bottom: 120,
    left: 120,
    right: 30,
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
      .scaleBand()
      .range([usableArea.left, usableArea.right])
      .domain(genres)
      .padding(0.05)
  );

  const yScale = $derived(
    // tip: use d3.scaleLinear() to create a linear scale for the y-axis
    // d3
    //   .scaleLinear()
    //   .range(xx)
    //   .domain(xxx),
    d3
      .scaleBand()
      .range([usableArea.top, usableArea.bottom])
      .domain(genres)
      .padding(0.05)
  );

  const maxCount = $derived(
    d3.max(relations, (d) => d.count) ?? 1
  );

  const colorScale = $derived(
    d3
      .scaleSequential(d3.interpolateBlues)
      .domain([0, maxCount])
  );

  let xAxis: any = $state(),
    yAxis: any = $state();

  function updateAxis() {
    d3.select(xAxis)
      .call(d3.axisBottom(xScale))
      .selectAll("text")
      .attr("transform", "rotate(45)")
      .style("text-anchor", "start");

    // tip:
    // similar to the x-axis, create a y-axis using d3.axisLeft() and bind it to the yAxis variable
    d3.select(yAxis)
      .call(d3.axisLeft(yScale))
      .selectAll("text")
      .attr("transform", "rotate(0)")
      .style("text-anchor", "end");
  }

  // the $effect function is used to run a function whenever the reactive variables change, also known as a side effect
  $effect(() => {
    if (genres.length > 0) {
      updateAxis();
    }
  });
</script>

<h3>
  Genre Co-occurrence Heatmap
</h3>

{#if movies.length > 0}
  <svg {width} {height}>
    <g class="bars">
      {#each relations as d}
        <g>
          <!-- tip: draw bars here using the svg <rect/> component -->
          <rect
            x={xScale(d.genre1)}
            y={yScale(d.genre2)}
            width={xScale.bandwidth()}
            height={yScale.bandwidth()}
            fill={colorScale(d.count)}
            class="bar"
          />

          <text
            x={xScale(d.genre1)! + xScale.bandwidth() / 2}
            y={yScale(d.genre2)! + yScale.bandwidth() / 2}
            font-size="10"
            text-anchor="middle"
            dominant-baseline="middle"
          >
          <!-- tip: the text below should change with the hover on interaction -->
            {d.count > 0 ? d.count : ""}
          </text>
        </g>
      {/each}
    </g>

    <g transform="translate(0, {usableArea.bottom})" bind:this={xAxis} />
    <g transform="translate({usableArea.left}, 0)" bind:this={yAxis} />
  </svg>
{/if}

<style>
  .bar {
    transition:
      y 0.1s ease,
      height 0.1s ease,
      width 0.1s ease; /* Smooth transition for height */
  }
</style>