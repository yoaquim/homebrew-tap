"""Unit tests for scripts/update_casks.py. No network access needed."""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import update_casks  # noqa: E402
from update_casks import UpdateError  # noqa: E402


class LoadManifestTest(unittest.TestCase):
    def write_manifest(self, content):
        path = Path(self.tmp.name) / "projects.json"
        path.write_text(content, encoding="utf-8")
        return path

    def setUp(self):
        import tempfile

        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_valid_manifest_with_defaults(self):
        path = self.write_manifest(
            """
            {"projects": [{"repo": "o/r", "cask": "app",
                           "assets": {"default": "App_{version}.dmg"}}]}
            """
        )
        entries = update_casks.load_manifest(path)
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry["repo"], "o/r")
        self.assertEqual(entry["cask"], "app")
        self.assertEqual(entry["assets"], {"default": "App_{version}.dmg"})
        self.assertFalse(entry["prerelease"])
        self.assertEqual(entry["tag_prefix"], "v")

    def test_explicit_options_override_defaults(self):
        path = self.write_manifest(
            """
            {"projects": [{"repo": "o/r", "cask": "app", "prerelease": true,
                           "tag_prefix": "",
                           "assets": {"arm": "a_{version}.dmg",
                                      "intel": "i_{version}.dmg"}}]}
            """
        )
        entry = update_casks.load_manifest(path)[0]
        self.assertTrue(entry["prerelease"])
        self.assertEqual(entry["tag_prefix"], "")
        self.assertEqual(sorted(entry["assets"]), ["arm", "intel"])

    def test_missing_required_key_fails(self):
        path = self.write_manifest('{"projects": [{"repo": "o/r", "cask": "app"}]}')
        with self.assertRaisesRegex(UpdateError, "assets"):
            update_casks.load_manifest(path)

    def test_empty_projects_fails(self):
        path = self.write_manifest('{"projects": []}')
        with self.assertRaisesRegex(UpdateError, "projects"):
            update_casks.load_manifest(path)

    def test_bad_asset_keys_fail(self):
        path = self.write_manifest(
            """
            {"projects": [{"repo": "o/r", "cask": "app",
                           "assets": {"default": "a.dmg", "arm": "b.dmg"}}]}
            """
        )
        with self.assertRaisesRegex(UpdateError, "assets"):
            update_casks.load_manifest(path)

    def test_duplicate_cask_tokens_fail(self):
        path = self.write_manifest(
            """
            {"projects": [
              {"repo": "o/r", "cask": "app", "assets": {"default": "a.dmg"}},
              {"repo": "o/r2", "cask": "app", "assets": {"default": "b.dmg"}}]}
            """
        )
        with self.assertRaisesRegex(UpdateError, "duplicate"):
            update_casks.load_manifest(path)


class VersionFromTagTest(unittest.TestCase):
    def test_strips_prefix(self):
        self.assertEqual(update_casks.version_from_tag("v1.8.4", "v"), "1.8.4")

    def test_empty_prefix_keeps_tag(self):
        self.assertEqual(update_casks.version_from_tag("1.8.4", ""), "1.8.4")

    def test_unexpected_tag_fails(self):
        with self.assertRaisesRegex(UpdateError, "tag_prefix"):
            update_casks.version_from_tag("release-1.8.4", "v")


class ParseCaskVersionTest(unittest.TestCase):
    def test_reads_version(self):
        text = (FIXTURES / "covalent.rb").read_text(encoding="utf-8")
        self.assertEqual(update_casks.parse_cask_version(text, "covalent.rb"), "1.8.2")

    def test_missing_version_fails(self):
        with self.assertRaisesRegex(UpdateError, "version"):
            update_casks.parse_cask_version('cask "x" do\nend\n', "x.rb")


