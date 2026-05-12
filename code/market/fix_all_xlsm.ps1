param(
    [string]$ConfigPath = ""
)

$ErrorActionPreference = "Stop"

# 如果没有提供配置文件路径，使用当前目录下的 config.ini
if ([string]::IsNullOrEmpty($ConfigPath)) {
    $scriptPath = $PSScriptRoot
    if ([string]::IsNullOrEmpty($scriptPath)) {
        $scriptPath = Get-Location
    }
    $ConfigPath = Join-Path $scriptPath "config.ini"
}

# 检查配置文件是否存在
if (-not (Test-Path $ConfigPath)) {
    Write-Host "Error: Config file not found - $ConfigPath" -ForegroundColor Red
    exit 1
}

# 读取配置文件
$configContent = Get-Content $ConfigPath -Raw
$caseNameMatch = [regex]::Match($configContent, "case_name\s*=\s*'([^']+)'")

if (-not $caseNameMatch.Success) {
    Write-Host "Error: Cannot find case_name in config file" -ForegroundColor Red
    exit 1
}

$caseName = $caseNameMatch.Groups[1].Value.Trim()

# 构建 Case/{case_name}/Input 路径
$casePath = Join-Path $PSScriptRoot "Case"
$inputPath = Join-Path $casePath $caseName
$inputPath = Join-Path $inputPath "Input"

# 检查 Input 文件夹是否存在
if (-not (Test-Path $inputPath)) {
    Write-Host "Error: Input folder not found - $inputPath" -ForegroundColor Red
    exit 1
}

# 查找 Input 文件夹中的所有 xlsm 文件（递归）
$xlsmFiles = Get-ChildItem -Path $inputPath -Filter "*.xlsm" -Recurse -File

if ($xlsmFiles.Count -eq 0) {
    exit 0
}

Write-Host "【中间步骤】重新生成 xlsm 文件..."

$successCount = 0
$failCount = 0
$failedFiles = @()

foreach ($file in $xlsmFiles) {
    $tempXlsx = Join-Path $file.DirectoryName "$($file.BaseName)_temp.xlsx"
    $excel = $null
    $workbook = $null
    
    try {
        # Step 1: Read file with openpyxl
        $pythonCmd = "from openpyxl import load_workbook; wb = load_workbook(r'$($file.FullName)', keep_vba=False); wb.save(r'$tempXlsx')"
        $result = python -c $pythonCmd 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "Python error: $result"
        }
        
        # Step 2: Start Excel
        $excel = New-Object -ComObject Excel.Application
        $excel.DisplayAlerts = $false
        $excel.Visible = $false
        
        # Step 3: Open temporary xlsx
        $workbook = $excel.Workbooks.Open($tempXlsx)
        
        # Step 4: Save as xlsm
        $workbook.SaveAs($file.FullName, 52)
        
        # Step 5: Verify
        $workbook.Close($false)
        $workbook = $excel.Workbooks.Open($file.FullName)
        $workbook.Close($false)
        
        # Step 6: Cleanup
        Remove-Item $tempXlsx -Force -ErrorAction SilentlyContinue
        
        $successCount++
    }
    catch {
        $failCount++
        $failedFiles += $file.FullName
    }
    finally {
        if ($workbook -ne $null) {
            try { $workbook.Close($false) } catch {}
            $workbook = $null
        }
        if ($excel -ne $null) {
            try {
                $excel.Quit()
                [System.Runtime.Interopservices.Marshal]::ReleaseComObject($excel) | Out-Null
            } catch {}
            $excel = $null
        }
        
        # 强制垃圾回收
        [GC]::Collect()
        [GC]::WaitForPendingFinalizers()
        [GC]::Collect()
        
        if (Test-Path $tempXlsx) {
            try { Remove-Item $tempXlsx -Force } catch {}
        }
    }
}

Write-Host ""
Write-Host "=========================================="
Write-Host "Summary"
Write-Host "=========================================="
Write-Host "Total files: $($xlsmFiles.Count)"
Write-Host "Success: $successCount"
Write-Host "Failed: $failCount"
Write-Host ""

if ($failCount -gt 0) {
    Write-Host "Failed files:"
    foreach ($file in $failedFiles) {
        Write-Host "  $file"
    }
}