/**
 * Voice Settings Fix Test Suite - Browser Console Version
 *
 * INSTRUCTIONS:
 * 1. Start dev server: ./run_voice.sh
 * 2. Open browser to http://localhost:8000
 * 3. Open DevTools Console (F12 or Cmd+Option+J)
 * 4. Copy this entire file and paste into console
 * 5. Press Enter to run tests
 */

(async function testVoiceSettingsFixes() {
    console.log('🧪 Voice Settings Fix Test Suite');
    console.log('='.repeat(60) + '\n');

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
        console.log(`    Main select: ${!!voiceSelect}`);
        console.log(`    Drawer select: ${!!voiceSelect2}`);
        results.failed++;
    }

    // Test 2: Check if both selects have same options
    console.log('\nTest 2: Check if both selects have matching options');
    if (voiceSelect && voiceSelect2) {
        const options1 = Array.from(voiceSelect.options).map(o => o.value);
        const options2 = Array.from(voiceSelect2.options).map(o => o.value);

        if (options1.length > 0 && JSON.stringify(options1) === JSON.stringify(options2)) {
            console.log('  ✅ PASS: Both selects have identical options');
            console.log(`    Options (${options1.length}): ${options1.join(', ')}`);
            results.passed++;
        } else if (options1.length === 0) {
            console.log('  ⚠️  WARN: No options loaded yet (may still be loading)');
            results.warnings++;
        } else {
            console.log('  ❌ FAIL: Selects have different options');
            console.log(`    Main (${options1.length}): ${options1.join(', ')}`);
            console.log(`    Drawer (${options2.length}): ${options2.join(', ')}`);
            results.failed++;
        }
    }

    // Test 3: Check for error handling elements
    console.log('\nTest 3: Check for error/retry UI elements');
    const errorBanner = document.getElementById('voice-error-banner');
    const retryBtn = document.getElementById('retry-voices');

    if (errorBanner && retryBtn) {
        console.log('  ✅ PASS: Error banner and retry button found');
        results.passed++;
    } else if (errorBanner || retryBtn) {
        console.log('  ⚠️  WARN: Partial error UI (missing some elements)');
        results.warnings++;
    } else {
        console.log('  ⚠️  INFO: No error UI found (optional feature)');
        results.warnings++;
    }

    // Test 4: Simulate drawer open and check sync
    console.log('\nTest 4: Test drawer sync when opened');
    const drawer = document.getElementById('voice-settings-drawer');
    const openBtn = document.getElementById('open-voice-settings');

    if (drawer && openBtn && voiceSelect && voiceSelect2) {
        const originalValue = voiceSelect.value;

        // Open drawer
        openBtn.click();

        // Wait for sync
        await new Promise(resolve => setTimeout(resolve, 100));

        if (voiceSelect2.value === originalValue) {
            console.log('  ✅ PASS: Drawer syncs selected value correctly');
            console.log(`    Value: ${originalValue}`);
            results.passed++;
        } else {
            console.log('  ❌ FAIL: Drawer does not sync properly');
            console.log(`    Main value: ${originalValue}`);
            console.log(`    Drawer value: ${voiceSelect2.value}`);
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
    console.log('\nTest 5: Check if selects are properly enabled');
    if (voiceSelect && voiceSelect2) {
        const mainDisabled = voiceSelect.disabled;
        const drawerDisabled = voiceSelect2.disabled;
        const hasOptions = voiceSelect.options.length > 1;

        if (!mainDisabled && !drawerDisabled && hasOptions) {
            console.log('  ✅ PASS: Both selects enabled and populated');
            results.passed++;
        } else if (!hasOptions) {
            console.log('  ⚠️  WARN: Selects have no options (API may not have loaded)');
            results.warnings++;
        } else {
            console.log('  ❌ FAIL: Selects disabled (stuck in loading)');
            console.log(`    Main disabled: ${mainDisabled}`);
            console.log(`    Drawer disabled: ${drawerDisabled}`);
            results.failed++;
        }
    }

    // Test 6: Check preview functionality
    console.log('\nTest 6: Voice preview functionality');
    const previewBtn = document.getElementById('voice-preview');
    const previewAudio = document.getElementById('voice-preview-audio');

    if (previewBtn && previewAudio && voiceSelect) {
        const selectedOption = voiceSelect.options[voiceSelect.selectedIndex];
        const hasPreviewUrl = selectedOption && selectedOption.dataset.previewUrl;

        if (hasPreviewUrl) {
            console.log('  ✅ PASS: Preview button and audio element configured');
            console.log(`    Preview URL: ${selectedOption.dataset.previewUrl}`);
            results.passed++;
        } else {
            console.log('  ⚠️  WARN: No preview URL found for selected voice');
            results.warnings++;
        }
    } else {
        console.log('  ⚠️  SKIP: Preview elements not found');
        results.warnings++;
    }

    // Summary
    console.log('\n' + '='.repeat(60));
    console.log(`📊 Test Results:`);
    console.log(`   ✅ Passed: ${results.passed}`);
    console.log(`   ❌ Failed: ${results.failed}`);
    console.log(`   ⚠️  Warnings: ${results.warnings}`);
    console.log('='.repeat(60));

    if (results.failed === 0 && results.warnings === 0) {
        console.log('✅ All tests passed! Voice settings fixes working correctly.');
    } else if (results.failed === 0) {
        console.log('✅ All critical tests passed (some optional features missing).');
    } else {
        console.log('❌ Some tests failed - fixes may not be complete.');
        console.log('   Review docs/VOICE_SETTINGS_FIXES.md');
    }

    return results;
})();
