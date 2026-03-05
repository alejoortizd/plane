#!/bin/sh
export DNS_RESOLVER=$(awk '/^nameserver/{print $2; exit}' /etc/resolv.conf)
: "${DNS_RESOLVER:=127.0.0.11}"
envsubst '${API_UPSTREAM} ${DNS_RESOLVER}' < /etc/nginx/templates/default.conf.template > /etc/nginx/nginx.conf
exec nginx -g 'daemon off;'
