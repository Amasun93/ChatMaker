[CmdletBinding()]
param(
    [string]$ProjectRoot = (Get-Location).Path,
    [switch]$CheckOnly
)

$ErrorActionPreference = "Stop"

function Get-FullPath([string]$PathValue) {
    return [System.IO.Path]::GetFullPath($PathValue)
}

function Test-LockedFile([string]$PathValue, $Artifact) {
    if (-not (Test-Path -LiteralPath $PathValue -PathType Leaf)) { return $false }
    $item = Get-Item -LiteralPath $PathValue
    if ($item.Length -ne [int64]$Artifact.size) { return $false }
    return (Get-FileHash -LiteralPath $PathValue -Algorithm SHA256).Hash.ToLowerInvariant() -eq [string]$Artifact.sha256
}

try {
    $bundleRoot = Get-FullPath $PSScriptRoot
    $project = Get-FullPath $ProjectRoot
    $manifestPath = Join-Path $bundleRoot "environment-manifest.json"
    $coreRoot = Join-Path $bundleRoot "core"
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) { throw "Environment manifest is missing." }
    if (-not (Test-Path -LiteralPath $coreRoot -PathType Container)) { throw "Bundled ChatMaker Core is missing." }
    $manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($manifest.schema_version -ne 1 -or $manifest.platform_tag -ne "windows-amd64") {
        throw "Environment manifest is invalid or unsupported."
    }
    $pythonArtifact = $manifest.python
    $bundledPython = Join-Path $bundleRoot ("cache\" + [string]$pythonArtifact.filename)
    if (-not (Test-LockedFile $bundledPython $pythonArtifact)) {
        throw "Bundled Python does not match the pinned environment manifest."
    }
    $runtimeRoot = Join-Path $project ".chatmaker-runtime"
    $downloadRoot = Join-Path $runtimeRoot "downloads"
    $cachedPython = Join-Path $downloadRoot ([string]$pythonArtifact.filename)
    $plan = [ordered]@{
        success = $true
        action = "install-environment-bundle"
        status = if ($CheckOnly) { "plan" } else { "pending" }
        project_root = $project
        runtime_root = $runtimeRoot
        core_root = $coreRoot
        python_version = [string]$pythonArtifact.version
        python_source = "bundled-offline-cache"
        global_path_modified = $false
        host_configuration_modified = $false
    }
    if ($CheckOnly) {
        $plan | ConvertTo-Json -Depth 5 -Compress
        exit 0
    }
    New-Item -ItemType Directory -Path $downloadRoot -Force | Out-Null
    if (-not (Test-LockedFile $cachedPython $pythonArtifact)) {
        $part = $cachedPython + ".part"
        Remove-Item -LiteralPath $part -Force -ErrorAction SilentlyContinue
        Copy-Item -LiteralPath $bundledPython -Destination $part
        if (-not (Test-LockedFile $part $pythonArtifact)) {
            Remove-Item -LiteralPath $part -Force -ErrorAction SilentlyContinue
            throw "Copying bundled Python into the project cache failed verification."
        }
        Move-Item -LiteralPath $part -Destination $cachedPython -Force
    }
    $setup = Join-Path $coreRoot "scripts\setup_local_runtime.ps1"
    if (-not (Test-Path -LiteralPath $setup -PathType Leaf)) { throw "Bundled setup script is missing." }
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $setup -SourceRoot $coreRoot -RuntimeRoot $runtimeRoot
    exit $LASTEXITCODE
} catch {
    [ordered]@{
        success = $false
        action = "install-environment-bundle"
        status = "failed"
        error = $_.Exception.Message
        global_path_modified = $false
        host_configuration_modified = $false
    } | ConvertTo-Json -Depth 5 -Compress
    exit 1
}
