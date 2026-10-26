# Why SQLite first, then PostgreSQL

Written on 2026-10-26.

The site reads my profile, resume and projects from a database. It started on
SQLite and now runs on PostgreSQL. Both use the same code: the app only changes
which database it connects to (`DATABASE_URL`), and Alembic builds the same
tables in either one.

## SQLite on the Azure VM

SQLite was the right place to start:

- **Nothing extra to run.** SQLite is a single file and comes built into
  Python, so the VM needed no database server to install, secure or keep
  running.
- **The site is small and mostly read-only.** Visitors only read pages, and I'm
  the only one who changes content, so a single-file database was enough.
- **Easy to back up and copy.** One file holds everything, and `sqlite3 .backup`
  takes a safe snapshot even while the site is running. That snapshot is what
  I later copied into Postgres.

## PostgreSQL on Railway

When I moved the site to Railway, I switched to Railway's PostgreSQL:

- **Railway doesn't keep files between deploys.** Each deploy starts a fresh
  container, so a SQLite file next to the app would be wiped every time I
  pushed to `main`. Postgres runs as its own service, so the data stays put
  however often the app is redeployed.
- **It's managed for me.** Railway runs the database in the same project and
  connects it to the app over a private network, so it isn't open to the
  internet.
- **It's stricter.** Postgres rejects data SQLite quietly accepts, such as text
  longer than a column allows. The tests run on both, which catches those
  problems before a deploy does.
- **It moves with me.** AWS offers managed PostgreSQL too, so the move to AWS
  after the midterm won't need a different database.

## What stayed on SQLite

Local development and the tests still use SQLite by default, because it needs
no setup. Setting `TEST_DATABASE_URL` runs the same tests against a local
Postgres.

## The trade-off

Postgres is a separate service, so it can be unreachable while the app is up.
When that happens the profile still shows, project pages say "Projects
temporarily unavailable" with an HTTP 503, and projects come back on the next
request once the database recovers. Postgres also uses some of the Railway
trial credit (see [costs](costs.md)).
