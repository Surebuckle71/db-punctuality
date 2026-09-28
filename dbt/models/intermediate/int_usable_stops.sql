-- Stops we trust for delay math: not cancelled, on the planned route, sane delays and times.

select *
from {{ ref('stg_stop_events') }}
where not is_cancelled
  and not is_additional_stop
  and has_plausible_delay
  and has_consistent_times
