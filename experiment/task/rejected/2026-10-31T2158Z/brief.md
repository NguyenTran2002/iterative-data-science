# Analysis Brief: One Week of Chicago Taxi Trips

## Background

We have one week of Chicago taxi trip records, Monday 2023-09-11 through Sunday 2023-09-17. The City of Chicago collects these records as the regulator. The file is `trips.csv` and should have 135,768 rows. `dataset.md` describes the columns.

I want a baseline picture of a typical week: when trips happen, what a typical trip looks like and costs, how riders pay and tip, and which companies carry the volume. This is descriptive work for internal use. It is not a forecast or a model.

## Questions

**1. When does demand happen?**
- How many trips were there each day? How do weekdays (Mon–Fri) compare with the weekend (Sat–Sun)?
- What does the hourly pattern look like? Use `trip_start_timestamp`. Show weekdays and weekends separately, and name the busiest hours of each.

**2. What does a typical trip look like, and what does it cost?**
- Give the median and the interquartile range for `trip_miles`, `trip_seconds`, `fare` and `trip_total`.
- What was the total of `trip_total` for the week, and how does it break down into `fare`, `tips`, `tolls` and `extras`?
- Do typical fares and distances differ between weekdays and weekends?

**3. How do riders pay, and how much do they tip?**
- What share of trips, and what share of `trip_total`, falls under each `payment_type`?
- For card or other electronic payment types only, what is the typical tip as a percentage of `fare`? What share of those trips have no tip at all? Leave cash trips out of the tip figures, because cash tips are mostly not recorded. Say so in the write-up.

**4. Which companies carry the market?**
- What share of trips and of `trip_total` does each `company` have? List the top 10 by trips and group the rest as "Other."
- For those same companies, how many distinct taxis (`taxi_id`) were active during the week, and how many trips did each taxi average?

## Data cautions

- **Timestamps are rounded to the nearest 15 minutes.** Use them only for hour-of-day and day-level grouping. For trip duration, use `trip_seconds`.
- **Not every trip is reported.** The City believes most trips are. Present the counts as reported trips, not total market size.
- **Check for bad values before you summarize.** Look for zero, missing or implausible values in `trip_seconds`, `trip_miles` and `fare`, and for rows where `trip_total` does not equal the sum of its components. Set a simple, stated rule for what you exclude. Report how many rows each rule removes. Don't spend long tuning these rules.
- **Location fields are often blank.** This happens especially for trips outside Chicago, and census tracts are also hidden for privacy. None of the questions above need location. If you notice anything about how often location is missing, a single line is enough.

## Out of scope

- Maps, geographic or route analysis, and origin–destination flows. These may come in a later piece of work.
- Comparisons with other weeks or years, and any external data.
- Forecasting, modeling, or driver-level performance reviews.

## Deliverables

1. **A short written summary, 1–2 pages.** Start with 4–6 headline findings, then give one short section per question with the key table or chart.
2. **The code or notebook** that produces every number in the summary. It must run from `trips.csv`.
3. **A data-quality note.** Include the row count you loaded, each exclusion rule with the number of rows it removed, and any caveats that affect how the results should be read.

## Time and format

- Expect about **2–3 hours** in total. A rough split: about 30 minutes to load and check the data, about 1.5 hours on the four questions, and about 30 minutes to write up.
- Simple tables and a few clear charts are plenty. A dashboard isn't needed.
- If you run short on time, cut the second bullet of Question 4 first, then the weekday/weekend comparison in Question 2. Note anything you dropped.
- If something in the data blocks a question, tell me early rather than working around it quietly.
