"""Compatibility probe for openpyxl.

openpyxl is the Excel engine behind pandas' xlsx read/write. The
meaningful check is an in-memory xlsx round-trip (write with Workbook,
save to BytesIO, load back with load_workbook) and cell-value
assertions: openpyxl is pure Python, so a bare import would catch
nothing and only breaks at the API boundary. No filesystem or network
access.
"""

import io

from openpyxl import Workbook, load_workbook


def main() -> None:
    buf = io.BytesIO()
    wb = Workbook()
    ws = wb.active
    ws.append(["name", "value"])
    ws.append(["alpha", 10])
    ws.append(["beta", 25])
    wb.save(buf)
    buf.seek(0)

    loaded = load_workbook(buf)
    sheet = loaded.active
    assert sheet["A1"].value == "name", f"A1 = {sheet['A1'].value!r}"
    assert sheet["A2"].value == "alpha", f"A2 = {sheet['A2'].value!r}"
    assert sheet["B2"].value == 10, f"B2 = {sheet['B2'].value!r}"
    assert sheet["B3"].value == 25, f"B3 = {sheet['B3'].value!r}"
    print("openpyxl: OK (xlsx round-trip)")


if __name__ == "__main__":
    main()
