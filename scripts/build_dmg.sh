#!/usr/bin/env bash
# Builds the standalone "DB Playground" macOS app (no Docker, no Homebrew required
# on the end user's machine) and packages it into a .dmg.
#
# Requires on the BUILD machine: Xcode command line tools, Homebrew with
# postgresql@16 and mongodb/brew/mongodb-community@7.0 and dylibbundler installed,
# Python 3.11+, and Node/pnpm (via corepack).
#
# Output: dist/DB Playground.dmg

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
SWIFT_DIR="$ROOT_DIR/desktop/DBPlaygroundApp"
DIST_DIR="$ROOT_DIR/dist"
APP_NAME="DB Playground"
APP_BUNDLE="$DIST_DIR/$APP_NAME.app"
BUNDLE_ID="com.shinhh95.dbplayground"
APP_VERSION="1.1.0"

POSTGRES_KEG="$(brew --prefix postgresql@16 2>/dev/null || true)"
MONGOD_KEG="$(brew --prefix mongodb-community@7.0 2>/dev/null || true)"

log() { printf '\n\033[1;32m==>\033[0m %s\n' "$1"; }
fail() { printf '\n\033[1;31mERROR:\033[0m %s\n' "$1" >&2; exit 1; }

[ -n "$POSTGRES_KEG" ] || fail "postgresql@16 not found via Homebrew. Run: brew install postgresql@16"
[ -n "$MONGOD_KEG" ] || fail "mongodb-community@7.0 not found via Homebrew. Run: brew tap mongodb/brew && brew install mongodb-community@7.0"
command -v dylibbundler >/dev/null || fail "dylibbundler not found. Run: brew install dylibbundler"
command -v swift >/dev/null || fail "swift not found. Install Xcode command line tools."
command -v node >/dev/null || fail "node not found."

rm -rf "$DIST_DIR"
mkdir -p "$DIST_DIR"

log "Building frontend (single-origin build: API and SPA share one port)"
cd "$FRONTEND_DIR"
corepack enable >/dev/null 2>&1 || true
pnpm install
VITE_API_URL="" pnpm build

log "Copying frontend build into backend/static"
rm -rf "$BACKEND_DIR/static"
cp -R "$FRONTEND_DIR/dist" "$BACKEND_DIR/static"

log "Setting up backend build virtualenv"
cd "$BACKEND_DIR"
rm -rf .build-venv
python3 -m venv .build-venv
source .build-venv/bin/activate
pip install -q --upgrade pip
pip install -q -e ".[desktop]"

log "Freezing backend with PyInstaller"
rm -rf build dist
pyinstaller --name db-playground-backend --onedir --noconfirm \
  --collect-all uvicorn --collect-all psycopg --collect-submodules pymongo \
  --collect-all alembic \
  desktop_entry.py

BACKEND_DIST="$BACKEND_DIR/dist/db-playground-backend"
[ -d "$BACKEND_DIST" ] || fail "PyInstaller did not produce $BACKEND_DIST"

# app.main resolves STATIC_DIR relative to sys.executable when frozen, so the
# frontend build must sit directly next to the frozen executable, not under _internal.
cp -R "$BACKEND_DIR/static" "$BACKEND_DIST/static"

# app.desktop.migrations resolves alembic.ini/alembic/ the same way, under
# "migrations/" -- Alembic's ScriptDirectory reads versions/*.py off disk, so
# these need to be real files next to the executable, not just importable
# from the frozen PYZ archive.
mkdir -p "$BACKEND_DIST/migrations"
cp "$BACKEND_DIR/alembic.ini" "$BACKEND_DIST/migrations/"
cp -R "$BACKEND_DIR/alembic" "$BACKEND_DIST/migrations/alembic"
find "$BACKEND_DIST/migrations" -name "__pycache__" -type d -prune -exec rm -rf {} +

log "Bundling self-contained PostgreSQL + MongoDB binaries (no Homebrew needed at runtime)"
DB_BIN="$BACKEND_DIST/db-bin"
mkdir -p "$DB_BIN"
cp "$POSTGRES_KEG/bin/postgres" "$POSTGRES_KEG/bin/initdb" "$POSTGRES_KEG/bin/pg_ctl" "$DB_BIN/"
cp "$MONGOD_KEG/bin/mongod" "$DB_BIN/"
chmod +w "$DB_BIN"/*

(
  cd "$DB_BIN"
  dylibbundler -od -b -x postgres -x initdb -x pg_ctl -d lib -p "@executable_path/lib/"
)

log "Verifying no remaining Homebrew references in bundled binaries"
for f in "$DB_BIN"/postgres "$DB_BIN"/initdb "$DB_BIN"/pg_ctl "$DB_BIN"/mongod "$DB_BIN"/lib/*.dylib; do
  if otool -L "$f" | grep -Eq "/opt/homebrew|/usr/local"; then
    fail "Homebrew-absolute dependency left in $f -- dylibbundler pass incomplete"
  fi
done

deactivate

log "Building the SwiftUI launcher app"
cd "$SWIFT_DIR"
swift build -c release
SWIFT_BIN_DIR="$(swift build -c release --show-bin-path)"

log "Assembling the .app bundle"
mkdir -p "$APP_BUNDLE/Contents/MacOS" "$APP_BUNDLE/Contents/Resources"
cp "$SWIFT_BIN_DIR/DBPlaygroundApp" "$APP_BUNDLE/Contents/MacOS/DBPlaygroundApp"
cp -R "$BACKEND_DIST" "$APP_BUNDLE/Contents/Resources/backend"

cat > "$APP_BUNDLE/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key><string>$APP_NAME</string>
    <key>CFBundleDisplayName</key><string>$APP_NAME</string>
    <key>CFBundleIdentifier</key><string>$BUNDLE_ID</string>
    <key>CFBundleVersion</key><string>$APP_VERSION</string>
    <key>CFBundleShortVersionString</key><string>$APP_VERSION</string>
    <key>CFBundleExecutable</key><string>DBPlaygroundApp</string>
    <key>CFBundlePackageType</key><string>APPL</string>
    <key>LSMinimumSystemVersion</key><string>13.0</string>
    <key>NSHighResolutionCapable</key><true/>
    <key>LSApplicationCategoryType</key><string>public.app-category.education</string>
</dict>
</plist>
PLIST

log "Ad-hoc code signing the app bundle"
codesign --force --deep --sign - "$APP_BUNDLE"

log "Creating the .dmg"
STAGING="$DIST_DIR/dmg-staging"
rm -rf "$STAGING"
mkdir -p "$STAGING"
cp -R "$APP_BUNDLE" "$STAGING/"
ln -s /Applications "$STAGING/Applications"

DMG_PATH="$DIST_DIR/$APP_NAME.dmg"
rm -f "$DMG_PATH"
hdiutil create -volname "$APP_NAME" -srcfolder "$STAGING" -ov -format UDZO "$DMG_PATH"
rm -rf "$STAGING"

log "Done: $DMG_PATH"
