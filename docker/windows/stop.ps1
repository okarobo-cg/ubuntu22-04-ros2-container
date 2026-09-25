<#
.SYNOPSIS
  diffbot_sim コンテナを停止する。

.PARAMETER Remove
  停止に加えてコンテナを削除する (docker compose down)。
  src / config / models / worlds はホストにあるので消えないが、
  コンテナ内の build / install や、コンテナ内で apt install したものは消える。

.EXAMPLE
  .\stop.ps1            # 停止のみ (次回 start.bat ですぐ再開)
  .\stop.ps1 -Remove    # 停止して削除
#>
param([switch]$Remove)

. (Join-Path $PSScriptRoot 'common.ps1')

try {
    if (-not (Test-DockerRunning)) { exit 1 }
    $compose = Get-ComposeArgs
    if ($Remove) {
        Write-Step "コンテナ $Script:Container を停止して削除します"
        Invoke-Compose $compose @('down')
    } else {
        Write-Step "コンテナ $Script:Container を停止します"
        Invoke-Compose $compose @('stop')
    }
    Write-Ok '完了'
}
catch {
    Write-Ng $_.Exception.Message
    exit 1
}
