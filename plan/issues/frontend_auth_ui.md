# Issue: Implement Login & Registration UI (Frontend)

**Label:** `frontend`, `enhancement`
**Status:** `To Do`
**Assignee:** Frontend Team

## Description
The backend has successfully migrated to a JWT-based authentication system. However, the frontend (`app.js`, `index.html`) currently has no UI for users to log in or register. The backend APIs are fully prepared and expect a `Bearer` token in the `Authorization` header for protected routes.

## Acceptance Criteria
- [ ] Create a Login/Register Modal or Page.
- [ ] When a user submits the register form, it should POST to `/api/auth/register` with `email` and `password`.
- [ ] When a user logs in, it should POST to `/api/auth/token` using standard `x-www-form-urlencoded` format (`username` and `password`).
- [ ] On successful login, the frontend should store the `access_token` in `localStorage` or `sessionStorage`.
- [ ] Update the `fetch` calls to `/api/portfolio` and `/api/paper-trade` in `app.js` to include the `Authorization: Bearer <token>` header.
- [ ] If an API responds with `401 Unauthorized`, the user should be automatically logged out and prompted to log in again.

## Technical Details
- Backend APIs: 
  - `POST /api/auth/register` (JSON payload)
  - `POST /api/auth/token` (Form data)
- Required Header for Auth: `Authorization: Bearer <your_jwt_token_here>`
