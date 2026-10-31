# Analysis Brief: Chicago Taxi Activity, Week of 11–17 September 2023

**To:** Data Analyst
**From:** Operations & Strategy Manager
**Time budget:** One sitting, about 2–3 hours
**Data:** `trips.csv`. One week of City of Chicago taxi trip records, Monday 2023-09-11 to Sunday 2023-09-17, 135,768 rows. The columns are described in `dataset.md`.

---

## Why we're asking

We want a clear, factual picture of one normal week of taxi activity in Chicago: when people ride, where trips start, who carries them, and how riders pay. This is a baseline snapshot, not a forecast. Keep it descriptive and well caveated. Please don't build anything elaborate.

## Questions to answer

### 1. When does demand happen?
- How many trips were there each day of the week? How does the weekday average compare with Saturday and Sunday?
- What is the hourly pattern of trip starts (hour 0–23)? Show weekdays and weekends separately. Name the busiest hours for each.
- Use `trip_start_timestamp`. Times are rounded to the nearest 15 minutes, so hourly bins are fine. Don't report anything finer than 15 minutes.

### 2. Where do trips start, and what are they worth?
- Which 10 pickup community areas (`pickup_community_area`) have the most trips? For each, give the trip count, its share of all trips, total `trip_total`, and median `trip_miles`.
- What share of trips has a blank pickup community area? Per the data dictionary, a blank usually means a pickup outside Chicago. Report this group as its own line. Don't drop it silently.
- Community areas are identified by number only. We don't have a name lookup in this folder, so report the numbers as they are.

### 3. How is the market split across companies?
- For each `company`, give trips, distinct taxis (`taxi_id`), total `trip_total`, and trips per taxi for the week.
- Show the top 10 companies by trip count. Group the rest as "All other". Give each company's share of trips and of revenue.
- Keep a blank or unknown company as its own row.

### 4. How do riders pay, and how much do they tip?
- What is the trip split by `payment_type`, by count and by share? Check the distinct values first and report them as they appear.
- For **card-type payments only**, what is the average tip as a percentage of `fare`? What share of those trips has a tip greater than zero? Give one figure overall and one per payment type.
- **Important:** cash tips are generally not recorded. Don't report a tip rate that includes cash trips, and don't present an "overall" tip rate that mixes cash and card.

## Data preparation (keep it light)

- Confirm the row count (135,768) and the date range. Note any trips that start outside 11–17 September.
- Before computing distance or fare figures, set clear exclusion rules, for example:
  - zero or missing `trip_seconds` or `trip_miles`
  - zero or negative `fare`
  - obviously implausible values, such as extreme durations, distances or totals
- Write down each rule and how many rows it removed. Use the full row set for trip counts in Q1 and Q3 unless a rule clearly applies.
- Spot-check that `trip_total` ≈ `fare + tips + tolls + extras`. Report the share of rows where it doesn't match, but don't try to reconcile them.
- Prefer medians to means for miles, duration and fare. A few extreme rows can distort averages.

## Deliverables

1. **A one-page summary** (Markdown or PDF):
   - 4–6 headline findings, one or two sentences each, with the key numbers.
   - A short caveats section (see below).
2. **Supporting tables and charts.** About one table or chart per question is enough. Suggested: trips by hour (weekday vs. weekend), top-10 pickup areas, company share, payment and tip summary.
3. **The notebook or script** used to produce the results. It should run start to finish on `trips.csv`, with exclusion rules visible in the code.

## Caveats to state in the summary

- This is one week of data. It may not represent other weeks or seasons.
- The City says not all trips are reported, though it believes most are. Treat all totals as lower bounds.
- Timestamps are rounded to 15 minutes. Census tracts are suppressed for some trips, and locations outside Chicago are often blank.
- Tip figures cover card payments only, because cash tips are generally not recorded.

## Out of scope

Please don't spend the session on any of the following:
- forecasting or modelling
- maps or geospatial work at census-tract level
- origin–destination flow analysis
- comparisons with other weeks or years
- comparisons with rideshare data
- external data joins (community-area names, weather, events)

If something interesting turns up, put it in a short "worth a follow-up" note at the end rather than pursuing it.

## Suggested time split

| Step | Time |
|---|---|
| Load, sanity checks, exclusion rules | ~30 min |
| Q1: timing | ~20 min |
| Q2: pickup areas | ~25 min |
| Q3: companies | ~20 min |
| Q4: payment and tips | ~25 min |
| Summary write-up and caveats | ~30 min |
| **Total** | **~2.5 hours** |

Questions about scope: ask before going beyond this brief.
