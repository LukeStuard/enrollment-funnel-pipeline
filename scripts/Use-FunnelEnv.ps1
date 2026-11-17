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

$md = Get-GatewayCredential -Target "EnrollmentFunnel-MotherDuck"
$env:MOTHERDUCK_TOKEN = $md.GetNetworkCredential().Password

# Dashboard data loaders: the funnel_dashboard service account, which can only
# read the enrollment_funnel share. Separate variable so it never replaces the
# pipeline's MOTHERDUCK_TOKEN.
$dash = Get-GatewayCredential -Target "EnrollmentFunnel-MotherDuck-RO"
$env:DASHBOARD_MOTHERDUCK_TOKEN = $dash.GetNetworkCredential().Password

Remove-Variable sf, r2, md, dash
Write-Host "Funnel environment set for this session (Salesforce extract user, R2, MotherDuck pipeline and dashboard accounts)."
