# Production Environment Checklist

Use this guide when you need to bootstrap or refresh the environment variables that power the production Docker stack. The goal is to create two shell-friendly files under `.envs/.production` and double-check that every required value is present before deploying.

## Directory Layout
```bash
.envs/
  .production/
    .config   # Django, third-party, and infrastructure configuration
    .keys     # Secrets such as Django secret key and database password
```

## Quick Checklist
- [ ] You have the production domain, email SMTP credentials, and Sentry DSN (if used).
- [ ] Database credentials are stored in a password manager or other secure vault.
- [ ] You are working on the host where `production.yml` will run (SSH into the server first).

## Step 1: Create the directory structure
```bash
mkdir -p .envs/.production
```

## Step 2: Scaffold the files
```bash
touch .envs/.production/.config .envs/.production/.keys
```

## Step 3: Populate `.config`
Fill in the non-secret configuration values. You can copy this template into your editor and replace the placeholders:

```
# General
DJANGO_APP_NAME=core
DJANGO_SETTINGS_MODULE=core.settings.production
DJANGO_ALLOWED_HOSTS=api.example.com
BACKEND_DOMAIN=api.example.com
BACKEND_URL=https://api.example.com
BACKEND_SLUG=production
ADMIN_URL=secure-admin

# Application behaviour
DJANGO_DEBUG=False
CORS_ALLOWED_ORIGINS=https://app.example.com,http://localhost:3000
DJANGO_WORKERS=4
SENTRY_DSN=https://your-sentry-dsn

# Database connection (mirrors docker compose service names)
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=app_production

# Email
EMAIL_HOST=smtp.sendgrid.net
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=super-secret-api-key
EMAIL_USE_TLS=True
EMAIL_PORT=587
```

Tips:
- Separate multiple origins in `CORS_ALLOWED_ORIGINS` with commas (no spaces).
- Keep comments for future editors but remove any placeholder values you do not use.

## Step 4: Populate `.keys`
Store secrets in this file. Keep it readable only by trusted users (`chmod 600`). Example:

```
# Secrets
DJANGO_SECRET_KEY=replace-with-a-long-random-string
POSTGRES_USER=app_user
POSTGRES_PASSWORD=set-a-strong-password
```

Generate a fresh Django secret key with:
```bash
python3 - <<'PY'
import secrets,string
alphabet = string.ascii_letters + string.digits + string.punctuation
print(''.join(secrets.choice(alphabet) for _ in range(64)))
PY
```

## Step 5: Secure the files
```bash
chmod 600 .envs/.production/.config .envs/.production/.keys
```

## Step 6: Verify variables load correctly
```bash
set -a
source .envs/.production/.config
source .envs/.production/.keys
set +a

# Spot-check a few values
env | grep -E "(DJANGO_APP_NAME|POSTGRES_DB|DJANGO_SECRET_KEY)"
```
If anything looks wrong, open the file, correct it, and rerun the snippet above.

## Step 7: Plug into Docker Compose
When the files look good, docker compose picks them up automatically:
```bash
docker compose -f production.yml config | grep DJANGO_APP_NAME
```
You should see the interpolated value instead of a blank string.

## Maintenance Tips
- Re-run Steps 6 and 7 after every edit to catch typos early.
- Rotate credentials periodically and update both `.config` and `.keys` in the same session.
- Back up these files securely; do not commit them to version control.

Happy deploying!
