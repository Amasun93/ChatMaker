[CmdletBinding()]
param(
    [string]$SourceRoot = "",
    [string]$RuntimeRoot = "",
    [switch]$IncludeNode,
    [switch]$ForcePortablePython,
    [switch]$CheckOnly
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Get-FullPath([string]$PathValue) {
    return [System.IO.Path]::GetFullPath($PathValue)
}

function Get-PythonInfo([string]$Executable, [string[]]$PrefixArgs) {
    if (-not $Executable) { return $null }
    try {
        $raw = & $Executable @PrefixArgs -c "import json,sys; print(json.dumps({'version':'.'.join(map(str,sys.version_info[:3])),'major':sys.version_info[0],'minor':sys.version_info[1],'executable':sys.executable}))" 2>$null
        if ($LASTEXITCODE -ne 0 -or -not $raw) { return $null }
        $value = $raw | ConvertFrom-Json
        if ($value.major -eq 3 -and $value.minor -eq 11) {
            return [pscustomobject]@{
                command = $Executable
                executable = [string]$value.executable
                version = [string]$value.version
                prefix_args = $PrefixArgs
            }
        }
    } catch {
        return $null
    }
    return $null
}

function Find-Python311([string]$PortablePython) {
    if (Test-Path -LiteralPath $PortablePython -PathType Leaf) {
        $found = Get-PythonInfo $PortablePython @()
        if ($found) { return $found }
    }
    if ($ForcePortablePython) { return $null }
    $launcher = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($launcher) {
        $found = Get-PythonInfo $launcher.Source @("-3.11")
        if ($found) { return $found }
    }
    foreach ($name in @("python.exe", "python3.exe")) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($command) {
            $found = Get-PythonInfo $command.Source @()
            if ($found) { return $found }
        }
    }
    return $null
}

function Test-Artifact([string]$PathValue, $Artifact) {
    if (-not (Test-Path -LiteralPath $PathValue -PathType Leaf)) { return $false }
    $item = Get-Item -LiteralPath $PathValue
    if ($item.Length -ne [int64]$Artifact.size) { return $false }
    return (Get-FileHash -LiteralPath $PathValue -Algorithm SHA256).Hash.ToLowerInvariant() -eq [string]$Artifact.sha256
}

