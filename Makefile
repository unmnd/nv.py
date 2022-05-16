#
# ------------------------------------------------------------------------------
#                                 NV MAKEFILE
# ------------------------------------------------------------------------------
#
# This Makefile is used to automatically build and tag a Docker image containing
# the latest version of the nv framework.
#
# USAGE:
#  make [option]-[target]
#
# OPTIONS:
#  help		Prints this help message.
#  version	Prints the version of this Makefile.
#  build	Builds the image.
#  tag		Tags the image with the version number.
#  push		Tags and pushes the image to the Docker registry.
#
# TARGETS:
#  latest	The 'latest' tag.
#  version	The version number of the image.
#  <none>	Both 'latest' and the version number.
#
# Callum Morrison, 2021
# UNMND, Ltd. 2021
# <callum@unmnd.com>
#
# All Rights Reserved

APP_NAME = "nv"
REMOTE_REGISTRY = "cr.xdgfx.com"
VERSION = $(shell cd nv && python3 -c "import version; print(version.__version__)")

.PHONY: help build all tag push version

help:
	@awk '/^#/ {print $0}' $(MAKEFILE_LIST)


build:
	docker build -t $(APP_NAME) .


tag: tag-latest tag-version

tag-latest:
	@echo "Tagging image as 'latest'"
	docker tag $(APP_NAME) $(REMOTE_REGISTRY)/$(APP_NAME):latest

tag-version:
	@echo "Tagging image as '$(VERSION)'"
	docker tag $(APP_NAME) $(REMOTE_REGISTRY)/$(APP_NAME):$(VERSION)


push: push-latest push-version

push-latest: tag-latest
	@echo "Pushing image as 'latest'"
	docker push $(REMOTE_REGISTRY)/$(APP_NAME):latest

push-version: tag-version
	@echo "Pushing image as '$(VERSION)'"
	docker push $(REMOTE_REGISTRY)/$(APP_NAME):$(VERSION)


all: build push


version:
	@echo "nv version: $(VERSION)"