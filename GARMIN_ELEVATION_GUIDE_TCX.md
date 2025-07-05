# Garmin Connect Elevation Preservation Guide (Updated for Clean TCX)

## The Problem
Garmin Connect automatically "corrects" elevation data in imported routes based on:
1. Geographic location (DEM - Digital Elevation Model)
2. Barometric pressure data
3. GPS elevation corrections

**Update**: Even TCX files with 5,000m elevation offset and remote ocean coordinates are being rejected by Garmin Connect with "Your course cannot be imported. Something is wrong with this file."

## New Solution: Clean TCX Conversion

### What Changed
After testing various anti-Garmin strategies (coordinate relocation, elevation offsets), we found that:
- ❌ **FIT files with 10,000m offset**: Garmin zeroed all elevations
- ❌ **TCX files with 5,000m offset + remote coordinates**: Garmin rejects import ("Something is wrong with this file")
- ✅ **Clean TCX files**: Direct conversion from original GPX to TCX without modifications

### Clean TCX Approach
The new `--clean-tcx` mode converts original GPX files directly to TCX format without any coordinate relocation or elevation offsets:

```bash
python3 gpxscaler.py --clean-tcx --folder .
```

**Benefits:**
- ✅ Uses original Tour de France coordinates (authentic geography)
- ✅ Preserves original elevation data (no artificial offsets)
- ✅ Maximum Garmin Connect compatibility (clean file structure)
- ✅ TCX format often better respected by Garmin than FIT files

**What This Creates:**
- Original coordinates: `50.5949800, 3.0371900` (France, not remote ocean)
- Original elevations: `42.0m` (not `5042.0m`)
- Clean TCX structure that Garmin Connect should accept

## Current Status - MAJOR FINDING

- ❌ **Modified files with anti-Garmin strategies**: Rejected by Garmin Connect
- ❌ **Clean TCX files with original data**: **IMPORTED BUT ELEVATIONS STILL ZEROED**
- 📁 **Output location**: `clean_tcx/` folder with `*_clean.tcx` files

### 🚨 **Critical Discovery**
Even perfectly clean TCX files with:
- ✅ Original Tour de France coordinates (authentic France locations)
- ✅ Original elevation data (no artificial offsets)
- ✅ Proper TCX format structure
- ✅ Successful import to Garmin Connect

**Still result in zeroed elevations!**

This proves that **Garmin Connect force-corrects ALL imported elevation data**, regardless of:
- File format (FIT, TCX, GPX)
- Coordinate location (real vs remote ocean)
- Elevation values (original vs offset)
- File structure quality

## What This Means

Garmin Connect appears to have an **aggressive DEM-based elevation correction system** that:
1. **Overrides all imported elevation data** with their own terrain database
2. **Treats all external elevation sources as "untrusted"**
3. **Cannot be bypassed** with file format or coordinate tricks

This is likely a deliberate design decision to ensure elevation consistency across their platform.

## How to Use Clean TCX Conversion

### Command Line (Recommended)
```bash
python3 gpxscaler.py --clean-tcx --folder .
```

This creates clean TCX files with:
- Original Tour de France coordinates (France, not remote ocean)
- Original elevation data (no artificial 5,000m offset)
- Maximum Garmin Connect compatibility

### File Comparison

| Feature | Modified TCX (Old) | Clean TCX (New) |
|---------|-------------------|-----------------|
| Coordinates | Remote ocean (0°, 180°) | Original France locations |
| Elevation | +5,000m offset applied | Original elevation data |
| Garmin Import | ❌ "Something is wrong" | ✅ Should import cleanly |

## Testing Clean TCX Files

### Step 1: Import to Garmin Connect
1. Go to Garmin Connect website
2. Import files from `clean_tcx/` folder
3. Files should have names like `stage-1-route_clean.tcx`

### Step 2: Check Results
- ✅ **Success**: Files import and elevations are preserved
- ❌ **Import error**: Garmin still rejects clean files
- ❌ **Elevations zeroed**: Garmin force-corrects all elevation data

