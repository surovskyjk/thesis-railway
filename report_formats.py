# Format-agnostic rendering of a plain list of report lines into TXT, Markdown, HTML, LaTeX, PDF and CSV
import csv
import html
import re

from PySide6.QtGui import QPdfWriter, QPageSize, QPageLayout, QTextDocument

REPORT_FORMATS = ("txt", "csv", "md", "pdf", "tex")

# Characters LaTeX treats specially, matched against the ORIGINAL text in one pass so a replacement's
# own braces (e.g. \textbackslash{}) never get caught and re-escaped by a later substitution
TEX_ESCAPE_MAP = {
    "\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$",
    "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}",
    "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
}
TEX_ESCAPE_PATTERN = re.compile("|".join(re.escape(char) for char in TEX_ESCAPE_MAP))


def linesToPlainText(reportLines):
    return "\n".join(reportLines)


# Section headers wrapped in === or --- become Markdown headings, everything else stays a code line
def linesToMarkdown(reportLines, titleText=""):
    mdLines = []
    if titleText:
        mdLines.append(f"# {titleText}")
        mdLines.append("")
    for line in reportLines:
        stripped = line.strip()
        if stripped.startswith("===") and stripped.endswith("==="):
            mdLines.append(f"## {stripped.strip('=').strip()}")
        elif stripped.startswith("---") and stripped.endswith("---"):
            mdLines.append(f"### {stripped.strip('-').strip()}")
        elif stripped == "":
            mdLines.append("")
        else:
            mdLines.append(f"    {line}")
    return "\n".join(mdLines)


def linesToHtml(reportLines, titleText=""):
    escapedBody = "\n".join(html.escape(line) for line in reportLines)
    safeTitle = html.escape(titleText)
    return (f"<html><head><meta charset='utf-8'><title>{safeTitle}</title></head>"
            f"<body><h1>{safeTitle}</h1>"
            f"<pre style='font-family:Consolas,monospace;font-size:10pt'>{escapedBody}</pre>"
            f"</body></html>")


def escapeTex(text):
    return TEX_ESCAPE_PATTERN.sub(lambda match: TEX_ESCAPE_MAP[match.group()], text)


def linesToTex(reportLines, titleText=""):
    texLines = [
        r"\documentclass{article}",
        r"\usepackage[utf8]{inputenc}",
        r"\usepackage[T1]{fontenc}",
        r"\usepackage{geometry}",
        r"\geometry{a4paper, landscape, margin=2cm}",
        r"\usepackage{alltt}",
        r"\begin{document}",
    ]
    if titleText:
        texLines.append(r"\section*{" + escapeTex(titleText) + "}")
    texLines.append(r"\begin{alltt}")
    texLines.extend(escapeTex(line) for line in reportLines)
    texLines.append(r"\end{alltt}")
    texLines.append(r"\end{document}")
    return "\n".join(texLines)


# Render HTML to a real, selectable-text PDF using PySide6's built in writer, no external dependency
def htmlToPdf(htmlText, pdfPath, isLandscape=True):
    document = QTextDocument()
    document.setHtml(htmlText)
    writer = QPdfWriter(pdfPath)
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    writer.setPageOrientation(QPageLayout.Orientation.Landscape if isLandscape else QPageLayout.Orientation.Portrait)
    document.print_(writer)


def rowsToCsv(filePath, headerRow, dataRows):
    with open(filePath, "w", newline="", encoding="utf-8") as fileHandle:
        writer = csv.writer(fileHandle)
        if headerRow:
            writer.writerow(headerRow)
        writer.writerows(dataRows)


# Render reportLines to filePath in whichever format its extension implies
def writeReportFile(reportLines, filePath, titleText=""):
    lowerPath = filePath.lower()
    if lowerPath.endswith(".pdf"):
        htmlToPdf(linesToHtml(reportLines, titleText), filePath)
    elif lowerPath.endswith(".md"):
        with open(filePath, "w", encoding="utf-8") as fileHandle:
            fileHandle.write(linesToMarkdown(reportLines, titleText))
    elif lowerPath.endswith(".tex"):
        with open(filePath, "w", encoding="utf-8") as fileHandle:
            fileHandle.write(linesToTex(reportLines, titleText))
    else:
        with open(filePath, "w", encoding="utf-8") as fileHandle:
            fileHandle.write(linesToPlainText(reportLines))
