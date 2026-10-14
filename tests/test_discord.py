import json
import unittest
from discord_notifications import notification_state, send_webhook, validate_webhook


class DiscordTests(unittest.TestCase):
    def test_webhook_accepts_only_discord_https(self):
        self.assertEqual(validate_webhook('https://discord.com/api/webhooks/123/example_token'),
                         'https://discord.com/api/webhooks/123/example_token')
        for url in ('http://discord.com/api/webhooks/123/token',
                    'https://example.com/api/webhooks/123/token',
                    'https://discord.com.evil.test/api/webhooks/123/token',
                    'https://discord.com/api/webhooks/123/token?unexpected=yes'):
            with self.assertRaises(ValueError): validate_webhook(url)

    def test_payload_disables_mentions_and_waits_for_confirmation(self):
        captured = {}
        class Response:
            def __enter__(self): return self
            def __exit__(self, *_): pass
            def read(self, _): return b'{}'
        class Opener:
            def open(self, req, timeout):
                captured['request'], captured['timeout'] = req, timeout
                return Response()
        send_webhook('https://discord.com/api/webhooks/123/example_token', '@everyone test', Opener())
        req = captured['request']; payload = json.loads(req.data)
        self.assertEqual(payload['allowed_mentions'], {'parse': []})
        self.assertTrue(req.full_url.endswith('?wait=true'))
        self.assertEqual(captured['timeout'], 10)

    def test_process_open_is_not_reported_as_character_online(self):
        state = notification_state('Aberto — sem mudança há 12 s')
        self.assertIn('não confirmada', state)
        self.assertEqual(state, notification_state('Aberto — sem mudança há 25 s'))
        self.assertIsNone(notification_state('Na fila — próximo reinício em 55 s'))


if __name__ == '__main__': unittest.main()
