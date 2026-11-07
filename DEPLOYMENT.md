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

## My Chat automation

Settings now offers independent opt-ins for newly collected server content and a
latest-five-content daily digest (default 09:00 Asia/Seoul). Both can be enabled;
the digest may repeat content delivered individually. Browser-only content is not
included. The five-minute authenticated Scheduler job calls
`/api/v1/kakao/automation/run`. Content collection must also run independently.

Configure `KAKAO_REST_API_KEY`, `KAKAO_CLIENT_SECRET` (when enabled in Kakao),
`KAKAO_REDIRECT_URI` (the public backend `/api/v1/kakao/callback` URL),
`KAKAO_FRONTEND_ORIGIN`, and a stable random `FLASK_SECRET_KEY` on Cloud Run.
Register the redirect URI in Kakao Developers and enable `talk_message` consent.
Users sign in to Moatok, connect Kakao under the automation section, select
triggers, and save. Credentials are encrypted with a domain-separated key derived
from the Flask secret, in `private_my_chat_accounts`; deny client Firestore access
to this collection and all its subcollections. Never rotate the Flask secret
without arranging reconnection or credential migration.

The Scheduler OIDC identity must equal `SCHEDULER_SERVICE_ACCOUNT_EMAIL`; its
OIDC audience must equal `SCHEDULER_OIDC_AUDIENCE`. Delivery receipts are claimed
atomically before contacting Kakao. Uncertain results are held for review rather
than retried automatically, to avoid duplicates. The UI reports connection/send
errors. Disconnect disables triggers and removes the encrypted credentials.

### Diagnosing an automatic-send connection 503

`POST /api/v1/kakao/automation/connect` returns 503 when any required OAuth
configuration is absent. Check `/api/v1/kakao/status` first: `configured: false`
is a configuration problem, not a transient collection failure. The frontend
keeps connection and trigger controls disabled until readiness succeeds.

Cloud Run must have `FLASK_SECRET_KEY`, `KAKAO_REST_API_KEY`,
`KAKAO_REDIRECT_URI`, and `KAKAO_FRONTEND_ORIGIN`. Set the callback to
`https://moatalk-e6fe1.web.app/api/v1/kakao/callback` and register that exact URL
in Kakao Developers. Use the REST API key, not the JavaScript key. Set
`KAKAO_CLIENT_SECRET` too if the provider app requires it. Supply credentials
through private deployment configuration; never commit them. Preserve existing
Cloud Run environment variables when updating OAuth configuration. Only declare
connection recovery complete after readiness is true and a real user completes
OAuth and saves the desired triggers.
