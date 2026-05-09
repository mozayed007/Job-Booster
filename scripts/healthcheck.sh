#!/bin/sh
set -e

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)

if [ "$HTTP_CODE" -eq 200 ]; then
    exit 0
else
    exit 1
fi
