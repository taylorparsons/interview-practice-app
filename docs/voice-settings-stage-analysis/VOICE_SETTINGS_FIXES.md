# Voice Settings Fixes - Implementation Guide

**Related**: See `VOICE_SETTINGS_BUGS.md` for full issue analysis
**Target Branch**: `stage` (commit `d317cd1`)
**Status**: Ready to implement

---

## Quick Start

```bash
# 1. Checkout stage branch
git checkout stage

# 2. Create backup branch
git checkout -b stage-voice-fixes-backup

# 3. Return to stage
git checkout stage

# 4. Run the fix validation script
node scripts/validate_voice_fixes.js

# 5. Apply fixes (manual - see sections below)

# 6. Run tests
./test.sh
node scripts/test_voice_fixes.js
```

---

## Automated Scripts

### Script 1: Backup Current Files

**File**: `scripts/backup_voice_files.sh`

```bash
#!/bin/bash
# Backup voice-related files before applying fixes

BACKUP_DIR="backups/voice-fixes-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "Creating backup in $BACKUP_DIR..."

cp app/static/js/app.js "$BACKUP_DIR/app.js.backup"
cp app/templates/index.html "$BACKUP_DIR/index.html.backup"

echo "✅ Backup complete!"
echo "To restore: cp $BACKUP_DIR/* app/static/js/ && cp $BACKUP_DIR/*.html app/templates/"
```

### Script 2: Validate Fixes Applied

**File**: `scripts/validate_voice_fixes.js`

```javascript
#!/usr/bin/env node
/**
 * Validates that voice settings fixes are properly applied
 * Run: node scripts/validate_voice_fixes.js
 */

const fs = require('fs');
const path = require('path');

const appJsPath = path.join(__dirname, '..', 'app', 'static', 'js', 'app.js');
const indexHtmlPath = path.join(__dirname, '..', 'app', 'templates', 'index.html');

console.log('🔍 Validating voice settings fixes...\n');

let passed = 0;
let failed = 0;

// Read files
const appJs = fs.readFileSync(appJsPath, 'utf8');
const indexHtml = fs.readFileSync(indexHtmlPath, 'utf8');

// Test 1: Check if initVoiceSelector populates both selects
console.log('Test 1: Check if initVoiceSelector populates both selects');
if (appJs.includes('[voiceSelect, voiceSelect2].forEach') &&
    appJs.includes('initVoiceSelector')) {
    console.log('  ✅ PASS: Both selects populated in initVoiceSelector\n');
    passed++;
} else {
    console.log('  ❌ FAIL: initVoiceSelector does not populate both selects\n');
    failed++;
}

// Test 2: Check for error handling functions
console.log('Test 2: Check for error handling functions');
if (appJs.includes('updateVoiceSelectsError') ||
    appJs.includes('Failed to load voices')) {
    console.log('  ✅ PASS: Error handling functions present\n');
    passed++;
} else {
    console.log('  ❌ FAIL: Missing error handling functions\n');
    failed++;
}

// Test 3: Check for retry button in HTML
console.log('Test 3: Check for retry button in HTML');
if (indexHtml.includes('retry-voices') ||
    indexHtml.includes('voice-error-banner')) {
    console.log('  ✅ PASS: Retry UI elements found\n');
    passed++;
} else {
    console.log('  ⚠️  WARN: Retry UI not found (optional feature)\n');
}

// Test 4: Check if syncVoiceSettingsDrawer is simplified
console.log('Test 4: Check if syncVoiceSettingsDrawer is simplified');
const syncFuncMatch = appJs.match(/function syncVoiceSettingsDrawer\(\)[^}]+\}/s);
if (syncFuncMatch && syncFuncMatch[0].length < 800) {
    console.log('  ✅ PASS: syncVoiceSettingsDrawer is simplified\n');
    passed++;
} else {
    console.log('  ❌ FAIL: syncVoiceSettingsDrawer still has lazy population logic\n');
    failed++;
}

// Test 5: Check for loading state in selects
console.log('Test 5: Check for initial disabled state on selects');
if (indexHtml.includes('id="voice-select"') &&
    indexHtml.match(/id="voice-select"[^>]*disabled/)) {
    console.log('  ✅ PASS: Voice selects start disabled\n');
    passed++;
} else {
    console.log('  ❌ FAIL: Voice selects should start disabled\n');
    failed++;
}

// Summary
console.log('='.repeat(50));
console.log(`Results: ${passed} passed, ${failed} failed`);
if (failed === 0) {
    console.log('✅ All critical fixes validated!');
    process.exit(0);
} else {
    console.log('❌ Some fixes missing or incomplete');
    process.exit(1);
}
```

