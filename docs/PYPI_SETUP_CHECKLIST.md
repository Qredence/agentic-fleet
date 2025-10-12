# PyPI Environment Setup - Quick Checklist

## 🎯 Goal

Set up automated PyPI publishing for AgenticFleet releases.

---

## ✅ Step 1: Create GitHub Environment (5 minutes)

### Browser Tab 1: GitHub Environments

**URL**: <https://github.com/Qredence/AgenticFleet/settings/environments>

**Actions**:

1. [ ] Click **"New environment"**
2. [ ] Name it: `pypi` (lowercase, exactly as shown)
3. [ ] Click **"Configure environment"**
4. [ ] Under "Deployment branches and tags":
   - [ ] Select **"Selected tags"**
   - [ ] Click **"Add deployment branch or tag rule"**
   - [ ] Enter pattern: `v[0-9]+.[0-9]+.[0-9]+*`
   - [ ] Click **"Add rule"**
   - [ ] **Note**: Use this exact pattern. `v*.*.*` will cause "Name is invalid" error!
5. [ ] (Optional) Add yourself as a required reviewer
6. [ ] Click **"Save protection rules"**

**Verification**: You should see "pypi" environment listed with tag rule `v[0-9]+.[0-9]+.[0-9]+*`

---

## ⭐ Step 2: Set Up PyPI Trusted Publishing (5 minutes)

### Browser Tab 2: PyPI Publishing

**URL**: <https://pypi.org/manage/account/publishing/>

**Actions**:

1. [ ] Log in to PyPI (create account if needed)
2. [ ] Scroll to **"Add a new pending publisher"**
3. [ ] Fill in the form:

   ```
   PyPI Project Name:      agentic-fleet
   Owner:                  Qredence
   Repository name:        AgenticFleet
   Workflow name:          release.yml
   Environment name:       pypi
   ```

4. [ ] Click **"Add"**

**Verification**: You should see the pending publisher listed below the form

---

## 🧪 Step 3: Test the Setup (5 minutes)

### In Terminal

```bash
# 1. Check everything is ready
./scripts/setup-pypi-environment.sh

# 2. Create a test tag
git tag v0.5.0-alpha1
git push origin v0.5.0-alpha1

# 3. Watch the release workflow
gh run watch
```

### In Browser

**URL**: <https://github.com/Qredence/AgenticFleet/actions/workflows/release.yml>

**Actions**:

1. [ ] Click on the latest workflow run
2. [ ] Verify all jobs are running/completed:
   - [ ] Build Distribution
   - [ ] Publish to PyPI (may require approval)
   - [ ] Create GitHub Release
3. [ ] If required reviewers are set:
   - [ ] Click **"Review deployments"**
   - [ ] Select `pypi` environment
   - [ ] Click **"Approve and deploy"**

---

## ✨ Step 4: Verify Release (2 minutes)

### Check PyPI

**URL**: <https://pypi.org/project/agentic-fleet/>

**Actions**:

1. [ ] Package appears on PyPI
2. [ ] Version matches your tag
3. [ ] README displays correctly
4. [ ] Install and test:

   ```bash
   pip install agentic-fleet
   pip show agentic-fleet
   ```

### Check GitHub

**URL**: <https://github.com/Qredence/AgenticFleet/releases>

**Actions**:

1. [ ] Release created with correct tag
2. [ ] Release notes generated
3. [ ] Artifacts uploaded (wheel + source distribution)

---

## 🎉 Done

Your automated PyPI publishing is now configured!

### For Future Releases

```bash
# 1. Update version in pyproject.toml
# 2. Commit and push changes
git commit -am "chore: bump version to X.Y.Z"
git push

# 3. Create and push tag
git tag vX.Y.Z
git push origin vX.Y.Z

# 4. Workflow runs automatically!
# 5. Check: https://github.com/Qredence/AgenticFleet/actions
```

---

## 📋 Troubleshooting

### ❌ Environment not found

- Check environment name is exactly: `pypi` (lowercase)
- Verify at: <https://github.com/Qredence/AgenticFleet/settings/environments>

### ❌ Trusted publishing failed

- Verify details at: <https://pypi.org/manage/account/publishing/>
- All fields must match exactly (case-sensitive)
- Wait 1-2 minutes and retry

### ❌ Workflow waiting forever

- You may have required reviewers enabled
- Go to: <https://github.com/Qredence/AgenticFleet/actions>
- Click workflow → "Review deployments" → "Approve and deploy"

### ❌ Package already exists

- You can't re-upload the same version
- Bump version in `pyproject.toml`
- Create new tag

---

## 📚 Documentation

- **Full Setup Guide**: `docs/PYPI_ENVIRONMENT_SETUP.md`
- **GitHub Actions Setup**: `docs/GITHUB_ACTIONS_SETUP.md`
- **Quick Reference**: `docs/WORKFLOWS_QUICK_REFERENCE.md`
- **Helper Script**: `./scripts/setup-pypi-environment.sh`

---

## 🔗 Important URLs

| Resource | URL |
|----------|-----|
| GitHub Environments | <https://github.com/Qredence/AgenticFleet/settings/environments> |
| PyPI Publishing | <https://pypi.org/manage/account/publishing/> |
| Workflow Runs | <https://github.com/Qredence/AgenticFleet/actions/workflows/release.yml> |
| PyPI Package | <https://pypi.org/project/agentic-fleet/> |
| Releases | <https://github.com/Qredence/AgenticFleet/releases> |

---

**Total Setup Time**: ~15-20 minutes

**Status**: Ready to publish! 🚀
