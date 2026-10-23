import base64
import unittest

from altiusnxt_core import allowed_visibility_for_role, can_access_copilot, extract_text_from_upload


class RolePolicyTests(unittest.TestCase):
    def test_marketing_cannot_access_hr_copilot(self):
        self.assertFalse(can_access_copilot("marketing", "hr"))

    def test_hr_can_access_hr_copilot(self):
        self.assertTrue(can_access_copilot("hr", "hr"))

    def test_admin_can_access_both_copilots(self):
        self.assertTrue(can_access_copilot("admin", "hr"))
        self.assertTrue(can_access_copilot("admin", "marketing"))

    def test_guest_has_only_shared_visibility(self):
        self.assertEqual(allowed_visibility_for_role("guest"), ["shared"])

    def test_marketing_does_not_get_hr_visibility(self):
        self.assertNotIn("hr", allowed_visibility_for_role("marketing"))

    def test_hr_visibility_excludes_admin(self):
        self.assertNotIn("admin", allowed_visibility_for_role("hr"))


class UploadParsingTests(unittest.TestCase):
    def test_plain_text_upload_returns_decoded_text_and_original_bytes(self):
        raw = b"hello from a unit test"
        payload = base64.b64encode(raw).decode("ascii")

        text, returned = extract_text_from_upload("note.txt", "text/plain", payload)

        self.assertEqual(text, raw.decode("utf-8"))
        self.assertEqual(returned, raw)

    def test_upload_over_six_mib_is_rejected(self):
        raw = b"x" * (6 * 1024 * 1024 + 1)
        payload = base64.b64encode(raw).decode("ascii")

        with self.assertRaisesRegex(ValueError, "Upload too large"):
            extract_text_from_upload("large.txt", "text/plain", payload)


