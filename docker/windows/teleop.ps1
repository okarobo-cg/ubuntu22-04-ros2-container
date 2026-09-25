<#
.SYNOPSIS
  キーボードでロボットを操縦する (teleop_twist_keyboard)。
  シミュレーションを start.bat で起動したあと、別の PowerShell / コマンドプロンプトで実行する。
.DESCRIPTION
  i: 前進  ,: 後退  j / l: 左右旋回  k: 停止  q / z: 速度アップ / ダウン  Ctrl+C: 終了
  ※ このウィンドウを選択 (アクティブに) した状態でキーを押すこと
.EXAMPLE
  .\teleop.ps1
#>
. (Join-Path $PSScriptRoot 'common.ps1')

if (-not (Test-DockerRunning)) { exit 1 }
if (-not (Test-ContainerRunning)) {
    Write-Ng "コンテナ $Script:Container が起動していません。先に start.bat (start.ps1) を実行してください。"
    exit 1
}
Write-Step 'キーボード操縦を開始 (i: 前進 / ,: 後退 / j,l: 旋回 / k: 停止 / Ctrl+C: 終了)'
& docker exec -it $Script:Container bash -c 'source /opt/ros/humble/setup.bash && ros2 run teleop_twist_keyboard teleop_twist_keyboard'
