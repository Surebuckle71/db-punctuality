-- Delay added while running between stations vs while standing at stations,
-- per day and train type, next to the scheduled minutes of each phase.
-- Answers: where in a journey does delay build up, relative to how long trains spend there?

with events as (
    select
        service_month,
        cast(from_departure_planned as date) as service_date,
        train_type,
        'running'                            as phase,
        run_delay_added_min                  as added_min,
        scheduled_run_min                    as scheduled_min
    from {{ ref('int_journey_legs') }}

    union all

    select
        service_month,
        cast(arrival_planned as date),
        train_type,
        'at_station',
        dwell_delay_added_min,
        scheduled_dwell_min
    from {{ ref('int_station_dwells') }}
)

select
    service_month,
    service_date,
    train_type,
    phase,
    count(*)                        as n_events,
    sum(scheduled_min)              as scheduled_min,
    sum(greatest(added_min, 0))     as minutes_gained,
    sum(least(added_min, 0))        as minutes_recovered,
    sum(added_min)                  as minutes_net
from events
group by all
