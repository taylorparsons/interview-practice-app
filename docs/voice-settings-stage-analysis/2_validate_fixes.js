#!/usr/bin/env node
/**
 * Validates that voice settings fixes are properly applied
 * Run: node voice-settings-fix-scripts/2_validate_fixes.js
 */

const fs = require('fs');
const path = require('path');

const appJsPath = path.join(__dirname, '..', 'app', 'static', 'js', 'app.js');
const indexHtmlPath = path.join(__dirname, '..', 'app', 'templates', 'index.html');

console.log('🔍 Validating voice settings fixes...\n');

let passed = 0;
let failed = 0;
let warnings = 0;

// Read files
let appJs, indexHtml;
try {
    appJs = fs.readFileSync(appJsPath, 'utf8');
    indexHtml = fs.readFileSync(indexHtmlPath, 'utf8');
} catch (err) {
    console.error('❌ ERROR: Cannot read files');
    console.error(err.message);
    process.exit(1);
}

// Test 1: Check if initVoiceSelector populates both selects
console.log('Test 1: initVoiceSelector populates both selects');
if (appJs.includes('[voiceSelect, voiceSelect2].forEach') &&
    appJs.includes('initVoiceSelector')) {
    console.log('  ✅ PASS: Both selects populated eagerly\n');
    passed++;
} else {
    console.log('  ❌ FAIL: initVoiceSelector does not populate both selects\n');
    failed++;
}

// Test 2: Check for error handling functions
console.log('Test 2: Error handling functions present');
if (appJs.includes('updateVoiceSelectsError') ||
    appJs.includes('Failed to load voices')) {
    console.log('  ✅ PASS: Error handling functions found\n');
    passed++;
} else {
    console.log('  ❌ FAIL: Missing error handling functions\n');
    failed++;
}

// Test 3: Check for retry button in HTML
console.log('Test 3: Retry UI elements in HTML');
if (indexHtml.includes('retry-voices') ||
    indexHtml.includes('voice-error-banner')) {
    console.log('  ✅ PASS: Retry UI elements found\n');
    passed++;
} else {
    console.log('  ⚠️  WARN: Retry UI not found (optional)\n');
    warnings++;
}

// Test 4: Check if syncVoiceSettingsDrawer is simplified
console.log('Test 4: syncVoiceSettingsDrawer simplified');
const syncFuncMatch = appJs.match(/function syncVoiceSettingsDrawer\(\)[^}]+\}/s);
if (syncFuncMatch && syncFuncMatch[0].length < 800) {
    console.log('  ✅ PASS: Sync function is simplified\n');
    passed++;
} else if (syncFuncMatch) {
    console.log('  ❌ FAIL: Sync function still has lazy population (>800 chars)\n');
    console.log(`    Current length: ${syncFuncMatch[0].length} chars\n`);
    failed++;
} else {
    console.log('  ❌ FAIL: Cannot find syncVoiceSettingsDrawer function\n');
    failed++;
}

// Test 5: Check for loading state in selects
console.log('Test 5: Initial disabled state on voice selects');
const voiceSelectMatch = indexHtml.match(/id="voice-select"[^>]*>/);
if (voiceSelectMatch && voiceSelectMatch[0].includes('disabled')) {
    console.log('  ✅ PASS: Main select starts disabled\n');
    passed++;
} else {
    console.log('  ⚠️  WARN: Main select should start disabled\n');
    warnings++;
}

const voiceSelect2Match = indexHtml.match(/id="voice-select-2"[^>]*>/);
if (voiceSelect2Match && voiceSelect2Match[0].includes('disabled')) {
    console.log('  ✅ PASS: Drawer select starts disabled\n');
    passed++;
} else {
    console.log('  ⚠️  WARN: Drawer select should start disabled\n');
    warnings++;
}

// Summary
console.log('='.repeat(60));
console.log(`Results: ${passed} passed, ${failed} failed, ${warnings} warnings`);

if (failed === 0 && warnings === 0) {
    console.log('✅ All fixes validated successfully!');
    process.exit(0);
} else if (failed === 0) {
    console.log('✅ Critical fixes validated (some optional features missing)');
    process.exit(0);
} else {
    console.log('❌ Some critical fixes missing or incomplete');
    console.log('   Review docs/VOICE_SETTINGS_FIXES.md for implementation details');
    process.exit(1);
}
