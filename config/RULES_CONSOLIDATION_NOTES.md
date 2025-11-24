# Rules.json Consolidation Notes

**Date:** 2025-11-24

## Source Files Compared

1. `/algorithm/engines/rules.json`
2. `/api/src/main/resources/rules.json`
3. `/modules/rules.json`

## Differences Found

### Difference 1: max-consecutive-days rule (line 14-22)

**algorithm/engines/rules.json** and **modules/rules.json**:
```json
{
  "id": "max-consecutive-days",
  "params": {
    "max_worked": 5
  }
}
```

**api/src/main/resources/rules.json** (MORE COMPLETE):
```json
{
  "id": "max-consecutive-days",
  "params": {
    "window": 6,
    "max_worked": 5
  }
}
```

**Decision:** Use API version with explicit `"window": 6` parameter for clarity.

---

### Difference 2: total-workdays rule ID (line 43-44)

**api/src/main/resources/rules.json**:
```json
"id": "max-workdays-per-year"
```

**algorithm/engines/rules.json** and **modules/rules.json**:
```json
"id": "total-workdays-per-year"
```

**Decision:** Use `"total-workdays-per-year"` as it appears in 2/3 files.

---

### Difference 3: total-workdays limits (line 49-51)

**algorithm/engines/rules.json** and **api/src/main/resources/rules.json**:
```json
"params": {
  "max": 223,
  "min": 223
}
```

**modules/rules.json** (DIFFERENT VALUES):
```json
"params": {
  "max": 300,
  "min": 300
}
```

**⚠️ CRITICAL DIFFERENCE:**
- 2 files use 223 days
- 1 file uses 300 days

**Decision:** Use **223** as it appears in 2/3 files and is more restrictive (safer default).

**Action Required:** User should verify which value is correct for production use.

---

## Consolidated Version

The consolidated `rules.json` uses:
- ✅ Explicit `window: 6` parameter (from API version)
- ✅ ID: `total-workdays-per-year` (from majority)
- ✅ Max/min: **223** days (from majority - but verify!)

## Migration Path

After consolidation:
1. All services will reference `/config/rules.json`
2. Old files can be safely deleted:
   - `/algorithm/engines/rules.json`
   - `/api/src/main/resources/rules.json`
   - `/modules/rules.json`
3. Services need config path updates

## TODO

- [ ] Verify with domain expert: Should total workdays be 223 or 300?
- [ ] Update Java Spring Boot to load from `/config/rules.json`
- [ ] Update Python modules to load from `/config/rules.json`
- [ ] Remove old duplicate files after validation
