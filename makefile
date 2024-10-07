.PHONY: deploy-all stop-all restart-all update-dags logs-airflow logs-elasticsearch logs-fastapi

deploy-all:
	docker-compose up -d

stop-all:
	docker-compose down

restart-all:
	docker-compose down
	docker-compose up -d

update-dags:
	docker cp ./dags/. airflow-webserver:/opt/airflow/dags
	docker-compose restart airflow-webserver airflow-scheduler

logs-airflow:
	docker-compose logs airflow-webserver airflow-scheduler

logs-elasticsearch:
	docker-compose logs elasticsearch

logs-fastapi:
	docker-compose logs fastapi

setup-env:
	cp .env.example .env
	echo "AIRFLOW_UID=$$(id -u)" >> .env
