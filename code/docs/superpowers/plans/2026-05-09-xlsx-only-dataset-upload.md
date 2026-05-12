# XLSX-Only Dataset Upload Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Switch the dataset management upload flow from csv-only to xlsx-only while keeping the same strict six-column template and existing view/delete/download behavior.

**Architecture:** Reuse the existing dataset upload/view pipeline and only swap the file-format boundary from strict CSV parsing to strict XLSX parsing. The backend upload route will accept only `.xlsx`, validate only the first worksheet against the exact six-column template, parse rows into the existing `DatasetRecord` model, and the frontend upload UI will only permit `.xlsx` and show explicit errors for every other format.

**Tech Stack:** FastAPI, SQLAlchemy, openpyxl, Vue 3, TypeScript, Vite, Python unittest

---

## File Structure

- Modify: `backend/app/services/excel_service.py`
  - Add strict xlsx template constants and parsing/validation for first-sheet-only six-column import.
- Modify: `backend/app/api/routes/datasets.py`
  - Change upload route from csv-only to xlsx-only and wire strict Excel validation/parsing.
- Modify: `backend/tests/test_dataset_upload_task1.py`
  - Replace csv-based upload tests with xlsx-based tests and assert non-xlsx rejection.
- Modify: `frontend/src/views/DatasetView.vue`
  - Change file input accept list, upload pre-checks, UI copy, and download default suffix to xlsx.
- Optional read-only reference: `E:/桌面/咸鱼/code/广东电价数据.xlsx`
  - Use as the real-world template example while implementing and manually verifying.

### Task 1: Add failing backend XLSX upload tests

**Files:**
- Modify: `backend/tests/test_dataset_upload_task1.py`
- Test: `backend/tests/test_dataset_upload_task1.py`

- [ ] **Step 1: Write the failing tests**

Replace the file fixtures and assertions so the test suite expects `.xlsx` uploads to succeed and `.csv` / `.xls` uploads to fail.

```python
from openpyxl import Workbook


def make_valid_xlsx_bytes() -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["时间", "电价(元/kWh)", "负荷(kW)", "温度(℃)", "风速(m/s)", "云量(%)"])
    sheet.append(["2022/1/1 0:00", 372.8917, 40456, 15, 1, 0])
    sheet.append(["2022/1/1 0:15", 393.635, 40143, 14.5, 1.5, 10])

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def make_wrong_header_xlsx_bytes() -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["时间", "电价(元/kWh)", "温度(℃)", "负荷(kW)", "风速(m/s)", "云量(%)"])
    sheet.append(["2022/1/1 0:00", 372.8917, 15, 40456, 1, 0])

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
```

Update the tests so they call `upload_dataset(... filename="valid.xlsx" ...)` and assert:
- valid xlsx upload succeeds and persists temperature / wind_speed / cloud_cover
- duplicate dataset name still returns `数据集名称已存在`
- non-xlsx upload returns `只支持Excel文件(.xlsx)`
- wrong-header xlsx returns an error containing `表头必须严格等于`
- the alias route `/upload-csv` path behavior (currently the `upload_csv_dataset` function) still follows the same xlsx-only rules

- [ ] **Step 2: Run the tests to verify they fail**

Run:
```bash
PYTHONPATH="E:/桌面/咸鱼/code/code/backend" "E:/桌面/咸鱼/code/code/backend/.venv/Scripts/python.exe" -m unittest discover -s "E:/桌面/咸鱼/code/code/backend/tests" -p "test_dataset_upload_task1.py"
```

Expected:
- FAIL because the current backend still rejects `.xlsx`
- FAIL because the current parser is wired to csv-only logic

- [ ] **Step 3: Write the minimal backend test-support code only if needed**

If the test helper imports are missing, add only the imports needed by the new tests:

```python
from openpyxl import Workbook
```

No production changes yet.

- [ ] **Step 4: Re-run the tests and confirm they still fail for the expected reason**

Run the same unittest command again.

Expected:
- FAIL for xlsx acceptance/validation behavior, not for syntax/import errors

### Task 2: Implement strict XLSX parsing and validation

**Files:**
- Modify: `backend/app/services/excel_service.py`
- Test: `backend/tests/test_dataset_upload_task1.py`

- [ ] **Step 1: Write the strict XLSX parser/validator**

Replace the loose Excel parsing behavior with first-sheet-only strict template parsing that mirrors the current CSV strictness.

Use code shaped like this in `backend/app/services/excel_service.py`:

