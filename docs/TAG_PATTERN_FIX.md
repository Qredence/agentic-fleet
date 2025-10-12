# GitHub Tag Pattern Fix

## ❌ Issue: "Name is invalid" error

When creating the tag rule for the `pypi` environment, you're getting an "Name is invalid" error.

## ✅ Solution: Use correct tag pattern syntax

GitHub uses **glob patterns** for tag rules. Here are the correct patterns:

### Option 1: Semver Tags (Recommended)

```
v[0-9]+.[0-9]+.[0-9]+
```

This matches:

- ✅ `v0.5.0`
- ✅ `v1.0.0`
- ✅ `v2.3.4`
- ❌ `v0.5.0-alpha` (does not match pre-releases)

### Option 2: Semver with Pre-releases

```
v[0-9]+.[0-9]+.[0-9]+*
```

This matches:

- ✅ `v0.5.0`
- ✅ `v1.0.0`
- ✅ `v0.5.0-alpha1`
- ✅ `v2.3.4-beta.2`

### Option 3: Any v-prefixed tag (Most permissive)

```
v*
```

This matches:

- ✅ `v0.5.0`
- ✅ `v1.0.0`
- ✅ `v0.5.0-alpha`
- ✅ `vanything`

## 🎯 Recommended Pattern

For production releases, use:

```
v[0-9]+.[0-9]+.[0-9]+
```

For testing with pre-releases, use:

```
v[0-9]+.[0-9]+.[0-9]+*
```

## 📋 Step-by-Step Fix

1. Go to: <https://github.com/Qredence/AgenticFleet/settings/environments>
2. Click on **"pypi"** environment (if already created)
3. Under "Deployment branches and tags":
   - If there's an existing rule with error, click the ❌ to remove it
   - Click **"Add deployment branch or tag rule"**
4. In the pattern field, enter: **`v[0-9]+.[0-9]+.[0-9]+*`**
5. Click **"Add rule"**

## ✅ Verification

After adding the rule, you should see:

- Tag pattern: `v[0-9]+.[0-9]+.[0-9]+*`
- No error messages

## 🧪 Test Pattern

The pattern `v[0-9]+.[0-9]+.[0-9]+*` will match:

| Tag | Matches? |
|-----|----------|
| `v0.5.0` | ✅ Yes |
| `v1.0.0` | ✅ Yes |
| `v0.5.0-alpha1` | ✅ Yes |
| `v2.3.4-beta.2` | ✅ Yes |
| `0.5.0` | ❌ No (missing `v` prefix) |
| `version-1.0` | ❌ No (wrong format) |

## 📝 Note

The original pattern `v*.*.*` uses shell glob syntax which GitHub doesn't support for tag rules. GitHub requires more specific patterns using:

- `*` - matches any characters
- `[0-9]+` - matches one or more digits
- `?` - matches single character

---

**TL;DR**: Use `v[0-9]+.[0-9]+.[0-9]+*` instead of `v*.*.*`
