#!/bin/sh
DNS_RESOLVER=$(awk '/^nameserver/{print $2; exit}' /etc/resolv.conf)
: "${DNS_RESOLVER:=127.0.0.11}"
case "$DNS_RESOLVER" in
  *:*) DNS_RESOLVER="[${DNS_RESOLVER}]" ;;
esac
export DNS_RESOLVER
envsubst '${API_UPSTREAM} ${DNS_RESOLVER}' < /etc/nginx/templates/default.conf.template > /etc/nginx/nginx.conf
exec nginx -g 'daemon off;'
