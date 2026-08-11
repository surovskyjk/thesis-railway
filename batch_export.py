# Assembles a batch run's reports, protocols and comparison data into one structured ZIP archive
import csv
import io
import json
import re
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

import numpy as np

import batch_metrics
import report_formats


# Turn an arbitrary label into a filesystem-safe slug, ASCII folded and capped for Windows path limits
def slugifyLabel(text, maxLength=60):
    normalized = text.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^A-Za-z0-9]+", "_", normalized).strip("_")
    return (slug or "variant")[:maxLength]


class BatchArchiveExporter:
    def __init__(self, resultStore, batchConfigData, lan, mergedLandXml=None, junctions=None):
        self.resultStore = resultStore
        self.batchConfigData = batchConfigData or {}
        self.lan = lan or {}
        self.mergedLandXml = mergedLandXml or {}
        self.junctions = junctions or []

    def buildVariantFolderName(self, result):
        label = result.get("spec", {}).get("label", result["variantId"])
        return f"{result['variantId']}_{slugifyLabel(label)}"

    # Assemble the whole archive, calling progressCallback(index, total) after each variant folder
    def exportArchive(self, zipPath, exportFormats, plotImagePaths=None, progressCallback=None):
        results = self.resultStore.results()
        plotImagePaths = plotImagePaths or []

        with zipfile.ZipFile(zipPath, "w", zipfile.ZIP_DEFLATED) as archive:
            self.writeReadme(archive, results)
            self.writeBatchConfig(archive)
            self.writeManifest(archive, results)
            self.writeComparisonMatrices(archive, results)
            self.writeComparisonReport(archive, results, exportFormats)
            for imagePath in plotImagePaths:
                imagePath = Path(imagePath)
                if imagePath.exists():
                    archive.write(str(imagePath), f"comparison/plots/{imagePath.name}")
            self.writeTrackFiles(archive)

            totalVariants = max(len(results), 1)
            for index, result in enumerate(results):
                self.writeVariantFolder(archive, result, exportFormats)
                if progressCallback:
                    progressCallback(index, totalVariants)

        return {"zipPath": zipPath, "variantCount": len(results)}

    def writeReadme(self, archive, results):
        lines = [
            "COYPU batch export",
            f"Generated: {datetime.now().isoformat(timespec='seconds')}",
            f"Configuration: {self.batchConfigData.get('configName', '')}",
            f"Variants: {len(results)}",
            "",
            "comparison/   overlay plots and side-by-side metric tables across every variant",
            "track/        the merged alignment used for every variant, and any junction warnings",
            "variants/     one folder per variant with its own reports, protocol and raw data",
        ]
        archive.writestr("README.txt", "\n".join(lines))

    def writeBatchConfig(self, archive):
        archive.writestr("batchConfig.json", json.dumps(self.batchConfigData, indent=2, ensure_ascii=False, default=str))

    def writeManifest(self, archive, results):
        manifest = {}
        for result in results:
            manifest[result["variantId"]] = {
                "label": result.get("spec", {}).get("label", result["variantId"]),
                "status": result["status"],
                "durationS": result.get("durationS"),
                "errorText": result.get("errorText", ""),
                "folder": f"variants/{self.buildVariantFolderName(result)}",
            }
        archive.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))

    def writeComparisonMatrices(self, archive, results):
        self.writeVariantMatrix(archive, results)
        self.writeTravelTimeMatrix(archive, results)
        self.writeProfileMatrices(archive, results)

    def writeVariantMatrix(self, archive, results):
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["variantId", "label", "status", "trackLengthKm", "maxSpeedDesignKmh",
                         "maxSpeedActualKmh", "meanSpeedActualKmh", "totalTimeS", "originDestTimeS",
                         "maxCantMm", "maxCantDefMm", "meanUtilD", "meanUtilI", "limitCountD", "limitCountI"])
        for result in results:
            label = result.get("spec", {}).get("label", result["variantId"])
            metrics = result.get("metrics", {})
            writer.writerow([result["variantId"], label, result["status"],
                             metrics.get("trackLengthKm"), metrics.get("maxSpeedDesignKmh"),
                             metrics.get("maxSpeedActualKmh"), metrics.get("meanSpeedActualKmh"),
                             metrics.get("totalTimeS"), metrics.get("originDestTimeS"),
                             metrics.get("maxCantMm"), metrics.get("maxCantDefMm"),
                             metrics.get("meanUtilD"), metrics.get("meanUtilI"),
                             metrics.get("limitCountD"), metrics.get("limitCountI")])
        archive.writestr("comparison/variantMatrix.csv", buffer.getvalue())

    def writeTravelTimeMatrix(self, archive, results):
        legLabelsInOrder = []
        seenLabels = set()
        variantColumns = []
        perVariantLegTimes = {}
        for result in results:
            if result["status"] != "ok":
                continue
            label = result.get("spec", {}).get("label", result["variantId"])
            variantColumns.append(label)
            legMap = dict(result.get("metrics", {}).get("interstationRows", []))
            perVariantLegTimes[label] = legMap
            for legLabel in legMap:
                if legLabel not in seenLabels:
                    seenLabels.add(legLabel)
                    legLabelsInOrder.append(legLabel)

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["leg"] + variantColumns)
        for legLabel in legLabelsInOrder:
            row = [legLabel]
            for variantLabel in variantColumns:
                legTime = perVariantLegTimes[variantLabel].get(legLabel)
                row.append(f"{legTime:.1f}" if legTime is not None else "")
            writer.writerow(row)
        archive.writestr("comparison/travelTimeMatrix.csv", buffer.getvalue())

    def writeProfileMatrices(self, archive, results):
        successfulResults = [r for r in results if r["status"] == "ok"]
        if not successfulResults:
            return
        gridKm = self.buildCommonGrid(successfulResults)
        if gridKm is None:
            return

        labels = [r.get("spec", {}).get("label", r["variantId"]) for r in successfulResults]
        speedColumns, cantColumns = [], []
        for result in successfulResults:
            series = result.get("seriesForPlot", {})
            speedColumns.append(batch_metrics.resampleSeries(series.get("stationKm", []), series.get("speedProfile", []), gridKm))
            cantColumns.append(batch_metrics.resampleSeries(series.get("stationKm", []), series.get("cantDeficiency", []), gridKm))

        archive.writestr("comparison/speedProfileMatrix.csv",
                         self.buildGridCsv(gridKm, labels, speedColumns))
        archive.writestr("comparison/cantDeficiencyMatrix.csv",
                         self.buildGridCsv(gridKm, labels, cantColumns))

    def buildGridCsv(self, gridKm, labels, columns):
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["stationKm"] + labels)
        for rowIndex, stationKm in enumerate(gridKm):
            writer.writerow([f"{stationKm:.4f}"] + [self.formatGridValue(col[rowIndex]) for col in columns])
        return buffer.getvalue()

    def buildCommonGrid(self, successfulResults, stepKm=0.1):
        allStations = [np.asarray(r.get("seriesForPlot", {}).get("stationKm", [])) for r in successfulResults]
        allStations = [s for s in allStations if len(s) > 0]
        if not allStations:
            return None
        minKm = min(float(np.min(s)) for s in allStations)
        maxKm = max(float(np.max(s)) for s in allStations)
        if maxKm <= minKm:
            return np.array([minKm])
        return np.arange(minKm, maxKm + stepKm, stepKm)

    def formatGridValue(self, value):
        return "" if np.isnan(value) else f"{value:.2f}"

    def writeComparisonReport(self, archive, results, exportFormats):
        reportLines = self.buildComparisonReportLines(results)
        titleText = self.lan.get("dashboardSummary", "Comparison report")
        if exportFormats.get("txt", True):
            archive.writestr("comparison/comparisonReport.txt", report_formats.linesToPlainText(reportLines))
        if exportFormats.get("pdf"):
            self.writeRenderedFile(archive, "comparison/comparisonReport.pdf", reportLines, titleText, "pdf")
        if exportFormats.get("tex"):
            archive.writestr("comparison/comparisonReport.tex", report_formats.linesToTex(reportLines, titleText))

    def buildComparisonReportLines(self, results):
        lines = [f"=== {self.lan.get('dashboardSummary', 'Comparison report')} ==="]
        lines.append(f"Configuration: {self.batchConfigData.get('configName', '')}")
        lines.append(f"Variants: {len(results)}")
        lines.append("")
        for result in results:
            label = result.get("spec", {}).get("label", result["variantId"])
            lines.append(f"--- {label} ({result['status']}) ---")
            if result["status"] == "ok":
                metrics = result.get("metrics", {})
                lines.append(f"  Track length: {metrics.get('trackLengthKm') or 0:.3f} km")
                lines.append(f"  Max design speed: {metrics.get('maxSpeedDesignKmh') or 0:.0f} km/h")
                lines.append(f"  Max actual speed: {metrics.get('maxSpeedActualKmh') or 0:.0f} km/h")
                lines.append(f"  Total time: {batch_metrics.formatDuration(metrics.get('totalTimeS'))}")
            elif result.get("errorText"):
                lines.append(f"  Error: {result['errorText']}")
            lines.append("")
        return lines

    def writeTrackFiles(self, archive):
        if self.mergedLandXml:
            buffer = io.StringIO()
            writer = csv.writer(buffer)
            writer.writerow(["chainageKm", "geometryType", "radius", "curvature"])
            stationHorizontal = self.mergedLandXml.get("stationHorizontal", [])
            geometryType = self.mergedLandXml.get("geometryType", [])
            radius = self.mergedLandXml.get("radius", [])
            curvature = self.mergedLandXml.get("curvature", [])
            for i in range(len(stationHorizontal)):
                writer.writerow([f"{stationHorizontal[i]:.4f}", self.safeIndex(geometryType, i),
                                 self.safeIndex(radius, i), self.safeIndex(curvature, i)])
            archive.writestr("track/mergedAlignment.csv", buffer.getvalue())

        if self.junctions:
            buffer = io.StringIO()
            writer = csv.writer(buffer)
            writer.writerow(["junctionIndex", "stationKm", "gapMeters"])
            for junction in self.junctions:
                writer.writerow([junction["junctionIndex"], f"{junction['stationKm']:.4f}", f"{junction['gapMeters']:.1f}"])
            archive.writestr("track/junctions.csv", buffer.getvalue())

        sourceLines = [source.get("fileName", "") for source in self.batchConfigData.get("trackSources", [])]
        archive.writestr("track/sourceFiles.txt", "\n".join(sourceLines))

    def writeVariantFolder(self, archive, result, exportFormats):
        folderName = f"variants/{self.buildVariantFolderName(result)}"
        archive.writestr(f"{folderName}/variantSpec.json",
                         json.dumps(result.get("spec", {}), indent=2, ensure_ascii=False, default=str))

        if result["status"] != "ok":
            archive.writestr(f"{folderName}/error.txt", result.get("errorText", ""))
            return

        dataStorage = result.get("dataStorage", {})
        protocolLines = self.buildProtocolLines(result)
        titleText = result.get("spec", {}).get("label", result["variantId"])
        if exportFormats.get("txt", True):
            archive.writestr(f"{folderName}/calculationProtocol.txt", report_formats.linesToPlainText(protocolLines))
        if exportFormats.get("pdf"):
            self.writeRenderedFile(archive, f"{folderName}/calculationProtocol.pdf", protocolLines, titleText, "pdf")
        if exportFormats.get("tex"):
            archive.writestr(f"{folderName}/calculationProtocol.tex", report_formats.linesToTex(protocolLines, titleText))

        self.writeVariantData(archive, folderName, dataStorage)

    def buildProtocolLines(self, result):
        spec = result.get("spec", {})
        lines = [f"=== {spec.get('label', result['variantId'])} ==="]
        lines.append(f"Stopping pattern: {spec.get('stopsProfileLabel', '')}")
        lines.append(f"Design approach: {spec.get('approachLabel', '')} {spec.get('designApproach', {})}")
        if spec.get("sweepParamKey"):
            lines.append(f"Sweep: {spec['sweepParamKey']} = {spec['sweepValue']}")
        lines.append(f"Calculation mode: {spec.get('calculationMode', '')}")
        lines.append(f"Design profile: {spec.get('designProfile', '')}")
        lines.append("")
        for key, value in result.get("metrics", {}).items():
            if key == "interstationRows":
                continue
            lines.append(f"{key}: {value}")
        return lines

    def writeVariantData(self, archive, folderName, dataStorage):
        lxml = dataStorage.get("LandXML", {})
        stationKm = lxml.get("stationCantPossible", lxml.get("stationHorizontal", []))

        if batch_metrics.hasData(stationKm):
            archive.writestr(f"{folderName}/data/speedProfile.csv", self.buildSpeedProfileCsv(dataStorage, stationKm))
            archive.writestr(f"{folderName}/data/cantProfile.csv", self.buildCantProfileCsv(lxml, stationKm))

        vehicleCount = int(dataStorage.get("num_vehicles", 0) or 0)
        for vehicleIndex in range(vehicleCount):
            kinematicsCsv = self.buildKinematicsCsv(dataStorage, vehicleIndex)
            if kinematicsCsv is not None:
                archive.writestr(f"{folderName}/data/kinematics_V{vehicleIndex + 1}.csv", kinematicsCsv)

    def buildSpeedProfileCsv(self, dataStorage, stationKm):
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["stationKm", "v100", "v130", "v150", "vK"])
        v100, v130 = dataStorage.get("speedLimits100", []), dataStorage.get("speedLimits130", [])
        v150, vK = dataStorage.get("speedLimits150", []), dataStorage.get("speedLimitsK", [])
        for i in range(len(stationKm)):
            writer.writerow([f"{stationKm[i]:.4f}", self.safeIndex(v100, i), self.safeIndex(v130, i),
                             self.safeIndex(v150, i), self.safeIndex(vK, i)])
        return buffer.getvalue()

    def buildCantProfileCsv(self, lxml, stationKm):
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["stationKm", "D", "I100", "I130", "I150", "IK"])
        cant = lxml.get("cantPossible", [])
        cDef100, cDef130 = lxml.get("cDef100", []), lxml.get("cDef130", [])
        cDef150, cDefK = lxml.get("cDef150", []), lxml.get("cDefK", [])
        for i in range(len(stationKm)):
            writer.writerow([f"{stationKm[i]:.4f}", self.safeIndex(cant, i), self.safeIndex(cDef100, i),
                             self.safeIndex(cDef130, i), self.safeIndex(cDef150, i), self.safeIndex(cDefK, i)])
        return buffer.getvalue()

    def buildKinematicsCsv(self, dataStorage, vehicleIndex):
        stationsM = dataStorage.get(f"kinematicsStationM_{vehicleIndex}")
        if not batch_metrics.hasData(stationsM):
            return None
        timesS = dataStorage.get(f"kinematicsTimeS_{vehicleIndex}", [])
        speedsMs = dataStorage.get(f"kinematicsSpeedM_{vehicleIndex}", [])
        accel = dataStorage.get(f"kinematicsAcceleration_{vehicleIndex}", [])
        fTrac = dataStorage.get(f"kinematicsForceTractionKN_{vehicleIndex}", [])
        fBrake = dataStorage.get(f"kinematicsForceBrakingKN_{vehicleIndex}", [])
        fRes = dataStorage.get(f"kinematicsForceResistanceKN_{vehicleIndex}", [])
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["stationM", "timeS", "speedMs", "accelMs2", "forceTracKN", "forceBrakeKN", "forceResKN"])
        for i in range(len(stationsM)):
            writer.writerow([self.safeIndex(stationsM, i), self.safeIndex(timesS, i), self.safeIndex(speedsMs, i),
                             self.safeIndex(accel, i), self.safeIndex(fTrac, i), self.safeIndex(fBrake, i),
                             self.safeIndex(fRes, i)])
        return buffer.getvalue()

    def safeIndex(self, array, index):
        return array[index] if index < len(array) else ""

    # PDF rendering needs a real file on disk, written to a temp file then folded into the archive
    def writeRenderedFile(self, archive, arcname, reportLines, titleText, formatKey):
        with tempfile.TemporaryDirectory() as tmpDir:
            tmpPath = str(Path(tmpDir) / f"rendered.{formatKey}")
            report_formats.writeReportFile(reportLines, tmpPath, titleText)
            archive.write(tmpPath, arcname)
