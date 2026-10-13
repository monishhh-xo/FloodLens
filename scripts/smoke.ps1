# FloodLens AI - live endpoint smoke test.
# Usage (from the repo root, with the backend already running):
#   powershell -ExecutionPolicy Bypass -File .\scripts\smoke.ps1
#   powershell -ExecutionPolicy Bypass -File .\scripts\smoke.ps1 -BaseUrl http://127.0.0.1:8000

param(
    [string]$BaseUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"
$script:pass = 0
$script:fail = 0

function Check {
    param([string]$Label, [scriptblock]$Action)
    try {
        $result = & $Action
        Write-Host "  PASS  $Label" -ForegroundColor Green
        $script:pass++
        return $result
    }
    catch {
        Write-Host "  FAIL  $Label -> $($_.Exception.Message)" -ForegroundColor Red
        $script:fail++
        return $null
    }
}

Write-Host ""
Write-Host "FloodLens AI smoke test against $BaseUrl" -ForegroundColor Cyan
Write-Host ("-" * 60)

# 1. health
$health = Check "GET /api/health" {
    $r = Invoke-RestMethod -Uri "$BaseUrl/api/health" -Method Get -TimeoutSec 20
    if (-not $r.status) { throw "no status field" }
    $r
}
if ($health) {
    Write-Host "        status=$($health.status) version=$($health.version) engine=$($health.predictor.mode)"
    Write-Host "        ml_artifact_available=$($health.ml_artifact.available) reports=$($health.database.reports_count)"
}

# 2. zones
$zones = Check "GET /api/zones" {
    $r = Invoke-RestMethod -Uri "$BaseUrl/api/zones" -Method Get -TimeoutSec 20
    if ($r.count -lt 1) { throw "no zones returned" }
    $r
}
if ($zones) {
    Write-Host "        zones=$($zones.count) focus=$($zones.focus_city)"
    foreach ($z in $zones.zones) {
        Write-Host ("        - {0,-12} {1,6:N1} {2}" -f $z.id, $z.baseline_demo_risk.score, $z.baseline_demo_risk.risk_level)
    }
}

# 3. assess (manual rainfall)
$assess = Check "POST /api/assess (manual rainfall)" {
    $body = @{
        zone_id          = "velachery"
        rainfall_mm_1h   = 45.0
        rainfall_mm_24h  = 190.0
        forecast_mm_next_24h = 95.0
    } | ConvertTo-Json
    $r = Invoke-RestMethod -Uri "$BaseUrl/api/assess" -Method Post -ContentType "application/json" -Body $body -TimeoutSec 30
    if ($null -eq $r.rule_estimate.score) { throw "no score returned" }
    $r
}
if ($assess) {
    Write-Host "        zone=$($assess.zone.name) score=$($assess.rule_estimate.score) level=$($assess.rule_estimate.risk_level)"
    Write-Host "        ml_prototype available=$($assess.ml_prototype.available) p=$($assess.ml_prototype.probability_flood) reliable=$($assess.ml_prototype.reliable)"
    Write-Host "        rainfall_source=$($assess.data_quality.rainfall_source)"
}

# 4. assess determinism
$assess2 = Check "POST /api/assess is deterministic" {
    $body = @{ zone_id = "velachery"; rainfall_mm_1h = 45.0; rainfall_mm_24h = 190.0; forecast_mm_next_24h = 95.0 } | ConvertTo-Json
    $r = Invoke-RestMethod -Uri "$BaseUrl/api/assess" -Method Post -ContentType "application/json" -Body $body -TimeoutSec 30
    if ($r.rule_estimate.score -ne $assess.rule_estimate.score) {
        throw "score changed between identical requests ($($r.rule_estimate.score) vs $($assess.rule_estimate.score))"
    }
    $r
}

# 5. validation error
Check "POST /api/assess rejects unknown zone with 404" {
    $body = @{ zone_id = "atlantis"; rainfall_mm_1h = 10 } | ConvertTo-Json
    try {
        Invoke-RestMethod -Uri "$BaseUrl/api/assess" -Method Post -ContentType "application/json" -Body $body -TimeoutSec 20 | Out-Null
        throw "expected 404 but the request succeeded"
    }
    catch {
        $code = $_.Exception.Response.StatusCode.value__
        if ($code -ne 404) { throw "expected 404, got $code" }
        "got 404"
    }
}

# 6. live weather
$weather = Check "GET /api/weather (live Open-Meteo)" {
    $r = Invoke-RestMethod -Uri "$BaseUrl/api/weather?latitude=13.0827&longitude=80.2707" -Method Get -TimeoutSec 30
    $r
}
if ($weather) {
    if ($weather.available) {
        Write-Host "        available=$($weather.available) source=$($weather.source)"
        Write-Host "        retrieved_at_utc=$($weather.retrieved_at_utc) units=$($weather.units.precipitation)"
        Write-Host "        next_24h_mm=$($weather.summary.next_24h_precipitation_mm) peak=$($weather.summary.next_24h_peak_hourly_mm)"
    }
    else {
        Write-Host "        OFFLINE/DEMO STATE: $($weather.reason)" -ForegroundColor Yellow
    }
}

# 7. reports
$report = Check "POST /api/reports" {
    $body = @{
        zone_id     = "velachery"
        latitude    = 12.98017
        longitude   = 80.22285
        description = "Smoke test: standing water reported near the bus stand approach."
        severity    = "High"
    } | ConvertTo-Json
    $r = Invoke-RestMethod -Uri "$BaseUrl/api/reports" -Method Post -ContentType "application/json" -Body $body -TimeoutSec 20
    if ($r.source -ne "user-submitted") { throw "report not marked user-submitted" }
    $r
}

Check "GET /api/reports" {
    $r = Invoke-RestMethod -Uri "$BaseUrl/api/reports?limit=5" -Method Get -TimeoutSec 20
    if (-not $r.reports) { throw "no reports returned" }
    Write-Host "        reports=$($r.count) source=$($r.source)"
    $r
}

# 8. model info
Check "GET /api/model" {
    $r = Invoke-RestMethod -Uri "$BaseUrl/api/model" -Method Get -TimeoutSec 30
    $t = $r.metrics.logistic_regression.test
    Write-Host "        dataset=$($r.dataset_integrity.rows)x$($r.dataset_integrity.columns) sha256=$($r.dataset_integrity.sha256.Substring(0,16))..."
    Write-Host "        test acc=$($t.accuracy) prec=$($t.precision) rec=$($t.recall) f1=$($t.f1) auc=$($t.roc_auc)"
    Write-Host "        baseline=$($r.metrics.majority_class_baseline.accuracy) control_auc=$($r.metrics.shuffled_label_control.roc_auc_vs_true_labels)"
    Write-Host "        verdict signal_detected=$($r.metrics.verdict.signal_detected)"
    $r
}

Write-Host ("-" * 60)
Write-Host "PASSED: $($script:pass)   FAILED: $($script:fail)" -ForegroundColor Cyan
Write-Host ""
if ($script:fail -gt 0) { exit 1 }
