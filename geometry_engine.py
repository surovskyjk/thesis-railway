import numpy as np

class GeometryCalculator:
    def __init__(self, dataStorage):
        self.data = dataStorage

    def runCalculationLoopI(self):
        self.setLoopsData()
        # Calculation loop
        self.calculationLoopI(self.designApproach, self.defaultProfile)
        self.sumCantDef()

    def runCalculationLoop(self):
        self.setLoopsData()
        # Calculation loop
        self.calculationLoop(self.designApproach, self.defaultProfile)
        self.sumCantDef()

    def setLoopsData(self):
        defaultVal = self.data.get("settingsData",{})
        self.designApproach = self.data.get("settingsData",{}).get("designApproach","standard")
        self.defaultProfile = self.data.get("defaultProfile","I150")
        lxml = self.data.get("LandXML",{})

        lxml["stationCantPossible"] = lxml.get("stationHorizontal",[])

        self.vInit = np.full(len(lxml["stationCantPossible"]),defaultVal.get("vInit",[120])[0])
        self.vMax = np.full(len(lxml["stationCantPossible"]),defaultVal.get("vInit",[0])[0])
        self.maxD = defaultVal.get("maxD",[0])[0]

        self.geometryType = np.array(lxml.get("geometryType",[]))

        self.spiralMask = np.where(self.geometryType == "Spiral")[0]
        self.curveMask = np.where(self.geometryType == "Curve")[0]
        self.lineMask = np.where(self.geometryType == "Line")[0]

        lenStationPos = len(lxml["stationCantPossible"])

        self.kappa = lxml.get("curvature",np.zeros(lenStationPos)) * lxml.get("curvatureSign",np.zeros(lenStationPos))
        self.curvSign = lxml.get("curvatureSign",np.zeros(lenStationPos))

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
        self.cant = lxml.get("cant",np.zeros(lenStationPos))
        self.stationsCant = lxml.get("stationCant","stationCantPossible")
        self.stationsNew = lxml["stationCantPossible"]
        self.cantNew = lxml["cantPossible"]
        self.cDef100 = lxml["cDef100"]
        self.cDef130 = lxml["cDef130"]
        self.cDef150 = lxml["cDef150"]
        self.cDefK = lxml["cDefK"]
        self.speed100 = self.data["speedLimits100"]
        self.speed130 = self.data["speedLimits130"]
        self.speed150 = self.data["speedLimits150"]
        self.speedK = self.data["speedLimitsK"]

    def sumCantDef(self):
        lxml = self.data.get("LandXML",{})
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

            # Stage 1 - based on Vinit in each element, calculate D
            cantTarget = np.zeros_like(self.cantNew)

            for i in range(0, len(self.cantNew)):
                Deq = self.calculateCant(self.vInit[i], 0, self.kappa[i])
                signKappa = np.sign(self.kappa[i]) if self.kappa[i] != 0 else 1
                cantTarget[i] = signKappa*min(np.abs(Deq), self.maxD, self.geometryMaxD(self.kappa[i]))

            cantTarget[self.lineMask] = 0

            cantFWD = np.copy(cantTarget)
            for i in range(1, len(self.stationsNew)):
                length = (self.stationsNew[i] - self.stationsNew[i-1])*1000
                dD = 0
                if length > 0 and self.geometryType[i] == "Spiral":
                    dD = self.calculateCantN(self.vInit[i],self.getNormLimit("nLin", self.vInit[i], approach), length)
                if self.geometryType[i] == "Line":
                    cantFWD[i] = 0
                else:
                    cantFWD[i] = np.clip(
                        cantFWD[i],
                        cantFWD[i-1] - dD,
                        cantFWD[i-1] + dD
                    )

                    if self.curvSign[i] > 0:
                        cantFWD[i] = max(0, cantFWD[i])
                    elif self.curvSign[i] < 0:
                        cantFWD[i] = min(0, cantFWD[i])


            cantBWD = np.copy(cantTarget)
            for i in range(len(self.stationsNew)-2, -1, -1):
                length = (self.stationsNew[i+1] - self.stationsNew[i])*1000
                dD = 0
                if length > 0 and self.geometryType[i+1] == "Spiral":
                    dD = self.calculateCantN(self.vInit[i],self.getNormLimit("nLin", self.vInit[i], approach), length)
                if self.geometryType[i] == "Line":
                    cantBWD[i] = 0
                else:
                    cantBWD[i] = np.clip(
                        cantBWD[i],
                        cantBWD[i+1] - dD,
                        cantBWD[i+1] + dD
                    )

                    if self.curvSign[i] > 0:
                        cantBWD[i] = max(0, cantFWD[i])
                    elif self.curvSign[i] < 0:
                        cantBWD[i] = min(0, cantFWD[i])


            self.cantNew[:] = np.where(np.abs(cantFWD) < np.abs(cantBWD), cantFWD, cantBWD)

            # Stage 2 - based on Vinit and D in each element, calculate I
            cantDefTarget = np.zeros_like(self.cantDef)

            for i in range(0, len(self.cantDef)):
                if self.geometryType[i] == "Line":
                    cantDefTarget[i] = 0
                else:
                    signKappa = np.sign(self.kappa[i]) if self.kappa[i] != 0 else 1
                    maxI = self.getNormLimit("I", self.vInit[i], approach)[0]
                    cantDefTarget[i] = signKappa*maxI

            cantDefTarget[self.lineMask] = 0
            
            cantDefFWD = np.copy(cantDefTarget)
            for i in range(1, len(self.stationsNew)):
                length = (self.stationsNew[i] - self.stationsNew[i-1])*1000
                dI = 0
                if length <= 0:
                    if self.geometryType[i] != "Spiral" and self.geometryType[i-1] != "Spiral" and self.kappa[i] != self.kappa[i-1]:
                        dI = self.getNormLimit("dI", self.vInit[i], approach)[0]
                elif self.geometryType[i] == "Spiral":
                    dI = self.calculateCantDefNi(self.vInit[i], self.getNormLimit("nILin", self.vInit[i], approach), length)
                if self.geometryType[i] == "Line":
                    cantDefFWD[i] = 0
                else:
                    cantDefFWD[i] = np.clip(
                        cantDefFWD[i],
                        cantDefFWD[i-1] - dI,
                        cantDefFWD[i-1] + dI
                    )

                    if self.curvSign[i] > 0:
                        cantDefFWD[i] = max(0, cantDefFWD[i])
                    elif self.curvSign[i] < 0:
                        cantDefFWD[i] = min(0, cantDefFWD[i])


            cantDefBWD = np.copy(cantDefTarget)
            for i in range(len(self.stationsNew)-2, -1, -1):
                length = (self.stationsNew[i+1] - self.stationsNew[i])*1000
                dI = 0
                if length <= 0:
                    if self.geometryType[i] != "Spiral" and self.geometryType[i+1] != "Spiral" and self.kappa[i] != self.kappa[i+1]:
                        dI = self.getNormLimit("dI", self.vInit[i], approach)[0]
                elif self.geometryType[i+1] == "Spiral":
                    dI = self.calculateCantDefNi(self.vInit[i], self.getNormLimit("nILin", self.vInit[i], approach), length)
                if self.geometryType[i] == "Line":
                    cantDefBWD[i] = 0
                else:
                    cantDefBWD[i] = np.clip(
                        cantDefBWD[i],
                        cantDefFWD[i+1] - dI,
                        cantDefFWD[i+1] + dI
                    )

                    if self.curvSign[i] > 0:
                        cantDefBWD[i] = max(0, cantDefBWD[i])
                    elif self.curvSign[i] < 0:
                        cantDefBWD[i] = min(0, cantDefBWD[i])


            self.cantDef[:] = np.where(np.abs(cantDefFWD) < np.abs(cantDefBWD), cantDefFWD, cantDefBWD)

            # Stage 3 - Ensure continuous D and I (exception of delta I for connecting lines and curves but not spirals)
            for i in range(1, len(self.stationsNew)):
                if self.stationsNew[i] == self.stationsNew[i-1]:
                    minD = min(np.abs(self.cantNew[i-1]), np.abs(self.cantNew[i]))
                    signD = np.sign(self.cantNew[i]) if self.cantNew[i] != 0 else np.sign(self.cantNew[i-1])
                    self.cantNew[i] = signD * minD
                    self.cantNew[i-1] = signD * minD
             
                    if self.geometryType[i] == "Spiral" or self.geometryType[i-1] == "Spiral":
                        minI = min(np.abs(self.cantDef[i-1]), np.abs(self.cantDef[i]))
                        signI = np.sign(self.cantDef[i]) if self.cantDef[i] != 0 else np.sign(self.cantDef[i-1])
                        self.cantDef[i] = signI * minI
                        self.cantDef[i-1] = signI * minI

            # Stage 4 - Calculate speed in respective section
            for i in range(0, len(self.cantNew), 2):
                v1 = self.calculateSpeed(np.abs(self.cantNew[i]), np.abs(self.cantDef[i]), np.abs(self.kappa[i]), 5, self.vInit[i])
                v2 = self.calculateSpeed(np.abs(self.cantNew[i+1]), np.abs(self.cantDef[i+1]), np.abs(self.kappa[i+1]), 5, self.vInit[i+1])

                minVmax = min(v1, v2)

                self.vMax[i] = min(self.vInit[i], minVmax)
                self.vMax[i+1] = min(self.vInit[i+1], minVmax)

                if self.vMax[i] < self.vInit[i] or self.vMax[i+1] < self.vInit[i+1]:
                    if self.vInit[i] > 20:
                        self.vInit[i] -= 5
                        self.vInit[i+1] -= 5
                        convergenceReached = False

                self.vMax[i] = min(self.vMax[i], self.vInit[i])

        # Debugging print
        for i in range(0,len(self.cantNew)):
            print(self.stationsNew[i], self.cantNew[i], self.cantDef[i], self.vMax[i], self.vInit[i], self.geometryType[i], self.kappa[i])
        print(self.getNormLimit("nLin", 120, approach))
        print(f"Convergation reached after {iterationN} iterations.")

        for i in range(0, len(self.cantNew)):        
            self.cantNew[i] = np.floor(np.abs(self.cantNew[i]))
            self.cantDef[i] = np.ceil(np.abs(self.cantDef[i]))

        for i in range(0, len(self.vMax)):
            self.speed100[i] = self.vMax[i]
            self.speed130[i] = self.vMax[i]
            self.speed150[i] = self.vMax[i]
            self.speedK[i] = self.vMax[i]

    def calculationLoopI(self, approach, profile):
        # Line segments - speed is initial speed, cant remains the same (or 0, if not provided), cant def. is also zero
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

            # Stage 1 - based on cant provided in each element, calculate D in stationCantPossible

            self.cantNew[:] = np.interp(self.stationsNew, self.stationsCant, self.cant)

            # Stage 2 - based on Vinit and D in each element, calculate I
            cantDefTarget = np.zeros_like(self.cantDef)

            for i in range(0, len(self.cantDef)):
                if self.geometryType[i] == "Line":
                    cantDefTarget[i] = 0
                else:
                    signKappa = np.sign(self.kappa[i]) if self.kappa[i] != 0 else 1
                    maxI = self.getNormLimit("I", self.vInit[i], approach)[0]
                    cantDefTarget[i] = signKappa*maxI

            cantDefTarget[self.lineMask] = 0
            
            cantDefFWD = np.copy(cantDefTarget)
            for i in range(1, len(self.stationsNew)):
                length = (self.stationsNew[i] - self.stationsNew[i-1])*1000
                dI = 0
                if length <= 0:
                    if self.geometryType[i] != "Spiral" and self.geometryType[i-1] != "Spiral" and self.kappa[i] != self.kappa[i-1]:
                        dI = self.getNormLimit("dI", self.vInit[i], approach)[0]
                elif self.geometryType[i] == "Spiral":
                    dI = self.calculateCantDefNi(self.vInit[i], self.getNormLimit("nILin", self.vInit[i], approach), length)
                if self.geometryType[i] == "Line":
                    cantDefFWD[i] = 0
                else:
                    cantDefFWD[i] = np.clip(
                        cantDefFWD[i],
                        cantDefFWD[i-1] - dI,
                        cantDefFWD[i-1] + dI
                    )

                    if self.curvSign[i] > 0:
                        cantDefFWD[i] = max(0, cantDefFWD[i])
                    elif self.curvSign[i] < 0:
                        cantDefFWD[i] = min(0, cantDefFWD[i])


            cantDefBWD = np.copy(cantDefTarget)
            for i in range(len(self.stationsNew)-2, -1, -1):
                length = (self.stationsNew[i+1] - self.stationsNew[i])*1000
                dI = 0
                if length <= 0:
                    if self.geometryType[i] != "Spiral" and self.geometryType[i+1] != "Spiral" and self.kappa[i] != self.kappa[i+1]:
                        dI = self.getNormLimit("dI", self.vInit[i], approach)[0]
                elif self.geometryType[i+1] == "Spiral":
                    dI = self.calculateCantDefNi(self.vInit[i], self.getNormLimit("nILin", self.vInit[i], approach), length)
                if self.geometryType[i] == "Line":
                    cantDefBWD[i] = 0
                else:
                    cantDefBWD[i] = np.clip(
                        cantDefBWD[i],
                        cantDefFWD[i+1] - dI,
                        cantDefFWD[i+1] + dI
                    )

                    if self.curvSign[i] > 0:
                        cantDefBWD[i] = max(0, cantDefBWD[i])
                    elif self.curvSign[i] < 0:
                        cantDefBWD[i] = min(0, cantDefBWD[i])


            self.cantDef[:] = np.where(np.abs(cantDefFWD) < np.abs(cantDefBWD), cantDefFWD, cantDefBWD)

            # Stage 3 - Ensure continuous D and I (exception of delta I for connecting lines and curves but not spirals)
            for i in range(1, len(self.stationsNew)):
                if self.stationsNew[i] == self.stationsNew[i-1]:
                    minD = min(np.abs(self.cantNew[i-1]), np.abs(self.cantNew[i]))
                    signD = np.sign(self.cantNew[i]) if self.cantNew[i] != 0 else np.sign(self.cantNew[i-1])
                    self.cantNew[i] = signD * minD
                    self.cantNew[i-1] = signD * minD
             
                    if self.geometryType[i] == "Spiral" or self.geometryType[i-1] == "Spiral":
                        minI = min(np.abs(self.cantDef[i-1]), np.abs(self.cantDef[i]))
                        signI = np.sign(self.cantDef[i]) if self.cantDef[i] != 0 else np.sign(self.cantDef[i-1])
                        self.cantDef[i] = signI * minI
                        self.cantDef[i-1] = signI * minI

            # Stage 4 - Calculate speed in respective section
            for i in range(0, len(self.cantNew), 2):
                v1 = self.calculateSpeed(np.abs(self.cantNew[i]), np.abs(self.cantDef[i]), np.abs(self.kappa[i]), 5, self.vInit[i])
                v2 = self.calculateSpeed(np.abs(self.cantNew[i+1]), np.abs(self.cantDef[i+1]), np.abs(self.kappa[i+1]), 5, self.vInit[i+1])

                minVmax = min(v1, v2)

                self.vMax[i] = min(self.vInit[i], minVmax)
                self.vMax[i+1] = min(self.vInit[i+1], minVmax)

                if self.vMax[i] < self.vInit[i] or self.vMax[i+1] < self.vInit[i+1]:
                    if self.vInit[i] > 20:
                        self.vInit[i] -= 5
                        self.vInit[i+1] -= 5
                        convergenceReached = False

                self.vMax[i] = min(self.vMax[i], self.vInit[i])

        # Debugging print
        for i in range(0,len(self.cantNew)):
            print(self.stationsNew[i], self.cantNew[i], self.cantDef[i], self.vMax[i], self.vInit[i], self.geometryType[i], self.kappa[i])
        print(self.getNormLimit("nLin", 120, approach))
        print(f"Convergation reached after {iterationN} iterations.")

        for i in range(0, len(self.cantNew)):        
            self.cantNew[i] = np.floor(np.abs(self.cantNew[i]))
            self.cantDef[i] = np.ceil(np.abs(self.cantDef[i]))

        for i in range(0, len(self.vMax)):
            self.speed100[i] = self.vMax[i]
            self.speed130[i] = self.vMax[i]
            self.speed150[i] = self.vMax[i]
            self.speedK[i] = self.vMax[i]

    def calculateCantN(self, v, n, length):
        if n[0] == 0 or v == 0:
            return 0
        gradient = max(n[0]*v, n[1])
        return length*1000/(gradient)

    def calculateCantDefNi(self, v, nI, length):
        if nI == 0 or v == 0:
            return 0
        return length*1000/(nI[0]*v)

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
        return (11.8 * (v**2) * kappa) - I

    def calculateCantDef(self, v, D, kappa):
        return (11.8 * (v**2) * kappa) - D

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



    