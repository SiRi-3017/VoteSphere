# Cloud-Based Online Voting System — starter backend

A beginner-friendly Flask + MySQL backend scaffold. No frontend or voting routes are included yet.

## Setup

1. Create and activate a virtual environment.
2. Install dependencies: `pip install -r requirements.txt`
3. Create a MySQL database, for example:

   ```sql
   CREATE DATABASE cloud_voting CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

4. Copy `.env.example` to `.env` and fill in your local MySQL values and a strong `SECRET_KEY`.
5. Initialize migrations and create tables:

   ```bash
   flask db init
   flask db migrate -m "Initial database schema"
   flask db upgrade
   ```

6. Start the development server:

   ```bash
   flask run
   ```

The root endpoint returns a small JSON health message.

## Important next-step validation

The database unique constraint prevents a user from having two vote rows for the same election. Before accepting a vote, application logic must also verify that the selected candidate belongs to that election, that the election is open, and that the authenticated user has the voter role. Those checks are intentionally not implemented in this scaffold.
