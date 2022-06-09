#!/usr/bin/env bash

set -x
broadwayd :5 &
python serve.py -p 8080 -P 8085 -d "${1:-/data}"
