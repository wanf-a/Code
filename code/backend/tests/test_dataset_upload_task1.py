from __future__ import annotations

import unittest
import zipfile
from datetime import datetime
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from xml.sax.saxutils import escape

from fastapi import HTTPException, UploadFile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes import datasets as datasets_route
from app.api.routes.dataset_records import list_records
from app.api.routes.datasets import compare_dataset_with_upload, upload_dataset, upload_csv_dataset
from app.core.security import get_password_hash
from app.db.session import Base
from app.models.admin import AdminUser
from app.models.dataset_record import DatasetRecord
from app.schemas.dataset_record import DatasetRecordOut


EXPECTED_HEADERS = ["时间", "电价(元/kWh)", "负荷(kW)", "温度(℃)", "风速(m/s)", "云量(%)"]
EXPECTED_FIELD_NAMES = ["Time", "Price", "Load", "Temperature", "WindSpeed", "CloudCover"]
EXPECTED_TYPE_NAMES = ["datetime", "Double", "Double", "Double", "Double", "Double"]
VALID_ROWS = [
    ["2022/1/1 0:00", 372.8917, 40456, 15, 1, 0],
    ["2022/1/1 0:15", 393.635, 40143, 14.5, 1.5, 10],
]
INVALID_HEADERS = ["时间", "电价(元/kWh)", "温度(℃)", "负荷(kW)", "风速(m/s)", "云量(%)"]
CSV_BYTES = "时间,电价(元/kWh),负荷(kW),温度(℃),风速(m/s),云量(%)\n2022/1/1 0:00,372.8917,40456,15,1,0\n".encode("utf-8")
TEXT_BYTES = b"not an excel file"


def _column_name(index: int) -> str:
    name = ""
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def _cell_xml(cell_ref: str, value: object) -> str:
    if isinstance(value, str):
        return (
            f'<c r="{cell_ref}" t="inlineStr">'
            f"<is><t>{escape(value)}</t></is>"
            "</c>"
        )
    return f'<c r="{cell_ref}"><v>{value}</v></c>'


def build_xlsx_bytes(headers: list[str], rows: list[list[object]]) -> bytes:
    sheet_rows: list[str] = []
    for row_index, row_values in enumerate([headers, *rows], start=1):
        cells = [
            _cell_xml(f"{_column_name(column_index)}{row_index}", value)
            for column_index, value in enumerate(row_values, start=1)
        ]
        sheet_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')

    worksheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(sheet_rows)}</sheetData>'
        '</worksheet>'
    )
    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets>'
        '</workbook>'
    )
    workbook_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        '</Relationships>'
    )
    root_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        '</Relationships>'
    )
    content_types_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '</Types>'
    )

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types_xml)
        archive.writestr("_rels/.rels", root_rels_xml)
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml)
        archive.writestr("xl/worksheets/sheet1.xml", worksheet_xml)
    return buffer.getvalue()


VALID_XLSX = build_xlsx_bytes(EXPECTED_HEADERS, [EXPECTED_FIELD_NAMES, EXPECTED_TYPE_NAMES, *VALID_ROWS])
INVALID_HEADER_XLSX = build_xlsx_bytes(INVALID_HEADERS, [EXPECTED_FIELD_NAMES, EXPECTED_TYPE_NAMES, VALID_ROWS[0]])
THREE_LINE_TEMPLATE_ROWS = [
    EXPECTED_FIELD_NAMES,
    EXPECTED_TYPE_NAMES,
    *VALID_ROWS,
]
THREE_LINE_TEMPLATE_XLSX = build_xlsx_bytes(EXPECTED_HEADERS, THREE_LINE_TEMPLATE_ROWS)