```python
STANDARD_XLSX_HEADERS = [
    "时间",
    "电价(元/kWh)",
    "负荷(kW)",
    "温度(℃)",
    "风速(m/s)",
    "云量(%)",
]

TIME_FORMATS = [
    "%Y/%m/%d %H:%M:%S",
    "%Y/%m/%d %H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%Y/%m/%d",
]


def _parse_excel_record_time(value: object, row_number: int) -> datetime:
    if isinstance(value, datetime):
        return value
    text = str(value).strip() if value is not None else ""
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"第{row_number}行时间格式错误")


def _parse_excel_float(value: object, column_name: str, row_number: int) -> float:
    if value is None or str(value).strip() == "":
        raise ValueError(f"第{row_number}行“{column_name}”不能为空")
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"第{row_number}行“{column_name}”不是合法数字") from exc


def parse_excel_file(file_content: bytes) -> List[Dict[str, Any]]:
    workbook = openpyxl.load_workbook(BytesIO(file_content), data_only=True)
    sheet = workbook.worksheets[0]
    rows = list(sheet.iter_rows(values_only=True))
    if len(rows) < 2:
        raise ValueError("Excel文件至少需要包含表头和一行数据")

    headers = [str(cell).strip() if cell is not None else "" for cell in rows[0]]
    if headers != STANDARD_XLSX_HEADERS:
        raise ValueError(f"表头必须严格等于: {', '.join(STANDARD_XLSX_HEADERS)}")

    records = []
    for row_number, row in enumerate(rows[1:], start=2):
        if not any(cell is not None and str(cell).strip() != "" for cell in row):
            continue
        if len(row) != len(STANDARD_XLSX_HEADERS):
            raise ValueError(f"第{row_number}行列数不正确")

        record_time = _parse_excel_record_time(row[0], row_number)
        price_kwh = _parse_excel_float(row[1], STANDARD_XLSX_HEADERS[1], row_number)
        load_kw = _parse_excel_float(row[2], STANDARD_XLSX_HEADERS[2], row_number)
        temperature = _parse_excel_float(row[3], STANDARD_XLSX_HEADERS[3], row_number)
        wind_speed = _parse_excel_float(row[4], STANDARD_XLSX_HEADERS[4], row_number)
        cloud_cover = _parse_excel_float(row[5], STANDARD_XLSX_HEADERS[5], row_number)

        weather_type = "晴" if cloud_cover <= 30 else "阴" if cloud_cover >= 70 else "多云"
        records.append({
            "record_time": record_time,
            "price_kwh": price_kwh,
            "generation_kwh": 0.0,
            "load_kw": load_kw,
            "temperature": temperature,
            "wind_speed": wind_speed,
            "cloud_cover": cloud_cover,
            "weather_type": weather_type,
            "is_holiday": False,
        })

    if not records:
        raise ValueError("Excel文件至少需要包含一行有效数据")
    return records


def validate_excel_structure(file_content: bytes) -> tuple[bool, str]:
    try:
        parse_excel_file(file_content)
        return True, ""
    except ValueError as exc:
        return False, str(exc)
```

- [ ] **Step 2: Run the tests to verify progress**

Run:
```bash
PYTHONPATH="E:/桌面/咸鱼/code/code/backend" "E:/桌面/咸鱼/code/code/backend/.venv/Scripts/python.exe" -m unittest discover -s "E:/桌面/咸鱼/code/code/backend/tests" -p "test_dataset_upload_task1.py"
```

Expected:
- Some tests may still fail because the route still enforces csv-only
- Parsing-related failures should move closer to green

- [ ] **Step 3: Refactor only if duplicate strict-template logic becomes obvious**

Keep helpers private to `excel_service.py`. Do not add a new abstraction shared with CSV unless a later task requires both. The current requirement is xlsx-only.

### Task 3: Switch dataset upload route to xlsx-only

**Files:**
- Modify: `backend/app/api/routes/datasets.py`
- Test: `backend/tests/test_dataset_upload_task1.py`

- [ ] **Step 1: Change `/datasets/upload` to accept only `.xlsx`**

In `backend/app/api/routes/datasets.py`, replace the current csv-only branch with xlsx-only validation and parsing.

Use code shaped like this:

```python
from app.services.excel_service import parse_excel_file, validate_excel_structure


@router.post("/upload", response_model=DatasetOut)
def upload_dataset(...):
    filename = file.filename or ""
    if not filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="只支持Excel文件(.xlsx)")

    content = file.file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件为空")

    normalized_name = _validate_dataset_name(name)
    existing_dataset = db.query(Dataset).filter(Dataset.name == normalized_name).first()
    if existing_dataset:
        raise HTTPException(status_code=400, detail="数据集名称已存在")

    is_valid, error_msg = validate_excel_structure(content)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    try:
        new_records = parse_excel_file(content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
```

Keep the rest of the record persistence and file-save logic unchanged.

