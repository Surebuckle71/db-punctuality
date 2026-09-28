# Data license

The code in this repository is MIT-licensed (see `LICENSE`). The data is not.

- **Original source:** Deutsche Bahn, Timetables API (DB API Marketplace),
  licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
  Product page: https://developers.deutschebahn.com/db-api-marketplace/apis/product/timetables
- **Collected and published by:** Piet Brömmel,
  [piebro/deutsche-bahn-data](https://github.com/piebro/deutsche-bahn-data)
  ([Hugging Face dataset](https://huggingface.co/datasets/piebro/deutsche-bahn-data)).

Raw data is not stored in this repository; `ingest/fetch_months.py` downloads it.
The files in `data/marts/` are aggregates derived from the data above and are shared
under the same CC BY 4.0 terms, with attribution to Deutsche Bahn.

Note: the API product page also points to the terms of the "Web-Bahnhofstafel" website,
which restrict commercial redistribution without DB's written consent. This project is a
non-commercial portfolio analysis. Check with DB before any commercial reuse.
