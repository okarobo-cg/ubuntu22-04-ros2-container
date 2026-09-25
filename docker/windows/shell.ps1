<#
.SYNOPSIS
  起動中の diffbot_sim コンテナで bash を開く (端末を増やすとき)。
.EXAMPLE
  .\shell.ps1
#>
. (Join-Path $PSScriptRoot 'common.ps1')

if (-not (Test-DockerRunning)) { exit 1 }
if (-not (Test-ContainerRunning)) {
    Write-Ng "コンテナ $Script:Container が起動していません。先に start.bat (start.ps1) を実行してください。"
    exit 1
}
Write-Step 'コンテナの bash を開きます (exit で抜ける。コンテナは動いたまま)'
# compose ファイルに依存しないよう docker exec を直接使う
& docker exec -it $Script:Container bash
