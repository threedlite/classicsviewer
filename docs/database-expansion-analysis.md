# Database Expansion Analysis: Adding All Greek Authors

## Executive Summary

Expanding the Classics Viewer database from 14 to ~100 Greek authors would increase the deployment size from 171MB to approximately 1.0-1.2GB compressed, requiring changes to the app's delivery strategy.

## Current Database Statistics

### Content
- **Greek Authors**: 14 out of ~100 available (14% coverage)
- **Greek Works**: 262
- **Text Lines**: 289,915
- **Works with Translations**: 249 (95% translation coverage)

### Dictionary/Morphology
- **Lemma Map Entries**: 69,435
- **Unique Lemmas**: 17,820
- **Dictionary Entries**: 28,647
- **Word Forms**: 2,767,662

### Storage
- **Uncompressed Database**: 774MB
- **Compressed (ZIP)**: 171MB (22% compression ratio)
- **Extraction Time**: ~6-7 seconds on typical device

## Projected Impact of Full Greek Corpus

### Size Estimates

Based on linear scaling with adjustments for author variation:

| Metric | Current | Projected | Multiplier |
|--------|---------|-----------|------------|
| Authors | 14 | ~100 | 7.1x |
| Uncompressed DB | 774MB | 4.6-5.4GB | 6-7x |
| Compressed DB | 171MB | 1.0-1.2GB | 6-7x |
| Text Lines | 290K | 1.7-2.0M | 6-7x |
| Unique Lemmas | 17.8K | 24-28K | 1.3-1.6x |
| Word Forms | 2.8M | 16-20M | 6-7x |

### Scaling Factors

The 6-7x multiplier (rather than 7.1x) accounts for:
- Current selection includes some of the larger authors
- Prose authors (Aristotle, Plato) have substantially more text than poets
- Not all works have available digital texts in Perseus

### Dictionary Growth

Dictionary growth is sub-linear (30-40% increase vs 600% for texts) because:
- Core vocabulary is shared across authors
- Many inflected forms map to existing lemmas
- Literary Greek has a relatively stable core vocabulary

## Deployment Implications

### Google Play Store Constraints

1. **APK Size Limit**: 150MB (exceeded by far)
2. **Asset Pack Limits**:
   - Install-time: 1GB total
   - Fast-follow: 512MB per pack
   - On-demand: 512MB per pack

### Required Changes

1. **Mandatory Fast-Follow Delivery**
   - Current: Install-time (optional for production)
   - Required: Fast-follow or on-demand
   - Users download core app first (~30-50MB)
   - Database downloads after install

2. **Potential Multi-Pack Strategy**
   - Split database by author groups
   - Multiple 200-300MB packs
   - Progressive download options

3. **User Experience Impact**
   - Initial app size: ~30-50MB
   - Post-install download: ~1GB+
   - Total storage needed: ~5-6GB (during extraction)
   - Extraction time: ~40-50 seconds

## Technical Considerations

### Database Optimization Opportunities

1. **Text Compression**
   - Store compressed text chunks
   - Decompress on-demand
   - Trade CPU for storage

2. **Selective Download**
   - Core authors in base pack
   - Additional authors on-demand
   - User choice of author sets

3. **Index Optimization**
   - Review and optimize indexes
   - Consider partial indexes
   - Balance query performance vs size

### Implementation Effort

1. **Minimal Changes** (Fast-follow only)
   - Change manifest delivery type
   - Add download progress UI
   - Handle download failures

2. **Moderate Changes** (Multi-pack)
   - Split database creation
   - Pack management logic
   - Selective author loading

3. **Major Changes** (On-demand authors)
   - Dynamic database schema
   - Author pack management
   - UI for author selection

## Recommendations

### Short Term (Minimal effort)
1. Switch to fast-follow delivery for current database
2. Test user acceptance of 1GB download
3. Monitor download completion rates

### Medium Term (If pursuing full corpus)
1. Implement multi-pack strategy
2. Create "Essential Greek Authors" base pack (300-400MB)
3. Offer additional packs by genre/period

### Long Term (Enhanced user control)
1. On-demand author downloads
2. User-selectable corpus subsets
3. Cloud backup of user selections

## Storage Requirements by User Scenario

| Scenario | Download | Extraction | Final | Total Needed |
|----------|----------|------------|-------|--------------|
| Current (14 authors) | 171MB | 774MB | 774MB | ~1GB |
| Full Greek (100 authors) | 1.2GB | 5.4GB | 5.4GB | ~6.6GB |
| Essential Pack (30 authors) | ~350MB | 1.6GB | 1.6GB | ~2GB |

## Conclusion

Adding all Greek authors is technically feasible but requires:
1. Switching to fast-follow or on-demand delivery
2. Users with 6-7GB available storage
3. Acceptance of larger download sizes
4. Potentially splitting into multiple packs for better user experience

The 6-7x size increase is substantial but manageable with modern devices and Google Play's asset delivery infrastructure.