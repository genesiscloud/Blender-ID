import base64
import json
import hashlib
import hmac

from django.test import TestCase


class LinkHMACTest(TestCase):
    def setUp(self):
        super().setUp()
        self.secret = 'heyyyyy'

    def _encode(self, payload):
        as_json = json.dumps(payload)
        b64 = base64.urlsafe_b64encode(as_json.encode())
        mac = hmac.new(self.secret.encode(), b64, hashlib.sha1).hexdigest()
        return b64, mac

    def test_happy(self):
        from bid_main import email

        b64, mac = self._encode({'e': 'test@here.nl', 'x': '2130-03-01T12:34'})
        with self.settings(SECRET_KEY=self.secret):
            result = email.check_verification_payload(b64.decode(), mac, 'test@here.nl')
        self.assertEqual(email.VerificationResult.OK, result)

    def test_expired(self):
        from bid_main import email

        b64, mac = self._encode({'e': 'test@here.nl', 'x': '2000-03-01T12:34'})

        with self.settings(SECRET_KEY=self.secret):
            result = email.check_verification_payload(b64.decode(), mac, 'test@here.nl')
        self.assertEqual(email.VerificationResult.EXPIRED, result)

    def test_other_user(self):
        from bid_main import email

        b64, mac = self._encode({'e': 'test@here.nl', 'x': '2000-03-01T12:34'})

        with self.settings(SECRET_KEY=self.secret):
            result = email.check_verification_payload(b64.decode(), mac, 'je@moeder.nl')
        self.assertEqual(email.VerificationResult.INVALID, result)

    def test_bad_hmac(self):
        from bid_main import email

        b64, mac = self._encode({'e': 'test@here.nl', 'x': '2000-03-01T12:34'})

        with self.settings(SECRET_KEY=self.secret):
            result = email.check_verification_payload(b64.decode(), 'well well well',
                                                      'test@here.nl')
        self.assertEqual(email.VerificationResult.INVALID, result)

    def test_bad_json(self):
        from bid_main import email

        as_json = "this is so invalid, I don't know where to start..."
        b64 = base64.urlsafe_b64encode(as_json.encode())
        mac = hmac.new(self.secret.encode(), b64, hashlib.sha1).hexdigest()

        with self.settings(SECRET_KEY=self.secret):
            result = email.check_verification_payload(b64.decode(), mac, 'test@here.nl')
        self.assertEqual(email.VerificationResult.INVALID, result)

    def test_bad_b64(self):
        from bid_main import email

        b64 = "မြန်မာဘာသာ".encode()
        mac = hmac.new(self.secret.encode(), b64, hashlib.sha1).hexdigest()

        with self.settings(SECRET_KEY=self.secret):
            result = email.check_verification_payload(b64.decode(), mac, 'test@here.nl')
        self.assertEqual(email.VerificationResult.INVALID, result)
