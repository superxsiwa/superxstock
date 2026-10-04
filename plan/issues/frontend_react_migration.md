# Issue: Migrate to React/Next.js for Advanced State Management

**Label:** `frontend`, `architecture`
**Status:** `Done`
**Assignee:** Frontend Team

## Description
As the application grows, managing state (JWT tokens, portfolios, real-time market data) with Vanilla JavaScript and HTML becomes complex and difficult to maintain. To support advanced UI features like interactive charts (TradingView) and dynamic dashboards, the frontend architecture should be modernized.

## Acceptance Criteria
- [x] Initialize a new React or Next.js project.
- [x] Migrate the current static `index.html` and `app.js` layout to component-based architecture.
- [x] Implement robust state management (e.g., Redux, Zustand, or React Context) to handle the user's Auth Token and Portfolio.
- [x] Integrate a professional charting library (e.g., Lightweight Charts or Chart.js) to replace any basic or static charts.
- [x] Ensure all existing API integrations (`/api/scan`, `/api/portfolio`, `/api/paper-trade`) work seamlessly with the new framework.
