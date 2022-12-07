#                                 NV MAKEFILE
# This Makefile is used to automatically build and tag a Docker image containing
#                   the latest version of the nv framework.
#
# USAGE:
#  make [option]-[target]
#
# OPTIONS:
#  help     Prints this help message.
#  version    Prints the version of this Makefile.
#  build    Builds the image.
#  tag        Tags the image with the version number.
#  push     Tags and pushes the image to the Docker registry.
#
# TARGETS:
#  latest    The 'latest' tag.
#  version    The version number of the image.
#  <none>    Both 'latest' and the version number.
#
# Callum Morrison
# UNMND, Ltd. 2022
# <callum@unmnd.com>
#
# This file is part of nv.
#
# nv is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# nv is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# nv. If not, see <https://www.gnu.org/licenses/>.

APP_NAME = "nv"
REMOTE_REGISTRY = "ghcr.io/unmnd"
VERSION = $(shell cd nv && python3 -c "import nv;import importlib; print(importlib.metadata.version('nv-framework'))")

.PHONY: help build all tag push version

help:
	@awk '/^#/ {print $0}' $(MAKEFILE_LIST) | sed 's/^#//'

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