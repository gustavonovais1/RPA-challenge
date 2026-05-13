#!/bin/sh
set -e

mkdir -p /app/data /app/database /app/logs /app/screenshots /app/output
chown -R appuser:appuser /app/data /app/database /app/logs /app/screenshots /app/output 2>/dev/null || true
exec runuser -u appuser -- "$@"
