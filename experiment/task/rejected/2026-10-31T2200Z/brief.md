# Analysis Brief: Chicago Taxi Trips, Week of 11–17 September 2023

## Background

We have one week of taxi trip records reported to the City of Chicago: Monday 2023-09-11 through Sunday 2023-09-17. That's 135,768 trips in `trips.csv`. The columns are described in `dataset.md`. I want a short, reliable picture of how taxi activity looked that week: when people rode, who carried them, where trips started, and how riders paid and tipped.

This is a descriptive snapshot of one week. It isn't a forecast, and it doesn't need to say anything about trends over time.

## Questions to answer

**1. When does demand happen?**
Count trips by day of week and by hour of day, using `trip_start_timestamp`. Identify the peak hours on weekdays and on the weekend, and say how the two patterns differ. Report the busiest and quietest day of the week.

**2. How is the market split among companies?**
For each `company`, report the number of trips, the share of all trips, the total `fare`, and the average fare per trip. Show the top 10 companies by trip count and group the rest as "Other". Tell me how concentrated the market is: what share of trips do the top 3 and top 10 companies carry? Report the number of distinct `taxi_id` values per company too, and the average trips per taxi.

**3. Where do trips start?**
Rank pickup locations by trip count and by total fare, using `pickup_community_area`. Give the top 10. Report what share of trips has a blank pickup community area; these are mostly pickups outside Chicago. List the top 10 pickup–dropoff community-area pairs by trip count.

**4. How do riders pay and tip?**
Give the trip count and share for each `payment_type`. Cash tips are generally not recorded, so calculate tipping only for payment types where tips are captured electronically. Justify which ones you include from the data: look at the share of trips with a non-zero tip for each type. For those trips, report the median tip as a percentage of `fare` and the share of trips with no tip. Show whether tip percentage differs between weekdays and the weekend.

## Data handling

- **Cleaning first.** Before answering anything, flag trips with zero or missing `trip_seconds` or `trip_miles`, a zero or missing `fare`, or extreme values (for example, trips over 100 miles, over 5 hours, or with fares over $500). Choose sensible thresholds, state them, and report how many rows each rule removes. Apply the same cleaned set to every question unless you explain why not.
- **Check the totals.** `trip_total` should equal fare + tips + tolls + extras. Report how many rows don't match to within $0.01. Use `fare` for revenue comparisons, so tips and extras don't distort them.
- **Timestamps are rounded to the nearest 15 minutes.** Hour-of-day counts are fine, but don't compute trip durations from the timestamps; use `trip_seconds`.
- **Location fields are partial.** Community area is blank outside Chicago, and census tract is suppressed for some trips for privacy. Use community area, not census tract, and always state the blank share next to location results.
- **Community areas are numbers.** We have no name lookup in this folder, so report the area numbers as they appear.
- **Not every trip is reported.** The City believes most trips are reported, but not all. Treat the counts as close to complete, not exact.

## Deliverables

1. **A one- to two-page summary** (markdown or PDF). It should have three to five headline findings and a direct answer to each of the four questions, with one table or chart per question.
2. **A data-quality note** (a short section of the summary is fine). Cover the cleaning rules, rows removed, the `trip_total` mismatch count, and the blank-location shares.
3. **Code** (a notebook or script) that reproduces every number in the summary from `trips.csv`.

## Scope and time

Plan on about **2½ hours** in one sitting:

| Task | Time |
|---|---|
| Load, inspect, clean, data-quality note | 40 min |
| Questions 1–4 (about 20 min each) | 80 min |
| Write-up and charts | 30 min |

**Out of scope:** predictive modelling, maps or other geospatial work beyond community-area counts, outside data sources (weather, events, area names), comparisons with other weeks or years, and driver- or taxi-level investigations beyond the trips-per-taxi figure in Question 2.

If something in the data blocks a question, write down what you found and move on rather than spending the time on it. Examples would be a column that is almost entirely blank, or payment types that don't separate cleanly.
