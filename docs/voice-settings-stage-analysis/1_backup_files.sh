#!/bin/bash
# Backup voice-related files before applying fixes

BACKUP_DIR="backups/voice-fixes-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "🔄 Creating backup in $BACKUP_DIR..."

cp app/static/js/app.js "$BACKUP_DIR/app.js.backup"
cp app/templates/index.html "$BACKUP_DIR/index.html.backup"

echo "✅ Backup complete!"
echo ""
echo "Files backed up:"
echo "  - app/static/js/app.js"
echo "  - app/templates/index.html"
echo ""
echo "To restore:"
echo "  cp $BACKUP_DIR/app.js.backup app/static/js/app.js"
echo "  cp $BACKUP_DIR/index.html.backup app/templates/index.html"
