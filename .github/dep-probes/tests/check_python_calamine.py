"""Compatibility probe for python-calamine.

calamine is the image's Excel read engine (pandas read_excel with
engine="calamine"). The probe builds a minimal xlsx in memory with the
stdlib only (zipfile + inline XML), then reads it back through both
APIs: python_calamine.load_workbook directly and pandas.read_excel with
engine="calamine". No writer dependency (openpyxl is intentionally not
used), no filesystem, no network.
"""

import io
import zipfile

import pandas as pd
from python_calamine import load_workbook


def make_xlsx() -> io.BytesIO:
    """Build a minimal xlsx with stdlib zipfile: one sheet, header row
    name/value and two data rows, using inline strings (no shared
    strings part needed).
    """
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '</Types>'
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        '</Relationships>'
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets>'
        '</workbook>'
    )
    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        '</Relationships>'
    )
    sheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetData>'
        '<row r="1">'
        '<c r="A1" t="inlineStr"><is><t>name</t></is></c>'
        '<c r="B1" t="inlineStr"><is><t>value</t></is></c>'
        '</row>'
        '<row r="2">'
        '<c r="A2" t="inlineStr"><is><t>alpha</t></is></c>'
        '<c r="B2"><v>10</v></c>'
        '</row>'
        '<row r="3">'
        '<c r="A3" t="inlineStr"><is><t>beta</t></is></c>'
        '<c r="B3"><v>25</v></c>'
        '</row>'
        '</sheetData>'
        '</worksheet>'
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("xl/workbook.xml", workbook)
        zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        zf.writestr("xl/worksheets/sheet1.xml", sheet)
    buf.seek(0)
    return buf


def main() -> None:
    # Direct calamine API.
    wb = load_workbook(make_xlsx())
    assert wb.sheet_names == ["Sheet1"], f"unexpected sheets: {wb.sheet_names}"
    sheet = wb.get_sheet_by_index(0)
    rows = list(sheet.to_python())
    assert rows[0] == ["name", "value"], f"header row: {rows[0]}"
    assert rows[1] == ["alpha", 10], f"row 2: {rows[1]}"
    assert rows[2] == ["beta", 25], f"row 3: {rows[2]}"
    print("python-calamine: OK (direct API)")

    # pandas integration path.
    df = pd.read_excel(make_xlsx(), engine="calamine")
    assert list(df.columns) == ["name", "value"], f"columns: {list(df.columns)}"
    assert df["value"].tolist() == [10, 25], f"values: {df['value'].tolist()}"
    print("python-calamine: OK (pandas read_excel engine=calamine)")


if __name__ == "__main__":
    main()
