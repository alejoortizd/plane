#!/bin/sh
envsubst '${API_UPSTREAM}' < /etc/nginx/templates/default.conf.template > /etc/nginx/nginx.conf
exec nginx -g 'daemon off;'
