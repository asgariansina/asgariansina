import json
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import update_profile as profile


class ProfileTests(unittest.TestCase):
    def test_repository_pagination_counts_all_stars(self):
        def page(stars, next_page, cursor):
            return {"followers": {"totalCount": 4}, "repositories": {
                "totalCount": 101, "nodes": [{"stargazerCount": n} for n in stars],
                "pageInfo": {"hasNextPage": next_page, "endCursor": cursor}},
                "contributionsCollection": {"startedAt": "2025-11-26", "endedAt": "2026-11-26", "totalCommitContributions": 23}}
        with patch.object(profile, "graphql", side_effect=[page([2, 3], True, "next"), page([7], False, None)]) as call:
            stats = profile.fetch_stats("not-a-real-token", "asgariansina")
        self.assertEqual(stats["stars"], 12)
        self.assertEqual(stats["repos"], 101)
        self.assertEqual(stats["commits"], 23)
        self.assertEqual(call.call_args.args[2], "next")

    def test_api_errors_do_not_become_zero_statistics(self):
        with patch.object(profile, "graphql", side_effect=RuntimeError("API failure")):
            with self.assertRaisesRegex(RuntimeError, "API failure"):
                profile.fetch_stats("not-a-real-token", "asgariansina")

    def test_themes_are_valid_svg_and_escape_text(self):
        config = json.loads((profile.ROOT/"config.json").read_text())
        config["heading"] = 'Sina & <research>'
        for theme in ("dark", "light"):
            for mobile in (False, True):
                svg = profile.render(config, {}, "", theme, mobile)
                root = ET.fromstring(svg)
                self.assertEqual(root.find('{http://www.w3.org/2000/svg}title').text, config["heading"])
                self.assertNotIn('<script', svg)
                self.assertNotIn('foreignObject', svg)
                self.assertIn(config["pending_label"], svg)

    def test_invalid_stats_and_unreadable_copy_rejected(self):
        config = json.loads((profile.ROOT/"config.json").read_text())
        with self.assertRaises(ValueError):
            profile.validate(config, {"repos": -1})
        config["fields"][0]["lines"] = ["x"*43]
        with self.assertRaises(ValueError):
            profile.validate(config, {})


if __name__ == '__main__':
    unittest.main()
