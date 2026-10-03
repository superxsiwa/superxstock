## Phase 4: Security (JWT Auth) & Automation (Celery Beat)

The goal of this phase is to secure the application by introducing User Authentication (JWT) and to fully automate the daily stock data ingestion process using Celery Beat (Cron jobs).

## User Review Required

> [!IMPORTANT]
> **Authentication Flow:** We will implement standard OAuth2 with Password (and hashing via passlib/bcrypt). The frontend UI will need to be updated eventually to support a login screen, but for this backend phase, we will secure the API endpoints.

> [!WARNING]
> **Market Schedule:** The Celery Beat schedule will be set to run at 17:30 BKK time on weekdays (Monday - Friday). Please confirm if this schedule aligns with your expectations for the Thai Stock Market.

## Open Questions

> [!NOTE]
> 1. **Frontend Update:** Do you want me to also build a simple Login/Register UI modal in `app.js` and `index.html` during this phase, or should we strictly focus on the Backend API for now?
> 2. **Password Policy:** Should we enforce a strict password policy (e.g., length, uppercase, numbers), or keep it simple for the MVP?

## Proposed Changes

---
### Dependencies
We need to add security libraries for hashing passwords and generating JWTs.

#### [MODIFY] backend/requirements.txt
```diff
 sqlalchemy
 psycopg2-binary
 pandas
 celery
 redis
 yfinance
 pydantic
 pydantic-settings
+passlib[bcrypt]
+python-jose[cryptography]
+python-multipart
```

---
### Component: Security Layer
Create the core authentication utilities and user management.

#### [NEW] backend/app/core/security.py
- Implement password hashing (`get_password_hash`, `verify_password`).
- Implement JWT token generation (`create_access_token`).
- Create `get_current_user` dependency for FastAPI routes.

#### [NEW] backend/app/api/routes/auth.py
- **POST `/api/auth/register`**: Endpoint to create a new `User` in the database.
- **POST `/api/auth/token`**: Endpoint to verify credentials and return a JWT access token.

---
### Component: Protected Endpoints
Update existing routes to require the JWT token and use the authenticated user's ID.

#### [MODIFY] backend/app/api/routes/frontend.py
```diff
-@router.get("/portfolio")
-def api_portfolio(db: Session = Depends(get_db)):
-    return get_portfolio_summary(db, user_id=1)
+@router.get("/portfolio")
+def api_portfolio(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
+    return get_portfolio_summary(db, user_id=current_user.id)
 
-@router.post("/paper-trade", response_model=TradeResponse)
-def api_paper_trade(trade: TradeRequest, db: Session = Depends(get_db)):
+@router.post("/paper-trade", response_model=TradeResponse)
+def api_paper_trade(trade: TradeRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
```

#### [MODIFY] backend/app/main.py
- Register the new `auth.router`.

---
### Component: Task Automation (Cron Job)
Configure Celery to run tasks on a schedule.

#### [MODIFY] backend/app/worker.py
- Add `celery_app.conf.beat_schedule` to configure a CRON job.
- Schedule `fetch_and_scan_daily_market` to execute Monday-Friday at 17:30.

## Verification Plan

### Manual Verification
1. **Security:** Use Postman or Swagger UI (`http://localhost:8000/docs`) to register a new user.
2. **Authentication:** Request an access token using the new user's credentials.
3. **Authorization:** Attempt to hit `/api/portfolio` without a token (should return 401 Unauthorized), then hit it with the token (should return an empty portfolio for the new user).
4. **Automation:** Start the celery beat process (`celery -A app.worker.celery_app beat`) and verify the logs show the scheduled task is registered.
