# GitHub Actions Workflow Guide: How to Re-run and Trigger Workflows

## Overview

This guide explains how to re-run and trigger GitHub Actions workflows, specifically focusing on the Jekyll deployment workflow that experienced issues in run #17764461227.

## The Issue: Startup Failure Analysis

### What Happened
- **Workflow Run**: [#17764461227](https://github.com/logic-arts-official/Better-Bahn/actions/runs/17764461227)
- **Status**: `startup_failure` 
- **Problem**: The workflow never started due to configuration issues
- **Solution**: Fixed in commit `4db5cc5` with action pinning and permission updates

### Root Cause
The workflow had configuration problems that prevented it from starting properly. The fix involved:
1. Pinning GitHub Actions to specific SHA versions for security
2. Setting proper permissions (`contents: read`, `pages: write`, `id-token: write`)
3. Updating action versions to compatible releases

## Methods to Re-run/Trigger GitHub Actions Workflows

### 1. **Re-run from GitHub UI** (Recommended for Manual Triggers)

Navigate to the specific workflow run and use the re-run options:

```
https://github.com/logic-arts-official/Better-Bahn/actions/runs/17764461227
```

**Available Options:**
- **Re-run all jobs**: Runs the entire workflow again with the same commit
- **Re-run failed jobs**: Only runs jobs that failed (not applicable for startup failures)

**Note**: For startup failures like #17764461227, this method won't work because the workflow never properly initialized.

### 2. **Push a New Commit** (Automatic Trigger)

The Jekyll workflow is configured to trigger on pushes to the `main` branch:

```yaml
on:
  push:
    branches: [ main ]
```

**Methods to trigger:**
```bash
# Make a small change and push
git commit --allow-empty -m "Trigger workflow re-run"
git push origin main

# Or modify a file
echo "# Updated $(date)" >> README.md
git add README.md
git commit -m "Update README to trigger workflow"
git push origin main
```

### 3. **Manual Workflow Dispatch** (If Configured)

Add `workflow_dispatch` to enable manual triggers:

```yaml
on:
  push:
    branches: [ main ]
  workflow_dispatch:  # Enables manual triggering
```

Then trigger via:
- GitHub UI: Actions tab → Select workflow → "Run workflow" button
- GitHub CLI: `gh workflow run jekyll-gh-pages.yml`
- GitHub API: POST to `/repos/OWNER/REPO/actions/workflows/WORKFLOW_ID/dispatches`

### 4. **Using GitHub CLI**

```bash
# List workflows
gh workflow list

# Run a specific workflow (if workflow_dispatch is enabled)
gh workflow run "Deploy docs to GitHub Pages"

# View recent runs
gh run list --workflow="jekyll-gh-pages.yml"

# Re-run a specific run (limited scenarios)
gh run rerun 17764461227
```

### 5. **Using GitHub API**

```bash
# Trigger workflow dispatch (if enabled)
curl -X POST \
  -H "Authorization: token YOUR_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/logic-arts-official/Better-Bahn/actions/workflows/jekyll-gh-pages.yml/dispatches \
  -d '{"ref":"main"}'

# Re-run a workflow
curl -X POST \
  -H "Authorization: token YOUR_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/logic-arts-official/Better-Bahn/actions/runs/17764461227/rerun
```

## Current Status: Problem Resolved ✅

The workflow issue has been **automatically resolved**:

- **Failed Run**: #17764461227 (startup_failure)
- **Fixed Run**: #17764625894 (success) 
- **Fix Commit**: `4db5cc5` - "Update GitHub Actions for Jekyll deployment"

The subsequent push triggered the workflow again and it completed successfully.

## Best Practices for Workflow Troubleshooting

### 1. **Diagnosis Steps**
```bash
# Check workflow configuration
cat .github/workflows/jekyll-gh-pages.yml

# View recent workflow runs
gh run list --workflow="jekyll-gh-pages.yml" --limit=5

# Check workflow status
gh run view RUN_ID
```

### 2. **Common Solutions**
- **Startup Failures**: Usually configuration issues → Check syntax and permissions
- **Permission Errors**: Add required permissions to workflow file
- **Action Version Issues**: Pin to specific working versions
- **Branch Protection**: Ensure workflow has permission to write to target branch

### 3. **Prevention Strategies**
- Pin actions to specific SHA versions for security and stability
- Use proper permission scopes
- Test workflow changes in feature branches
- Monitor workflow runs for early detection of issues

## Workflow Configuration Analysis

### Current Working Configuration
```yaml
name: Deploy docs to GitHub Pages
on:
  push:
    branches: [ main ]

permissions:
  contents: read    # Read repository contents
  pages: write      # Deploy to GitHub Pages
  id-token: write   # OIDC token for deployment

concurrency:
  group: "pages"
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@08c6903cd8c0fde910a37f88322edcfb5dd907a8  # v5.0.0
      - name: Configure Pages
        uses: actions/configure-pages@983d7736d9b0ae728b81ab479565c72886d7745b  # v5
      - name: Build with Jekyll
        uses: actions/jekyll-build-pages@44a6e6beabd48582f863aeeb6cb2151cc1716697  # v1.0.13
        with:
          source: ./docs
          destination: ./_site
      - name: Upload artifact
        uses: actions/upload-pages-artifact@7b1f4a764d45c48632c6b24a0339c27f5614fb0b  # v4.0.0
        with:
          path: ./_site

  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    needs: build
    steps:
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@d6db90164ac5ed86f2b6aed7e0febac5b3c0c03e  # v4.0.5
```

### Key Improvements Made
1. **Action Pinning**: All actions pinned to specific SHA hashes
2. **Proper Permissions**: Explicit permission grants for pages deployment
3. **Concurrency Control**: Prevents multiple deployments from running simultaneously
4. **Environment Configuration**: Proper GitHub Pages environment setup

## Summary

**For the specific issue #17764461227**: The problem was automatically resolved by the fix in commit `4db5cc5`. The workflow now runs successfully on every push to main.

**For future re-runs**: Use any of the methods above, with pushing a new commit being the most reliable approach for this particular workflow configuration.