class MatchAssetsTest(unittest.TestCase):
    RELEASE_ASSETS = [
        {"name": "Covalent_1.8.4_aarch64.dmg", "browser_download_url": "u1"},
        {"name": "Covalent_1.8.4_x64-setup.exe", "browser_download_url": "u2"},
    ]

    def test_matches_single_asset(self):
        matched = update_casks.match_assets(
            {"default": "Covalent_{version}_aarch64.dmg"},
            self.RELEASE_ASSETS,
            "1.8.4",
            "yoaquim/covalent",
        )
        self.assertEqual(matched["default"]["name"], "Covalent_1.8.4_aarch64.dmg")

    def test_glob_pattern(self):
        matched = update_casks.match_assets(
            {"default": "Covalent_{version}_*.dmg"},
            self.RELEASE_ASSETS,
            "1.8.4",
            "yoaquim/covalent",
        )
        self.assertEqual(matched["default"]["name"], "Covalent_1.8.4_aarch64.dmg")

    def test_missing_asset_fails(self):
        with self.assertRaisesRegex(UpdateError, "no release asset"):
            update_casks.match_assets(
                {"default": "Covalent_{version}_universal.dmg"},
                self.RELEASE_ASSETS,
                "1.8.4",
                "yoaquim/covalent",
            )

    def test_ambiguous_pattern_fails(self):
        with self.assertRaisesRegex(UpdateError, "matches 2"):
            update_casks.match_assets(
                {"default": "Covalent_{version}_*"},
                self.RELEASE_ASSETS,
                "1.8.4",
                "yoaquim/covalent",
            )


class RewriteCaskTest(unittest.TestCase):
    def test_single_arch_rewrites_only_version_and_sha(self):
        original = (FIXTURES / "covalent.rb").read_text(encoding="utf-8")
        new_sha = "a" * 64
        rewritten = update_casks.rewrite_cask(
            original, "1.8.4", {"default": new_sha}, "covalent.rb"
        )
        self.assertIn('version "1.8.4"', rewritten)
        self.assertIn(f'sha256 "{new_sha}"', rewritten)
        # Everything except the version and sha256 lines is preserved verbatim.
        changed = [
            (a, b)
            for a, b in zip(original.splitlines(), rewritten.splitlines())
            if a != b
        ]
        self.assertEqual(len(changed), 2)
        self.assertIn("version", changed[0][0])
        self.assertIn("sha256", changed[1][0])
        self.assertIn("postflight", rewritten)
        self.assertIn('url "https://github.com/yoaquim/covalent', rewritten)
        self.assertIn("#{version}", rewritten)

    def test_dual_arch_rewrites_both_shas(self):
        original = (FIXTURES / "dual_arch.rb").read_text(encoding="utf-8")
        rewritten = update_casks.rewrite_cask(
            original, "2.1.0", {"arm": "3" * 64, "intel": "4" * 64}, "dual_arch.rb"
        )
        self.assertIn('version "2.1.0"', rewritten)
        self.assertIn('arm:   "' + "3" * 64 + '"', rewritten)
        self.assertIn('intel: "' + "4" * 64 + '"', rewritten)
        # The arch stanza (not a sha256 line) must be untouched.
        self.assertIn('arch arm: "aarch64", intel: "x86_64"', rewritten)

    def test_dual_arch_single_line_form(self):
        text = (
            'cask "x" do\n'
            '  version "1.0.0"\n'
            '  sha256 arm: "%s", intel: "%s"\n'
            "end\n" % ("5" * 64, "6" * 64)
        )
        rewritten = update_casks.rewrite_cask(
            text, "1.1.0", {"arm": "7" * 64, "intel": "8" * 64}, "x.rb"
        )
        self.assertIn('sha256 arm: "%s", intel: "%s"' % ("7" * 64, "8" * 64), rewritten)

    def test_arm_only_per_arch_cask(self):
        text = 'cask "x" do\n  version "1.0.0"\n  sha256 arm: "%s"\nend\n' % ("5" * 64)
        rewritten = update_casks.rewrite_cask(text, "1.1.0", {"arm": "9" * 64}, "x.rb")
        self.assertIn('sha256 arm: "%s"' % ("9" * 64), rewritten)

    def test_missing_sha_line_fails(self):
        text = 'cask "x" do\n  version "1.0.0"\nend\n'
        with self.assertRaisesRegex(UpdateError, "sha256"):
            update_casks.rewrite_cask(text, "1.1.0", {"default": "a" * 64}, "x.rb")

    def test_arch_key_mismatch_fails(self):
        text = 'cask "x" do\n  version "1.0.0"\n  sha256 "%s"\nend\n' % ("5" * 64)
        with self.assertRaisesRegex(UpdateError, "arm"):
            update_casks.rewrite_cask(text, "1.1.0", {"arm": "9" * 64}, "x.rb")

    def test_duplicate_version_lines_fail(self):
        text = 'cask "x" do\n  version "1.0.0"\n  version "1.0.0"\n  sha256 "%s"\nend\n' % (
            "5" * 64
        )
        with self.assertRaisesRegex(UpdateError, "version"):
            update_casks.rewrite_cask(text, "1.1.0", {"default": "a" * 64}, "x.rb")


if __name__ == "__main__":
    unittest.main()