- [ ] **Step 2: Keep the alias route aligned**

Ensure the compatibility function `upload_csv_dataset` still delegates to `upload_dataset` so there is only one active upload behavior:

```python
@router.post("/upload-csv", response_model=DatasetOut)
def upload_csv_dataset(...):
    return upload_dataset(
        file=file,
        name=name,
        description=description,
        db=db,
        current_admin=current_admin,
    )
```

Do not reintroduce overwrite behavior or csv-specific parsing.

- [ ] **Step 3: Run the backend tests to verify they pass**

Run:
```bash
PYTHONPATH="E:/桌面/咸鱼/code/code/backend" "E:/桌面/咸鱼/code/code/backend/.venv/Scripts/python.exe" -m unittest discover -s "E:/桌面/咸鱼/code/code/backend/tests" -p "test_dataset_upload_task1.py"
```

Expected:
- PASS
- Valid `.xlsx` upload succeeds
- `.csv` / `.xls` are rejected with `只支持Excel文件(.xlsx)`

### Task 4: Update frontend upload UI to xlsx-only

**Files:**
- Modify: `frontend/src/views/DatasetView.vue`

- [ ] **Step 1: Write the failing manual verification expectation**

Before editing, define the expected UI behaviors:
- file input only advertises `.xlsx`
- selecting `.csv` and clicking upload shows `只支持Excel文件(.xlsx)` or the pre-check equivalent
- empty form message mentions Excel instead of CSV
- downloaded default filename ends with `.xlsx`

No automated frontend test framework exists here, so the build plus manual behavior check is the verification path.

- [ ] **Step 2: Change the upload UI and client-side checks**

In `frontend/src/views/DatasetView.vue`, update these pieces:

```vue
<input type="file" accept=".xlsx" @change="onFileChange" />
```

```ts
if (!uploadForm.name || !uploadForm.file) {
  alert("请填写数据集名称并选择Excel文件");
  return;
}
if (!uploadForm.file.name.toLowerCase().endsWith(".xlsx")) {
  alert("只支持Excel文件(.xlsx)");
  return;
}
```

Also change the default download suffix:

```ts
a.download = `${ds.name}.xlsx`;
```

Do not change the dataset records view, pagination, delete flow, or backend error passthrough.

- [ ] **Step 3: Build the frontend to verify it compiles**

Run:
```bash
cd "E:/桌面/咸鱼/code/code/frontend" && npm run build
```

Expected:
- Vite build completes successfully
- No TypeScript/Vue compile errors

### Task 5: End-to-end verification and migration note

**Files:**
- Modify: none (verification only)
- Test: `backend/tests/test_dataset_upload_task1.py`

- [ ] **Step 1: Run backend verification fresh**

Run:
```bash
PYTHONPATH="E:/桌面/咸鱼/code/code/backend" "E:/桌面/咸鱼/code/code/backend/.venv/Scripts/python.exe" -m unittest discover -s "E:/桌面/咸鱼/code/code/backend/tests" -p "test_dataset_upload_task1.py"
```

Expected:
- `Ran ... tests`
- `OK`

- [ ] **Step 2: Run frontend verification fresh**

Run:
```bash
cd "E:/桌面/咸鱼/code/code/frontend" && npm run build
```

Expected:
- `✓ built`

- [ ] **Step 3: Manual verification with the real file**

Use the real file:
- `E:/桌面/咸鱼/code/广东电价数据.xlsx`

Manual checks:
1. Open the dataset upload modal.
2. Confirm the file chooser only accepts `.xlsx`.
3. Upload `广东电价数据.xlsx` with a new dataset name.
4. Open “查看” and confirm the six columns display real values.
5. Try uploading a `.csv` or `.xls` file and confirm the page shows `只支持Excel文件(.xlsx)`.
6. Download the dataset and confirm the saved filename defaults to `.xlsx`.

- [ ] **Step 4: Note database migration requirement**

If the environment uses an existing database, apply migrations before manual verification:

```bash
cd "E:/桌面/咸鱼/code/code/backend" && .venv/Scripts/alembic.exe upgrade head
```

Expected:
- Alembic applies the existing precision migration and any pending revisions successfully.

---

## Self-Review

- Spec coverage: The plan covers xlsx-only frontend input, backend xlsx-only enforcement, strict first-sheet six-column template validation, invalid-format rejection, and unchanged view/delete/download behavior with only the download suffix updated.
- Placeholder scan: No TODO/TBD placeholders remain; each task has concrete commands and code snippets.
- Type consistency: The plan consistently uses `parse_excel_file`, `validate_excel_structure`, `upload_dataset`, and the existing `DatasetRecord` persistence path without introducing mismatched names.
