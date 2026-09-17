# Career Platform

## Local Codespaces

```bash
python -m pip install -r requirements.txt
uvicorn app.main:create_app --factory --reload
```

The public site is available at `http://127.0.0.1:8000`. The `/health`
endpoint reports database availability and whether degraded fallback mode is
active. The homepage continues to render the core profile when the database is
unavailable.

## Azure VM

Install Python 3.12+, install the requirements, and run:

```bash
uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000
```

Persist `DATABASE_URL` to a durable VM path. Keep the fallback profile deployed
with the application so identity, summary, contact links, and the primary CTA
remain available during database outages.