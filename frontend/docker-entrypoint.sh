#!/bin/sh

# Write env variables to a JS file for the frontend to read
cat <<EOF > /usr/share/nginx/html/env-config.js
window._env_ = {
  REACT_APP_API_URL: "${REACT_APP_API_URL}"
};
EOF

exec "$@"

