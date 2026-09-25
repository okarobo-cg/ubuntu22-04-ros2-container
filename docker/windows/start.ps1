<#
.SYNOPSIS
  diffbot_sim を Windows (Docker Desktop) で起動する。

.DESCRIPTION
  1. Docker Desktop が動いているか確認
  2. イメージが無ければビルド (初回は 10 分程度)
  3. コンテナを起動
  4. コンテナ内で colcon build してシミュレーションを起動 (または bash を開く)

.PARAMETER Launch
  robocon : ABU Robocon 2027 フィールド (既定)
  diffbot : 練習用ワールド
  shell   : シミュレーションは起動せず、コンテナの bash を開く

.PARAMETER Team
  robocon のときのチーム (red / blue)。既定 red

.PARAMETER Display
  wslg   : WSLg で GUI を表示 (既定。Windows 11 / WSL2 標準)
  vcxsrv : VcXsrv (X サーバ) で表示。先に XLaunch を "Disable access control" にチェックして起動しておく

.PARAMETER Gpu
  GPU 描画を使う (試験的)。うまく動かなければ付けずに実行する

.PARAMETER Build
  イメージを作り直す (Dockerfile を変更したとき)

.PARAMETER NoRviz
  RViz2 を起動しない (軽くしたいとき)

.PARAMETER Headless
  Gazebo の画面を出さない (GUI が出ないときの切り分け用)

.EXAMPLE
  .\start.ps1
  .\start.ps1 -Launch diffbot
  .\start.ps1 -Team blue -NoRviz
  .\start.ps1 -Launch shell
  .\start.ps1 -Display vcxsrv
  .\start.ps1 -Gpu
#>
param(
    [ValidateSet('robocon', 'diffbot', 'shell')][string]$Launch = 'robocon',
    [ValidateSet('red', 'blue')][string]$Team = 'red',
    [ValidateSet('wslg', 'vcxsrv')][string]$Display = 'wslg',
    [switch]$Gpu,
    [switch]$Build,
    [switch]$NoRviz,
    [switch]$Headless
)

. (Join-Path $PSScriptRoot 'common.ps1')

try {
    Write-Step 'Docker Desktop の確認'
    if (-not (Test-DockerRunning)) { exit 1 }
    Write-Ok 'Docker Desktop は起動しています'

    Initialize-ProjectDirs
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

    Write-Step 'コンテナを起動'
    # 設定 (-Gpu / -Display) が変わっていれば compose がコンテナを作り直す
    Invoke-Compose $compose @('up', '-d')
    Write-Ok "コンテナ $Script:Container が起動しました"

    if ($Launch -eq 'shell') {
        Write-Step 'コンテナの bash を開きます (exit で抜ける。コンテナは動いたまま)'
        & docker @compose exec ros2 bash
        exit 0
    }

    # コンテナ内で実行するコマンド (ダブルクォートを含めないこと: PowerShell 5.1 の引数渡しで壊れるため)
    $rviz = if ($NoRviz) { 'false' } else { 'true' }
    $gui  = if ($Headless) { 'false' } else { 'true' }
    $launchCmd = switch ($Launch) {
        'robocon' { "ros2 launch robocon2027_field robocon2027.launch.py team:=$Team rviz:=$rviz gui:=$gui" }
        'diffbot' { "ros2 launch diffbot_sim sim.launch.py rviz:=$rviz gui:=$gui" }
    }
    # 最初に前回の Gazebo が残っていたら止める ([i] は pkill が自分自身にマッチしないための書き方。
    # 該当なしで失敗してもよいので ; でつなぐ)
    $cmd = "pkill -f '[i]gn gazebo' ; sleep 1 ; " + (@(
        'source /opt/ros/humble/setup.bash',
        'cd /ros2_ws',
        'colcon build --symlink-install',
        'source install/setup.bash',
        $launchCmd
    ) -join ' && ')

    Write-Step "シミュレーションを起動: $launchCmd"
    Write-Host '  終了するときはこの画面で Ctrl+C を押してください。'
    Write-Host '  操縦するには、別の PowerShell で windows\teleop.bat (または teleop.ps1) を実行します。'
    & docker @compose exec ros2 bash -c $cmd
}
catch {
    Write-Ng $_.Exception.Message
    exit 1
}