function Get-Artifact([string]$Destination, $Artifact) {
    if (Test-Artifact $Destination $Artifact) {
        return [pscustomobject]@{ changed = $false; source_id = "local-cache"; source_kind = "verified_cache" }
    }
    $sources = @($Artifact.sources)
    $customBase = [string]$env:CHATMAKER_DOWNLOAD_MIRROR_BASE
    if ($customBase) {
        if (-not $customBase.StartsWith("https://", [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "CHATMAKER_DOWNLOAD_MIRROR_BASE must use HTTPS."
        }
        $custom = [pscustomobject]@{
            id = "configured-domestic-mirror"
            kind = "domestic_mirror"
            url = $customBase.TrimEnd("/") + "/" + [string]$Artifact.filename
        }
        $sources = @($custom) + $sources
    }
    $part = $Destination + ".part"
    $errors = New-Object System.Collections.Generic.List[string]
    foreach ($source in $sources) {
        Remove-Item -LiteralPath $part -Force -ErrorAction SilentlyContinue
        try {
            Write-Verbose ("Trying {0}: {1}" -f $source.kind, $source.id)
            $curl = Get-Command curl.exe -ErrorAction SilentlyContinue
            if ($curl) {
                & $curl.Source -L --fail --silent --show-error --connect-timeout 20 --max-time 300 --retry 2 --output $part $source.url
                if ($LASTEXITCODE -ne 0) { throw "curl download failed with exit code $LASTEXITCODE" }
            } else {
                Invoke-WebRequest -UseBasicParsing -Uri $source.url -OutFile $part -TimeoutSec 300
            }
            if (-not (Test-Artifact $part $Artifact)) {
                throw "Downloaded size or SHA-256 does not match the pinned manifest."
            }
            Move-Item -LiteralPath $part -Destination $Destination -Force
            return [pscustomobject]@{
                changed = $true
                source_id = [string]$source.id
                source_kind = [string]$source.kind
            }
        } catch {
            $errors.Add(([string]$source.id + ":" + $_.Exception.GetType().Name))
            Remove-Item -LiteralPath $part -Force -ErrorAction SilentlyContinue
        }
    }
    throw "All pinned download sources failed: $($errors -join ', ')"
}

function Assert-SafeStaging([string]$Candidate, [string]$Parent) {
    $candidateFull = Get-FullPath $Candidate
    $parentFull = (Get-FullPath $Parent).TrimEnd("\") + "\"
    if (-not $candidateFull.StartsWith($parentFull, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Staging directory escaped the ChatMaker runtime root."
    }
}

function Quarantine-Directory([string]$PathValue, [string]$RuntimePath) {
    if (-not (Test-Path -LiteralPath $PathValue)) { return }
    Assert-SafeStaging $PathValue $RuntimePath
    $name = (Split-Path -Leaf $PathValue) + ".old-" + (Get-Date -Format "yyyyMMddHHmmss")
    Move-Item -LiteralPath $PathValue -Destination (Join-Path $RuntimePath $name)
}

function Install-PortablePython($Artifact, [string]$RuntimePath, [string]$CachePath) {
    $archive = Join-Path $CachePath ([string]$Artifact.filename)
    $receipt = Get-Artifact $archive $Artifact
    $staging = Join-Path $RuntimePath (".staging-python-" + $PID)
    Assert-SafeStaging $staging $RuntimePath
    Remove-Item -LiteralPath $staging -Recurse -Force -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Path $staging | Out-Null
    $tar = Get-Command tar.exe -ErrorAction SilentlyContinue
    if (-not $tar) { throw "tar.exe is required to extract the pinned portable Python archive." }
    & $tar.Source -xzf $archive -C $staging
    if ($LASTEXITCODE -ne 0) { throw "Portable Python extraction failed." }
    $extracted = Join-Path $staging ([string]$Artifact.archive_root)
    $pythonExe = Join-Path $extracted "python.exe"
    if (-not (Test-Path -LiteralPath $pythonExe -PathType Leaf)) { throw "Portable Python archive layout is invalid." }
    $target = Join-Path $RuntimePath "python"
    Quarantine-Directory $target $RuntimePath
    Move-Item -LiteralPath $extracted -Destination $target
    Remove-Item -LiteralPath $staging -Recurse -Force
    return [pscustomobject]@{ python = (Join-Path $target "python.exe"); receipt = $receipt }
}

function Install-PortableNode($Artifact, [string]$RuntimePath, [string]$CachePath) {
    $archive = Join-Path $CachePath ([string]$Artifact.filename)
    $receipt = Get-Artifact $archive $Artifact
    $staging = Join-Path $RuntimePath (".staging-node-" + $PID)
    Assert-SafeStaging $staging $RuntimePath
    Remove-Item -LiteralPath $staging -Recurse -Force -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Path $staging | Out-Null
    Expand-Archive -LiteralPath $archive -DestinationPath $staging
    $extracted = Join-Path $staging ([string]$Artifact.archive_root)
    if (-not (Test-Path -LiteralPath (Join-Path $extracted "node.exe") -PathType Leaf)) {
        throw "Portable Node.js archive layout is invalid."
    }
    $target = Join-Path $RuntimePath "node"
    Quarantine-Directory $target $RuntimePath
    Move-Item -LiteralPath $extracted -Destination $target
    Remove-Item -LiteralPath $staging -Recurse -Force
    return [pscustomobject]@{ node = (Join-Path $target "node.exe"); receipt = $receipt }
}

try {
    if (-not $SourceRoot) { $SourceRoot = Split-Path -Parent $PSScriptRoot }
    $SourceRoot = Get-FullPath $SourceRoot
    if (-not $RuntimeRoot) { $RuntimeRoot = Join-Path $SourceRoot ".chatmaker-runtime" }
    $RuntimeRoot = Get-FullPath $RuntimeRoot
    $registryPath = Join-Path $SourceRoot "runtime\chatmaker\installers\runtime_sources.json"
    $lockPath = Join-Path $SourceRoot "distribution\core-runtime\requirements.lock"
    $coreRequirements = Join-Path $SourceRoot "core-runtime\requirements.txt"
    $coreWheelhouse = Join-Path $SourceRoot "core-runtime\wheelhouse"
    $offlineCore = (Test-Path -LiteralPath $coreRequirements -PathType Leaf) -and (Test-Path -LiteralPath $coreWheelhouse -PathType Container)
    if (-not (Test-Path -LiteralPath $registryPath -PathType Leaf)) { throw "Pinned runtime source registry is missing." }
    if (-not $offlineCore -and -not (Test-Path -LiteralPath $lockPath -PathType Leaf)) { throw "Pinned Python dependency lock is missing." }
    $registry = Get-Content -Raw -LiteralPath $registryPath -Encoding UTF8 | ConvertFrom-Json
    if ($registry.schema_version -ne 1 -or $registry.policy -ne "domestic-first") { throw "Runtime source registry is invalid." }
    $pythonArtifact = $registry.python.'windows-amd64'
    $nodeArtifact = $registry.node.'windows-amd64'
    $portablePython = Join-Path $RuntimeRoot "python\python.exe"
    $python = Find-Python311 $portablePython
    $mode = if ($python) { "existing-python" } else { "portable-python" }
    $plan = [ordered]@{
        success = $true
        action = "setup-local-runtime"
        status = if ($CheckOnly) { "plan" } else { "pending" }
        mode = $mode
        package_mode = if ($offlineCore) { "offline-core-wheelhouse" } else { "source-checkout" }
        source_root = $SourceRoot
        runtime_root = $RuntimeRoot
        python = if ($python) { @{ version = $python.version; executable = $python.executable } } else { @{ version = $pythonArtifact.version; sources = $pythonArtifact.sources } }
        include_node = [bool]$IncludeNode
        pip_indexes = $registry.pip_indexes
        npm_registries = $registry.npm_registries
        global_path_modified = $false
        host_configuration_modified = $false
    }
    if ($CheckOnly) {
        $plan | ConvertTo-Json -Depth 8 -Compress
        exit 0
    }

    New-Item -ItemType Directory -Force -Path $RuntimeRoot | Out-Null
    $cache = Join-Path $RuntimeRoot "downloads"
    New-Item -ItemType Directory -Force -Path $cache | Out-Null
    $pythonReceipt = $null
    if (-not $python) {
        $installed = Install-PortablePython $pythonArtifact $RuntimeRoot $cache
        $python = Get-PythonInfo $installed.python @()
        $pythonReceipt = $installed.receipt
        if (-not $python) { throw "Portable Python was extracted but failed its version check." }
    }

    $venvRoot = Join-Path $RuntimeRoot "venv"
    $venvPython = Join-Path $venvRoot "Scripts\python.exe"
    $venvInfo = Get-PythonInfo $venvPython @()
    if (-not $venvInfo) {
        Quarantine-Directory $venvRoot $RuntimeRoot
        $venvArgs = @($python.prefix_args) + @("-m", "venv", "--copies", $venvRoot)
        & $python.command $venvArgs
        if ($LASTEXITCODE -ne 0) { throw "Project-local Python environment creation failed." }
    }
    $venvInfo = Get-PythonInfo $venvPython @()
    if (-not $venvInfo) { throw "Project-local Python environment cannot start." }

    $pipSource = $null
    if ($offlineCore) {
        $pipOutput = & $venvPython -m pip install --disable-pip-version-check --no-index --require-hashes --find-links $coreWheelhouse -r $coreRequirements 2>&1
        if ($LASTEXITCODE -ne 0) { throw "Bundled offline ChatMaker wheelhouse installation failed." }
        $pipSource = [pscustomobject]@{ id = "bundled-wheelhouse"; kind = "offline_verified"; url = $coreWheelhouse }
    } else {
        $setuptoolsVersion = "82.0.1"
        $pipErrors = New-Object System.Collections.Generic.List[string]
        foreach ($index in @($registry.pip_indexes)) {
            Write-Verbose ("Installing pinned Python dependencies from {0}" -f $index.id)
            $pipOutput = & $venvPython -m pip install --disable-pip-version-check --index-url $index.url "setuptools==$setuptoolsVersion" -r $lockPath 2>&1
            if ($LASTEXITCODE -eq 0) {
                $pipSource = $index
                break
            }
            $pipErrors.Add(([string]$index.id + ":pip_failed"))
        }
        if (-not $pipSource) { throw "Pinned Python dependency installation failed: $($pipErrors -join ', ')" }
        $projectOutput = & $venvPython -m pip install --disable-pip-version-check --no-deps --no-build-isolation -e $SourceRoot 2>&1
        if ($LASTEXITCODE -ne 0) { throw "ChatMaker local runtime installation failed." }
    }

    $nodeResult = $null
    if ($IncludeNode) {
        $nodeCommand = Get-Command node.exe -ErrorAction SilentlyContinue
        $nodeVersion = $null
        if ($nodeCommand) {
            try {
                $nodeVersion = (& $nodeCommand.Source --version 2>$null).TrimStart("v")
                if ([int]($nodeVersion.Split(".")[0]) -lt 22) { $nodeVersion = $null }
            } catch { $nodeVersion = $null }
        }
        if ($nodeCommand -and $nodeVersion) {
            $nodeResult = @{ executable = $nodeCommand.Source; version = $nodeVersion; source = "existing-node" }
        } else {
            $portableNode = Install-PortableNode $nodeArtifact $RuntimeRoot $cache
            $nodeResult = @{ executable = $portableNode.node; version = $nodeArtifact.version; source = $portableNode.receipt.source_id }
        }
    }

    $binRoot = Join-Path $RuntimeRoot "bin"
    New-Item -ItemType Directory -Force -Path $binRoot | Out-Null
    foreach ($entry in Get-ChildItem -LiteralPath (Join-Path $venvRoot "Scripts") -Filter "chatmaker-*.exe" -File) {
        $name = [System.IO.Path]::GetFileNameWithoutExtension($entry.Name)
        $wrapper = Join-Path $binRoot ($name + ".cmd")
        $body = "@echo off`r`nset `"CHATMAKER_RUNTIME_ROOT=%~dp0..`"`r`nset `"PATH=%~dp0..\node;%PATH%`"`r`n`"%~dp0..\venv\Scripts\$($entry.Name)`" %*`r`n"
        [System.IO.File]::WriteAllText($wrapper, $body, [System.Text.UTF8Encoding]::new($false))
    }

    $doctorRaw = & $venvPython -m chatmaker.installers.local local 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $doctorRaw) { throw "ChatMaker local environment check failed." }
    $doctor = $doctorRaw | ConvertFrom-Json
    $result = [ordered]@{
        success = $true
        action = "setup-local-runtime"
        status = "ready"
        mode = $mode
        package_mode = if ($offlineCore) { "offline-core-wheelhouse" } else { "source-checkout" }
        runtime_root = $RuntimeRoot
        python = @{ version = $venvInfo.version; executable = $venvInfo.executable; download = $pythonReceipt }
        pip_source = @{ id = $pipSource.id; kind = $pipSource.kind; url = $pipSource.url }
        node = $nodeResult
        launcher_directory = $binRoot
        local_check = @{ status = $doctor.status; host_scan_performed = $doctor.host_scan_performed }
        global_path_modified = $false
        host_configuration_modified = $false
    }
    $result | ConvertTo-Json -Depth 8 -Compress
    exit 0
} catch {
    [ordered]@{
        success = $false
        action = "setup-local-runtime"
        status = "failed"
        error = $_.Exception.Message
        global_path_modified = $false
        host_configuration_modified = $false
    } | ConvertTo-Json -Depth 5 -Compress
    exit 1
}
