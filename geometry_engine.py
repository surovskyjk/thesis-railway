import numpy as np

class GeometryCalculator:
    def __init__(self, dataStorage):
        self.data = dataStorage

    def runCalculationLoop(self):
        defaultVal = self.data.get("settingsData",{})
        designApproach = self.data.get("settingsData",{}).get("designApproach","standard")
        defaultProfile = self.data.get("defaultProfile","I150")
        lxml = self.data.get("LandXML",{})

        lxml["stationCantPossible"] = lxml.get("stationHorizontal",[])

        self.vInit = np.full(len(lxml["stationCantPossible"]),defaultVal.get("vInit",[120])[0])
        self.vMax = np.full(len(lxml["stationCantPossible"]),defaultVal.get("vInit",[0])[0])
        self.maxD = defaultVal.get("maxD",[0])[0]

        self.geometryType = np.array(lxml.get("geometryType",[]))

        self.spiralMask = np.where(self.geometryType == "Spiral")[0]
        self.curveMask = np.where(self.geometryType == "Curve")[0]
        self.lineMask = np.where(self.geometryType == "Line")[0]

        self.kappa = lxml.get("curvature",[]) * lxml.get("curvatureSign",[])

        lenStationPos = len(lxml["stationCantPossible"])

        # Cant arrays
        lxml["cantPossible"] = np.zeros(lenStationPos)
        lxml["cDef100"] = np.zeros(lenStationPos)
        lxml["cDef130"] = np.zeros(lenStationPos)
        lxml["cDef150"] = np.zeros(lenStationPos)
        lxml["cDefK"] = np.zeros(lenStationPos)

        # Speed arrays
        self.data["stationSpeed100"] = lxml["stationCantPossible"]
        self.data["stationSpeed130"] = lxml["stationCantPossible"]
        self.data["stationSpeed150"] = lxml["stationCantPossible"]
        self.data["stationSpeedK"] = lxml["stationCantPossible"]

        self.data["speedLimits100"] = np.zeros(lenStationPos)
        self.data["speedLimits130"] = np.zeros(lenStationPos)
        self.data["speedLimits150"] = np.zeros(lenStationPos)
        self.data["speedLimitsK"] = np.zeros(lenStationPos)

        # Pointers
        self.stations = lxml["stationCantPossible"]
        self.cantNew = lxml["cantPossible"]
        self.cDef100 = lxml["cDef100"]
        self.cDef130 = lxml["cDef130"]
        self.cDef150 = lxml["cDef150"]
        self.cDefK = lxml["cDefK"]
        self.speed100 = self.data["speedLimits100"]
        self.speed130 = self.data["speedLimits130"]
        self.speed150 = self.data["speedLimits150"]
        self.speedK = self.data["speedLimitsK"]

        # Calculation loop
        self.calculationLoop(designApproach, defaultProfile)

        lxml["cantDef100"] = lxml["cantPossible"] + lxml["cDef100"]
        lxml["cantDef130"] = lxml["cantPossible"] + lxml["cDef130"]
        lxml["cantDef150"] = lxml["cantPossible"] + lxml["cDef150"]
        lxml["cantDefK"] = lxml["cantPossible"] + lxml["cDefK"]

    def calculationLoop(self, approach, profile):
        # Line segments - speed is initial speed, cant is zero, cant def. is also zero
        self.cantNew[self.lineMask] = 0
        self.cDef100[self.lineMask] = 0
        self.cDef130[self.lineMask] = 0
        self.cDef150[self.lineMask] = 0
        self.cDefK[self.lineMask] = 0

        self.speed100[self.lineMask] = self.vInit[self.lineMask]
        self.speed130[self.lineMask] = self.vInit[self.lineMask]
        self.speed150[self.lineMask] = self.vInit[self.lineMask]
        self.speedK[self.lineMask] = self.vInit[self.lineMask]

        # Switch for profile (V_cDef profile)
        if profile == "I100":
            self.cantDef = self.cDef100
        elif profile == "I130":
            self.cantDef = self.cDef130
        elif profile == "I150":
            self.cantDef = self.cDef150
        elif profile == "K":
            self.cantDef = self.cDefK
        else:
            self.cantDef = self.cDef100

        # Iterative solver

        convergenceReached = False
        iterationN = 0
        maxIterations = 50

        while not convergenceReached and iterationN < maxIterations:
            convergenceReached = True
            iterationN += 1

            # Calculate Deq for each segment, set maximum D and rest put into I
            for i in range(0, len(self.cantNew)):
                Deq = self.calculateCant(self.vInit[i], 0, self.kappa[i])
                signKappa = np.sign(self.kappa[i]) if self.kappa[i] != 0 else 1
                self.cantNew[i] = signKappa*min(np.abs(Deq), self.maxD, self.geometryMaxD(self.kappa[i]))
                
                I = self.calculateCantDef(self.vInit[i], self.cantNew[i], self.kappa[i])
                self.cantDef[i] = signKappa*min(abs(I), self.getNormLimit("I", self.vInit[i], approach)[0])

            # Force D and I in line elements zero
            self.cantNew[self.lineMask] = 0
            self.cantDef[self.lineMask] = 0

            # Go element-wise and assign max possible change of D and I - forward
            for i in range(1, len(self.stations)):
                length = (self.stations[i] - self.stations[i-1])*1000
                if length <= 0:
                    if self.geometryType[i] != "Spiral" and self.geometryType[i-1] != "Spiral" and self.kappa[i] != self.kappa[i-1]:
                        dD = 0
                        dI = self.getNormLimit("dI", self.vInit[i], approach)[0]
                        
                if self.geometryType[i] == "Spiral":
                    dD = self.calculateCantN(self.vMax[i],self.getNormLimit("nLin", self.vMax[i], approach), length)
                    dI = self.calculateCantDefNi(self.vMax[i], self.getNormLimit("nILin", self.vMax[i], approach), length)
                else:
                    dD = 0
                    dI = 0

                self.cantNew[i] = np.clip(
                    self.cantNew[i],
                    self.cantNew[i-1] - dD,
                    self.cantNew[i-1] + dD
                )

                self.cantDef[i] = np.clip(
                    self.cantDef[i],
                    self.cantDef[i-1] - dI,
                    self.cantDef[i-1] + dI
                )

            # Go element-wise and assign max possible change of D and I - backward
            # for i in range(len(self.stations)-2, -1, -1):
            #     length = (self.stations[i+1] - self.stations[i])*1000
            #     if length <= 0:
            #         if self.geometryType[i] != "Spiral" and self.geometryType[i+1] != "Spiral" and self.kappa[i] != self.kappa[i+1]:
            #             dD = 0
            #             dI = self.getNormLimit("dI", self.vInit[i], approach)[0]
            #     if self.geometryType[i] == "Spiral":
            #         dD = self.calculateCantN(self.vMax[i],self.getNormLimit("nLin", self.vMax[i], approach), length)
            #         dI = self.calculateCantDefNi(self.vMax[i], self.getNormLimit("nILin", self.vMax[i], approach), length)
            #     else:
            #         dD = 0
            #         dI = 0

            #     self.cantNew[i] = np.clip(
            #         self.cantNew[i],
            #         self.cantNew[i+1] - dD,
            #         self.cantNew[i+1] + dD
            #     )

            #     self.cantDef[i] = np.clip(
            #         self.cantDef[i],
            #         self.cantDef[i+1] - dI,
            #         self.cantDef[i+1] + dI
            #     )

            # Assign max I and D values, assign speed
            for i in range(0, len(self.cantNew)):
                self.cantNew[i] = np.abs(self.cantNew[i])
                self.cantDef[i] = np.abs(self.cantDef[i])

                self.vMax[i] = self.calculateSpeed(self.cantNew[i], self.cantDef[i], np.abs(self.kappa[i]), 5, self.vInit[i])

                if self.vMax[i] < self.vInit[i]:
                    if self.vInit[i] > 20:
                        self.vInit[i] -= 5
                        convergenceReached = False

                self.vMax[i] = min(self.vMax[i], self.vInit[i])

        for i in range(0, len(self.vMax)):
            self.speed100[i] = self.vMax[i]
            self.speed130[i] = self.vMax[i]
            self.speed150[i] = self.vMax[i]
            self.speedK[i] = self.vMax[i]

        # Debugging print
        for i in range(0,len(self.cantNew)):
            print(self.stations[i], self.cantNew[i], self.cantDef[i], self.vMax[i])
        print(self.getNormLimit("nLin", 120, approach))
        print(f"Convergation reached after {iterationN} iterations.")

    def runCalculationLoopI(self):

        pass

    def calculateCantN(self, v, n, length):
        if n[0] == 0 or v == 0:
            return 0
        gradient = max(n[0]*v, n[1])
        return np.floor(length*1000/(gradient))

    def calculateCantDefNi(self, v, nI, length):
        if nI == 0 or v == 0:
            return 0
        return np.ceil(length*1000/(nI[0]*v))

    def calculateN(self, v, length, D):
        if D == 0:
            return np.inf
        if v == 0:
            return 0
        return length*1000/(D*v)

    def calculateNi(self, v, length, I):
        if I == 0:
            return np.inf
        if v == 0:
            return 0
        return length*1000/(I*v)

    def calculateCant(self, v, I, kappa):
        return np.floor((11.8 * (v**2) * kappa) - I)

    def calculateCantDef(self, v, D, kappa):
        return np.ceil((11.8 * (v**2) * kappa) - D)

    def calculateSpeed(self, D, I, kappa, round, vInit):
        if kappa == 0:
            return vInit
        if round == 0:
            return np.sqrt(max(0, np.abs(D + I) / (11.8 * np.abs(kappa))))

        return (int(np.sqrt(max(0, np.abs(D + I) / (11.8 * np.abs(kappa))))) // round) * round

    def geometryMaxD(self, kappa):
        if kappa == 0:
            return 0
        radius = 1/np.abs(kappa)
        maxD = np.floor((radius - 50)/1.5)
        return maxD
        

    def getNormLimit(self, parameter, speedLimit, approach): 
        normLimits = self.data.get("settingsData", {}).get(parameter,[])

        if parameter == "nLin":
            approachDict = {
                "standard": 2,
                "limit": 4,
                "minmax": 6
            }

        else:
            approachDict = {
                "standard": 2,
                "limit": 3,
                "minmax": 4
            }

        col = approachDict.get(approach, 3)

        if parameter == "nLin":
            for row in normLimits:
                vMin, vMax = row[0], row[1]
                if vMin < speedLimit <= vMax:
                    return np.array([row[col],row[col+1]])
                
            return np.array([normLimits[-1][col]]) if normLimits else np.array([0,0])

        else:
            for row in normLimits:
                vMin, vMax = row[0], row[1]
                if vMin < speedLimit <= vMax:
                    return np.array([row[col]])  
            
            return np.array([normLimits[-1][col]]) if normLimits else np.array([0])



    