### Script 3: Test Voice Loading Scenarios

**File**: `scripts/test_voice_fixes.js`

```javascript
#!/usr/bin/env node
/**
 * Browser-based test script for voice settings fixes
 * Copy-paste into browser console when app is running
 */

console.log(`
/**
 * Voice Settings Fix Test Suite
 * Run this in the browser console with the app loaded
 */

(async function testVoiceSettingsFixes() {
    console.log('🧪 Starting Voice Settings Fix Tests...\\n');

    const results = {
        passed: 0,
        failed: 0,
        warnings: 0
    };

    // Test 1: Both selects exist
    console.log('Test 1: Check if both voice selects exist');
    const voiceSelect = document.getElementById('voice-select');
    const voiceSelect2 = document.getElementById('voice-select-2');

    if (voiceSelect && voiceSelect2) {
        console.log('  ✅ PASS: Both selects found');
        results.passed++;
    } else {
        console.log('  ❌ FAIL: Missing voice select elements');
        results.failed++;
    }

    // Test 2: Check if both selects have same options
    console.log('\\nTest 2: Check if both selects have matching options');
    if (voiceSelect && voiceSelect2) {
        const options1 = Array.from(voiceSelect.options).map(o => o.value);
        const options2 = Array.from(voiceSelect2.options).map(o => o.value);

        if (JSON.stringify(options1) === JSON.stringify(options2)) {
            console.log('  ✅ PASS: Both selects have identical options');
            console.log(\`    Options: \${options1.join(', ')}\`);
            results.passed++;
        } else {
            console.log('  ❌ FAIL: Selects have different options');
            console.log(\`    Main: \${options1.join(', ')}\`);
            console.log(\`    Drawer: \${options2.join(', ')}\`);
            results.failed++;
        }
    }

    // Test 3: Check for error handling elements
    console.log('\\nTest 3: Check for error/retry UI elements');
    const errorBanner = document.getElementById('voice-error-banner');
    const retryBtn = document.getElementById('retry-voices');

    if (errorBanner && retryBtn) {
        console.log('  ✅ PASS: Error banner and retry button found');
        results.passed++;
    } else if (errorBanner || retryBtn) {
        console.log('  ⚠️  WARN: Partial error UI (missing some elements)');
        results.warnings++;
    } else {
        console.log('  ⚠️  WARN: No error UI found (not critical)');
        results.warnings++;
    }

    // Test 4: Simulate drawer open and check sync
    console.log('\\nTest 4: Test drawer sync when opened');
    const drawer = document.getElementById('voice-settings-drawer');
    const openBtn = document.getElementById('open-voice-settings');

    if (drawer && openBtn && voiceSelect && voiceSelect2) {
        const originalValue = voiceSelect.value;

        // Open drawer
        openBtn.click();

        // Wait a tick for sync
        await new Promise(resolve => setTimeout(resolve, 100));

        if (voiceSelect2.value === originalValue) {
            console.log('  ✅ PASS: Drawer syncs selected value correctly');
            results.passed++;
        } else {
            console.log('  ❌ FAIL: Drawer does not sync properly');
            console.log(\`    Main value: \${originalValue}\`);
            console.log(\`    Drawer value: \${voiceSelect2.value}\`);
            results.failed++;
        }

        // Close drawer
        const closeBtn = document.getElementById('close-voice-settings');
        if (closeBtn) closeBtn.click();
    } else {
        console.log('  ⚠️  SKIP: Cannot test (missing elements)');
        results.warnings++;
    }

    // Test 5: Check if selects are enabled (not stuck in loading)
    console.log('\\nTest 5: Check if selects are properly enabled');
    if (voiceSelect && voiceSelect2) {
        const mainDisabled = voiceSelect.disabled;
        const drawerDisabled = voiceSelect2.disabled;

        if (!mainDisabled && !drawerDisabled) {
            console.log('  ✅ PASS: Both selects are enabled');
            results.passed++;
        } else {
            console.log('  ❌ FAIL: Selects are disabled (stuck in loading state)');
            console.log(\`    Main disabled: \${mainDisabled}\`);
            console.log(\`    Drawer disabled: \${drawerDisabled}\`);
            results.failed++;
        }
    }

    // Summary
    console.log('\\n' + '='.repeat(50));
    console.log(\`Results: \${results.passed} passed, \${results.failed} failed, \${results.warnings} warnings\`);

    if (results.failed === 0) {
        console.log('✅ All critical tests passed!');
    } else {
        console.log('❌ Some tests failed - fixes may not be complete');
    }

    return results;
})();
`);
```

### Script 4: Generate Fix Patches

**File**: `scripts/generate_voice_patches.sh`

```bash
#!/bin/bash
# Generate patch files for voice settings fixes

PATCH_DIR="patches"
mkdir -p "$PATCH_DIR"

echo "📦 Generating patch files for voice settings fixes..."

# This script generates separate patches for each fix
# Apply with: git apply patches/fix-*.patch

cat > "$PATCH_DIR/README.md" <<'EOF'
# Voice Settings Fix Patches

Apply these patches in order:

```bash
# Apply all patches
git apply patches/fix-1-eager-population.patch
git apply patches/fix-2-simplified-sync.patch
git apply patches/fix-3-retry-ui.patch

# Or apply individually as needed
```

## Patch Descriptions

- **fix-1-eager-population.patch**: Updates initVoiceSelector to populate both selects immediately
- **fix-2-simplified-sync.patch**: Simplifies syncVoiceSettingsDrawer function
- **fix-3-retry-ui.patch**: Adds error banner and retry button

## Rollback

```bash
git apply -R patches/fix-*.patch
```
EOF

echo "✅ Patch README created"
echo ""
echo "Note: Actual patches must be created manually using git diff after fixes are applied:"
echo "  git diff > patches/voice-settings-complete.patch"
```

### Script 5: Interactive Fix Applier

**File**: `scripts/apply_voice_fixes.sh`

```bash
#!/bin/bash
# Interactive script to guide through applying voice settings fixes

set -e

echo "🔧 Voice Settings Fix Application Script"
echo "========================================"
echo ""

# Check we're on stage branch
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "stage" ]; then
    echo "⚠️  Warning: You're on branch '$CURRENT_BRANCH', not 'stage'"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Step 1: Backup
echo "Step 1: Creating backup..."
BACKUP_DIR="backups/voice-fixes-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp app/static/js/app.js "$BACKUP_DIR/"
cp app/templates/index.html "$BACKUP_DIR/"
echo "  ✅ Backed up to $BACKUP_DIR"
echo ""

# Step 2: Check current state
echo "Step 2: Checking current state..."
if grep -q "voiceSelect2.innerHTML = '';" app/static/js/app.js 2>/dev/null; then
    echo "  ⚠️  Warning: Lazy population logic detected in syncVoiceSettingsDrawer"
fi
if grep -q "updateVoiceSelectsError" app/static/js/app.js 2>/dev/null; then
    echo "  ℹ️  Error handling already present"
fi
echo ""

# Step 3: Manual fix prompts
echo "Step 3: Apply fixes manually using VOICE_SETTINGS_FIXES.md"
echo ""
echo "Please apply the following fixes:"
echo "  1. Update initVoiceSelector() function in app/static/js/app.js"
echo "  2. Update syncVoiceSettingsDrawer() function in app/static/js/app.js"
echo "  3. Add error banner HTML to app/templates/index.html"
echo "  4. Add retry button event listener to app/static/js/app.js"
echo ""
read -p "Press Enter when fixes are applied..."

# Step 4: Validate
echo ""
echo "Step 4: Validating fixes..."
if [ -f "scripts/validate_voice_fixes.js" ]; then
    node scripts/validate_voice_fixes.js
else
    echo "  ⚠️  Validation script not found (scripts/validate_voice_fixes.js)"
fi

# Step 5: Test
echo ""
echo "Step 5: Running tests..."
read -p "Run test suite? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    ./test.sh
fi

# Step 6: Create commit
echo ""
echo "Step 6: Commit changes"
read -p "Create commit now? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    git add app/static/js/app.js app/templates/index.html
    git commit -m "fix(voice/ux): resolve voice settings drawer synchronization issues

- Populate both main and drawer voice selects immediately (no lazy loading)
- Add error handling and retry UI for failed /voices API calls
- Simplify syncVoiceSettingsDrawer to only sync values, not options
- Add disabled state to selects during initial load

Fixes race conditions and sync issues documented in docs/VOICE_SETTINGS_BUGS.md"
    echo "  ✅ Commit created"
else
    echo "  Skipped commit. Run manually: git add ... && git commit"
fi

echo ""
echo "✅ Fix application complete!"
echo ""
echo "Next steps:"
echo "  1. Start dev server: ./run_voice.sh"
echo "  2. Open browser console and run: scripts/test_voice_fixes.js"
echo "  3. Test manually with network throttling"
echo ""
echo "To rollback: cp $BACKUP_DIR/* app/static/js/ && cp $BACKUP_DIR/*.backup app/templates/"
```

---

## Fix 1: Eager Population with Error Handling

**File**: `app/static/js/app.js`
**Function**: `initVoiceSelector()`
**Lines to Replace**: ~1775-1874

### Complete Implementation

```javascript
async function initVoiceSelector() {
    let voices = [];

    // Fetch voices from API
    try {
        const res = await fetch('/voices');
        if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to load voices`);
        voices = await res.json();
    } catch (err) {
        console.error('Voice catalog load error:', err);
        updateVoiceSelectsError(err.message);
        return;
    }

    // Handle empty response
    if (!voices || voices.length === 0) {
        updateVoiceSelectsEmpty();
        return;
    }

    // Populate BOTH main and drawer selects immediately (no lazy loading)
    [voiceSelect, voiceSelect2].forEach(select => {
        if (!select) return;

        // Clear existing options
        while (select.firstChild) {
            select.removeChild(select.firstChild);
        }

        // Add voice options
        voices.forEach(v => {
            const opt = document.createElement('option');
            opt.value = v.id;
            opt.textContent = v.label || v.id;
            if (v.preview_url) opt.dataset.previewUrl = v.preview_url;
            select.appendChild(opt);
        });

        // Enable the select
        select.disabled = false;
    });

    // Wire up preview button for main voice selector
    if (voicePreviewBtn && voiceSelect && voicePreviewAudio) {
        const setPreviewLoading = (loading) => {
            const orig = voicePreviewBtn.dataset.origLabel || voicePreviewBtn.textContent;
            if (!voicePreviewBtn.dataset.origLabel) {
                voicePreviewBtn.dataset.origLabel = orig;
            }
            voicePreviewBtn.disabled = !!loading;
            voicePreviewBtn.classList.toggle('opacity-50', !!loading);
            voiceSelect.disabled = !!loading;
            if (startVoiceBtn) startVoiceBtn.disabled = !!loading;
            voicePreviewBtn.textContent = loading ? 'Loading…' : voicePreviewBtn.dataset.origLabel;
        };

        const attachAutoRestore = () => {
            const restore = () => setPreviewLoading(false);
            voicePreviewAudio.addEventListener('playing', restore, { once: true });
            voicePreviewAudio.addEventListener('canplay', restore, { once: true });
            voicePreviewAudio.addEventListener('error', restore, { once: true });
            voicePreviewAudio.addEventListener('ended', restore, { once: true });
        };

        voicePreviewBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            const opt = voiceSelect.options[voiceSelect.selectedIndex];
            const url = opt && opt.dataset.previewUrl;
            if (!url) {
                alert('No preview available for this voice.');
                return;
            }
            try {
                setPreviewLoading(true);
                attachAutoRestore();
                try { voicePreviewAudio.pause(); } catch (_) {}
                voicePreviewAudio.currentTime = 0;
                voicePreviewAudio.src = url;
                voicePreviewAudio.classList.remove('hidden');
                await voicePreviewAudio.play().catch(() => {});
            } catch (_) {
                setPreviewLoading(false);
            }
        });
    }

    // Wire up save button for main voice selector
    if (voiceSaveBtn && voiceSelect) {
        voiceSaveBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            if (!state.sessionId) {
                alert('Start or resume a session first.');
                return;
            }
            const voiceId = voiceSelect.value;
            if (!voiceId) return;
            try {
                const r = await fetch(`/session/${state.sessionId}/voice`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ voice_id: voiceId })
                });
                if (!r.ok) {
                    const detail = await r.text();
                    throw new Error(detail || 'Failed to save voice');
                }
                if (voiceSelect2) voiceSelect2.value = voiceId;
                let applied = false;
                if (state.voice && state.voice.peer) {
                    applied = confirm('Voice saved. Restart the voice session now to apply the new voice?');
                    if (applied) {
                        try { stopVoiceInterview({ silent: true }); } catch (_) {}
                        setTimeout(() => startVoiceInterview(), 150);
                    }
                }
                if (!applied) alert('Voice saved. New prompts will use this voice.');
            } catch (err) {
                alert(err.message || 'Unable to save voice');
            }
        });
    }
}

// Helper: Show error state in both selects
function updateVoiceSelectsError(message) {
    [voiceSelect, voiceSelect2].forEach(select => {
        if (!select) return;
        select.innerHTML = `<option value="">⚠️ Failed to load voices</option>`;
        select.disabled = true;
        select.title = message || 'Error loading voice catalog';
    });
    const voiceErrorBanner = document.getElementById('voice-error-banner');
    const voiceErrorMessage = document.getElementById('voice-error-message');
    if (voiceErrorBanner && voiceErrorMessage) {
        voiceErrorMessage.textContent = message || 'Network error or service unavailable.';
        voiceErrorBanner.classList.remove('hidden');
    }
}

// Helper: Show empty state in both selects
function updateVoiceSelectsEmpty() {
    [voiceSelect, voiceSelect2].forEach(select => {
        if (!select) return;
        select.innerHTML = `<option value="">No voices available</option>`;
        select.disabled = true;
    });
}
```

---

## Fix 2: Simplified Sync Function

**File**: `app/static/js/app.js`
**Function**: `syncVoiceSettingsDrawer()`
**Lines to Replace**: ~3099-3114

```javascript
function syncVoiceSettingsDrawer() {
    if (!state || !state.voice) return;
    if (toggleBrowserAsr2) toggleBrowserAsr2.checked = !!(state.voice.config && state.voice.config.useBrowserAsr);
    if (toggleShowMetadata2) toggleShowMetadata2.checked = !!(state.voice.config && state.voice.config.showMetadata);
    if (coachLevelSelect && coachLevelSelect2) coachLevelSelect2.value = coachLevelSelect.value;
    // Sync voice selection (both already have same options from initVoiceSelector)
    if (voiceSelect && voiceSelect2 && voiceSelect.value) {
        voiceSelect2.value = voiceSelect.value;
    }
}
```

---

## Fix 3: Add Retry UI

### HTML Changes

**File**: `app/templates/index.html`
**Add after line ~312 (inside voice-settings-drawer):**

```html
<!-- ERROR BANNER -->
<div id="voice-error-banner" class="hidden mb-3 p-3 bg-red-50 border border-red-200 rounded-md">
    <div class="flex items-start gap-2">
        <svg class="w-5 h-5 text-red-600 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 9.586 8.707 8.293z" clip-rule="evenodd"/>
        </svg>
        <div class="flex-1 text-sm">
            <p class="font-medium text-red-800">Failed to load voices</p>
            <p id="voice-error-message" class="text-red-700 mt-1"></p>
            <button id="retry-voices" class="mt-2 py-1 px-3 border border-red-300 rounded-md text-xs font-medium text-red-700 bg-white hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-red-500">
                Retry
            </button>
        </div>
    </div>
</div>
```

### JavaScript Changes

**File**: `app/static/js/app.js`
**Add in DOMContentLoaded or setupEventListeners:**

```javascript
// Retry button for voice loading failures
const retryVoicesBtn = document.getElementById('retry-voices');
const voiceErrorBanner = document.getElementById('voice-error-banner');

if (retryVoicesBtn) {
    retryVoicesBtn.addEventListener('click', async () => {
        if (voiceErrorBanner) voiceErrorBanner.classList.add('hidden');
        [voiceSelect, voiceSelect2].forEach(select => {
            if (!select) return;
            select.innerHTML = '<option value="">⏳ Loading voices...</option>';
            select.disabled = true;
        });
        await initVoiceSelector();
    });
}
```

---

## Implementation Checklist

- [ ] **Step 1**: Run `bash scripts/backup_voice_files.sh`
- [ ] **Step 2**: Apply Fix 1 - Replace `initVoiceSelector()`
- [ ] **Step 3**: Apply Fix 2 - Replace `syncVoiceSettingsDrawer()`
- [ ] **Step 4**: Apply Fix 3 - Add HTML error banner
- [ ] **Step 5**: Apply Fix 3 - Add retry event listener
- [ ] **Step 6**: Update select initial states to `disabled`
- [ ] **Step 7**: Run `node scripts/validate_voice_fixes.js`
- [ ] **Step 8**: Start server and run browser tests
- [ ] **Step 9**: Test with network throttling
- [ ] **Step 10**: Commit changes

---

## Questions?

Contact: jennifer.mckinney@outlook.com