class DatasetUploadTask1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()
        self.admin = AdminUser(
            username="task1_admin",
            password_hash=get_password_hash("task1-pass"),
            email="task1@example.com",
        )
        self.db.add(self.admin)
        self.db.commit()
        self.db.refresh(self.admin)

        self.temp_dir = TemporaryDirectory()
        self.original_save_upload_file = datasets_route.save_upload_file

        def fake_save_upload_file(file_bytes: bytes, original_name: str) -> tuple[str, str]:
            stored_path = Path(self.temp_dir.name) / original_name
            stored_path.write_bytes(file_bytes)
            return original_name, str(stored_path)

        datasets_route.save_upload_file = fake_save_upload_file

    def tearDown(self) -> None:
        datasets_route.save_upload_file = self.original_save_upload_file
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.temp_dir.cleanup()

    def _upload_file(self, filename: str, content: bytes) -> UploadFile:
        return UploadFile(filename=filename, file=BytesIO(content))

    def test_upload_accepts_three_line_template_xlsx(self) -> None:
        dataset = upload_dataset(
            file=self._upload_file("three-line.xlsx", THREE_LINE_TEMPLATE_XLSX),
            name="三行模板数据集",
            description="template",
            db=self.db,
            current_admin=self.admin,
        )

        records = (
            self.db.query(DatasetRecord)
            .filter(DatasetRecord.dataset_id == dataset.id)
            .order_by(DatasetRecord.record_time.asc())
            .all()
        )
        self.assertEqual(len(records), 2)
        self.assertEqual(str(records[0].record_time), "2022-01-01 00:00:00")
        self.assertEqual(float(records[0].price_kwh), 372.8917)
        self.assertEqual(float(records[1].price_kwh), 393.635)

    def test_upload_parses_excel_only_once(self) -> None:
        parse_events: list[str] = []

        def fake_validate_excel_structure(_file_content: bytes):
            parse_events.append("validate")
            return True, ""

        def fake_parse_excel_file(_file_content: bytes):
            parse_events.append("parse")
            return [
                {
                    "record_time": datetime(2022, 1, 1, 0, 0),
                    "price_kwh": 1.0,
                    "generation_kwh": 0.0,
                    "load_kw": 1.0,
                    "weather_type": "晴",
                    "temperature": 1.0,
                    "wind_speed": 1.0,
                    "cloud_cover": 1.0,
                    "is_holiday": False,
                }
            ]

        with patch("app.api.routes.datasets.validate_excel_structure", side_effect=fake_validate_excel_structure):
            with patch("app.api.routes.datasets.parse_excel_file", side_effect=fake_parse_excel_file):
                upload_dataset(
                    file=self._upload_file("single-parse.xlsx", VALID_XLSX),
                    name="只解析一次",
                    description=None,
                    db=self.db,
                    current_admin=self.admin,
                )

        self.assertEqual(len(parse_events), 1)
        self.assertEqual(parse_events, ["parse"])

    def test_upload_uses_bulk_insert_for_records(self) -> None:
        original_bulk_insert_mappings = self.db.bulk_insert_mappings
        captured_batches: list[tuple[object, list[dict[str, object]]]] = []

        def tracking_bulk_insert_mappings(mapper, mappings, *args, **kwargs):
            captured_batches.append((mapper, list(mappings)))
            return original_bulk_insert_mappings(mapper, mappings, *args, **kwargs)

        self.db.bulk_insert_mappings = tracking_bulk_insert_mappings  # type: ignore[method-assign]
        try:
            upload_dataset(
                file=self._upload_file("bulk-insert.xlsx", VALID_XLSX),
                name="批量插入",
                description=None,
                db=self.db,
                current_admin=self.admin,
            )
        finally:
            self.db.bulk_insert_mappings = original_bulk_insert_mappings  # type: ignore[method-assign]

        self.assertEqual(len(captured_batches), 1)
        mapper, mappings = captured_batches[0]
        self.assertIs(mapper, DatasetRecord)
        self.assertEqual(len(mappings), 2)
        self.assertTrue(all(item["dataset_id"] is not None for item in mappings))

    def test_upload_rejects_duplicate_dataset_name(self) -> None:
        upload_dataset(
            file=self._upload_file("valid.xlsx", VALID_XLSX),
            name="重复数据集",
            description=None,
            db=self.db,
            current_admin=self.admin,
        )

        with self.assertRaises(HTTPException) as ctx:
            upload_dataset(
                file=self._upload_file("valid.xlsx", VALID_XLSX),
                name="重复数据集",
                description=None,
                db=self.db,
                current_admin=self.admin,
            )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.detail, "数据集名称已存在")

    def test_upload_csv_route_matches_task1_rules(self) -> None:
        dataset = upload_csv_dataset(
            file=self._upload_file("valid.xlsx", VALID_XLSX),
            name="upload-csv路径",
            description="task1",
            db=self.db,
            current_admin=self.admin,
        )

        self.assertIsNotNone(dataset.id)

        with self.assertRaises(HTTPException) as ctx:
            upload_csv_dataset(
                file=self._upload_file("valid.xlsx", VALID_XLSX),
                name="upload-csv路径",
                description=None,
                db=self.db,
                current_admin=self.admin,
            )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.detail, "数据集名称已存在")

        for filename in ("legacy.csv", "legacy.xls", "legacy.txt"):
            with self.subTest(filename=filename):
                with self.assertRaises(HTTPException) as invalid_ctx:
                    upload_csv_dataset(
                        file=self._upload_file(filename, CSV_BYTES if filename.endswith(".csv") else TEXT_BYTES),
                        name=f"invalid-{filename}",
                        description=None,
                        db=self.db,
                        current_admin=self.admin,
                    )

                self.assertEqual(invalid_ctx.exception.status_code, 400)
                self.assertEqual(invalid_ctx.exception.detail, "只支持Excel文件(.xlsx)")

        with self.assertRaises(HTTPException) as wrong_header_ctx:
            upload_csv_dataset(
                file=self._upload_file("wrong-header.xlsx", INVALID_HEADER_XLSX),
                name="upload-csv错误表头",
                description=None,
                db=self.db,
                current_admin=self.admin,
            )

        self.assertEqual(wrong_header_ctx.exception.status_code, 400)
        self.assertIn("表头必须严格等于", wrong_header_ctx.exception.detail)

    def test_upload_rejects_non_xlsx_files(self) -> None:
        invalid_cases = [
            ("invalid.csv", CSV_BYTES),
            ("invalid.xls", TEXT_BYTES),
            ("invalid.txt", TEXT_BYTES),
        ]

        for filename, content in invalid_cases:
            with self.subTest(filename=filename):
                with self.assertRaises(HTTPException) as ctx:
                    upload_dataset(
                        file=self._upload_file(filename, content),
                        name=f"非xlsx-{filename}",
                        description=None,
                        db=self.db,
                        current_admin=self.admin,
                    )

                self.assertEqual(ctx.exception.status_code, 400)
                self.assertEqual(ctx.exception.detail, "只支持Excel文件(.xlsx)")

    def test_upload_rejects_xlsx_with_wrong_header_order(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            upload_dataset(
                file=self._upload_file("invalid.xlsx", INVALID_HEADER_XLSX),
                name="错误表头",
                description=None,
                db=self.db,
                current_admin=self.admin,
            )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("表头必须严格等于", ctx.exception.detail)


    def test_compare_upload_passes_for_identical_xlsx(self) -> None:
        dataset = upload_dataset(
            file=self._upload_file("same.xlsx", THREE_LINE_TEMPLATE_XLSX),
            name="compare-source",
            description=None,
            db=self.db,
            current_admin=self.admin,
        )

        verified = compare_dataset_with_upload(
            dataset_id=dataset.id,
            file=self._upload_file("same.xlsx", THREE_LINE_TEMPLATE_XLSX),
            db=self.db,
            _admin=self.admin,
        )

        self.assertEqual(verified.verify_status, "????")


if __name__ == "__main__":
    unittest.main()
