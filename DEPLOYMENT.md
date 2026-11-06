# Backend and Hosting deployment

Deployed on 2026-11-06:

- Hosting: https://moatalk-e6fe1.web.app
- Backend: https://moatok-backend-523175594353.us-central1.run.app
- Runtime identity: `moatok-backend@moatalk-e6fe1.iam.gserviceaccount.com`
- Cloud Run: `us-central1`, 512 MiB, 1 CPU, 0 minimum / 2 maximum instances.
- Billing is linked to the user-selected account ending `1DB6EB`.
- Verified Hosting `/health` returns HTTP 200 JSON; unauthenticated `/api/v1/messages`
  returns HTTP 401 JSON with `missing_token`.
- Firebase anonymous sign-in is currently disabled (`ADMIN_ONLY_OPERATION`). Use
  an enabled sign-in method in Settings to access protected briefing data.

Health and API requests bypass browser caches so responses cached before the
backend deployment do not continue to show a disconnected server. Hosting also
sends `Cache-Control: no-store` for these routes.

The target project is `moatalk-e6fe1`. Cloud Billing must be linked (Firebase
Blaze plan) before enabling Cloud Run or building its container. Do not deploy
the Hosting rewrites until the backend has successfully deployed.

Run commands from the repository root. Keep the existing gcloud default project
unchanged; every command below explicitly selects this project's resources.

```sh
export CLOUDSDK_METRICS_ENVIRONMENT=datacloud.codex
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com --project moatalk-e6fe1

# Create once. For subsequent deployments, reuse this account and its grants.
gcloud iam service-accounts create moatok-backend --display-name='Moatok backend' --project moatalk-e6fe1
gcloud projects add-iam-policy-binding moatalk-e6fe1 --member=serviceAccount:moatok-backend@moatalk-e6fe1.iam.gserviceaccount.com --role=roles/datastore.user --condition=None
gcloud projects add-iam-policy-binding moatalk-e6fe1 --member=serviceAccount:moatok-backend@moatalk-e6fe1.iam.gserviceaccount.com --role=roles/firebasecloudmessaging.admin --condition=None

gcloud run deploy moatok-backend --project moatalk-e6fe1 --region us-central1 --source . --service-account moatok-backend@moatalk-e6fe1.iam.gserviceaccount.com --allow-unauthenticated --min-instances 0 --max-instances 2 --memory 512Mi --cpu 1 --set-env-vars GOOGLE_CLOUD_PROJECT=moatalk-e6fe1,FLASK_ENV=production --quiet

# The frontend uses its own origin; firebase.json routes /api/** and /health
# to Cloud Run before the SPA fallback. No frontend API secret is needed.
VITE_API_BASE_URL= npm run build:prod
firebase deploy --only hosting --project moatalk-e6fe1

curl --fail-with-body https://moatalk-e6fe1.web.app/health
curl -i https://moatalk-e6fe1.web.app/api/v1/messages
```

The health response must be JSON with `status: "ok"`. An unauthenticated messages
request must return JSON with HTTP 401 (`missing_token`), never HTML. Then sign in
through Settings and verify the pending/history requests succeed with a Firebase
ID token and read Firestore. API routes retain application-level authentication
even though Cloud Run permits requests to reach Flask.

`.gcloudignore` uploads only the backend build inputs, excluding local credentials,
virtual environments, frontend dependencies, logs, and test artifacts.

Scheduler setup and enabling English lesson imports are separate operations;
the internal collection job remains closed until its OIDC account is configured.
