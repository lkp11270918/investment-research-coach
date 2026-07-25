import os
import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException

from backend.auth import authenticate_user, create_user, init_auth_db, to_auth_user
from backend.main import delete_me
from backend.models import CompanyProfile, DeleteAccountRequest, ResearchProjectCreate
from backend.storage import create_research_project, init_research_runs_db, list_research_projects


class AccountDeletionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.previous_database_url = os.environ.get("DATABASE_URL")
        self.temp_dir = tempfile.TemporaryDirectory()
        os.environ["DATABASE_URL"] = f"sqlite:///{Path(self.temp_dir.name) / 'account.db'}"
        init_auth_db()
        init_research_runs_db()

    def tearDown(self) -> None:
        if self.previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = self.previous_database_url
        self.temp_dir.cleanup()

    def test_password_confirmation_deletes_account_and_research_assets(self) -> None:
        user = create_user(email="delete@example.com", password="correct-password", name="待删除用户")
        create_research_project(
            user.user_id,
            ResearchProjectCreate(company_profile=CompanyProfile(company_name="测试公司", industry="制造业")),
        )

        delete_me(DeleteAccountRequest(password="correct-password"), to_auth_user(user))

        self.assertEqual(list_research_projects(user.user_id), [])
        with self.assertRaises(HTTPException) as error:
            authenticate_user(email=user.email, password="correct-password")
        self.assertEqual(error.exception.status_code, 401)

    def test_wrong_password_preserves_account(self) -> None:
        user = create_user(email="keep@example.com", password="correct-password")

        with self.assertRaises(HTTPException) as error:
            delete_me(DeleteAccountRequest(password="wrong-password"), to_auth_user(user))

        self.assertEqual(error.exception.status_code, 401)
        self.assertEqual(authenticate_user(email=user.email, password="correct-password").user_id, user.user_id)


if __name__ == "__main__":
    unittest.main()
