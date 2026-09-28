-- Guard against an upstream change: fail if more than 1% of non-cancelled stops
-- have implausible delays or impossible times.
select
    service_month,
    avg((not has_plausible_delay or not has_consistent_times)::int) as bad_share
from {{ ref('stg_stop_events') }}
where not is_cancelled
group by service_month
having bad_share > 0.01
