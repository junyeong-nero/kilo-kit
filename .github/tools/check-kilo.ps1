# Disposable CI runner only: verify relocated setup and startup without a real model API.
param([Parameter(Mandatory=$true)][string]$Bundle)
$ErrorActionPreference = 'Stop'
$utf8 = New-Object Text.UTF8Encoding($false)
$profile = Join-Path $env:RUNNER_TEMP ('kilo-profile-' + [guid]::NewGuid().ToString('N'))
foreach ($kind in @('CONFIG', 'CACHE', 'DATA', 'STATE')) {
    [Environment]::SetEnvironmentVariable("XDG_${kind}_HOME", (Join-Path $profile $kind.ToLower()), 'Process')
}
$project = Join-Path $profile 'project'
New-Item -ItemType Directory -Force -Path $project | Out-Null
$registry = @{
    provider = @{ id = 'corp'; name = 'Smoke test'; baseUrl = 'http://127.0.0.1:1/v1'; apiKeyEnv = 'sk-ci-placeholder' }
    default = 'kit-smoke'
    models = @(@{ id = 'kit-smoke'; contextWindow = 8192; maxTokens = 1024; imageInput = $true })
}
[IO.File]::WriteAllText((Join-Path $Bundle 'config\models.json'), ($registry | ConvertTo-Json -Depth 8), $utf8)
$exe = Join-Path $Bundle 'bin\kilo\kilo.exe'
$rule = 'kilo-kit-ci-' + [guid]::NewGuid().ToString('N')
New-NetFirewallRule -DisplayName $rule -Direction Outbound -Program $exe -Action Block -Profile Any | Out-Null
Push-Location $project
try {
    & (Join-Path $Bundle 'setup.ps1') -NonInteractive
    foreach ($file in @('models.json', 'models.json.bak')) {
        $text = [IO.File]::ReadAllText((Join-Path $Bundle "config\$file"), $utf8)
        if ($text.Contains('sk-ci-placeholder')) { throw 'Inline key leaked to registry or backup.' }
        if (($text | ConvertFrom-Json).provider.apiKeyEnv -ne 'CORP_LLM_API_KEY') { throw 'Key variable was not normalized.' }
    }
    if ([Environment]::GetEnvironmentVariable('CORP_LLM_API_KEY', 'Machine') -cne 'sk-ci-placeholder') { throw 'Key was not registered exactly.' }
    $configPath = Join-Path $env:XDG_CONFIG_HOME 'kilo\kilo.json'
    $config = [IO.File]::ReadAllText($configPath, $utf8) | ConvertFrom-Json
    if ($config.model -ne 'corp/kit-smoke') { throw 'Provider/model config did not install.' }
    foreach ($name in @('build_center', 'word', 'windows')) {
        if ($config.mcp.$name.enabled -ne $true) { throw "Missing MCP: $name" }
    }
    # This does not call a model or desktop tools. Capture native stderr safely on PowerShell 5.1.
    $ErrorActionPreference = 'Continue'
    $output = @(& $exe session list --format json 2>&1 | ForEach-Object { "$_" })
    $code = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    if ($code) { throw "Kilo session startup failed: $($output -join '`n')" }
    Write-Host 'KILO_SETUP_KEYS_AND_SESSION_OK (no model inference or desktop UI test)'
} finally {
    Pop-Location
    Remove-NetFirewallRule -DisplayName $rule
}
