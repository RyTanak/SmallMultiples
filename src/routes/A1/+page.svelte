<script lang="ts">
  import * as d3 from "d3";
  import { onMount } from "svelte";
  import type { TMovie } from "../../types";
  import Bar from "../../lib/Bar.svelte";
  import Bump from "../../lib/Bump.svelte";
  import Heatmap from "../../lib/Heatmap.svelte";

  // Reactive variable for storing the data
  let movies: TMovie[] = [];

  // Function to load the CSV
  async function loadCsv() {
    try {
      const csvUrl = "./summer_movies.csv";
      movies = await d3.csv(csvUrl, (row) => {
        // TIP: in row, all values are strings, so we need to use a row conversion function here to format them
        return {
          ...row, // spread syntax to copy all properties from row
          tconst: row.tconst,
          title_type: row.title_type,
          primary_title: row.primary_title,
          original_title: row.original_title,
          year: new Date(Number(row.year), 0, 1),
          runtime_minutes: Number(row.runtime_minutes),
          genres: row.genres.split(",").map((genre) => genre.trim()),
          simple_title: row.simple_title,
          average_rating: Number(row.average_rating),
          num_votes: Number(row.num_votes)
          // please also format the values for other non-string attributes. You can check the attributes in the CSV file
        };
      });

      console.log("Loaded CSV Data:", movies);
    } catch (error) {
      console.error("Error loading CSV:", error);
    }
  }
  // Call the loader when the component mounts
  onMount(loadCsv);
</script>

<h1>Summer Movies</h1>

<p>Here are {movies.length == 0 ? "..." : movies.length + " "} movies</p>
<Bar {movies} />

<p>Q1: How do the top three movie genres (by number of movies) change over time?</p>
<Bump {movies} />

<p>The top three movie genres that occurred most was drama, comedy, and romance. Drama and comedy were consistently in top 1 and 2, while
    romance fluctuated through second and third positions over the years. 
</p>

<br />
<p>Q2: What are the correlations between different genres? For example, which genre often co-occurs with comedy in a movie?</p>
<Heatmap {movies} />
<p>
    From the heatmap, we can see that the genre pairs that co-occurred the most were romance and drama, comedy and drama, and romance and comedy. 
    Throughout the map, we can see that drama, romance, and comedy were the most co-occurring genres with all the other genres. 
</p>