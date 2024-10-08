.PHONY: up down

up:
	docker-compose up -d

down:
	docker-compose down

install-docker:
	sudo apt update
	sudo apt install -y docker.io
	sudo systemctl start docker
	sudo systemctl enable docker
	sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$$(uname -s)-$$(uname -m)" -o /usr/local/bin/docker-compose
	sudo chmod +x /usr/local/bin/docker-compose
	sudo usermod -a -G docker $$(whoami)
	newgrp docker
