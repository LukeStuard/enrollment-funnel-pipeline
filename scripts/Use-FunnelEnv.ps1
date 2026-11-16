# Sets the extract's environment variables for this PowerShell session from
# Windows Credential Manager. Nothing is written to disk or printed.
# Usage (dot-source so the variables stay in your session):  . .\scripts\Use-FunnelEnv.ps1

. "$PSScriptRoot\GatewayCredential.ps1"

$sf = Get-GatewayCredential -Target "EnrollmentFunnel-SF"
$env:SF_INSTANCE_URL  = "https://orgfarm-5ea30c60fa-dev-ed.develop.my.salesforce.com"
$env:SF_CLIENT_ID     = $sf.UserName
$env:SF_CLIENT_SECRET = $sf.GetNetworkCredential().Password

$r2 = Get-GatewayCredential -Target "EnrollmentFunnel-R2"
$env:R2_ACCOUNT_ID        = "e0c21530d52ee1a25cbb8a6853b02168"
$env:R2_ACCESS_KEY_ID     = $r2.UserName
$env:R2_SECRET_ACCESS_KEY = $r2.GetNetworkCredential().Password

Remove-Variable sf, r2
Write-Host "Funnel environment set for this session (Salesforce extract user, R2)."
