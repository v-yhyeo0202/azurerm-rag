#!/bin/bash

git submodule update --init --recursive

cd chunk-line-extractor
go mod init chunk-line-extractor
go mod tidy
go mod vendor
go build

cd ../builder
python -m venv venv-azurerm-rag-builder
source venv-azurerm-rag-builder/bin/activate
pip install -r requirements.txt
