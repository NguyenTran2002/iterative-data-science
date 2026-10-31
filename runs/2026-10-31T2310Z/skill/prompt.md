/iterative-data-science The data is in `trips.csv` in this folder. Do the analysis in a Jupyter notebook named `analysis.ipynb` in this folder.

# Brief: Chicago Taxi Trips, Week of 11–17 September 2023

## Purpose

We want a descriptive picture of one ordinary week of Chicago taxi activity: when people ride, where trips start, how they pay, and which companies carry the trips. It is a routine summary, not a modelling exercise. Plan on one sitting of about two to three hours.

## Data and setup

- You will work alone in one folder. It contains `trips.csv` (135,768 trips, Monday 2023-09-11 to Sunday 2023-09-17) and `dataset.md`, which describes the columns. Read `dataset.md` before you start.
- Software: Python 3.13 with pandas, numpy, matplotlib, seaborn, scipy, statsmodels, scikit-learn and Jupyter. You have internet access and may install packages, but shouldn't need to.
- Deliverable: one Jupyter notebook named `analysis.ipynb`, saved in that folder.
- No one will be available to answer questions while you work. If something is unclear, make a reasonable assumption, state it in the notebook, and carry on.

## Business questions

1. **When is demand highest?** Count trips by day of week and by hour of trip start. Name the busiest and quietest periods and how weekdays differ from weekends.
2. **Where do trips start?** List the top 10 pickup community areas by trip count and by total `trip_total`. Report the share of trips with no pickup community area (mostly trips starting outside Chicago, per `dataset.md`).
3. **How do riders pay and tip?** For each `payment_type`, give the number of trips, total revenue and average fare. Calculate tips as a percentage of fare. Cash tips are generally not recorded, so don't compare tipping across payment types as like for like.
4. **Which companies carry the trips?** For the top 10 companies by trip count, show trips, total revenue, share of all trips, and number of distinct taxis (`taxi_id`).

## Data cautions

- Timestamps are rounded to the nearest 15 minutes; use `trip_seconds` for duration.
- Not all trips are reported. Describe the figures as reported trips, not total market volume.
- Before you summarise, check for missing values and implausible values, such as zero or extreme miles, durations or fares, and trips where `trip_total` doesn't match the sum of its parts. Decide how to treat them, state how many rows each decision affects, and apply it consistently.
- Census tracts are often suppressed. Use community areas for geography.

## Out of scope

Predictive models, statistical testing beyond simple comparisons, maps, outside data such as community area names or weather, and comparisons with other weeks. Note anything else interesting in one sentence as a possible follow-up.

## What the notebook should contain

1. A short summary at the top: three to five bullet points answering the questions.
2. Data loading and a cleaning section that lists every assumption and exclusion.
3. One section per question, each with a table or chart and a short plain-language takeaway.
4. Titled charts with labelled axes; the notebook must run top to bottom without errors.
