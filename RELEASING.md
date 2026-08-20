# Releasing

This guide explains how to publish a new release of Stashify. Releases are driven entirely by git tags: pushing a `v*` tag triggers the [release workflow](.github/workflows/release.yml), which publishes to PyPI and creates a GitHub Release.

> **Current state:** The latest published version is `v0.1.1`. The next release must be `v0.2.0` (PyPI does not allow re-uploading a version that already exists).

## Prerequisites

Before the workflow can succeed, the following must be configured:

- **`PYPI_API_TOKEN`** repository secret (Settings → Secrets and variables → Actions).
  This is a PyPI API token (scope: your account or the `stashify` project) used as `TWINE_PASSWORD`.
  Create one at <https://pypi.org/manage/account/token/>.
- **`contents: write`** permission for the workflow (already set in `release.yml`) so the GitHub Release can be created.
- An up-to-date `main` with all fixes merged (PRs to `main` require a review; merge them first).

## Versioning

Stashify follows [semantic versioning](https://semver.org/):

| Bump | When | Example |
|------|------|---------|
| **Major** (`X.0.0`) | Breaking changes | `1.0.0` → `2.0.0` |
| **Minor** (`0.X.0`) | New backward-compatible features | `0.1.0` → `0.2.0` |
| **Patch** (`0.0.X`) | Bug fixes and small changes | `0.1.0` → `0.1.1` |

The version is defined in **one place**: `version` in `pyproject.toml`.

## Release checklist (manual)

Every release requires a new tag. This is the manual workflow:

1. **Merge all work to `main`** and confirm CI passes (lint, mypy, pytest, build, docker).

2. **Bump the version** in `pyproject.toml`:

   ```toml
   version = "0.2.0"
   ```

3. **Commit the bump on a branch** (per the repo workflow) and merge it to `main`:

   ```bash
   git checkout -b release/v0.2.0
   # edit pyproject.toml
   git add pyproject.toml
   git commit -m "chore: bump version to 0.2.0"
   git push origin release/v0.2.0
   # open a PR to main and merge it
   ```

4. **Pull main and verify the version**:

   ```bash
   git checkout main
   git pull origin main
   grep '^version' pyproject.toml
   ```

5. **Create and push the tag** pointing at the release commit:

   ```bash
   git tag v0.2.0
   git push origin v0.2.0
   ```

   Pushing the tag triggers the release workflow automatically.

6. **Watch the workflow** (Actions → Release). It will:
   - Build the package (`python -m build`)
   - Validate it (`twine check dist/*`)
   - Publish to PyPI (`twine upload dist/*`)
   - Create a GitHub Release with auto-generated release notes

7. **Verify** the release appears at:
   - <https://github.com/Sparkleeop/Stashify/releases>
   - <https://pypi.org/project/stashify/>

## How it works

- **Tags** are immutable pointers to a commit. Pushing a tag runs the workflow once.
- **The release workflow only runs on tag pushes** (`on: push: tags: v*`). Commits to `main` do not trigger it.
- **The GitHub Release step runs after PyPI publishing.** If the PyPI upload fails, the workflow stops and no GitHub Release is created. Fix the failing step and re-tag (see below).

## If a release fails

Check the failed run in Actions → Release and read the failing step.

**Common failure: `403 Forbidden` from `upload.pypi.org`**
- The `PYPI_API_TOKEN` is missing, invalid, expired, or lacks permission to upload to the `stashify` project.
- Regenerate the token at <https://pypi.org/manage/account/token/> and update the repo secret.
- Re-run the workflow (or re-tag with a new version).

**Common failure: version already exists on PyPI**
- A tag/version was pushed twice, or the version was uploaded before.
- Bump to the next version and create a new tag. You cannot reuse a version once it's on PyPI.

**Recovering from a partial failure**
- If PyPI succeeded but the GitHub Release step failed, create the release manually from the tag:
  GitHub → Tags → select the tag → "Create release".
- If nothing was published, fix the issue, bump the version again, and push a new tag.

## Quick reference

```bash
# One-liner for a patch release (after merging to main)
git checkout main && git pull origin main
sed -i 's/version = "0.2.0"/version = "0.2.1"/' pyproject.toml
git add pyproject.toml && git commit -m "chore: bump version to 0.2.1"
git tag v0.2.1 && git push origin main v0.2.1
```

> **Note:** the one-liner pushes `main` directly, which this repo's branch protection disallows. Use a branch + PR for the version bump, then push only the tag.

## FAQ

**Do I have to create a new tag every update?**
Yes. A new tag is required for every release because PyPI never allows a version to be re-uploaded. The version bump + tag are the two manual steps.

**Can this be automated?**
Yes. Tools like [release-please](https://github.com/googleapis/release-please) or [semantic-release](https://semantic-release.gitbook.io/) compute the next version from conventional commits (`feat:`, `fix:`), bump the version, create the tag, and generate changelogs automatically on merge.