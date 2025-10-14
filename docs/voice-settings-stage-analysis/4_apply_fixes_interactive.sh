#!/bin/bash
# Interactive script to guide through applying voice settings fixes

set -e

echo "🔧 Voice Settings Fix Application Guide"
echo "========================================"
echo ""

# Check we're in the right directory
if [ ! -f "app/main.py" ]; then
    echo "❌ Error: Must run from repository root"
    echo "   Current dir: $(pwd)"
    exit 1
fi

# Check branch
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
if [ "$CURRENT_BRANCH" != "stage" ]; then
    echo "⚠️  Warning: You're on branch '$CURRENT_BRANCH', not 'stage'"
    echo "   These fixes are designed for the stage branch"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "Current branch: $CURRENT_BRANCH"
echo ""

# Step 1: Backup
echo "📦 Step 1: Creating backup..."
BACKUP_DIR="backups/voice-fixes-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp app/static/js/app.js "$BACKUP_DIR/"
cp app/templates/index.html "$BACKUP_DIR/"
echo "  ✅ Backed up to $BACKUP_DIR"
echo ""

# Step 2: Check current state
echo "🔍 Step 2: Checking current state..."
echo ""

if grep -q "voiceSelect2.innerHTML = '';" app/static/js/app.js 2>/dev/null; then
    echo "  ⚠️  Lazy population logic detected in syncVoiceSettingsDrawer"
    echo "     This will be fixed by applying Fix #2"
fi

if grep -q "updateVoiceSelectsError" app/static/js/app.js 2>/dev/null; then
    echo "  ✅ Error handling functions already present"
else
    echo "  ℹ️  Error handling functions need to be added (Fix #1)"
fi

if grep -q "voice-error-banner" app/templates/index.html 2>/dev/null; then
    echo "  ✅ Retry UI already present"
else
    echo "  ℹ️  Retry UI needs to be added (Fix #3)"
fi

echo ""

# Step 3: Manual fix prompts
echo "📝 Step 3: Apply fixes"
echo ""
echo "Please open these files and apply the fixes from docs/VOICE_SETTINGS_FIXES.md:"
echo ""
echo "  File: app/static/js/app.js"
echo "    - Fix 1: Replace initVoiceSelector() function (~line 1775-1874)"
echo "    - Fix 2: Replace syncVoiceSettingsDrawer() function (~line 3099-3114)"
echo "    - Fix 3: Add retry button event listener (in DOMContentLoaded)"
echo ""
echo "  File: app/templates/index.html"
echo "    - Fix 3: Add error banner HTML (~line 312, inside voice-settings-drawer)"
echo "    - Fix 4: Add 'disabled' attribute to both voice select elements"
echo ""
echo "Documentation: docs/VOICE_SETTINGS_FIXES.md"
echo ""
read -p "Press Enter when fixes are applied (or Ctrl+C to exit)..."

# Step 4: Validate
echo ""
echo "✓ Step 4: Validating fixes..."
if [ -f "voice-settings-fix-scripts/2_validate_fixes.js" ]; then
    if command -v node >/dev/null 2>&1; then
        node voice-settings-fix-scripts/2_validate_fixes.js
        VALIDATE_STATUS=$?
    else
        echo "  ⚠️  Node.js not found, skipping validation"
        echo "     Install Node.js to run validation script"
        VALIDATE_STATUS=0
    fi
else
    echo "  ⚠️  Validation script not found"
    VALIDATE_STATUS=0
fi

echo ""

# Step 5: Test
echo "🧪 Step 5: Testing"
echo ""
echo "Manual testing steps:"
echo "  1. Start dev server: ./run_voice.sh"
echo "  2. Open browser to http://localhost:8000"
echo "  3. Open DevTools Console (F12)"
echo "  4. Copy/paste contents of: voice-settings-fix-scripts/3_test_browser.js"
echo "  5. Verify all tests pass"
echo ""
read -p "Run automated test suite now? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ -f "./test.sh" ]; then
        ./test.sh
    else
        echo "  ⚠️  test.sh not found"
    fi
fi

echo ""

# Step 6: Review changes
echo "📋 Step 6: Review changes"
echo ""
git diff --stat app/static/js/app.js app/templates/index.html
echo ""

# Step 7: Create commit
echo "💾 Step 7: Commit changes"
echo ""
read -p "Create commit now? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    git add app/static/js/app.js app/templates/index.html

    git commit -m "fix(voice/ux): resolve voice settings drawer synchronization issues

- Populate both main and drawer voice selects immediately (no lazy loading)
- Add error handling and retry UI for failed /voices API calls
- Simplify syncVoiceSettingsDrawer to only sync values, not options
- Add disabled state to selects during initial load

Fixes race conditions and sync issues documented in:
- docs/VOICE_SETTINGS_BUGS.md (issue analysis)
- docs/VOICE_SETTINGS_FIXES.md (implementation guide)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

    echo ""
    echo "  ✅ Commit created"
    git log -1 --oneline
else
    echo "  ⏭️  Skipped commit"
    echo ""
    echo "To commit manually:"
    echo "  git add app/static/js/app.js app/templates/index.html"
    echo "  git commit -m 'fix(voice/ux): resolve voice settings drawer sync issues'"
fi

echo ""
echo "✅ Fix application complete!"
echo ""
echo "📚 Next steps:"
echo "  1. Start dev server: ./run_voice.sh"
echo "  2. Test in browser (see Step 5 above)"
echo "  3. Test with network throttling (DevTools → Network → Slow 3G)"
echo "  4. Test with /voices blocked (DevTools → Network → Request blocking)"
echo ""
echo "🔄 To rollback:"
echo "  cp $BACKUP_DIR/app.js $PWD/app/static/js/"
echo "  cp $BACKUP_DIR/index.html $PWD/app/templates/"
echo ""
echo "📖 Documentation:"
echo "  - Issue analysis: docs/VOICE_SETTINGS_BUGS.md"
echo "  - Implementation: docs/VOICE_SETTINGS_FIXES.md"
echo "  - Scripts: voice-settings-fix-scripts/README.md"
