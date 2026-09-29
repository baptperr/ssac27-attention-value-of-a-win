"""Connection to the observatory Postgres, reusing its .env. Read-only by convention:
nothing in prep/ writes to the observatory database."""
import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

OBS = Path("/Users/baptisteperrier/code/baptperr/observatory")
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

for line in (OBS / ".env").read_text().splitlines():
    if line.strip() and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


def connect():
    return psycopg.connect(
        host="127.0.0.1", port=os.environ.get("POSTGRES_PORT", "5432"),
        dbname=os.environ["POSTGRES_DB"], user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"], row_factory=dict_row)


# The study's bout universe. Every other step reads bouts through this, so the
# exclusions are decided once:
#   tuf_house_exhibition  The Ultimate Fighter's in-house tournament fights --
#                         exhibitions, not on anyone's pro record. (TUF *Finales*
#                         are real UFC cards and stay.)
#   road_to_ufc           separate prospect-tournament cards, kept apart the same
#                         way the observatory keeps Contender Series apart.
#   not_ufc_regional      Sherdog event 63593, "UFC MMA - Ultimate Fight Canaa":
#                         a Brazilian regional show the observatory's "^UFC-" slug
#                         pattern catches by mistake.
UNIVERSE = """
select b.bout_id, e.event_id, e.external_id as event_sherdog_id, e.date,
       e.name as event_name, b.bout_order, b.is_main, b.is_title,
       b.weight_class, b.scheduled_rounds,
       case when e.name ~* 'ultimate fighter' and e.name !~* 'finale'
                 then 'tuf_house_exhibition'
            when e.name ~* 'road to ufc' then 'road_to_ufc'
            when e.external_id = '63593' then 'not_ufc_regional'
            else 'ufc_card' end as event_kind
  from bouts b join events e using(event_id)
 where e.promotion = 'UFC'
   and e.date between '2015-01-01' and current_date
"""
