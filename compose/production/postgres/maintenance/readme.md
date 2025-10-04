# Postgres Maintenance Toolkit

This directory bundles the shell helpers used to back up, inspect, and restore the production PostgreSQL database when you deploy with `production.yml`. Each script is meant to be executed inside the `postgres` service container so it has direct access to the database files and the shared `/backups` volume (mounted from `./data/backups` on the host).

## Prerequisites
- The production environment variables are populated (see `envs/production/readme.md`).
- `POSTGRES_USER` is **not** set to the default `postgres` user; the scripts will refuse to run otherwise.
- You are running commands from the project root so paths resolve correctly.
- Docker Compose v2 (`docker compose`) is available on the host.

## Quick Reference
```
Task              Command
--------------    -------------------------------------------------------------
Create backup     docker compose -f production.yml run --rm postgres backup
List backups      docker compose -f production.yml run --rm postgres backups
Restore backup    docker compose -f production.yml run --rm postgres restore <name>
```
You can replace `run --rm` with `exec` if the container is already running.

Backups are stored under `/backups/` inside the container and appear on the host inside `./data/backups`. Each run creates a dated folder (for example `backup_20250904`) using the parallel directory format (`pg_dump -Fd`).

## Creating a Backup
1. Ensure the `postgres` container can reach the database (usually by running `docker compose -f production.yml up -d postgres`).
2. Trigger the backup:
   ```bash
   docker compose -f production.yml run --rm postgres backup
   ```
3. On success you will see a `SUCCESS` message and a new folder under `./data/backups`. The script also creates the `/backups` directory if it is missing.

### What the script does
- Loads connection details from the environment.
- Verifies that `POSTGRES_USER` is not `postgres`.
- Uses `pg_dump -Fd -j 4` to write a directory-formatted dump named `backup_<YYYYMMDD>`.

## Listing Existing Backups
To view every backup folder currently stored:
```bash
docker compose -f production.yml run --rm postgres backups
```
The script prints the available directories. If nothing is found it reminds you that the folder is empty. You can also inspect the mounted directory on the host:
```bash
ls -1 data/backups
```

## Restoring a Backup
Restoring replaces the current database with the contents of a backup. Plan downtime and ensure the application can be offline while the operation completes.

1. Choose the folder or file to restore. Use the `backups` command first if you are unsure of the exact name.
2. Run the restore command with that name:
   ```bash
   docker compose -f production.yml run --rm postgres restore backup_20250904
   ```
   If you stored a compressed SQL file in `/backups`, specify the filename instead (for example `snapshot.sql.gz`).

### What the script does
- Validates that an argument was provided and that the matching folder or file exists.
- Terminates active connections to the target database.
- Drops and recreates the database owned by `POSTGRES_USER`.
- Restores either from a directory-format dump (`pg_restore -j 4`) or from a compressed SQL file streamed through `psql`.

If anything fails the script prints an `ERROR` message and exits with a non-zero status so CI or automation can detect it.

## Housekeeping Tips
- Rotate backups manually by pruning old folders in `data/backups` once you confirm newer dumps are healthy.
- Consider scheduling the `backup` command via cron or a managed task runner, binding the same directory into the job.
- Keep the `/backups` mount on reliable storage; losing it means you lose every offline snapshot.
- After a restore, smoke-test the application and run `docker compose -f production.yml logs postgres` to review the database startup output.

Stay disciplined about automation, and these helpers will keep your production data safe and recoverable.
