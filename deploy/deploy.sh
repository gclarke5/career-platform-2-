#!/usr/bin/env bash
# Deploy the latest commit on the AWS EC2 server. Run on the server as ubuntu:
#   ~/career-platform/deploy/deploy.sh            # deploys main
#   BRANCH=aws-migration ~/career-platform/deploy/deploy.sh
# Never seeds: migrations only, so live content is never overwritten.
set -euo pipefail

APP_DIR=/home/ubuntu/career-platform
ENV_FILE=/etc/career-platform.env
BRANCH="${BRANCH:-main}"
UV="$HOME/.local/bin/uv"

cd "$APP_DIR"
git fetch --prune origin
git checkout -q "$BRANCH"
git pull --ff-only -q origin "$BRANCH"
sha=$(git rev-parse HEAD)
echo "Deploying $BRANCH at ${sha:0:7}"

"$UV" sync --frozen --no-dev
"$UV" run --no-sync --env-file "$ENV_FILE" alembic upgrade head

# Record the commit so /health reports what's live.
if sudo grep -q '^GIT_COMMIT_SHA=' "$ENV_FILE"; then
  sudo sed -i "s/^GIT_COMMIT_SHA=.*/GIT_COMMIT_SHA=$sha/" "$ENV_FILE"
else
  echo "GIT_COMMIT_SHA=$sha" | sudo tee -a "$ENV_FILE" >/dev/null
fi

sudo systemctl restart career-platform

for _ in $(seq 1 20); do
  if health=$(curl -fsS http://127.0.0.1:8000/health 2>/dev/null); then
    echo "$health"
    if [[ "$health" == *'"fallback":false'* && "$health" == *"\"commit\":\"${sha:0:7}\""* ]]; then
      echo "Deploy OK"
      exit 0
    fi
  fi
  sleep 1
done
echo "Deploy FAILED: /health did not report a healthy database at ${sha:0:7}" >&2
sudo journalctl -u career-platform -n 30 --no-pager >&2
exit 1
