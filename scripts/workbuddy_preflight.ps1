param(
    [string]$SourceRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$RuntimeRoot = "",
    [string]$ExpectedRevision = "",
    [string]$ExpectedTag = "v0.2.0-beta.6"
)

$ErrorActionPreference = "Stop"
$previousRuntime = $env:CHATMAKER_RUNTIME_ROOT
try {
    $SourceRoot = [System.IO.Path]::GetFullPath($SourceRoot)
    if (-not $RuntimeRoot) { $RuntimeRoot = Join-Path $SourceRoot ".chatmaker-runtime" }
    $RuntimeRoot = [System.IO.Path]::GetFullPath($RuntimeRoot)
    if (-not $ExpectedRevision) {
        $resolved = & git -C $SourceRoot rev-parse --verify "${ExpectedTag}^{commit}" 2>$null
        if ($LASTEXITCODE -ne 0) { throw "release_tag_missing: fetch origin tags before testing" }
        $ExpectedRevision = ([string]$resolved).Trim()
    }
    if ($ExpectedRevision -notmatch '^[0-9a-f]{40}$') { throw "full_commit_sha_required" }
    $python = Join-Path $RuntimeRoot "venv\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw "runtime_missing: run setup_local_runtime.ps1 for this source and runtime" }
    $env:CHATMAKER_RUNTIME_ROOT = $RuntimeRoot
    $raw = & $python -m chatmaker.hardware.workflow --version --expect-revision $ExpectedRevision --expect-source-root $SourceRoot --progress none
    $commandExit = $LASTEXITCODE
    $result = $raw | ConvertFrom-Json
    if ($commandExit -ne 0 -or -not $result.success) { throw "runtime_guard_failed:$($result.error)" }
    if ($result.runtime.source_dirty -ne $false) { throw "source_not_clean: preserve changes and report before testing" }
    if ($result.runtime.version -ne "0.2.0b6" -or $result.runtime.installed_version -ne "0.2.0b6") {
        throw "installed_version_mismatch: rerun setup_local_runtime.ps1 for this checkout"
    }
    if ([System.IO.Path]::GetFullPath($result.runtime.python) -ne $python) { throw "python_path_mismatch" }
    if ([System.IO.Path]::GetFullPath($result.runtime.runtime_root) -ne $RuntimeRoot) { throw "runtime_root_mismatch" }
    [ordered]@{ success = $true; action = "workbuddy-preflight"; expected_revision = $ExpectedRevision;
        runtime = $result.runtime; hardware_test_performed = $false } | ConvertTo-Json -Depth 6 -Compress
    exit 0
} catch {
    [ordered]@{ success = $false; action = "workbuddy-preflight"; error = $_.Exception.Message;
        hardware_test_performed = $false } | ConvertTo-Json -Compress
    exit 1
} finally {
    $env:CHATMAKER_RUNTIME_ROOT = $previousRuntime
}
