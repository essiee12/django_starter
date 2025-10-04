#!/bin/sh

# Replace the domain name placeholder in nginx.conf with the actual value from the environment
envsubst '$BACKEND_DOMAIN' < /etc/nginx/nginx.conf > /etc/nginx/nginx.conf.tmp \
&& mv /etc/nginx/nginx.conf.tmp /etc/nginx/nginx.conf

# Start Nginx
nginx -g 'daemon off;'