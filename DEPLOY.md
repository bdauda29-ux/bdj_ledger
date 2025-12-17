# Deployment Guide

This application is configured for easy deployment on **Render**, a cloud platform that supports Python and PostgreSQL.

## Option 1: Deploy to Render (Recommended)

1.  **Push to GitHub/GitLab**:
    - Ensure this project is pushed to a repository on GitHub or GitLab.

2.  **Create a Render Account**:
    - Go to [render.com](https://render.com) and sign up (you can use your GitHub account).

3.  **Create a New Blueprint**:
    - In the Render Dashboard, click **New +** and select **Blueprint**.
    - Connect your GitHub/GitLab account and select this repository.
    - Render will automatically detect the `render.yaml` file.

4.  **Deploy**:
    - Click **Apply**. Render will:
        - Build the Docker image for your app.
        - Create a managed PostgreSQL database.
        - Link them together automatically.

    *Note: The `render.yaml` is set to use the 'free' plan for both the web service and the database. The free database expires after 90 days. For production use, you may want to upgrade the database plan to 'starter'.*

## Option 2: Deploy to Vercel

Vercel is great for serverless deployments.

1.  **Install Vercel CLI** (optional) or connect your GitHub repository to Vercel.
2.  **Database Configuration**:
    - Vercel uses ephemeral file systems, so **SQLite (the default) will reset** on every deployment or cold start.
    - **Highly Recommended**: Create a PostgreSQL database (e.g., using Vercel Postgres, Neon, or Supabase).
    - Add the `POSTGRES_URL` environment variable in your Vercel project settings.
3.  **Deploy**:
    - If using the CLI: Run `vercel`.
    - If using Git: Push to main, and Vercel will auto-deploy if connected.

## Option 3: Deploy to Heroku

1.  **Install Heroku CLI**: Download and install the Heroku CLI.
2.  **Login**: Run `heroku login`.
3.  **Create App**: Run `heroku create`.
4.  **Add Database**: Run `heroku addons:create heroku-postgresql:mini`.
5.  **Deploy**:
    ```bash
    git push heroku main
    ```

## Environment Variables

The application uses the following environment variables (automatically handled by `render.yaml`):

- `POSTGRES_URL`: Connection string for the PostgreSQL database.
- `SECRET_KEY`: Security key for sessions (generated automatically).
- `SMTP_*`: Email settings (optional, configure in Render dashboard if needed).
