PROJECT_NAME=split
PWD=$(shell pwd)
REGISTRY_NAME=$(shell grep REGISTRY_NAME .env | cut -d "=" -f2)
IMAGE_PATH = /guild/split
TAG = latest

# Make sure poetry virtual env is active
local:
	poetry run python ./raidsplit

azure_login:
	az acr login --name $(REGISTRY_NAME)

build:
	docker build -t $(PROJECT_NAME):$(TAG)  . 

run:
	docker run -e API_TOKEN=$(API_TOKEN) \
			-e DB_PATH=$(DB_PATH) \
			-v $(PWD)/$(DB_PATH):/service/$(DB_PATH) \
			   $(PROJECT_NAME):$(TAG) $(cmd)

# Go into the container
inspect:
	docker run -it /bin/bash

generate_oauth:
	$(MAKE) run CLIENT_ID=$(CLIENT_ID) \
		        GUILD_ID=$(GUILD_ID) \
				cmd="poetry run python ./scripts/generate_oauth.py"

publish:
	$(MAKE) build PROJECT_NAME=$(REGISTRY_NAME)$(IMAGE_PATH) TAG=$(TAG)
	docker push $(REGISTRY_NAME)$(IMAGE_PATH):$(TAG)
