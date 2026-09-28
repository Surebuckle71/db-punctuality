"""Print the headline finding and its robustness checks from the dbt warehouse.

uv run python -m analysis.finding
"""

import duckdb

WAREHOUSE = "data/warehouse.duckdb"

CHECKS = {
    "Headline: share of scheduled time vs share of net delay, per month": """
        select service_month,
               round(sum(scheduled_min) filter (phase = 'at_station') / sum(scheduled_min), 3)
                   as station_share_of_schedule,
               round(sum(minutes_net) filter (phase = 'at_station') / sum(minutes_net), 3)
                   as station_share_of_net_delay,
               round(sum(minutes_net) filter (phase = 'at_station')
                     / (sum(scheduled_min) filter (phase = 'at_station') / 60), 1)
                   as station_net_min_per_sched_hour,
               round(sum(minutes_net) filter (phase = 'running')
                     / (sum(scheduled_min) filter (phase = 'running') / 60), 2)
                   as running_net_min_per_sched_hour
        from fct_delay_by_phase group by 1 order by 1""",
    "Gained vs recovered, per phase": """
        select service_month, phase, sum(minutes_gained) as gained,
               sum(minutes_recovered) as recovered,
               round(-sum(minutes_recovered) / sum(minutes_gained), 2) as share_recovered
        from fct_delay_by_phase group by 1, 2 order by 1, 2""",
    "By train type: station share of net delay": """
        select service_month, train_type, sum(n_events) as events,
               round(sum(minutes_net) filter (phase = 'at_station') / sum(minutes_net), 3)
                   as station_share
        from fct_delay_by_phase group by 1, 2 order by 1, 2""",
    "Weekday vs weekend: station share of net delay": """
        select service_month, dayofweek(service_date) in (0, 6) as is_weekend,
               round(sum(minutes_net) filter (phase = 'at_station') / sum(minutes_net), 3)
                   as station_share
        from fct_delay_by_phase group by 1, 2 order by 1, 2""",
    "Day-to-day spread of the station share": """
        with d as (
            select service_month, service_date,
                   sum(minutes_net) filter (phase = 'at_station') / sum(minutes_net) as share
            from fct_delay_by_phase
            where strftime(service_date, '%Y-%m') = service_month  -- drop spill-over days
            group by 1, 2 having sum(minutes_net) > 0
        )
        select service_month, count(*) as days, round(min(share), 2) as min,
               round(median(share), 2) as median, round(max(share), 2) as max
        from d group by 1 order by 1""",
    "Outliers: station share after dropping the 1% most extreme events": """
        with ev as (
            select service_month, 'running' as phase, run_delay_added_min as added
            from int_journey_legs
            union all
            select service_month, 'at_station', dwell_delay_added_min from int_station_dwells
        ),
        t as (select *, quantile_cont(abs(added), 0.99) over () as p99 from ev)
        select service_month,
               round(sum(added) filter (phase = 'at_station') / sum(added), 3) as station_share
        from t where abs(added) <= p99 group by 1 order by 1""",
    "Coverage: stops used for delay math": """
        select s.service_month, count(*) as stops,
               count(u.stop_id) as usable, round(count(u.stop_id) / count(*), 3) as share_usable
        from stg_stop_events s left join int_usable_stops u using (stop_id)
        group by 1 order by 1""",
}


def main() -> None:
    con = duckdb.connect(WAREHOUSE, read_only=True)
    for title, sql in CHECKS.items():
        print(f"\n## {title}")
        print(con.sql(sql))


if __name__ == "__main__":
    main()
