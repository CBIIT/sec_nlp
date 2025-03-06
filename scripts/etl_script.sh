#!/usr/bin/env bash

python sec_poc_tokenizer.py --dbname sec --host oel8-postgres-1 --user secapp --port 5432
python sec_poc_classifier.py --dbname sec --host oel8-postgres-1 --user secapp --port 5432
python sec_poc_expression_generator.py --dbname sec --host oel8-postgres-1 --user secapp --port 5432
