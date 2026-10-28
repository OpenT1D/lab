param([ValidateSet('install','check','start')][string]$Action = 'check')
$ErrorActionPreference = 'Stop'
$packetPath = Split-Path -Parent $PSScriptRoot
try {
    if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) {
        throw 'WSL is required. Follow the WSL step in the supplied session guide, restart Windows, create your Ubuntu user, then try again.'
    }
    $manifest = Get-Content -LiteralPath (Join-Path $packetPath 'manifest.json') -Raw | ConvertFrom-Json
    if ($manifest.schema -ne 'opent1d.usability-packet/1' -or $manifest.commit -notmatch '^[0-9a-f]{40}$' -or $manifest.id -notmatch '^packet-[0-9a-f]{32}$') { throw 'Invalid test packet.' }
    $hash = (Get-FileHash -LiteralPath (Join-Path $packetPath 'source.bundle') -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($hash -ne $manifest.bundle_sha256) { throw 'Source bundle changed. Request an intact packet.' }
    $starterHash = (Get-FileHash -LiteralPath (Join-Path $packetPath 'Install.command') -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($starterHash -ne $manifest.inventory.files.'Install.command'.sha256) { throw 'Launch file changed. Request an intact packet.' }
    $distributions = (& wsl.exe --list --quiet 2>&1 | Out-String).Replace([string][char]0,'')
    if ($LASTEXITCODE -ne 0 -or $distributions -notmatch '(?m)^\s*Ubuntu\s*$') { throw 'Ubuntu is not initialized. Follow the supplied WSL guide and create your Ubuntu user first.' }
    $versions = (& wsl.exe --list --verbose 2>&1 | Out-String).Replace([string][char]0,'')
    if ($LASTEXITCODE -ne 0 -or $versions -notmatch '(?m)^\s*\*?\s*Ubuntu\s+.+\s+2\s*$') { throw 'This route requires Ubuntu on WSL 2. Check wsl --list --verbose; no distribution setting was changed.' }
    $linuxPacket = (& wsl.exe --distribution Ubuntu --exec wslpath -u $packetPath | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or -not $linuxPacket.StartsWith('/')) { throw 'Cannot map the packet folder into Ubuntu.' }
    if ($Action -eq 'start') {
        & wsl.exe --distribution Ubuntu --exec env OPENT1D_NO_BROWSER=1 bash ($linuxPacket + '/Install.command') start | ForEach-Object {
            Write-Host $_
            if ($_ -match '^OpenT1D session: (http://127[.]0[.]0[.]1:[0-9]+/test/)$') { Start-Process $Matches[1] }
        }
    } else {
        & wsl.exe --distribution Ubuntu --exec bash ($linuxPacket + '/Install.command') $Action
    }
    if ($LASTEXITCODE -ne 0) { throw 'OpenT1D did not complete this operation. Keep the error and use the supplied recovery guide.' }
} catch {
    Write-Host ('OpenT1D: ' + $_.Exception.Message) -ForegroundColor Red
    exit 1
}
