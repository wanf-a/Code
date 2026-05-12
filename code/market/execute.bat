@echo off
chcp 65001 >nul 2>&1
title 数据转换+计算程序批处理脚本
echo ==============================
echo 开始执行数据转换+计算任务
echo 执行时间：%date% %time%
echo ==============================
echo.
@REM echo 【第一步】开始执行数据转换程序...
@REM echo.

@REM :: **************************
@REM "main_Convert_V1.exe"

@REM :: 判断第一个程序是否执行成功（%errorlevel%=0为成功，非0为失败/异常）
@REM if %errorlevel% neq 0 (
@REM     echo.
@REM     echo ==============================
@REM     echo 错误：数据转换程序执行失败/异常！
@REM     echo 终止后续计算程序执行，请检查数据转换程序
@REM     echo ==============================
@REM     echo.
@REM     pause
@REM     exit /b 1
@REM )

@REM echo 【第一步完成】数据转换程序执行成功！
echo.
echo 【中间步骤】重新生成 xlsm 文件...
echo.

:: **************************
powershell -ExecutionPolicy Bypass -File "fix_all_xlsm.ps1"

echo 【中间步骤完成】xlsm 文件重新生成完成！
echo.
echo 【第二步】执行计算程序...
echo.

:: **************************
"main_da_market_V1.exe"

if %errorlevel% equ 0 (
    echo.
    echo 【第二步完成】计算程序执行成功！
) else (
    echo.
    echo 警告：计算程序执行可能存在异常！
)

echo.
echo ==============================
echo 全部任务执行结束！
echo 执行完成时间：%date% %time%
echo ==============================
echo.
:: 执行完不自动关闭窗口，方便查看结果（不需要可删除下面的pause）
pause
exit /b 0