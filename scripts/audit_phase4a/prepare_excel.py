"""Create synthetic XLSX fixtures without saving source identities or grades.

The input is read-only. XML editing preserves layout, headers, formulas and caches;
all pupil identifiers, input marks, metadata and nonacademic strings are replaced.
Only the privately inspected one-sheet institutional layout is supported.
"""

import argparse
import json
import re
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from openpyxl import load_workbook

NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"


def Q(name):
    return f"{{{NS}}}{name}"


def key(text):
    return re.sub(r"\s+", " ", text.strip()).upper()


HEADERS = {
    "REGISTRO DE NOTAS",
    "CODIGO",
    "NOMBRE Y APELLIDOS",
    "1 MES",
    "2 MES",
    "PROMEDIO LITERAL",
    "ACTITUD ANTE EL AREA",
    "CUADERNO",
    "MODULO",
    "EXPOSICION-TRABAJOS",
    "EVALUACION",
    "PROMEDIO MENSUAL",
    "PROMEDIO BIMESTRAL",
    "BIMESTRE",
    "PROMEDIO BIMESTRE",
    "P.S",
    "P.F",
}


def inline(cell, value):
    for child in list(cell):
        cell.remove(child)
    cell.set("t", "inlineStr")
    text = ET.SubElement(ET.SubElement(cell, Q("is")), Q("t"))
    text.text = value


def prepare(source, output):
    workbook = load_workbook(source, data_only=False)
    assert len(workbook.worksheets) == 1, "Privately review any different workbook first"
    sheet = workbook.active
    assert sheet.title == "Hoja1", "Unexpected worksheet name"
    assert (sheet.max_row, sheet.max_column) == (22, 16), "Unexpected layout"
    formulas = {c.coordinate: c.value for row in sheet for c in row if c.data_type == "f"}
    assert len(formulas) == 64 and not workbook._external_links
    assert all("!" not in value and "[" not in value for value in formulas.values())
    merged = sorted(str(item) for item in sheet.merged_cells.ranges)
    inputs = [f"{column}{row}" for row in range(7, 23) for column in "CDEFGIJKLM"]
    output.mkdir(parents=True, exist_ok=True)
    for filled in (False, True):
        destination = output / (
            "institucional-sintetico.xlsx" if filled else "institucional-vacios.xlsx"
        )
        with ZipFile(source) as original, ZipFile(destination, "w") as synthetic:
            for info in original.infolist():
                data = original.read(info.filename)
                if info.filename == "xl/sharedStrings.xml":
                    root = ET.fromstring(data)
                    for item in root.findall(Q("si")):
                        text = "".join(t.text or "" for t in item.iter(Q("t")))
                        replacement = text if key(text) in HEADERS else "SINTETICO"
                        for child in list(item):
                            item.remove(child)
                        ET.SubElement(item, Q("t")).text = replacement
                    data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
                elif info.filename == "xl/worksheets/sheet1.xml":
                    root = ET.fromstring(data)
                    cells = {cell.get("r"): cell for cell in root.iter(Q("c"))}
                    for cell in cells.values():
                        if cell.get("t") == "inlineStr":
                            text = "".join(t.text or "" for t in cell.iter(Q("t")))
                            if key(text) not in HEADERS:
                                inline(cell, "SINTETICO")
                    for row in range(7, 23):
                        inline(cells[f"A{row}"], f"1SA{row - 6:03d}")
                        inline(cells[f"B{row}"], f"SINTETICO, ALUMNO {row - 6:03d}")
                    for position in inputs:
                        cell = cells[position]
                        for child in list(cell):
                            cell.remove(child)
                        cell.attrib.pop("t", None)
                        if filled and position.endswith("7"):
                            value = dict(
                                zip(
                                    "CDEFGIJKLM",
                                    [10, 12, 14, 16, 18, 20, 20, 20, 20, 20],
                                    strict=False,
                                )
                            )[position[0]]
                            ET.SubElement(cell, Q("v")).text = str(value)
                    for position, cell in cells.items():
                        if position in formulas:
                            cached = cell.find(Q("v"))
                            if cached is None:
                                cached = ET.SubElement(cell, Q("v"))
                            row = int(re.search(r"\d+", position).group())
                            if position[0] == "P":
                                cell.set("t", "str")
                                cached.text = "AD" if filled and row == 7 else "C"
                            else:
                                cell.attrib.pop("t", None)
                                cached.text = (
                                    str({"H": 14, "N": 20, "O": 17}[position[0]])
                                    if filled and row == 7
                                    else "0"
                                )
                    # No annotations or data validations carrying source text.
                    for tag in ("legacyDrawing", "drawing", "extLst", "dataValidations"):
                        for element in root.findall(Q(tag)):
                            root.remove(element)
                    data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
                elif info.filename == "xl/worksheets/_rels/sheet1.xml.rels":
                    root = ET.fromstring(data)
                    for relation in list(root):
                        if any(
                            part in relation.get("Type", "").lower()
                            for part in (
                                "drawing",
                                "image",
                                "comment",
                                "printersettings",
                                "hyperlink",
                            )
                        ):
                            root.remove(relation)
                    data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
                elif info.filename == "[Content_Types].xml":
                    root = ET.fromstring(data)
                    for part in list(root):
                        if any(
                            token in part.get("PartName", "").lower()
                            for token in (
                                "comment",
                                "drawing",
                                "media/",
                                "printersettings",
                                "customxml",
                                "external",
                                "vba",
                            )
                        ):
                            root.remove(part)
                    data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
                elif info.filename == "xl/workbook.xml":
                    root = ET.fromstring(data)
                    defined = root.find(Q("definedNames"))
                    if defined is not None:
                        root.remove(defined)
                    data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
                elif info.filename == "docProps/core.xml":
                    root = ET.fromstring(data)
                    for child in root:
                        child.text = ""
                    data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
                elif info.filename == "docProps/app.xml":
                    root = ET.fromstring(data)
                    for element in root.iter():
                        if element.tag.endswith("}lpstr") or element.tag.endswith("}Company"):
                            element.text = "SINTETICO"
                    data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
                elif any(
                    part in info.filename.lower()
                    for part in (
                        "comment",
                        "drawing",
                        "media/",
                        "printersettings",
                        "customxml",
                        "external",
                        "vba",
                    )
                ):
                    # Input has no external links/macros; omit any private annotations.
                    continue
                synthetic.writestr(info, data)
        check = load_workbook(destination, data_only=False)
        actual = {c.coordinate: c.value for row in check.active for c in row if c.data_type == "f"}
        assert actual == formulas
        assert sorted(str(item) for item in check.active.merged_cells.ranges) == merged
        assert all(
            check.active.cell(r, c).value == sheet.cell(r, c).value
            for r in (5, 6)
            for c in range(1, 17)
        )
        assert all(
            check.active[f"B{r}"].value == f"SINTETICO, ALUMNO {r - 6:03d}" for r in range(7, 23)
        )
    manifest = {
        "layout": [22, 16],
        "sheets": 1,
        "synthetic_students": 16,
        "formula_count": len(formulas),
        "merged_ranges": merged,
        "formulas": {p: formulas[p] for p in ("H7", "N7", "O7", "P7")},
        "source_identities_and_input_marks_saved": False,
        "formula_and_merge_equality_verified": True,
    }
    (output / "excel-structure.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    prepare(args.source, args.output)
