#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/docker-compose.yml"

FRONTEND_SERVICE="webui-frontend"
BACKEND_SERVICE="webui-backend"

echo "Container status:"
docker compose -f "$COMPOSE_FILE" ps
echo

echo "Select service target:"
echo "1) frontend"
echo "2) backend"
echo "3) all"
read -r -p "Enter choice [1-3]: " service_choice

case "$service_choice" in
  1) services=("$FRONTEND_SERVICE") ;;
  2) services=("$BACKEND_SERVICE") ;;
  3) services=("$BACKEND_SERVICE" "$FRONTEND_SERVICE") ;;
  *) echo "Invalid service choice: $service_choice" >&2; exit 1 ;;
esac

echo
echo "Select action:"
echo "1) restart"
echo "2) rebuild"
echo "3) start"
read -r -p "Enter choice [1-3]: " action_choice

case "$action_choice" in
  1) docker compose -f "$COMPOSE_FILE" restart "${services[@]}" ;;
  2)
    docker compose -f "$COMPOSE_FILE" up -d --build --force-recreate "${services[@]}"
    docker image prune -f
    ;;
  3) docker compose -f "$COMPOSE_FILE" up -d "${services[@]}" ;;
  *) echo "Invalid action choice: $action_choice" >&2; exit 1 ;;
esac
