FROM nginx:latest

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

COPY nginx.conf /etc/nginx/nginx.conf

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]