' 机械臂视觉抓取系统 - 静默启动（不显示命令行窗口）
' 双击此文件即可在后台启动服务器

Set objShell = CreateObject("WScript.Shell")
strPath = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)

' 激活虚拟环境并启动服务器
objShell.Run "cmd /c cd /d """ & strPath & """ && call .venv\Scripts\activate.bat && start http://localhost:5000 && python web_server.py", 0, False

' 提示
MsgBox "服务器正在后台启动..." & vbCrLf & vbCrLf & _
       "请稍等几秒后在浏览器中打开：" & vbCrLf & _
       "http://localhost:5000" & vbCrLf & vbCrLf & _
       "要停止服务器，请在任务管理器中结束 python.exe", _
       vbInformation, "机械臂视觉抓取系统"
