# Analyst Brief: Chicago Taxi Trips, Week of 11–17 September 2023

## Background

We have one week of taxi trip records that taxi companies reported to the City of Chicago. The week runs from Monday 2023-09-11 to Sunday 2023-09-17. I'd like a short, factual picture of how taxi activity looked that week: when people ride, which companies carry the trips and earn the money, how tipping works, and where trips start. This is a routine descriptive readout. It is not a research project.

## Data

- **File:** `trips.csv`, with 135,768 rows (one row per trip). The columns are described in `dataset.md`.
- **What's in it:** trip times, duration, distance, pickup and dropoff locations (census tract, community area and centroid coordinates), fare components (`fare`, `tips`, `tolls`, `extras`, `trip_total`), `payment_type`, `company` and an anonymised `taxi_id`.
- **Use only this file.** You don't need external data. Report community areas by their number.

### Known limitations (from the City's documentation)

Keep these in mind and state them where they affect a result:

- Start and end timestamps are **rounded to the nearest 15 minutes**. Use them for hour-of-day and day-of-week grouping only. Use `trip_seconds` for durations.
- **Cash tips generally are not recorded.** Tip figures for cash trips will look close to zero and must not be read as "cash riders don't tip."
- Pickup and dropoff locations are **blank for many trips outside Chicago**, and census tracts are sometimes suppressed for privacy.
- **Not every trip is reported**, though the City believes most are. Treat the totals as reported activity, not complete market totals.

## Questions to answer

**1. When does demand happen?**
- Trips per day, Monday through Sunday.
- Trips by hour of day (from `trip_start_timestamp`), comparing weekdays with the weekend.
- Which hours are the busiest and quietest, and how different is the weekend pattern?

**2. Which companies carry the trips and the revenue?**
- For each company: trip count, total `trip_total`, share of all trips, share of all revenue, and number of distinct `taxi_id`s active during the week.
- Average revenue per active taxi, by company.
- List the top 10 companies and group the rest as "Other." Note any trips with a blank `company`.

**3. How does tipping vary by payment type?**
- Trip count and share by `payment_type`.
- For each payment type: average tip and tip as a percentage of `fare`.
- For the payment types where tips are actually recorded, does the tip percentage differ between short and long trips? Use a few simple distance bands of your choosing.

**4. Where do trips start?**
- The top 10 pickup community areas by trip count and by total `trip_total`.
- The share of trips with a blank pickup community area.
- The five most common pickup-to-dropoff community-area pairs.

## Data cleaning

Some rows will be unusable for some questions, for example zero or missing `trip_seconds` or `trip_miles`, zero or extreme fares, or a `trip_total` that doesn't match its components. Use your judgement and keep it simple:

- Set a small number of clear exclusion rules and apply them consistently.
- **Report how many rows each rule removes.** If a rule removes more than a few percent of the data, tell me.
- Don't drop rows from a question that doesn't need the problem field. For example, a trip with missing distance still counts toward trips-per-hour.

## Deliverable

One short document (Markdown, a notebook export or a slide deck is fine) containing:

1. A **summary of 5–8 bullet points** with the main findings, in plain language.
2. One section per question with a table or chart and one or two sentences of interpretation. About one chart per question is enough.
3. A **data notes** section listing your cleaning rules, the row counts each rule removed, and any caveats that affect the conclusions.
4. The code or queries you used, so the numbers can be reproduced.

## Scope and time

- **Timebox:** about 2–3 hours in one sitting. Roughly 30 minutes for loading and checking the data, 1.5 hours for the four questions, and 30 minutes for the write-up.
- **Out of scope:** maps and geospatial work, forecasting or modelling, comparisons with other weeks or years, and joining external reference data such as community area names, weather or events.
- If a question turns out to be unanswerable or misleading with this data, say so briefly and move on. Don't work around it.
- Ask me early if anything in this brief is unclear.
