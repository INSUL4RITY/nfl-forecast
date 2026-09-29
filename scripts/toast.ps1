# Show one Windows toast notification (no extra modules). Used by nflcast alerts.
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File toast.ps1 -Title "..." -Body "..." [-Url "https://..."]
param([Parameter(Mandatory = $true)][string]$Title, [Parameter(Mandatory = $true)][string]$Body, [string]$Url = "")
$ErrorActionPreference = "Stop"
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
function Esc([string]$s) { [System.Security.SecurityElement]::Escape($s) }
$launch = if ($Url) { " activationType=`"protocol`" launch=`"$(Esc $Url)`"" } else { "" }
$xml = "<toast$launch><visual><binding template=`"ToastGeneric`"><text>$(Esc $Title)</text><text>$(Esc $Body)</text></binding></visual></toast>"
$doc = New-Object Windows.Data.Xml.Dom.XmlDocument
$doc.LoadXml($xml)
# Windows PowerShell's registered app id, so the toast shows without installing anything.
$app = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe'
$notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($app)
# Exit non-zero when Windows would not show it (notifications turned off for this app/user/policy), so it is logged
# as NOT SHOWN and retried. (Do-not-disturb / Focus hides the banner but still keeps it in the notification centre.)
if ($notifier.Setting -ne [Windows.UI.Notifications.NotificationSetting]::Enabled) { Write-Output "notifications disabled: $($notifier.Setting)"; exit 2 }
$notifier.Show([Windows.UI.Notifications.ToastNotification]::new($doc))
