# Holds the results of the most recently run batch, deliberately outside MainWindow.dataStorage
import plot_widgets


class BatchResultStore:
    def __init__(self):
        self.resultList = []
        self.configData = {}
        self.colorAssignments = {}

    def setResults(self, results):
        self.resultList = list(results)
        self.colorAssignments = {}
        for index, result in enumerate(self.resultList):
            self.colorAssignments[result["variantId"]] = plot_widgets.VARIANT_COLORS[index % len(plot_widgets.VARIANT_COLORS)]

    def results(self):
        return self.resultList

    def resultById(self, variantId):
        for result in self.resultList:
            if result["variantId"] == variantId:
                return result
        return None

    def successfulResults(self):
        return [result for result in self.resultList if result["status"] == "ok"]

    def colorFor(self, variantId):
        return self.colorAssignments.get(variantId, plot_widgets.FALLBACK_COLOR)

    def isEmpty(self):
        return len(self.resultList) == 0

    def clear(self):
        self.resultList = []
        self.configData = {}
        self.colorAssignments = {}

    def batchConfig(self):
        return self.configData

    def setBatchConfig(self, configData):
        self.configData = configData
