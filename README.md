# Graduation report API

A Flask REST API for managing final-year project reports at Tunis Business School. Built over a sequence of Web Services assignments, the project grew from in-memory request handling to a Dockerized MySQL application with JWT authentication and request logging.

## Run locally

1. Install Docker with Compose and start the Docker engine.
2. Copy `.env.example` to `.env`. Set a separate random value for each blank entry. Run `openssl rand -hex 32` once per value.
3. Run `docker compose up --build -d`. The first start initializes the student, report and request history tables.
4. Open `http://localhost:5003/reports`. A fresh database returns `{"reports":[]}`.
5. Import `postman/PFE.postman_collection.json` into Postman. Set the collection's username and password locally to match your configuration. Run **Login**, **Create student**, **Create report**, then **Search reports**. The requests save the token and sample record IDs for subsequent requests.

## Data and routes

A student can have a report for each declared major. A foreign key links each report to its student, and deleting a student removes their reports. Request history records the HTTP method, path, response status and timestamp.

| Resource | Operations | Access |
|---|---|---|
| `/auth/login`, `/auth/refresh` | POST for an access token or renewal | Credentials or refresh token |
| `/students`, `/students/{id}` | List, create, read, update, delete | Access token |
| `/reports`, `/reports/{id}` | List, create, read, update, delete | Public reads, authenticated writes |
| `/reports/search` | GET with optional keyword, major and type filters | Public |

The Python implementation is in `app.py`, database connection settings in `db.py`, allowed majors in `models.py`, and the MySQL schema in `sql/init.sql`. Compose persists records in a named volume. Use `docker compose down` to stop the application.

## Tests

With Python dependencies installed (`python -m pip install -r requirements.txt`), run `python -m unittest discover -s tests -v`. The tests exercise Flask authentication and request validation with an isolated database mock. The Postman workflow exercises the running API and MySQL together.