## Current Clean TCX Status
- ✅ **19 files converted** to clean TCX format
- ✅ **Original coordinates preserved** (France locations)
- ✅ **Original elevations preserved** (no artificial offsets)
- 🧪 **Ready for Garmin Connect testing**

## File Structure
TCX files contain elevation data like this:
```xml
<Trackpoint>
  <Position>
    <LatitudeDegrees>0.000000</LatitudeDegrees>
    <LongitudeDegrees>180.000000</LongitudeDegrees>
  </Position>
  <AltitudeMeters>5000.0</AltitudeMeters>
</Trackpoint>
```

## Backup Strategy
If Garmin Connect still corrects the TCX elevation:
1. Use the generated GPX files instead
2. Import to other platforms like Strava, TrainingPeaks, or RideWithGPS
3. Try third-party Garmin tools like Garmin BaseCamp
4. Consider using different coordinate locations (try terrain options 2-6)

## File Locations
- Scaled TCX files: `YYYYMMDD_HHMMSS/` folder (*.tcx extension)
- Original GPX files: Current directory
- This guide: `GARMIN_ELEVATION_GUIDE.md`

## Command Reference
```bash
# List available terrain coordinates
python3 gpxscaler.py --list-terrain

# Scale with specific terrain and TCX output
python3 gpxscaler.py --scale 0.5 --terrain 1 --fit

# Scale with custom coordinates
python3 gpxscaler.py --scale 0.5 --start-lat 0 --start-lon 180 --fit
```

## Next Steps for Testing
1. **Import one TCX file** into Garmin Connect
2. **Check elevation profile** - should show elevations around 5,000m+
3. **Verify shape preservation** - the elevation profile shape should match your scaled profile
4. **Test different terrain options** if first attempt still gets corrected
5. **Report results** to determine if TCX format works better

## Alternative Strategies (If TCX Fails)
1. **Try different terrain coordinates** (options 2-6)
2. **Increase elevation offset** back to 10,000m or higher
3. **Use pure GPX import** to Garmin Connect
4. **Switch to alternative platforms** that respect elevation data

## Alternative Solutions (Since Garmin Cannot Be Bypassed)

Since Garmin Connect force-corrects all elevation data, here are working alternatives:

### 1. Use Other Platforms ✅
- **Strava**: Often preserves imported elevation data
- **TrainingPeaks**: Respects TCX elevation values
- **RideWithGPS**: Good elevation preservation
- **Komoot**: Maintains imported profiles

### 2. Garmin Desktop Tools ✅
- **Garmin BaseCamp**: Desktop software that may respect elevation
- **Garmin Connect IQ**: Developer tools for custom data handling

### 3. Manual Workaround for Garmin Connect
1. Import your clean TCX files to get the route geometry
2. Note Garmin's auto-corrected elevations
3. Use external elevation analysis tools to get the real profile
4. Manually adjust training zones/power targets based on real elevation

### 4. Generate Reference Data
Use the elevation analysis tool to document the real elevation profiles:

```bash
python3 elevation_analysis.py stage-1-route.gpx
```

This gives you the actual ascent/descent data to reference while using Garmin's auto-corrected routes.

### 5. Hybrid Approach
- Use Garmin Connect for device sync and route navigation
- Use other platforms (Strava, TrainingPeaks) for elevation-accurate training analysis
- Keep the clean TCX files as reference for real elevation data

## Final Recommendation

**For Training with Accurate Elevation Data:**
1. Import clean TCX files to **Strava or TrainingPeaks**
2. Use these platforms for elevation-based training analysis
3. Sync routes to Garmin devices for navigation (accept the elevation auto-correction)

**For Garmin Connect Users:**
1. Accept that Garmin will auto-correct elevations
2. Use the route geometry for navigation
3. Reference the original elevation data for training planning

---
*Generated by GPXScaler - Updated for TCX Format*
