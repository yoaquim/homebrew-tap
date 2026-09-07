#!/usr/bin/env python3
"""Update Homebrew casks from the GitHub releases listed in projects.json.

For each manifest entry this script finds the latest suitable release,
downloads the release asset(s), computes their sha256 locally, and rewrites
only the `version` and `sha256` lines of the existing cask file. It never
regenerates a cask from a template.

Standard library only. Set GITHUB_TOKEN to raise API rate limits.

Usage:
  python3 scripts/update_casks.py [--dry-run] [--only CASK]
"""

import argparse
import difflib
import fnmatch
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
API_ROOT = "https://api.github.com"
SHA256_RE = "[0-9a-fA-F]{64}"


class UpdateError(Exception):
    """A loud, human-readable failure. Never silently skipped."""


# --------------------------------------------------------------------------
# Manifest


def load_manifest(path):
    """Parse projects.json and return a list of entries with defaults applied."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise UpdateError(f"{path}: cannot read manifest: {exc}") from exc

    projects = data.get("projects")
    if not isinstance(projects, list) or not projects:
        raise UpdateError(f"{path}: expected a non-empty 'projects' list")

    entries = []
    seen_casks = set()
    for i, raw in enumerate(projects):
        where = f"{path}: projects[{i}]"
        for key in ("repo", "cask", "assets"):
            if key not in raw:
                raise UpdateError(f"{where} is missing required key '{key}'")

        assets = raw["assets"]
        keys = set(assets) if isinstance(assets, dict) else set()
        if not keys or not (keys == {"default"} or keys <= {"arm", "intel"}):
            raise UpdateError(
                f"{where}: 'assets' must be an object with either a single "
                "'default' key or 'arm'/'intel' keys"
            )

        if raw["cask"] in seen_casks:
            raise UpdateError(f"{where}: duplicate cask token '{raw['cask']}'")
        seen_casks.add(raw["cask"])

        entries.append(
            {
                "repo": raw["repo"],
                "cask": raw["cask"],
                "assets": assets,
                "prerelease": raw.get("prerelease", False),
                "tag_prefix": raw.get("tag_prefix", "v"),
            }
        )
    return entries


# --------------------------------------------------------------------------
# GitHub API


def github_json(url, token):
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "homebrew-tap-updater",
        },
    )
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        raise UpdateError(f"GET {url} failed: HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise UpdateError(f"GET {url} failed: {exc.reason}") from exc


def fetch_latest_release(repo, include_prerelease, token):
    """Return the newest non-draft release (skipping prereleases unless allowed)."""
    releases = github_json(f"{API_ROOT}/repos/{repo}/releases?per_page=30", token)
    for release in releases:
        if release["draft"]:
            continue
        if release["prerelease"] and not include_prerelease:
            continue
        return release
    raise UpdateError(f"{repo}: no suitable release found among the latest 30")


def version_from_tag(tag, tag_prefix):
    if not tag_prefix:
        return tag
    if not tag.startswith(tag_prefix):
        raise UpdateError(
            f"tag '{tag}' does not start with tag_prefix '{tag_prefix}'"
        )
    return tag[len(tag_prefix):]


def match_assets(patterns, release_assets, version, repo):
    """Map each manifest asset key to exactly one release asset, or fail."""
    names = [asset["name"] for asset in release_assets]
    matched = {}
    for key, pattern in patterns.items():
        resolved = pattern.replace("{version}", version)
        hits = [a for a in release_assets if fnmatch.fnmatchcase(a["name"], resolved)]
        if not hits:
            raise UpdateError(
                f"{repo}: no release asset matches '{resolved}' "
                f"(assets: {', '.join(names) or 'none'})"
            )
        if len(hits) > 1:
            raise UpdateError(
                f"{repo}: pattern '{resolved}' matches {len(hits)} assets: "
                f"{', '.join(a['name'] for a in hits)}"
            )
        matched[key] = hits[0]
    return matched


def sha256_of_url(url):
    """Download url and return its sha256 hex digest, computed locally."""
    request = urllib.request.Request(
        url, headers={"User-Agent": "homebrew-tap-updater"}
    )
    digest = hashlib.sha256()
    try:
        with urllib.request.urlopen(request) as response:
            while chunk := response.read(1 << 20):
                digest.update(chunk)
    except urllib.error.URLError as exc:
        raise UpdateError(f"download of {url} failed: {exc}") from exc
    return digest.hexdigest()


# --------------------------------------------------------------------------
# Cask rewriting


def parse_cask_version(text, path):
    matches = re.findall(r'^\s*version "([^"]+)"', text, flags=re.M)
    if len(matches) != 1:
        raise UpdateError(f"{path}: expected exactly one version line, found {len(matches)}")
    return matches[0]


def _replace_exactly_once(text, pattern, replacement, description, path):
    new_text, count = re.subn(pattern, replacement, text, flags=re.M)
    if count != 1:
        raise UpdateError(f"{path}: expected exactly one {description}, found {count}")
    return new_text


def rewrite_cask(text, new_version, shas, path):
    """Replace only the version and sha256 values; leave everything else verbatim.

    `shas` is {"default": hex} for single-sha casks, or a dict with "arm"
    and/or "intel" keys for `sha256 arm: "...", intel: "..."` casks.
    """
    text = _replace_exactly_once(
        text,
        r'^(\s*version ")[^"]+(")',
        rf"\g<1>{new_version}\g<2>",
        "version line",
        path,
    )
    if "default" in shas:
        text = _replace_exactly_once(
            text,
            rf'^(\s*sha256 "){SHA256_RE}(")',
            rf"\g<1>{shas['default']}\g<2>",
            "sha256 line",
            path,
        )
    else:
        for arch, sha in shas.items():
            # Matches both `sha256 arm: "..."` and a bare `intel: "..."`
            # continuation line, but not the `arch arm:` stanza (which holds
            # an arch string, not a 64-char hex digest).
            text = _replace_exactly_once(
                text,
                rf'(\b{arch}:\s*"){SHA256_RE}(")',
                rf"\g<1>{sha}\g<2>",
                f"sha256 {arch}: entry",
                path,
            )
    return text


# --------------------------------------------------------------------------
# Main flow


def process_entry(entry, casks_dir, dry_run, token):
    """Update one cask. Returns True if the cask file changed (or would)."""
    cask = entry["cask"]
    cask_path = casks_dir / f"{cask}.rb"
    if not cask_path.exists():
        raise UpdateError(f"{cask}: cask file {cask_path} does not exist")
    original = cask_path.read_text(encoding="utf-8")
    current_version = parse_cask_version(original, cask_path)

    release = fetch_latest_release(entry["repo"], entry["prerelease"], token)
    new_version = version_from_tag(release["tag_name"], entry["tag_prefix"])

    if new_version == current_version:
        # Still confirm the release assets exist: an asset deleted or renamed
        # upstream without a new tag should fail the run, not stay invisible.
        match_assets(entry["assets"], release["assets"], new_version, entry["repo"])
        print(f"{cask}: up to date at {current_version}")
        return False

    print(f"{cask}: {current_version} -> {new_version} ({release['html_url']})")
    matched = match_assets(entry["assets"], release["assets"], new_version, entry["repo"])

    shas = {}
    for key, asset in matched.items():
        print(f"{cask}: downloading {asset['name']} ...")
        shas[key] = sha256_of_url(asset["browser_download_url"])
        print(f"{cask}: sha256({asset['name']}) = {shas[key]}")

    rewritten = rewrite_cask(original, new_version, shas, cask_path)

    if dry_run:
        rel = cask_path.relative_to(REPO_ROOT)
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            rewritten.splitlines(keepends=True),
            fromfile=f"a/{rel}",
            tofile=f"b/{rel}",
        )
        sys.stdout.writelines(diff)
        print(f"{cask}: dry run, not writing changes")
    else:
        cask_path.write_text(rewritten, encoding="utf-8")
        print(f"{cask}: wrote {cask_path}")
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest", default=str(REPO_ROOT / "projects.json"), help="manifest path"
    )
    parser.add_argument(
        "--casks-dir", default=str(REPO_ROOT / "Casks"), help="directory of cask files"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="print the diff, change nothing"
    )
    parser.add_argument("--only", metavar="CASK", help="only process this cask token")
    args = parser.parse_args(argv)

    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print("warning: GITHUB_TOKEN not set, using unauthenticated API rate limits")

    entries = load_manifest(args.manifest)
    if args.only:
        entries = [e for e in entries if e["cask"] == args.only]
        if not entries:
            print(f"error: no manifest entry for cask '{args.only}'", file=sys.stderr)
            return 1

    errors = []
    for entry in entries:
        try:
            process_entry(entry, Path(args.casks_dir), args.dry_run, token)
        except UpdateError as exc:
            print(f"error: {exc}", file=sys.stderr)
            errors.append(entry["cask"])

    if errors:
        print(f"error: failed to update: {', '.join(errors)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
