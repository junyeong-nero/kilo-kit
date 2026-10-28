# Run the one-time setup from the extracted bundle root. See scripts\setup.ps1 for the options.
param(
    [switch]$Check,
    [string]$BaseUrl,
    [string]$ApiKey,
    [string]$Model,
    [string]$RedisPassword,
    [string]$RedisUsername,
    [switch]$Reconfigure,
    [switch]$NonInteractive,
    [switch]$SystemOnly,
    [string]$SecretBlob
)
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'scripts\setup.ps1') @PSBoundParameters
