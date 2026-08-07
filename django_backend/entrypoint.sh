#!/bin/sh
set -e

# If cookie contents are provided via environment, write them to a file and set YT_DLP_COOKIEFILE
if [ -n "$YT_DLP_COOKIE_CONTENTS" ]; then
  printf '%s' "$YT_DLP_COOKIE_CONTENTS" > /app/www.youtube.com_cookies.txt
  export YT_DLP_COOKIEFILE=/app/www.youtube.com_cookies.txt
  echo "[entrypoint] Wrote cookie file to /app/www.youtube.com_cookies.txt"
fi

# Run the command
exec "$@"
