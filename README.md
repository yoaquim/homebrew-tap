# homebrew-tap

Personal Homebrew tap. Casks in this tap update themselves: a scheduled
GitHub Actions workflow polls each project's GitHub releases, verifies the
release assets, and bumps the cask's `version` and `sha256` in place.

```sh
brew tap yoaquim/tap
brew install --cask covalent
```

## How updates work

- `projects.json` lists every project this tap tracks.
- `scripts/update_casks.py` (Python, standard library only) runs daily via
  [`update-casks.yml`](.github/workflows/update-casks.yml) at midnight
  Puerto Rico time (04:00 UTC — Puerto Rico is UTC-4 year-round).
- For each project it fetches the latest non-draft, non-prerelease release,
  downloads the matching asset(s), computes the sha256 **locally** (digests
  published by third parties are never trusted), and rewrites only the
  `version` and `sha256` lines of the cask. Everything else in the cask file
  is preserved verbatim.
- Changed casks are checked with `brew style` and `brew audit --cask`, then
  committed one commit per cask (`Update <name> to <version>`) and pushed.
- Any error — API failure, missing asset, malformed cask — fails the workflow
  run visibly. Nothing is silently skipped, so a stale cask never goes
  unnoticed.

Authentication uses only the workflow's built-in `GITHUB_TOKEN`. There is no
personal access token anywhere: no cross-repo secrets to rotate, leak, or
have quietly expire.

The manifest is JSON rather than YAML because the updater is dependency-free
and Python's standard library has no YAML parser.

## Adding a project

1. Write an initial cask file at `Casks/<token>.rb` by hand (the updater only
   bumps existing casks; it never generates one from a template).
2. Add an entry to `projects.json`:

   ```json
   {
     "repo": "owner/name",
     "cask": "token",
     "assets": {
       "default": "App_{version}_aarch64.dmg"
     }
   }
   ```

   - `repo` — the GitHub repository to poll for releases.
   - `cask` — the cask token; the file must exist at `Casks/<cask>.rb`.
   - `assets` — glob patterns (with `{version}` substituted) that must each
     match exactly one release asset. Use `"default"` for a cask with a single
     `sha256 "..."` line, or `"arm"` / `"intel"` keys for a cask using
     `sha256 arm: "...", intel: "..."`.
   - Optional: `"prerelease": true` to accept prereleases (default `false`),
     `"tag_prefix"` if tags are not `v<version>` (default `"v"`).

3. Run the updater locally to check the entry:

   ```sh
   python3 scripts/update_casks.py --dry-run --only <token>
   python3 -m unittest discover -s tests
   ```

## Triggering a manual run

From the repo's **Actions** tab, pick **Update casks** → **Run workflow**.
Two optional inputs:

- **cask** — update just one cask token (blank runs all of them).
- **dry_run** — print the would-be diff in the log without committing.

Or with the GitHub CLI:

```sh
gh workflow run update-casks.yml -f dry_run=true
gh workflow run update-casks.yml -f cask=covalent
```

## Notes

- `Casks/covalent.rb` keeps its `xattr -cr` postflight until the app is
  notarized; the updater never touches it.
- Tests live in `tests/` and use fixtures only — no network:
  `python3 -m unittest discover -s tests -v`.
