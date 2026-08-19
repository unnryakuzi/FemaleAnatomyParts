@echo off
REM MaleAnatomy内の女性版 (3DAnatomyFemale.blend) を blender-mcp=9876 / blender-ai-mcp=8765 で起動
REM ※男性版(start-blender-male.cmd)とは同じポートなので同時起動不可。どちらか一方。
setlocal
set "BLENDER=C:\Program Files\Blender Foundation\Blender 5.0\blender.exe"
set "BLEND=%~dp03DAnatomyFemale.blend"
set "AUTOSTART=C:\Users\abesh\tools\blender-mcp\blendermcp_autostart.py"
set "BLENDERMCP_PORT=9876"
set "BLENDER_AI_MCP_RPC_PORT=8765"
REM TMPは既定（サフィックスなし）
if not exist "%BLENDER%" echo [ERROR] Blender not found: %BLENDER% & pause & exit /b 1
if not exist "%BLEND%"   echo [ERROR] .blend not found: %BLEND%   & pause & exit /b 1
echo Starting MaleAnatomy (Female)  blender-mcp=%BLENDERMCP_PORT%  blender-ai-mcp=%BLENDER_AI_MCP_RPC_PORT%
start "" "%BLENDER%" "%BLEND%" --python "%AUTOSTART%"
endlocal
