# Production Nginx Notes

This folder contains the assets used by the `nginx` service in `production.yml`. The Dockerfile extends `nginx:latest`, injects our config, and runs an entrypoint script that templates the domain before starting Nginx.

## Files
- `Dockerfile` - builds the runtime image.
- `nginx.conf` - reverse proxy that forwards traffic to the Django container, serves static files from `/staticfiles`, and exposes media from `/media`.
- `entrypoint.sh` - replaces `$BACKEND_DOMAIN` inside `nginx.conf` using `envsubst` and launches Nginx in the foreground.

## Usage
1. Set `BACKEND_DOMAIN` in `.envs/.production/.config`.
2. Build and run the production stack:
   ```bash
   docker compose -f production.yml up -d nginx
   ```
3. Static files must exist in `./data/django_template_production_staticfiles`; run `collectstatic` via the Django container before first boot.

If you need to tweak headers or caching rules, edit `nginx.conf` and rebuild the image with `docker compose -f production.yml build nginx`.
