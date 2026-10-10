AF = docker compose exec -T airflow-scheduler airflow

up:        ## build + start Airflow (8080) and Spark (master UI 8082)
	docker compose up -d --build
down:
	docker compose down
smoke:     ## prove Airflow -> Spark cluster works
	$(AF) dags test smoke_spark
pipeline:  ## full run: ingest everything for one day, then Bronze -> Gold -> data/merchant_scores.json
	$(AF) dags test olist_bronze_ingest
	$(AF) dags test cfpb_complaints_incremental 2026-09-22
	$(AF) dags test fx_rates_daily 2026-09-22
	$(AF) dags test stripe_events_synthetic 2026-09-22
	$(AF) dags test mdt_build_gold
unpause:   ## let the scheduler run the daily DAGs (they backfill from 2026-09-20)
	$(AF) dags unpause olist_bronze_ingest; $(AF) dags unpause cfpb_complaints_incremental; \
	$(AF) dags unpause fx_rates_daily; $(AF) dags unpause stripe_events_synthetic; $(AF) dags unpause mdt_build_gold
reset-lake:
	rm -rf lake/*
