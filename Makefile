.PHONY: build stop start all

build:
	cd api && mvn clean install

stop:
	docker-compose down --remove-orphans

start:
	docker-compose up --build

all: build stop start
