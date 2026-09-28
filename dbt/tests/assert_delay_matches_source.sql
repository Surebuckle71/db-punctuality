-- Our computed delay must equal the source's delay_in_min, which is the departure delay,
-- or the arrival delay at the final stop. Returns the rows that disagree.
select stop_id, departure_delay_min, arrival_delay_min, source_delay_min
from {{ ref('stg_stop_events') }}
where source_delay_min is distinct from coalesce(departure_delay_min, arrival_delay_min)
