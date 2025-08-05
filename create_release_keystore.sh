#!/bin/bash

# Script to create a release keystore for signing the app
# IMPORTANT: Keep the keystore and passwords secure!

KEYSTORE_DIR="app/keystore"
KEYSTORE_FILE="$KEYSTORE_DIR/release-keystore.jks"
KEY_ALIAS="classics-viewer-key"

# Create keystore directory
mkdir -p "$KEYSTORE_DIR"

# Check if keystore already exists
if [ -f "$KEYSTORE_FILE" ]; then
    echo "Keystore already exists at: $KEYSTORE_FILE"
    echo "If you want to create a new one, please delete the existing file first."
    exit 1
fi

echo "Creating release keystore..."
echo "You will be prompted for:"
echo "1. Keystore password (min 6 characters)"
echo "2. Key password (can be same as keystore password)"
echo "3. Your name/organization details"
echo ""
echo "IMPORTANT: Save these passwords securely! You'll need them for all future updates."
echo ""

# Generate keystore
keytool -genkey -v \
    -keystore "$KEYSTORE_FILE" \
    -alias "$KEY_ALIAS" \
    -keyalg RSA \
    -keysize 2048 \
    -validity 10000

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Keystore created successfully at: $KEYSTORE_FILE"
    echo "✓ Key alias: $KEY_ALIAS"
    echo ""
    echo "NEXT STEPS:"
    echo "1. Create a file 'keystore.properties' in the project root with:"
    echo "   storePassword=YOUR_KEYSTORE_PASSWORD"
    echo "   keyPassword=YOUR_KEY_PASSWORD"
    echo "   keyAlias=$KEY_ALIAS"
    echo "   storeFile=keystore/release-keystore.jks"
    echo ""
    echo "2. Add keystore.properties to .gitignore"
    echo "3. Keep a secure backup of both the keystore file and passwords"
else
    echo "Failed to create keystore"
    exit 1
fi