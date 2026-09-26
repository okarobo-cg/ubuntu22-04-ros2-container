<#
.SYNOPSIS
  diffbot_sim の Docker コンテナを Windows (Docker Desktop) でバックグラウンド起動する。

.DESCRIPTION
  1. Docker Desktop が動いているか確認
  2. イメージが無ければビルド (初回は 10 分程度)
  3. コンテナをバックグラウンドで起動
  起動後は shell.bat でコンテナに入り、コンテナの中で colcon build と ros2 launch を実行する
  (Ubuntu 側と同じ手順。詳しくは README の「2. クイックスタート」を参照)。

.PARAMETER Display
  wslg   : WSLg で GUI を表示 (既定。Windows 11 / WSL2 標準)
  vcxsrv : VcXsrv (X サーバ) で表示。先に XLaunch を "Disable access control" にチェックして起動しておく

.PARAMETER Gpu
  GPU 描画を使う (試験的)。うまく動かなければ付けずに実行する

.PARAMETER Build
  イメージを作り直す (Dockerfile を変更したとき)

.EXAMPLE
  .\start.ps1
  .\start.ps1 -Display vcxsrv
  .\start.ps1 -Gpu
  .\start.ps1 -Build
#>
param(
    [ValidateSet('wslg', 'vcxsrv')][string]$Display = 'wslg',
    [switch]$Gpu,
    [switch]$Build
)

. (Join-Path $PSScriptRoot 'common.ps1')

try {
    Write-Step 'Docker Desktop の確認'
    if (-not (Test-DockerRunning)) { exit 1 }
    Write-Ok 'Docker Desktop は起動しています'

    Set-DisplayEnv $Display
    Write-Ok "GUI の表示先: $Display (DISPLAY=$env:DIFFBOT_DISPLAY)"
    if ($Gpu) { Write-Warn2 'GPU 描画 (試験的) を使います' }

    $compose = Get-ComposeArgs -Gpu:$Gpu

    if ($Build -or -not (Test-ImageExists)) {
        Write-Step "イメージ $Script:ImageName をビルドします (初回は 10 分ほどかかります)"
        Invoke-Compose $compose @('build')
    } else {
        Write-Ok "イメージ $Script:ImageName があります (作り直すときは -Build)"
    }

    Write-Step 'コンテナをバックグラウンドで起動'
    # 設定 (-Gpu / -Display) が変わっていれば compose がコンテナを作り直す
    Invoke-Compose $compose @('up', '-d')
    Write-Ok "コンテナ $Script:Container が起動しました"

    Write-Host ''
    Write-Host '次は shell.bat でコンテナに入り、中で以下を実行してください:'
    Write-Host '  cd /ros2_ws && colcon build --symlink-install && source install/setup.bash'
    Write-Host '  ros2 launch robocon2027_field robocon2027.launch.py'
}
catch {
    Write-Ng $_.Exception.Message
    exit 1
}
