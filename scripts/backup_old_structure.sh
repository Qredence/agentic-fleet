#!/bin/bash
# Archive old folder structure before cleanup
# This creates a backup that can be restored if needed

echo "Creating backup of old structure..."

# Create backup directory with timestamp
BACKUP_DIR=".backup_old_structure_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Copy old folders and files
echo "Backing up old folders..."
cp -r agents/ "$BACKUP_DIR/" 2>/dev/null || true
cp -r config/ "$BACKUP_DIR/" 2>/dev/null || true
cp -r context_provider/ "$BACKUP_DIR/" 2>/dev/null || true
cp -r workflows/ "$BACKUP_DIR/" 2>/dev/null || true
cp main.py "$BACKUP_DIR/" 2>/dev/null || true

echo "✅ Backup created in: $BACKUP_DIR"
echo ""
echo "Old structure backed up. You can safely remove the old files:"
echo "  rm -rf agents/ config/ context_provider/ workflows/ main.py"
echo ""
echo "To restore if needed:"
echo "  cp -r $BACKUP_DIR/* ."
