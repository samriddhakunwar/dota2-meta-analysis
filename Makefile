# Usage: make all ZIP=path/to/archive.zip   (default: ../archive.zip)
PY  ?= python
ZIP ?= ../archive.zip
RUN  = PYTHONPATH=src $(PY) -m

.PHONY: all data analysis figures test

all: data analysis figures test

data:            ## selective unzip -> raw DuckDB tables -> clean tables + Parquet
	$(RUN) dota_meta.load $(ZIP)
	$(RUN) dota_meta.clean

analysis:        ## run sql/*.sql, save result tables to data/processed/
	$(RUN) dota_meta.metrics

figures:         ## render PNG charts to reports/figures/
	$(RUN) dota_meta.charts

test:
	$(PY) -m pytest -q
