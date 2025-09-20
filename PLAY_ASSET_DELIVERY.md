# Play Asset Delivery Migration

This app has been migrated from OBB files to Google Play Asset Delivery with fast-follow delivery.

## Key Changes

1. **Asset Pack Configuration**
   - Created `perseus_database` asset pack module
   - Configured as fast-follow delivery (downloads after app install)
   - Database is compressed from 774MB to 171MB using ZIP

2. **Local Testing**
   - Use bundletool with `--local-testing` flag
   - Fast-follow packs behave as on-demand in local testing
   - App requests pack download if not available

3. **Deployment**
   ```bash
   ./deploy_with_bundletool.sh
   ```

## Production Behavior

- On Google Play: Fast-follow pack downloads automatically after install
- In local testing: App requests download when needed
- Database is decompressed on first launch

## Technical Details

- Asset pack: `perseus_database` 
- Compressed size: 171MB
- Uncompressed size: 774MB
- Delivery type: fast-follow