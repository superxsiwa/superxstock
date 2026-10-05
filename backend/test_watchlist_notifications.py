import unittest
from sqlalchemy import create_engine, text
from unittest.mock import call, patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.routes.notifications import (
    get_notification_settings,
    test_notification as send_test_notification,
    update_notification_settings,
)
from app.api.routes.auth import UserCreate, register
from app.api.routes.watchlist import add_to_watchlist, get_watchlist, remove_from_watchlist
from app.core.database import Base, ensure_user_role_column
from app.core.security import get_admin_user
from app.line_messaging import decrypt_channel_access_token
from app.models.all_models import (
    Stock,
    User,
    UserNotificationSettings,
    Watchlist,
)
from app.schemas import LineNotificationUpdate, WatchlistCreate


class WatchlistNotificationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.user = User(email="first@example.com", password_hash="unused")
        self.other_user = User(email="second@example.com", password_hash="unused")
        self.db.add_all([self.user, self.other_user, Stock(symbol="AOT.BK", name="AOT")])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_watchlist_is_user_scoped_and_supports_add_remove(self):
        result = add_to_watchlist(WatchlistCreate(symbol=" aot.bk "), self.db, self.user)

        self.assertEqual(result, {"symbol": "AOT.BK"})
        self.assertEqual(get_watchlist(self.db, self.user), ["AOT.BK"])
        self.assertEqual(get_watchlist(self.db, self.other_user), [])
        with self.assertRaises(HTTPException) as duplicate:
            add_to_watchlist(WatchlistCreate(symbol="AOT.BK"), self.db, self.user)
        self.assertEqual(duplicate.exception.status_code, 409)

        remove_from_watchlist("aot.bk", self.db, self.user)
        self.assertEqual(get_watchlist(self.db, self.user), [])

    def test_line_token_is_encrypted_and_test_message_uses_saved_settings(self):
        line_user_id = "U" + "a" * 32
        update_notification_settings(
            LineNotificationUpdate(
                line_user_id=line_user_id,
                channel_access_token="private-test-token",
            ),
            self.db,
            self.user,
        )
        settings = self.db.query(UserNotificationSettings).filter_by(user_id=self.user.id).one()

        self.assertNotEqual(settings.encrypted_channel_access_token, "private-test-token")
        self.assertEqual(decrypt_channel_access_token(settings.encrypted_channel_access_token), "private-test-token")
        self.assertEqual(get_notification_settings(self.db, self.user), {
            "line_user_id": line_user_id,
            "configured": True,
        })

        with patch("app.api.routes.notifications.send_line_message") as send_message:
            self.assertEqual(send_test_notification(self.db, self.user), {"ok": True})
        send_message.assert_called_once_with(
            "private-test-token",
            line_user_id,
            "SuperX Stock test notification.",
        )

    def test_worker_only_sends_matching_actionable_watchlist_alerts(self):
        line_user_id = "U" + "b" * 32
        self.db.add_all([
            Watchlist(user_id=self.user.id, symbol="AOT.BK"),
            UserNotificationSettings(
                user_id=self.user.id,
                line_user_id=line_user_id,
                encrypted_channel_access_token="encrypted-token",
            ),
            Watchlist(user_id=self.other_user.id, symbol="PTT.BK"),
        ])
        self.db.commit()

        from app import worker

        with (
            patch.object(worker, "SessionLocal", self.Session),
            patch.object(worker, "decrypt_channel_access_token", return_value="private-test-token"),
            patch.object(worker, "send_line_message") as send_message,
        ):
            worker._send_watchlist_alerts([
                {"symbol": "AOT.BK", "recommendation": "BUY", "price": 42.5},
                {"symbol": "PTT.BK", "recommendation": "WATCH", "price": 35.0},
                {"symbol": "KBANK.BK", "recommendation": "SELL", "price": 120.0},
            ])

        send_message.assert_has_calls([
            call(
                "private-test-token",
                line_user_id,
                "SuperX Stock signal: BUY AOT.BK at 42.50 THB.",
            ),
        ])
        self.assertEqual(send_message.call_count, 1)

    def test_non_admin_is_forbidden_and_admin_is_allowed(self):
        self.user.role = "user"
        with self.assertRaises(HTTPException) as forbidden:
            get_admin_user(self.user)
        self.assertEqual(forbidden.exception.status_code, 403)

        self.user.role = "admin"
        self.assertIs(get_admin_user(self.user), self.user)

    def test_role_migration_preserves_existing_users_as_regular_users(self):
        legacy_engine = create_engine("sqlite://")
        try:
            with legacy_engine.begin() as connection:
                connection.execute(text(
                    "CREATE TABLE users (id INTEGER PRIMARY KEY, email VARCHAR, password_hash VARCHAR)"
                ))
                connection.execute(text(
                    "INSERT INTO users (id, email, password_hash) VALUES (1, 'legacy@example.com', 'hash')"
                ))

            ensure_user_role_column(legacy_engine)
            with legacy_engine.connect() as connection:
                user = connection.execute(text("SELECT email, password_hash, role FROM users WHERE id = 1")).one()
            self.assertEqual(tuple(user), ("legacy@example.com", "hash", "user"))
        finally:
            legacy_engine.dispose()

    def test_admin_email_bootstraps_only_matching_new_account(self):
        with patch.dict("os.environ", {"ADMIN_EMAIL": "admin@example.com"}), patch(
            "app.api.routes.auth.get_password_hash", return_value="hash"
        ):
            register(UserCreate(email="admin@example.com", password="password123"), self.db)
            register(UserCreate(email="member@example.com", password="password123"), self.db)

        roles = dict(self.db.query(User.email, User.role).all())
        self.assertEqual(roles["admin@example.com"], "admin")
        self.assertEqual(roles["member@example.com"], "user")


if __name__ == "__main__":
    unittest.main()