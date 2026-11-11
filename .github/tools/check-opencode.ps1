# CI only: a disposable Windows runner, relocated bundle, empty profile and blocked OpenCode egress.
param([Parameter(Mandatory=$true)][string]$Bundle)
$ErrorActionPreference = 'Stop'
$utf8 = New-Object Text.UTF8Encoding($false)
$profile = Join-Path $env:RUNNER_TEMP ('opencode-profile-' + [guid]::NewGuid().ToString('N'))
$env:XDG_CONFIG_HOME = Join-Path $profile 'config'
$env:XDG_CACHE_HOME = Join-Path $profile 'cache'
$env:XDG_DATA_HOME = Join-Path $profile 'data'
$env:XDG_STATE_HOME = Join-Path $profile 'state'
$project = Join-Path $profile 'project'
New-Item -ItemType Directory -Force -Path $project | Out-Null
$registry = @{
    provider = @{ id = 'corp'; name = 'Smoke test'; baseUrl = 'http://127.0.0.1:1/v1'; apiKeyEnv = 'OPENCODE_KIT_CI_KEY' }
    default = 'kit-smoke'
    models = @(@{ id = 'kit-smoke'; contextWindow = 8192; maxTokens = 1024; imageInput = $true })
}
[IO.File]::WriteAllText((Join-Path $Bundle 'config\models.json'), ($registry | ConvertTo-Json -Depth 8), $utf8)
# The unreachable loopback API exercises the saved-model fallback; this does not test inference.
& (Join-Path $Bundle 'setup.ps1') -NonInteractive
$command = Join-Path $Bundle 'bin\opencode.cmd'
$exe = Join-Path $Bundle 'bin\opencode\opencode.exe'
$rule = 'opencode-kit-ci-' + [guid]::NewGuid().ToString('N')
New-NetFirewallRule -DisplayName $rule -Direction Outbound -Program $exe -Action Block -Profile Any | Out-Null
Push-Location $project
try {
    & $command --version
    if ($LASTEXITCODE) { throw 'OpenCode version check failed.' }
    # Do not invoke desktop MCP tools on the runner. These are imported separately during packaging.
    $configPath = Join-Path $env:XDG_CONFIG_HOME 'opencode\opencode.json'
    $config = [IO.File]::ReadAllText($configPath, $utf8) | ConvertFrom-Json
    foreach ($property in $config.mcp.PSObject.Properties) { $property.Value.enabled = $false }
    [IO.File]::WriteAllText($configPath, ($config | ConvertTo-Json -Depth 20), $utf8)
    $beforeLock = Get-FileHash (Join-Path $env:XDG_CONFIG_HOME 'opencode\package-lock.json')
    $resolved = (& $command debug config | Out-String)
    if ($LASTEXITCODE) { throw 'OpenCode config initialization failed.' }
    $parsed = $resolved | ConvertFrom-Json
    if ($parsed.model -ne 'corp/kit-smoke') { throw 'Custom provider/model did not load.' }
    $agent = (& $command debug agent build | Out-String)
    if ($LASTEXITCODE) { throw 'OpenCode tool initialization failed.' }
    $tools = ($agent | ConvertFrom-Json).tools
    foreach ($name in @('encoding_read', 'encoding_edit', 'encoding_write')) {
        if ($tools.$name -ne $true) { throw "Encoding tool not available: $name" }
    }
    if ($tools.apply_patch -eq $true) { throw 'apply_patch bypass is enabled.' }
    $afterLock = Get-FileHash (Join-Path $env:XDG_CONFIG_HOME 'opencode\package-lock.json')
    if ($beforeLock.Hash -ne $afterLock.Hash) { throw 'OpenCode changed preinstalled dependencies during first startup.' }
    Write-Host 'OFFLINE_CONFIG_AND_TOOLS_OK (no model inference or desktop UI test)'
} finally {
    Pop-Location
    Remove-NetFirewallRule -DisplayName $rule
}
