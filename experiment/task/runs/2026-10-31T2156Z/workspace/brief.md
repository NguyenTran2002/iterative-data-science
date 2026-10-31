# Analysis Brief: Chicago Taxi Trips, Week of 11–17 September 2023

**To:** Data Analyst
**From:** Operations Manager
**Data:** `trips.csv`. One week of taxi trips reported to the City of Chicago, Monday 2023-09-11 to Sunday 2023-09-17, 135,768 rows. Column definitions are in `dataset.md`.
**Time budget:** One sitting of about 2–3 hours.

---

## Why we're asking

We want a clear picture of a normal week of taxi activity in the city: when people ride, where trips start, how money flows through the trips, and how the market splits across companies. This is a baseline snapshot, not a deep study. Plain, reliable numbers beat clever ones.

## Questions to answer

### 1. When does demand happen?
- How many trips started on each day of the week? How does an average weekday compare with Saturday and Sunday?
- What is the hourly pattern of trip starts? Show weekdays and weekends separately. Which hours are the peaks?

*Use `trip_start_timestamp`. Start times are rounded to the nearest 15 minutes, so hourly buckets are fine. Don't try to analyse anything finer than 15 minutes.*

### 2. What does a typical trip look like, and how much revenue did the week bring in?
- Total trips, total `fare`, and total `trip_total` for the week, plus the same figures for each day.
- Median and average `trip_miles`, `trip_seconds` (shown in minutes), and `fare` per trip.
- Median fare per mile, calculated only on trips with a sensible distance (see data rules below).

*Use `trip_seconds` for trip duration. Don't calculate duration from the two timestamps, because both are rounded.*

### 3. How do tips vary by payment type?
- Trip count and share of trips for each `payment_type`.
- Average tip and tip rate (total `tips` ÷ total `fare`) for each payment type.
- For card-type payments only: the share of trips that included a tip.

*Important: cash tips generally are not recorded, so cash trips will look like they have almost no tips. Say this clearly next to any tipping figure, and don't present a single overall tip rate that blends cash and card trips.*

### 4. Which companies and pickup areas account for the business?
- Trips, total `trip_total`, and number of distinct `taxi_id`s for each `company`. Show the top 10 by trips and put everyone else in an "All other" row. Add trips per active taxi per day as a rough measure of how busy each fleet is.
- The top 10 `pickup_community_area`s by trip count, with each one's share of all trips. Report how many trips have a blank pickup community area. Blank usually means the trip started outside Chicago, so treat these as their own "Outside / unknown" group and don't drop them without saying so.

*Report community areas by their number. Don't spend time looking up names or drawing maps.*

## Data rules (keep this to about 30 minutes)

Do a quick quality pass. Don't try to perfect the data. At minimum:

- Count rows with missing or zero `trip_seconds`, `trip_miles`, or `fare`, and rows with extreme values. Pick simple, stated cut-offs for what counts as extreme (for example, very long durations, very long distances, or very high fares) and apply them consistently.
- Check that `trip_total` is roughly equal to `fare + tips + tolls + extras`. Report how often it isn't.
- Check that `trip_id` is unique.
- **Default approach:** keep all rows for trip counts (Q1, Q4). Exclude the flagged rows only from the per-trip averages, medians, and fare-per-mile figures (Q2) and from the tipping figures (Q3). Write down how many rows each rule removes.

Keep a short list of what you excluded and why. That list matters as much as the answers.

## Deliverables

1. **A one- to two-page summary** (Markdown or PDF). Put 4–6 headline findings at the top, then one short section per question with a small table or chart. Finish with a "Data caveats" section.
2. **The code** (notebook or script) that reproduces every number in the summary from `trips.csv`.
3. **A data-quality note** (it can go in the summary appendix) listing each cleaning rule and the number of rows it affected.

## Out of scope

- Comparisons with other weeks, months, or years, and any explanation that needs outside data (weather, events, and so on). This is a single-week snapshot.
- Census-tract-level analysis, maps, and work using the latitude/longitude columns.
- Forecasting, modelling, or statistical testing.
- Investigating individual taxis or drivers.

If something interesting turns up outside these questions, put it in one line under "Possible follow-ups". Don't chase it in this sitting.

## Suggested time plan

| Step | Time |
|---|---|
| Load the data, check columns, quality pass, set data rules | 30–40 min |
| Q1: demand by day and hour | 20 min |
| Q2: trip profile and revenue | 20 min |
| Q3: tips by payment type | 20 min |
| Q4: companies and pickup areas | 25 min |
| Write the summary and caveats | 30 min |
| **Total** | **about 2.5–3 hours** |

## Caveats to carry into the write-up

- Not every trip is reported to the City, though the City believes most are. Treat totals as close to complete, not exact.
- Start and end times are rounded to the nearest 15 minutes.
- Cash tips are generally not recorded.
- Pickup and dropoff locations are often blank for trips outside Chicago, and census tracts are sometimes hidden for privacy.
