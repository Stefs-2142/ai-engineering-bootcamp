run-docker-compose:
	uv sync
	docker compose up --build

clean-notebook-outputs:
	jupyter nbconvert --clear-output --inplace notebooks/*/*.ipynb

run-evals-retriever:
	uv sync
	PYTHONPATH=${PWD}/apps/api:${PWD}/apps/api/src:$$PYTHONPATH:${PWD} uv run --env-file .env python -m evals.eval_retriever

# PostgreSQL commands
postgres-shell:
	docker exec -it $$(docker compose ps -q postgres) psql -U bootcamp -d amazon_products

postgres-count:
	docker exec -it $$(docker compose ps -q postgres) psql -U bootcamp -d amazon_products -c "SELECT COUNT(*) FROM products;"

# Run ETL notebook to load data into PostgreSQL
run-etl-postgres:
	uv sync
	uv run --env-file .env jupyter execute notebooks/week_1/06-etl-postgres.ipynb
