import numpy as np
from pyclothoids import Clothoid

class GeometryCalculator:
    def __init__(self, dataStorage):
        self.data = dataStorage

    def runCalculationLoopI(self):
        self.setLoopsData()
        profiles = ["I100", "I130", "I150", "K"]

        # Calculation loop
        for profile in profiles:
            self.resetInitialSpeed()
            self.calculationLoopI(self.designApproach, profile, currentCant=True)
            
        self.sumCantDef()

    def runCalculationLoop(self):
        self.setLoopsData()
        profiles = ["I100", "I130", "I150", "K"]

        # Calculation loop
        self.resetInitialSpeed()
        self.calculationLoop(self.designApproach, self.defaultProfile)

        for profile in profiles:
            self.resetInitialSpeed()
            self.calculationLoopI(self.designApproach, profile, currentCant=False)

        self.sumCantDef()

    def setLoopsData(self):
        defaultVal = self.data.get("settingsData",{})
        self.designApproach = self.data.get("settingsData",{}).get("designApproach","standard")
        self.defaultProfile = self.data.get("defaultProfile","I150")
        lxml = self.data.get("LandXML",{})

        lxml["stationCantPossible"] = lxml.get("stationHorizontal",[])

        self.vInit = np.full(len(lxml["stationCantPossible"]),defaultVal.get("vInit",[120])[0])
        self.vMax = np.full(len(lxml["stationCantPossible"]),defaultVal.get("vInit",[0])[0])
        maxD_val = defaultVal.get("maxD", 150.0)
        self.maxD = float(maxD_val[0]) if isinstance(maxD_val, list) else float(maxD_val)
        self.isGeometryMaxDDisabled = bool(defaultVal.get("disableGeometryMaxD", False))
        self.isInflectionBalancingEnabled = bool(defaultVal.get("balanceInflectionCants", False))

        self.geometryType = np.array(lxml.get("geometryType",[]))

        self.spiralMask = np.where(self.geometryType == "Spiral")[0]
        self.curveMask = np.where(self.geometryType == "Curve")[0]
        self.lineMask = np.where(self.geometryType == "Line")[0]

        lenStationPos = len(lxml["stationCantPossible"])

        self.kappa = lxml.get("curvature",np.zeros(lenStationPos))
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

        # Time derivative arrays
        lxml["dDdt100"] = np.zeros(lenStationPos)
        lxml["dDdt130"] = np.zeros(lenStationPos)
        lxml["dDdt150"] = np.zeros(lenStationPos)
        lxml["dDdtK"] = np.zeros(lenStationPos)

        lxml["dIdt100"] = np.zeros(lenStationPos)
        lxml["dIdt130"] = np.zeros(lenStationPos)
        lxml["dIdt150"] = np.zeros(lenStationPos)
        lxml["dIdtK"] = np.zeros(lenStationPos)

        self.dDdt100 = lxml["dDdt100"]
        self.dDdt130 = lxml["dDdt130"]
        self.dDdt150 = lxml["dDdt150"]
        self.dDdtK = lxml["dDdtK"]

        self.dIdt100 = lxml["dIdt100"]
        self.dIdt130 = lxml["dIdt130"]
        self.dIdt150 = lxml["dIdt150"]
        self.dIdtK = lxml["dIdtK"]

    def sumCantDef(self):
        lxml = self.data.get("LandXML",{})
        lxml["cantDef100"] = lxml["cantPossible"] + lxml["cDef100"]
        lxml["cantDef130"] = lxml["cantPossible"] + lxml["cDef130"]
        lxml["cantDef150"] = lxml["cantPossible"] + lxml["cDef150"]
        lxml["cantDefK"] = lxml["cantPossible"] + lxml["cDefK"]

    # Opt-in inflection balancer, enforces D1/D2 = L1/L2 on opposite-sign spiral pairs and zeroes cant at the crossing
    def balanceInflectionCants(self):
        for i in range(1, len(self.stationsNew)):
            if self.stationsNew[i] != self.stationsNew[i-1]:
                continue
            if self.geometryType[i-1] != "Spiral" or self.geometryType[i] != "Spiral":
                continue
            if self.curvSign[i-1] == 0 or self.curvSign[i] == 0 or self.curvSign[i-1] == self.curvSign[i]:
                continue
            if i-2 < 0 or i+1 >= len(self.stationsNew):
                continue

            L1 = abs(self.stationsNew[i-1] - self.stationsNew[i-2])
            L2 = abs(self.stationsNew[i+1] - self.stationsNew[i])
            if L1 <= 0 or L2 <= 0:
                continue

            D1 = np.abs(self.cantNew[i-2])
            D2 = np.abs(self.cantNew[i+1])

            # Always reduce the steeper ramp so no other limit already satisfied can be violated
            if D1 * L2 > D2 * L1:
                D1 = D2 * L1 / L2
            else:
                D2 = D1 * L2 / L1

            signD1 = np.sign(self.cantNew[i-2]) if self.cantNew[i-2] != 0 else self.curvSign[i-2]
            signD2 = np.sign(self.cantNew[i+1]) if self.cantNew[i+1] != 0 else self.curvSign[i+1]

            self.cantNew[i-2] = signD1 * D1
            self.cantNew[i+1] = signD2 * D2
            self.cantNew[i-1] = 0
            self.cantNew[i] = 0

            # Propagate the balanced cant into an adjacent circular arc sharing the same junction
            if i-3 >= 0 and self.stationsNew[i-2] == self.stationsNew[i-3]:
                self.cantNew[i-3] = self.cantNew[i-2]
                if i-4 >= 0 and self.geometryType[i-3] == "Curve":
                    self.cantNew[i-4] = self.cantNew[i-3]

            if i+2 < len(self.stationsNew) and self.stationsNew[i+1] == self.stationsNew[i+2]:
                self.cantNew[i+2] = self.cantNew[i+1]
                if i+3 < len(self.stationsNew) and self.geometryType[i+2] == "Curve":
                    self.cantNew[i+3] = self.cantNew[i+2]

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
            self.dDdt = self.dDdt100
            self.dIdt = self.dIdt100
            profileI = 100
        elif profile == "I130":
            self.cantDef = self.cDef130
            self.dDdt = self.dDdt130
            self.dIdt = self.dIdt130
            profileI = 130
        elif profile == "I150":
            self.cantDef = self.cDef150
            self.dDdt = self.dDdt150
            self.dIdt = self.dIdt150
            profileI = 150
        elif profile == "K":
            self.cantDef = self.cDefK
            self.dDdt = self.dDdtK
            self.dIdt = self.dIdtK
            profileI = 240
        else:
            self.cantDef = self.cDef100
            self.dDdt = self.dDdt100
            self.dIdt = self.dIdt100
            profileI = 100

        # Iterative solver
        convergenceReached = False
        iterationN = 0
        iterationStep = float(self.data.get("settingsData", {}).get("iterationStep", 5.0))
        maxIterations = int(self.data.get("settingsData", {}).get("maxIterations", 50))

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
                        cantBWD[i] = max(0, cantBWD[i])
                    elif self.curvSign[i] < 0:
                        cantBWD[i] = min(0, cantBWD[i])

            self.cantNew[:] = np.where(np.abs(cantFWD) < np.abs(cantBWD), cantFWD, cantBWD)

            # Stage 2 - based on Vinit and D in each element, calculate I
            cantDefTarget = np.zeros_like(self.cantDef)

            for i in range(0, len(self.cantDef)):
                if self.geometryType[i] == "Line":
                    cantDefTarget[i] = 0
                else:
                    signKappa = np.sign(self.kappa[i]) if self.kappa[i] != 0 else 1
                    maxI = min(self.getNormLimit("I", self.vInit[i], approach)[0], profileI)
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
                    dI_nI = self.calculateCantDefNi(self.vInit[i], self.getNormLimit("nILin", self.vInit[i], approach), length)
                    dI_delta = self.getNormLimit("dI", self.vInit[i], approach)[0]
                    dI = max(dI_nI, dI_delta)
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
                    dI_nI = self.calculateCantDefNi(self.vInit[i], self.getNormLimit("nILin", self.vInit[i], approach), length)
                    dI_delta = self.getNormLimit("dI", self.vInit[i], approach)[0]
                    dI = max(dI_nI, dI_delta)
                if self.geometryType[i] == "Line":
                    cantDefBWD[i] = 0
                else:
                    cantDefBWD[i] = np.clip(
                        cantDefBWD[i],
                        cantDefBWD[i+1] - dI,
                        cantDefBWD[i+1] + dI
                    )

                    if self.curvSign[i] > 0:
                        cantDefBWD[i] = max(0, cantDefBWD[i])
                    elif self.curvSign[i] < 0:
                        cantDefBWD[i] = min(0, cantDefBWD[i])

            self.cantDef[:] = np.where(np.abs(cantDefFWD) < np.abs(cantDefBWD), cantDefFWD, cantDefBWD)

            # Stage 3 - Ensure continuous D
            for i in range(1, len(self.stationsNew)):
                if self.stationsNew[i] == self.stationsNew[i-1]:
                    minD = min(np.abs(self.cantNew[i-1]), np.abs(self.cantNew[i]))
                    signD = np.sign(self.cantNew[i]) if self.cantNew[i] != 0 else np.sign(self.cantNew[i-1])
                    self.cantNew[i] = signD * minD
                    self.cantNew[i-1] = signD * minD

            # Opt-in inflection balancer, runs every iteration since cantNew is rebuilt above each pass
            if self.isInflectionBalancingEnabled:
                self.balanceInflectionCants()

            # # Stage 3.5 - Inflection points D1/D2 = L1/L2
            # for i in range(1, len(self.stationsNew)):
            #     if self.stationsNew[i] == self.stationsNew[i-1]:
            #         if self.geometryType[i-1] == "Spiral" and self.geometryType[i] == "Spiral":
            #             if self.curvSign[i-1] != self.curvSign[i] and self.curvSign[i-1] != 0 and self.curvSign[i] != 0:
            #                 L1 = abs(self.stationsNew[i-1] - self.stationsNew[i-2])
            #                 L2 = abs(self.stationsNew[i+1] - self.stationsNew[i])
            #                 if L1 > 0 and L2 > 0:
            #                     D1 = np.abs(self.cantNew[i-2])
            #                     D2 = np.abs(self.cantNew[i+1])
                                
            #                     # Ponížení převýšení pro dodržení poměru (vždy se přizpůsobí strmější rampa)
            #                     if D1 * L2 > D2 * L1:
            #                         D1 = D2 * L1 / L2
            #                     else:
            #                         D2 = D1 * L2 / L1
                                
            #                     signD1 = np.sign(self.cantNew[i-2]) if self.cantNew[i-2] != 0 else self.curvSign[i-2]
            #                     signD2 = np.sign(self.cantNew[i+1]) if self.cantNew[i+1] != 0 else self.curvSign[i+1]
                                
            #                     self.cantNew[i-2] = signD1 * D1
            #                     self.cantNew[i+1] = signD2 * D2
            #                     self.cantNew[i-1] = 0
            #                     self.cantNew[i] = 0
                                
            #                     # Okamžité propsání upraveného převýšení do přilehlých kružnicových oblouků
            #                     if i-3 >= 0 and self.stationsNew[i-2] == self.stationsNew[i-3]:
            #                         self.cantNew[i-3] = self.cantNew[i-2]
            #                         if self.geometryType[i-3] == "Curve":
            #                             self.cantNew[i-4] = self.cantNew[i-3]
                                        
            #                     if i+2 < len(self.stationsNew) and self.stationsNew[i+1] == self.stationsNew[i+2]:
            #                         self.cantNew[i+2] = self.cantNew[i+1]
            #                         if self.geometryType[i+2] == "Curve":
            #                             self.cantNew[i+3] = self.cantNew[i+2]

            # cantDefSpeed — speed limit from I change in spiral
            # Higher of: nI-based speed  OR  virtual-deltaI-based speed
            # Uses physical I (computed from geometry) to avoid circular dependency with Stage 2 clipping
            cantDefSpeed = np.full(len(self.stationsNew), np.inf)
            for i in range(1, len(self.stationsNew)):
                length = (self.stationsNew[i] - self.stationsNew[i-1]) * 1000
                if length > 0 and self.geometryType[i] == "Spiral":
                    # Physical I at each end of the spiral segment (from geometry, not designed cantDef)
                    I_i    = self.calculateCantDef(self.vInit[i], abs(self.cantNew[i]),   abs(self.kappa[i]))
                    I_prev = self.calculateCantDef(self.vInit[i], abs(self.cantNew[i-1]), abs(self.kappa[i-1]))
                    dI_actual  = abs(I_i - I_prev)
                    dKappa     = abs(self.kappa[i] - self.kappa[i-1])
                    nI_lim     = self.getNormLimit("nILin", self.vInit[i], approach)
                    v_nI       = self.calculateCantDefSpeedNI(length, nI_lim[0], dI_actual)
                    deltaI_lim = self.getNormLimit("dI", self.vInit[i], approach)[0]
                    # Signed cant credit: +|dD| when |D| and |κ| change in the same direction
                    # (cant change reduces deltaI), −|dD| when opposite (cant change increases deltaI).
                    _kappa_dir = abs(self.kappa[i]) - abs(self.kappa[i-1])
                    _D_change  = abs(self.cantNew[i]) - abs(self.cantNew[i-1])
                    dD_credit  = _D_change * (np.sign(_kappa_dir) if _kappa_dir != 0.0 else 0.0)
                    v_deltaI   = self.calculateCantDefSpeedDeltaI(dD_credit, deltaI_lim, dKappa)
                    # More lenient of the two; fall back gracefully when one is not applicable (inf)
                    if np.isinf(v_nI) and np.isinf(v_deltaI):
                        cantDefSpeed[i] = np.inf
                    elif np.isinf(v_deltaI):
                        cantDefSpeed[i] = v_nI
                    elif np.isinf(v_nI):
                        cantDefSpeed[i] = v_deltaI
                    else:
                        cantDefSpeed[i] = max(v_nI, v_deltaI)

            # boundaryDeltaISpeed — speed limit from sudden deltaI at L=0 curve-curve boundaries
            # Physical deltaI = 11.8·v²·|Δκ|; D cancels because Stage 3 enforces D-continuity
            boundaryDeltaISpeed = np.full(len(self.stationsNew), np.inf)
            for i in range(1, len(self.stationsNew)):
                length = (self.stationsNew[i] - self.stationsNew[i-1]) * 1000
                if length <= 0 and self.geometryType[i] == "Curve" and self.geometryType[i-1] == "Curve":
                    dKappa = abs(self.kappa[i] - self.kappa[i-1])
                    if dKappa > 1e-10:
                        v_eval     = min(self.vInit[i], self.vInit[i-1])
                        deltaI_lim = self.getNormLimit("dI", v_eval, approach)[0]
                        v_lim      = self.calculateBoundarySpeed(deltaI_lim, dKappa)
                        boundaryDeltaISpeed[i-1] = min(boundaryDeltaISpeed[i-1], v_lim)
                        boundaryDeltaISpeed[i]   = min(boundaryDeltaISpeed[i],   v_lim)

            # Stage 4 - Calculate speed in respective section
            for i in range(0, len(self.cantNew), 2):
                v1 = self.calculateSpeed(np.abs(self.cantNew[i]), np.abs(self.cantDef[i]), np.abs(self.kappa[i]), iterationStep, self.vInit[i])
                v2 = self.calculateSpeed(np.abs(self.cantNew[i+1]), np.abs(self.cantDef[i+1]), np.abs(self.kappa[i+1]), iterationStep, self.vInit[i+1])

                minVmax              = min(v1, v2)
                minCantDefSpeed      = min(cantDefSpeed[i], cantDefSpeed[i+1])
                minBoundaryDeltaI    = min(boundaryDeltaISpeed[i], boundaryDeltaISpeed[i+1])

                self.vMax[i] = min(self.vInit[i], minVmax, minCantDefSpeed, minBoundaryDeltaI)
                self.vMax[i+1] = min(self.vInit[i+1], minVmax, minCantDefSpeed, minBoundaryDeltaI)

                if self.vMax[i] < self.vInit[i] or self.vMax[i+1] < self.vInit[i+1]:
                    if self.vInit[i] > iterationStep:
                        self.vInit[i] -= iterationStep
                        self.vInit[i+1] -= iterationStep
                        convergenceReached = False

        # # Debugging print
        # for i in range(0,len(self.cantNew)):
        #     print(self.stationsNew[i], self.cantNew[i], self.cantDef[i], self.vMax[i], self.vInit[i], self.geometryType[i], self.kappa[i])
        # print(self.getNormLimit("nLin", 120, approach))
        # print(f"Convergation reached after {iterationN} iterations.")

        # Debugging print - cantDefSpeed (calculationLoop)
        # for i in range(len(self.stationsNew)):
        #     if cantDefSpeed[i] < np.inf:
        #         print(f"  cantDefSpeed[{i}] sta={self.stationsNew[i]:.3f} {self.geometryType[i]}: {cantDefSpeed[i]:.1f} km/h")

        for i in range(0, len(self.cantNew)):
            signD = np.sign(self.cantNew[i]) if self.cantNew[i] != 0 else 1.0
            self.cantNew[i] = signD * np.floor(np.abs(self.cantNew[i]))
            
            temp_I = np.ceil(np.abs(self.calculateCantDef(self.vMax[i], np.abs(self.cantNew[i]), np.abs(self.kappa[i]))))

            # Finální kontrola matematického vztahu - V = sqrt((D+I)*R/11.8)
            if np.abs(self.kappa[i]) > 0:
                v_check = np.sqrt((np.abs(self.cantNew[i]) + temp_I) / (11.8 * np.abs(self.kappa[i])))
                self.vMax[i] = min(self.vMax[i], v_check)
                
            # Zaokrouhlení výsledné rychlosti na krok iterace dolů
            self.vMax[i] = np.floor(self.vMax[i] / iterationStep) * iterationStep

            # Skutečný přepočet nedostatku převýšení pro finální rychlost
            signKappa = np.sign(self.kappa[i]) if self.kappa[i] != 0 else 1.0
            self.cantDef[i] = signKappa * np.ceil(np.abs(self.calculateCantDef(self.vMax[i], np.abs(self.cantNew[i]), np.abs(self.kappa[i]))))

        self.determineLimitReasons(profile, approach, profileI)

        for i in range(1, len(self.stationsNew), 2):
            length = (self.stationsNew[i] - self.stationsNew[i-1]) * 1000
            if length > 0:
                v_mps = self.vMax[i] / 3.6
                if v_mps > 0:
                    dt = length / v_mps
                    dD_dt = abs(self.cantNew[i] - self.cantNew[i-1]) / dt
                    dI_dt = abs(self.cantDef[i] - self.cantDef[i-1]) / dt
                else:
                    dD_dt = 0
                    dI_dt = 0
            else:
                dD_dt = 0
                dI_dt = 0
                
            self.dDdt[i-1] = dD_dt
            self.dDdt[i] = dD_dt
            self.dIdt[i-1] = dI_dt
            self.dIdt[i] = dI_dt

        if profile == "I100":
            self.speed100[:] = self.vMax
        elif profile == "I130":
            self.speed130[:] = self.vMax
        elif profile == "I150":
            self.speed150[:] = self.vMax
        elif profile == "K":
            self.speedK[:] = self.vMax
        else:
            self.speed100[:] = self.vMax       

    def calculationLoopI(self, approach, profile, currentCant = True):
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
            self.dDdt = self.dDdt100
            self.dIdt = self.dIdt100
            profileI = 100
        elif profile == "I130":
            self.cantDef = self.cDef130
            self.dDdt = self.dDdt130
            self.dIdt = self.dIdt130
            profileI = 130
        elif profile == "I150":
            self.cantDef = self.cDef150
            self.dDdt = self.dDdt150
            self.dIdt = self.dIdt150
            profileI = 150
        elif profile == "K":
            self.cantDef = self.cDefK
            self.dDdt = self.dDdtK
            self.dIdt = self.dIdtK
            profileI = 240
        else:
            self.cantDef = self.cDef100
            self.dDdt = self.dDdt100
            self.dIdt = self.dIdt100
            profileI = 100

        # Iterative solver
        convergenceReached = False
        iterationN = 0
        iterationStep = float(self.data.get("settingsData", {}).get("iterationStep", 5.0))
        maxIterations = int(self.data.get("settingsData", {}).get("maxIterations", 50))

        while not convergenceReached and iterationN < maxIterations:
            convergenceReached = True
            iterationN += 1

            # Stage 1 - based on cant provided in each element, calculate D in stationCantPossible and maximum speed for respective dD
            if currentCant:
                self.cantNew[:] = np.interp(self.stationsNew, self.stationsCant, self.cant)
                # Opt-in inflection balancer, reapplied every iteration since interp resets cantNew above
                if self.isInflectionBalancingEnabled:
                    self.balanceInflectionCants()
            cantSpeed = np.full_like(self.stationsNew, np.inf)

            for i in range(1, len(self.cantNew)):
                length = (self.stationsNew[i] - self.stationsNew[i-1])*1000
                dD = abs(self.cantNew[i] - self.cantNew[i-1])
                cantSpeed[i] = self.calculateSpeedCant(length, dD, self.getNormLimit("nLin", self.vInit[i], approach))

            cantSpeed[self.lineMask] = self.vInit[self.lineMask]
            cantSpeed[self.curveMask] = self.vInit[self.curveMask]

            # Stage 2 - based on Vinit and D in each element, calculate I
            cantDefTarget = np.zeros_like(self.cantDef)

            for i in range(0, len(self.cantDef)):
                if self.geometryType[i] == "Line":
                    cantDefTarget[i] = 0
                else:
                    signKappa = np.sign(self.kappa[i]) if self.kappa[i] != 0 else 1
                    maxI = min(self.getNormLimit("I", self.vInit[i], approach)[0], profileI)
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
                    dI_nI = self.calculateCantDefNi(self.vInit[i], self.getNormLimit("nILin", self.vInit[i], approach), length)
                    dI_delta = self.getNormLimit("dI", self.vInit[i], approach)[0]
                    dI = max(dI_nI, dI_delta)
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
                    dI_nI = self.calculateCantDefNi(self.vInit[i], self.getNormLimit("nILin", self.vInit[i], approach), length)
                    dI_delta = self.getNormLimit("dI", self.vInit[i], approach)[0]
                    dI = max(dI_nI, dI_delta)
                if self.geometryType[i] == "Line":
                    cantDefBWD[i] = 0
                else:
                    cantDefBWD[i] = np.clip(
                        cantDefBWD[i],
                        cantDefBWD[i+1] - dI,
                        cantDefBWD[i+1] + dI
                    )

                    if self.curvSign[i] > 0:
                        cantDefBWD[i] = max(0, cantDefBWD[i])
                    elif self.curvSign[i] < 0:
                        cantDefBWD[i] = min(0, cantDefBWD[i])

            self.cantDef[:] = np.where(np.abs(cantDefFWD) < np.abs(cantDefBWD), cantDefFWD, cantDefBWD)

            # cantDefSpeed — speed limit from I change in spiral
            # Higher of: nI-based speed  OR  virtual-deltaI-based speed
            # Uses physical I (computed from geometry) to avoid circular dependency with Stage 2 clipping
            cantDefSpeed = np.full(len(self.stationsNew), np.inf)
            for i in range(1, len(self.stationsNew)):
                length = (self.stationsNew[i] - self.stationsNew[i-1]) * 1000
                if length > 0 and self.geometryType[i] == "Spiral":
                    # Physical I at each end of the spiral segment (from geometry, not designed cantDef)
                    I_i    = self.calculateCantDef(self.vInit[i], abs(self.cantNew[i]),   abs(self.kappa[i]))
                    I_prev = self.calculateCantDef(self.vInit[i], abs(self.cantNew[i-1]), abs(self.kappa[i-1]))
                    dI_actual  = abs(I_i - I_prev)
                    dKappa     = abs(self.kappa[i] - self.kappa[i-1])
                    nI_lim     = self.getNormLimit("nILin", self.vInit[i], approach)
                    v_nI       = self.calculateCantDefSpeedNI(length, nI_lim[0], dI_actual)
                    deltaI_lim = self.getNormLimit("dI", self.vInit[i], approach)[0]
                    # Signed cant credit: +|dD| when |D| and |κ| change in the same direction
                    # (cant change reduces deltaI), −|dD| when opposite (cant change increases deltaI).
                    _kappa_dir = abs(self.kappa[i]) - abs(self.kappa[i-1])
                    _D_change  = abs(self.cantNew[i]) - abs(self.cantNew[i-1])
                    dD_credit  = _D_change * (np.sign(_kappa_dir) if _kappa_dir != 0.0 else 0.0)
                    v_deltaI   = self.calculateCantDefSpeedDeltaI(dD_credit, deltaI_lim, dKappa)
                    # More lenient of the two; fall back gracefully when one is not applicable (inf)
                    if np.isinf(v_nI) and np.isinf(v_deltaI):
                        cantDefSpeed[i] = np.inf
                    elif np.isinf(v_deltaI):
                        cantDefSpeed[i] = v_nI
                    elif np.isinf(v_nI):
                        cantDefSpeed[i] = v_deltaI
                    else:
                        cantDefSpeed[i] = max(v_nI, v_deltaI)

            # boundaryDeltaISpeed — speed limit from sudden deltaI at L=0 curve-curve boundaries
            # Physical deltaI = 11.8·v²·|Δκ|; D cancels because Stage 3 enforces D-continuity
            boundaryDeltaISpeed = np.full(len(self.stationsNew), np.inf)
            for i in range(1, len(self.stationsNew)):
                length = (self.stationsNew[i] - self.stationsNew[i-1]) * 1000
                if length <= 0 and self.geometryType[i] == "Curve" and self.geometryType[i-1] == "Curve":
                    dKappa = abs(self.kappa[i] - self.kappa[i-1])
                    if dKappa > 1e-10:
                        v_eval     = min(self.vInit[i], self.vInit[i-1])
                        deltaI_lim = self.getNormLimit("dI", v_eval, approach)[0]
                        v_lim      = self.calculateBoundarySpeed(deltaI_lim, dKappa)
                        boundaryDeltaISpeed[i-1] = min(boundaryDeltaISpeed[i-1], v_lim)
                        boundaryDeltaISpeed[i]   = min(boundaryDeltaISpeed[i],   v_lim)

            # Stage 4 - Calculate speed in respective section
            for i in range(0, len(self.cantNew), 2):
                v1 = self.calculateSpeed(np.abs(self.cantNew[i]), np.abs(self.cantDef[i]), np.abs(self.kappa[i]), iterationStep, self.vInit[i])
                v2 = self.calculateSpeed(np.abs(self.cantNew[i+1]), np.abs(self.cantDef[i+1]), np.abs(self.kappa[i+1]), iterationStep, self.vInit[i+1])

                minVmax              = min(v1, v2)
                minCantSpeed         = min(cantSpeed[i], cantSpeed[i+1])
                minCantDefSpeed      = min(cantDefSpeed[i], cantDefSpeed[i+1])
                minBoundaryDeltaI    = min(boundaryDeltaISpeed[i], boundaryDeltaISpeed[i+1])

                self.vMax[i] = min(self.vInit[i], minVmax, minCantSpeed, minCantDefSpeed, minBoundaryDeltaI)
                self.vMax[i+1] = min(self.vInit[i+1], minVmax, minCantSpeed, minCantDefSpeed, minBoundaryDeltaI)

                if self.vMax[i] < self.vInit[i] or self.vMax[i+1] < self.vInit[i+1]:
                    if self.vInit[i] > iterationStep:
                        self.vInit[i] -= iterationStep
                        self.vInit[i+1] -= iterationStep
                        convergenceReached = False

        # # Debugging print
        # for i in range(0,len(self.cantNew)):
        #     print(self.stationsNew[i], self.cantNew[i], self.cantDef[i], self.vMax[i], self.vInit[i], self.geometryType[i], self.kappa[i])
        # print(self.getNormLimit("nLin", 120, approach))

        # Debugging print - cantDefSpeed (calculationLoopI)
        # for i in range(len(self.stationsNew)):
        #     if cantDefSpeed[i] < np.inf:
        #         print(f"  cantDefSpeed[{i}] sta={self.stationsNew[i]:.3f} {self.geometryType[i]}: {cantDefSpeed[i]:.1f} km/h")

        for i in range(0, len(self.cantNew)):
            signD = np.sign(self.cantNew[i]) if self.cantNew[i] != 0 else 1.0
            self.cantNew[i] = signD * np.floor(np.abs(self.cantNew[i]))
            
            temp_I = np.ceil(np.abs(self.calculateCantDef(self.vMax[i], np.abs(self.cantNew[i]), np.abs(self.kappa[i]))))

            # Finální kontrola matematického vztahu - V = sqrt((D+I)*R/11.8)
            if np.abs(self.kappa[i]) > 0:
                v_check = np.sqrt((np.abs(self.cantNew[i]) + temp_I) / (11.8 * np.abs(self.kappa[i])))
                self.vMax[i] = min(self.vMax[i], v_check)
                
            # Zaokrouhlení výsledné rychlosti na krok iterace dolů
            self.vMax[i] = np.floor(self.vMax[i] / iterationStep) * iterationStep

            # Skutečný přepočet nedostatku převýšení pro finální rychlost
            signKappa = np.sign(self.kappa[i]) if self.kappa[i] != 0 else 1.0
            self.cantDef[i] = signKappa * np.ceil(np.abs(self.calculateCantDef(self.vMax[i], np.abs(self.cantNew[i]), np.abs(self.kappa[i]))))

        self.determineLimitReasons(profile, approach, profileI)

        for i in range(1, len(self.stationsNew), 2):
            length = (self.stationsNew[i] - self.stationsNew[i-1]) * 1000
            if length > 0:
                v_mps = self.vMax[i] / 3.6
                if v_mps > 0:
                    dt = length / v_mps
                    dD_dt = abs(self.cantNew[i] - self.cantNew[i-1]) / dt
                    dI_dt = abs(self.cantDef[i] - self.cantDef[i-1]) / dt
                else:
                    dD_dt = 0
                    dI_dt = 0
            else:
                dD_dt = 0
                dI_dt = 0
                
            self.dDdt[i-1] = dD_dt
            self.dDdt[i] = dD_dt
            self.dIdt[i-1] = dI_dt
            self.dIdt[i] = dI_dt

        if profile == "I100":
            self.speed100[:] = self.vMax
        elif profile == "I130":
            self.speed130[:] = self.vMax
        elif profile == "I150":
            self.speed150[:] = self.vMax
        elif profile == "K":
            self.speedK[:] = self.vMax
        else:
            self.speed100[:] = self.vMax 

    def determineLimitReasons(self, profile, approach, profileI):
        limitReachedD = np.zeros(len(self.stationsNew), dtype=bool)
        limitReachedI = np.zeros(len(self.stationsNew), dtype=bool)
        
        util_D = np.zeros(len(self.stationsNew))
        util_I = np.zeros(len(self.stationsNew))

        for i in range(len(self.stationsNew)):
            if self.geometryType[i] == "Line":
                continue

            v_check = self.vMax[i]

            I_val = np.abs(self.cantDef[i])
            D_val = np.abs(self.cantNew[i])
            kappa_val = np.abs(self.kappa[i])

            I_lim = min(self.getNormLimit("I", v_check, approach)[0], profileI)
            D_lim = min(self.maxD, self.geometryMaxD(kappa_val))

            util_I[i] = I_val / I_lim if I_lim > 0 else 0
            util_D[i] = D_val / D_lim if D_lim > 0 else 0
            
            if util_D[i] >= 0.99: limitReachedD[i] = True
            if util_I[i] >= 0.99: limitReachedI[i] = True

        self.data["LandXML"][f"util_D_{profile}"] = util_D
        self.data["LandXML"][f"util_I_{profile}"] = util_I
        self.data["LandXML"][f"limitReachedD_{profile}"] = limitReachedD
        self.data["LandXML"][f"limitReachedI_{profile}"] = limitReachedI

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

    def calculateBoundarySpeed(self, deltaI_lim, dKappa):
        """v_lim = sqrt(deltaI_lim / (11.8·dKappa)) at an L=0 curvature boundary.
        D cancels because Stage 3 enforces cant continuity at L=0 junctions."""
        if dKappa <= 1e-10 or deltaI_lim <= 0:
            return np.inf
        return np.sqrt(deltaI_lim / (11.8 * dKappa))

    def calculateCantDefSpeedNI(self, length, nI_lim, dI_actual):
        """v_lim = L*1000 / (nI_lim * dI_actual) [km/h] from the nI criterion on a spiral."""
        if nI_lim <= 0 or dI_actual <= 0:
            return np.inf
        return length * 1000 / (nI_lim * dI_actual)

    def calculateCantDefSpeedDeltaI(self, dD_credit, deltaI_lim, dKappa):
        """v_lim = sqrt((deltaI_lim + dD_credit) / (11.8·dKappa)) from the virtual-ΔI criterion.
        dD_credit is signed: +|dD| when D and κ change in the same direction (credit),
        −|dD| when opposite directions (penalty). Returns inf if dKappa≈0, 0 if limit≤0."""
        if dKappa <= 1e-10:
            return np.inf
        effective_lim = deltaI_lim + dD_credit
        if effective_lim <= 0:
            return 0.0  # no speed can satisfy this constraint
        return np.sqrt(effective_lim / (11.8 * dKappa))

    def calculateSpeedCant(self, length, dD, nLin):
        if nLin[0] == 0:
            return 0
        if dD == 0:
            return np.inf

        return length*1000/(dD*nLin[0])

    def geometryMaxD(self, kappa):
        if kappa == 0:
            return 0
        if getattr(self, "isGeometryMaxDDisabled", False):
            return np.inf
        radius = 1/np.abs(kappa)
        maxD = np.floor((radius - 50)/1.5)
        return maxD
        
    def resetInitialSpeed(self):
        defaultVal = self.data.get("settingsData",{})
        lxml = self.data.get("LandXML",{})
        lenStationPos = len(lxml.get("stationHorizontal",[]))

        self.vInit = np.full(lenStationPos,defaultVal.get("vInit",[120])[0])
        self.vMax = np.full(lenStationPos, defaultVal.get("vInit", [0])[0])

    def getNormLimit(self, parameter, speedLimit, approach): 
        normLimits = self.data.get("settingsData", {}).get(parameter,[])

        if isinstance(approach, dict):
            current_approach = approach.get(parameter, "standard")
        else:
            current_approach = approach

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

        col = approachDict.get(current_approach, 3)

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


# --- Alignment optimization ---

OPTIMIZATION_MODE_NONE = "none"
OPTIMIZATION_MODE_SHIFT_AND_EXTEND = "shiftAndExtend"
OPTIMIZATION_MODE_EXTEND_SPIRALS = "extendSpirals"
OPTIMIZATION_MODE_SHIFT_ARC = "shiftArc"
OPTIMIZATION_MODE_INVERTED_SHIFT = "invertedShift"

OPTIMIZATION_MODES = (OPTIMIZATION_MODE_SHIFT_AND_EXTEND, OPTIMIZATION_MODE_EXTEND_SPIRALS, OPTIMIZATION_MODE_SHIFT_ARC, OPTIMIZATION_MODE_INVERTED_SHIFT)
# The only modes offered for an L-C-L group, which has no spirals to extend
LCL_OPTIMIZATION_MODES = (OPTIMIZATION_MODE_SHIFT_AND_EXTEND, OPTIMIZATION_MODE_SHIFT_ARC)

# Per-type parser arrays the optimizer needs, appended to LEAN_LANDXML_KEYS for batch runs
OPTIMIZER_INPUT_KEYS = (
    "lineStartX", "lineStartY", "lineEndX", "lineEndY", "lineStationStart",
    "spiralStartX", "spiralStartY", "spiralPIX", "spiralPIY", "spiralEndX", "spiralEndY",
    "spiralStationStart", "spiralLength", "spiralRadiusStart", "spiralRadiusEnd",
    "spiralRot", "spiralType",
    "curveStartX", "curveStartY", "curveEndX", "curveEndY", "curveCenterX", "curveCenterY",
    "curveStationStart", "curveRot", "curveRadius"
)

# Spiral shorter than this is treated as geometrically degenerate, not a real clothoid
MIN_CLOTHOID_LENGTH_M = 0.5

# Points sampled per element when comparing the candidate axis against the baseline axis
SLEW_SAMPLE_COUNT = 50

# Bisection stops once the search bracket narrows below this, in meters
BISECTION_TOLERANCE_M = 1e-4

BISECTION_MAX_ITER = 60


class OptimizerGeometryError(Exception):
    pass


def vecSub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def vecAdd(a, b):
    return (a[0] + b[0], a[1] + b[1])


def vecScale(a, s):
    return (a[0] * s, a[1] * s)


def vecLen(a):
    return float(np.hypot(a[0], a[1]))


def vecNormalize(a):
    n = vecLen(a)
    return (a[0] / n, a[1] / n) if n > 1e-12 else (0.0, 0.0)


def vecDot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def vecCross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def vecPerp(a):
    return (-a[1], a[0])


def intersectLines(anchor1, dir1, anchor2, dir2):
    denom = vecCross(dir1, dir2)
    if abs(denom) < 1e-9:
        raise OptimizerGeometryError("parallel tangents")
    diff = vecSub(anchor2, anchor1)
    t1 = vecCross(diff, dir2) / denom
    return vecAdd(anchor1, vecScale(dir1, t1))


def pointToSegmentDistance(p, a, b):
    ab = vecSub(b, a)
    abLen2 = vecDot(ab, ab)
    if abLen2 <= 1e-12:
        return vecLen(vecSub(p, a))
    t = float(np.clip(vecDot(vecSub(p, a), ab) / abLen2, 0.0, 1.0))
    proj = vecAdd(a, vecScale(ab, t))
    return vecLen(vecSub(p, proj))


def pointToPolylineDistance(p, polyline):
    best = np.inf
    for k in range(1, len(polyline)):
        d = pointToSegmentDistance(p, polyline[k-1], polyline[k])
        if d < best:
            best = d
    return best


class AlignmentOptimizer:
    # config keys: dMaxM, lMinM, modeLcl, modeLscsl
    def __init__(self, lxml, config):
        self.lxml = lxml
        self.dMaxM = float(config.get("dMaxM", 0.5))
        self.lMinM = float(config.get("lMinM", 25.0))
        self.modeLcl = config.get("modeLcl", OPTIMIZATION_MODE_NONE)
        self.modeLscsl = config.get("modeLscsl", OPTIMIZATION_MODE_NONE)
        self.elements = []
        self.groups = []
        self.summaryGroups = []
        self.lineRemainingLength = {}
        self.newElementData = {}
        self.newLineEndpoints = {}
        self.hasOptimizedAny = False

    def run(self):
        self.buildElementList()
        self.findGroups()
        for groupRange in self.groups:
            self.optimizeGroup(groupRange)
        summary = self.buildSummary()
        self.lxml["optimizationSummary"] = summary
        optimizedElements = self.assembleOutputs() if self.hasOptimizedAny else None
        return summary, optimizedElements

    # --- Element / group construction ---

    def buildElementList(self):
        geometryType = list(self.lxml.get("geometryType", []))
        stationHorizontal = list(self.lxml.get("stationHorizontal", []))
        curvatureSign = list(self.lxml.get("curvatureSign", []))
        lineIdx = 0
        spiralIdx = 0
        curveIdx = 0
        elemIdx = 0
        elements = []
        for k in range(0, len(geometryType), 2):
            elemType = geometryType[k]
            staStart = float(stationHorizontal[k])
            staEnd = float(stationHorizontal[k+1])
            curvSign = float(curvatureSign[k])
            if elemType == "Line":
                elements.append(self.buildLineElement(elemIdx, lineIdx, staStart, staEnd, curvSign))
                lineIdx += 1
            elif elemType == "Spiral":
                elements.append(self.buildSpiralElement(elemIdx, spiralIdx, staStart, staEnd, curvSign))
                spiralIdx += 1
            elif elemType == "Curve":
                elements.append(self.buildCurveElement(elemIdx, curveIdx, staStart, staEnd, curvSign))
                curveIdx += 1
            else:
                elements.append({"elemIndex": elemIdx, "type": elemType, "typeIdx": -1, "staStart": staStart, "staEnd": staEnd, "curvSign": curvSign})
            elemIdx += 1
        self.elements = elements

    def buildLineElement(self, elemIdx, idx, staStart, staEnd, curvSign):
        return {
            "elemIndex": elemIdx, "type": "Line", "typeIdx": idx, "staStart": staStart, "staEnd": staEnd, "curvSign": curvSign,
            "startX": float(self.lxml["lineStartX"][idx]), "startY": float(self.lxml["lineStartY"][idx]),
            "endX": float(self.lxml["lineEndX"][idx]), "endY": float(self.lxml["lineEndY"][idx]),
        }

    def buildSpiralElement(self, elemIdx, idx, staStart, staEnd, curvSign):
        return {
            "elemIndex": elemIdx, "type": "Spiral", "typeIdx": idx, "staStart": staStart, "staEnd": staEnd, "curvSign": curvSign,
            "startX": float(self.lxml["spiralStartX"][idx]), "startY": float(self.lxml["spiralStartY"][idx]),
            "piX": float(self.lxml["spiralPIX"][idx]), "piY": float(self.lxml["spiralPIY"][idx]),
            "endX": float(self.lxml["spiralEndX"][idx]), "endY": float(self.lxml["spiralEndY"][idx]),
            "length": float(self.lxml["spiralLength"][idx]),
            "radiusStart": float(self.lxml["spiralRadiusStart"][idx]), "radiusEnd": float(self.lxml["spiralRadiusEnd"][idx]),
            "rot": self.lxml["spiralRot"][idx],
        }

    def buildCurveElement(self, elemIdx, idx, staStart, staEnd, curvSign):
        return {
            "elemIndex": elemIdx, "type": "Curve", "typeIdx": idx, "staStart": staStart, "staEnd": staEnd, "curvSign": curvSign,
            "startX": float(self.lxml["curveStartX"][idx]), "startY": float(self.lxml["curveStartY"][idx]),
            "centerX": float(self.lxml["curveCenterX"][idx]), "centerY": float(self.lxml["curveCenterY"][idx]),
            "endX": float(self.lxml["curveEndX"][idx]), "endY": float(self.lxml["curveEndY"][idx]),
            "rot": self.lxml["curveRot"][idx],
            "radius": float(self.lxml["curveRadius"][idx]),
        }

    def findGroups(self):
        groups = []
        n = len(self.elements)
        i = 0
        while i < n:
            if self.elements[i]["type"] == "Line":
                i += 1
                continue
            j = i
            while j < n and self.elements[j]["type"] != "Line":
                j += 1
            groups.append((i, j))
            i = j
        self.groups = groups

    # --- Pattern classification ---

    def classifyPattern(self, runElements):
        runTypes = [e["type"] for e in runElements]
        if runTypes == ["Curve"]:
            return "lcl"
        if runTypes == ["Spiral", "Curve", "Spiral"]:
            entry, arc, exitElem = runElements
            if not self.isClothoidSpiral(entry) or not self.isClothoidSpiral(exitElem):
                return "notClothoid"
            if entry["curvSign"] == 0 or entry["curvSign"] != arc["curvSign"] or arc["curvSign"] != exitElem["curvSign"]:
                return "notClothoid"
            return "lscsl"
        if runTypes == ["Spiral", "Curve", "Spiral", "Spiral", "Curve", "Spiral"]:
            midEntry, midExit = runElements[2], runElements[3]
            if midEntry["curvSign"] != 0 and midExit["curvSign"] != 0 and midEntry["curvSign"] != midExit["curvSign"]:
                return "reverseCompound"
        return "compound"

    def isClothoidSpiral(self, spiralElement):
        if spiralElement.get("length", 0.0) <= MIN_CLOTHOID_LENGTH_M:
            return False
        return np.isinf(spiralElement["radiusStart"]) or np.isinf(spiralElement["radiusEnd"])

    # --- Group optimization dispatch ---

    def optimizeGroup(self, groupRange):
        startIdx, endIdx = groupRange
        runElements = self.elements[startIdx:endIdx]
        patternType = self.classifyPattern(runElements)

        if patternType == "reverseCompound":
            self.optimizeReverseCompound(startIdx, endIdx, runElements)
            return

        if patternType not in ("lcl", "lscsl"):
            reason = "optSkipCompound" if patternType == "compound" else "optSkipNotClothoid"
            self.recordSkip(startIdx, endIdx, patternType, reason)
            return

        mode = self.modeLcl if patternType == "lcl" else self.modeLscsl
        if mode == OPTIMIZATION_MODE_NONE:
            self.recordSkip(startIdx, endIdx, patternType, "optSkipPatternDisabled")
            return

        lineBefore = self.elements[startIdx-1] if startIdx-1 >= 0 and self.elements[startIdx-1]["type"] == "Line" else None
        lineAfter = self.elements[endIdx] if endIdx < len(self.elements) and self.elements[endIdx]["type"] == "Line" else None
        if lineBefore is None or lineAfter is None:
            self.recordSkip(startIdx, endIdx, patternType, "optSkipNoTangent")
            return

        self.solveGroup(startIdx, endIdx, patternType, mode, lineBefore, lineAfter, runElements)

    def optimizeReverseCompound(self, startIdx, endIdx, runElements):
        mode = self.modeLscsl
        if mode == OPTIMIZATION_MODE_NONE:
            self.recordSkip(startIdx, endIdx, "reverseCompound", "optSkipPatternDisabled")
            return

        lineBefore = self.elements[startIdx-1] if startIdx-1 >= 0 and self.elements[startIdx-1]["type"] == "Line" else None
        lineAfter = self.elements[endIdx] if endIdx < len(self.elements) and self.elements[endIdx]["type"] == "Line" else None
        if lineBefore is None or lineAfter is None:
            self.recordSkip(startIdx, endIdx, "reverseCompound", "optSkipNoTangent")
            return

        firstHalf = runElements[0:3]
        secondHalf = runElements[3:6]
        midEntry, midExit = runElements[2], runElements[3]
        if abs(midEntry["endX"] - midExit["startX"]) > 1e-3 or abs(midEntry["endY"] - midExit["startY"]) > 1e-3:
            self.recordSkip(startIdx, endIdx, "reverseCompound", "optSkipDiscontinuous")
            return

        headingBefore = self.spiralHeadingAt(midEntry, atStart=False)
        headingAfter = self.spiralHeadingAt(midExit, atStart=True)
        if vecDot(headingBefore, headingAfter) < 1 - 1e-6:
            self.recordSkip(startIdx, endIdx, "reverseCompound", "optSkipDiscontinuous")
            return

        # Virtual fixed tangent through the baseline inflection point, standing in for a bounding Line
        virtualLine = {
            "elemIndex": None, "isVirtual": True, "type": "Line",
            "startX": midEntry["endX"], "startY": midEntry["endY"],
            "endX": midEntry["endX"] + headingBefore[0], "endY": midEntry["endY"] + headingBefore[1],
        }

        # The side touching the virtual junction keeps its baseline spiral length, only the outer side may grow
        self.solveGroup(startIdx, startIdx+3, "lscsl", mode, lineBefore, virtualLine, firstHalf, allowExtendExit=False)
        self.solveGroup(startIdx+3, endIdx, "lscsl", mode, virtualLine, lineAfter, secondHalf, allowExtendEntry=False)

    def spiralHeadingAt(self, spiralElement, atStart):
        if atStart:
            return vecNormalize(vecSub((spiralElement["piX"], spiralElement["piY"]), (spiralElement["startX"], spiralElement["startY"])))
        return vecNormalize(vecSub((spiralElement["endX"], spiralElement["endY"]), (spiralElement["piX"], spiralElement["piY"])))

    # --- Fixed frame and candidate geometry ---

    def buildFixedFrame(self, lineBefore, lineAfter):
        anchor1 = (lineBefore["endX"], lineBefore["endY"])
        u1 = vecNormalize(vecSub(anchor1, (lineBefore["startX"], lineBefore["startY"])))
        anchor2 = (lineAfter["startX"], lineAfter["startY"])
        u2 = vecNormalize(vecSub((lineAfter["endX"], lineAfter["endY"]), anchor2))
        cross = vecCross(u1, u2)
        if abs(cross) < 1e-9:
            raise OptimizerGeometryError("parallel tangents")
        pi = intersectLines(anchor1, u1, anchor2, u2)
        deflection = float(np.arctan2(cross, vecDot(u1, u2)))
        turnSign = 1.0 if deflection >= 0 else -1.0
        return {
            "anchor1": anchor1, "u1": u1, "n1": vecScale(vecPerp(u1), turnSign),
            "anchor2": anchor2, "u2": u2, "n2": vecScale(vecPerp(u2), turnSign),
            "pi": pi, "deflection": deflection, "turnSign": turnSign,
        }

    def clothoidShiftAndFoot(self, L, R):
        if R <= 0 or L <= 0:
            return 0.0, 0.0, 0.0
        thetaS = L / (2.0 * R)
        deltaR = (L*L)/(24.0*R) - (L**4)/(2688.0*(R**3))
        xm = L/2.0 - (L**3)/(240.0*R*R)
        return thetaS, deltaR, xm

    def solveCenter(self, frame, offset1, offset2):
        n1, n2 = frame["n1"], frame["n2"]
        b1 = vecDot(n1, frame["anchor1"]) + offset1
        b2 = vecDot(n2, frame["anchor2"]) + offset2
        det = n1[0]*n2[1] - n1[1]*n2[0]
        if abs(det) < 1e-9:
            return None
        ox = (b1*n2[1] - b2*n1[1]) / det
        oy = (n1[0]*b2 - n2[0]*b1) / det
        return (ox, oy)

    def projectOntoLine(self, point, anchor, direction):
        t = vecDot(vecSub(point, anchor), direction)
        return vecAdd(anchor, vecScale(direction, t))

    def evaluateClothoid(self, startPoint, direction, R, L, turnSign):
        if L <= 0 or R <= 0:
            return [startPoint]
        azimuth = float(np.arctan2(direction[1], direction[0]))
        dKappa = turnSign / (R * L)
        spiral = Clothoid.StandardParams(startPoint[0], startPoint[1], azimuth, 0.0, dKappa, L)
        ts = np.linspace(0.0, L, SLEW_SAMPLE_COUNT)
        return [(float(spiral.X(t)), float(spiral.Y(t))) for t in ts]

    def evaluateArc(self, center, R, startPoint, endPoint, turnSign):
        angleStart = float(np.arctan2(startPoint[1]-center[1], startPoint[0]-center[0]))
        angleEnd = float(np.arctan2(endPoint[1]-center[1], endPoint[0]-center[0]))
        if turnSign > 0:
            while angleEnd < angleStart:
                angleEnd += 2*np.pi
        else:
            while angleEnd > angleStart:
                angleEnd -= 2*np.pi
        angles = np.linspace(angleStart, angleEnd, SLEW_SAMPLE_COUNT)
        return [(center[0]+R*np.cos(a), center[1]+R*np.sin(a)) for a in angles]

    def buildCandidateGeometry(self, frame, R, Lentry, Lexit):
        if R <= 0:
            return None
        thetaEntry, deltaREntry, xmEntry = self.clothoidShiftAndFoot(Lentry, R)
        thetaExit, deltaRExit, xmExit = self.clothoidShiftAndFoot(Lexit, R)
        center = self.solveCenter(frame, R + deltaREntry, R + deltaRExit)
        if center is None:
            return None

        footEntry = self.projectOntoLine(center, frame["anchor1"], frame["u1"])
        footExit = self.projectOntoLine(center, frame["anchor2"], frame["u2"])
        ts = vecSub(footEntry, vecScale(frame["u1"], xmEntry))
        st = vecAdd(footExit, vecScale(frame["u2"], xmExit))

        sweep = abs(frame["deflection"]) - thetaEntry - thetaExit
        if sweep <= 1e-6:
            return None

        entrySpiralPoints = self.evaluateClothoid(ts, frame["u1"], R, Lentry, frame["turnSign"]) if Lentry > 0 else [ts]
        exitSpiralPointsRaw = self.evaluateClothoid(st, vecScale(frame["u2"], -1.0), R, Lexit, -frame["turnSign"]) if Lexit > 0 else [st]
        exitSpiralPoints = list(reversed(exitSpiralPointsRaw))

        arcStart = entrySpiralPoints[-1] if Lentry > 0 else ts
        arcEnd = exitSpiralPoints[0] if Lexit > 0 else st
        arcPoints = self.evaluateArc(center, R, arcStart, arcEnd, frame["turnSign"])

        return {
            "center": center, "ts": ts, "st": st, "arcStart": arcStart, "arcEnd": arcEnd,
            "thetaEntry": thetaEntry, "thetaExit": thetaExit,
            "deltaREntry": deltaREntry, "deltaRExit": deltaRExit,
            "arcLength": R * sweep, "sweep": sweep,
            "entrySpiralPoints": entrySpiralPoints, "exitSpiralPoints": exitSpiralPoints, "arcPoints": arcPoints,
            "samplePoints": entrySpiralPoints[:-1] + arcPoints + exitSpiralPoints[1:],
        }

    def sampleBaselineAxis(self, lineBefore, entrySpiral, arcElement, exitSpiral, lineAfter, frame, R0, L0entry, L0exit):
        points = [(lineBefore["startX"], lineBefore["startY"]), (lineBefore["endX"], lineBefore["endY"])]
        if entrySpiral:
            points += self.evaluateClothoid((entrySpiral["startX"], entrySpiral["startY"]), frame["u1"], R0, L0entry, frame["turnSign"])[1:]
        if arcElement.get("centerX") is not None:
            points += self.evaluateArc((arcElement["centerX"], arcElement["centerY"]), R0,
                                        (arcElement["startX"], arcElement["startY"]), (arcElement["endX"], arcElement["endY"]), frame["turnSign"])[1:]
        else:
            points.append((arcElement["startX"], arcElement["startY"]))
            points.append((arcElement["endX"], arcElement["endY"]))
        if exitSpiral:
            pts = self.evaluateClothoid((exitSpiral["endX"], exitSpiral["endY"]), vecScale(frame["u2"], -1.0), R0, L0exit, -frame["turnSign"])
            points += list(reversed(pts))[1:]
        points += [(lineAfter["startX"], lineAfter["startY"]), (lineAfter["endX"], lineAfter["endY"])]
        return points

    def evaluateSlew(self, baselineAxis, candidatePoints):
        worst = 0.0
        for p in candidatePoints:
            d = pointToPolylineDistance(p, baselineAxis)
            if d > worst:
                worst = d
        return worst

    # --- Shared line budget (lMin-or-zero rule) ---

    def lineKey(self, lineElement):
        return ("virtual", id(lineElement)) if lineElement.get("isVirtual") else (lineElement["type"], lineElement["typeIdx"])

    def lineBaselineLength(self, lineElement):
        if lineElement.get("isVirtual"):
            return 0.0
        return float(np.hypot(lineElement["endX"]-lineElement["startX"], lineElement["endY"]-lineElement["startY"]))

    def availableLineBudget(self, lineElement):
        key = self.lineKey(lineElement)
        if key not in self.lineRemainingLength:
            self.lineRemainingLength[key] = self.lineBaselineLength(lineElement)
        return self.lineRemainingLength[key]

    def consumeLine(self, lineElement, consumedLength):
        if lineElement.get("isVirtual") or consumedLength <= 0:
            return
        key = self.lineKey(lineElement)
        self.lineRemainingLength[key] = self.availableLineBudget(lineElement) - consumedLength

    # Cap a desired extra spiral-length consumption against what a shared Line can still give up
    def resolveSharedLine(self, remainingLength, desiredConsumption, lMinM):
        desiredConsumption = max(0.0, desiredConsumption)
        if remainingLength <= lMinM:
            return min(desiredConsumption, max(0.0, remainingLength))
        return min(desiredConsumption, remainingLength - lMinM)

    # --- Bisection ---

    def bisectMaximize(self, feasibleFn, low, initialStep):
        if not feasibleFn(low):
            return low, False
        lo = low
        hi = low
        step = initialStep
        for _ in range(BISECTION_MAX_ITER):
            hi = lo + step
            if not feasibleFn(hi):
                break
            lo = hi
            step *= 1.6
        for _ in range(BISECTION_MAX_ITER):
            if hi - lo < BISECTION_TOLERANCE_M:
                break
            mid = 0.5*(lo+hi)
            if feasibleFn(mid):
                lo = mid
            else:
                hi = mid
        return lo, True

    # --- Mode solvers ---

    def solveShiftArc(self, frame, R0, L0entry, L0exit, baselineAxis):
        def isFeasible(R):
            geometry = self.buildCandidateGeometry(frame, R, L0entry, L0exit)
            if geometry is None or geometry["arcLength"] < self.lMinM:
                return False
            return self.evaluateSlew(baselineAxis, geometry["samplePoints"]) <= self.dMaxM

        if not isFeasible(R0):
            return {"feasible": False, "reason": "optSkipLMinViolated"}

        Rnew, _ = self.bisectMaximize(isFeasible, R0, max(1.0, R0*0.1))
        if Rnew - R0 < 0.01:
            return {"feasible": False, "reason": "optSkipEnvelopeExhausted"}
        return {"feasible": True, "Rnew": Rnew, "Lentry": L0entry, "Lexit": L0exit}

    def solveShiftAndExtend(self, frame, R0, L0entry, L0exit, baselineAxis, entryBudget, exitBudget, allowEntry, allowExit):
        stage1 = self.solveShiftArc(frame, R0, L0entry, L0exit, baselineAxis)
        if not stage1["feasible"]:
            return stage1
        Rnew = stage1["Rnew"]
        Lentry, Lexit = L0entry, L0exit

        if allowEntry and L0entry > 0:
            def isFeasibleEntry(L):
                geometry = self.buildCandidateGeometry(frame, Rnew, L, Lexit)
                if geometry is None or geometry["arcLength"] < self.lMinM:
                    return False
                if self.resolveSharedLine(entryBudget, L - L0entry, self.lMinM) < L - L0entry - 1e-6:
                    return False
                return self.evaluateSlew(baselineAxis, geometry["samplePoints"]) <= self.dMaxM
            Lentry, _ = self.bisectMaximize(isFeasibleEntry, L0entry, max(1.0, L0entry*0.2))

        if allowExit and L0exit > 0:
            def isFeasibleExit(L):
                geometry = self.buildCandidateGeometry(frame, Rnew, Lentry, L)
                if geometry is None or geometry["arcLength"] < self.lMinM:
                    return False
                if self.resolveSharedLine(exitBudget, L - L0exit, self.lMinM) < L - L0exit - 1e-6:
                    return False
                return self.evaluateSlew(baselineAxis, geometry["samplePoints"]) <= self.dMaxM
            Lexit, _ = self.bisectMaximize(isFeasibleExit, L0exit, max(1.0, L0exit*0.2))

        return {"feasible": True, "Rnew": Rnew, "Lentry": Lentry, "Lexit": Lexit}

    def solveExtendSpirals(self, frame, R0, L0entry, L0exit, baselineAxis, entryBudget, exitBudget, allowEntry, allowExit):
        if L0entry <= 0 or L0exit <= 0:
            return {"feasible": False, "reason": "optSkipNoSpirals"}

        Lentry, Lexit = L0entry, L0exit

        if allowEntry:
            def isFeasibleEntry(L):
                geometry = self.buildCandidateGeometry(frame, R0, L, Lexit)
                if geometry is None or geometry["arcLength"] < self.lMinM:
                    return False
                if self.resolveSharedLine(entryBudget, L - L0entry, self.lMinM) < L - L0entry - 1e-6:
                    return False
                return self.evaluateSlew(baselineAxis, geometry["samplePoints"]) <= self.dMaxM
            Lentry, _ = self.bisectMaximize(isFeasibleEntry, L0entry, max(1.0, L0entry*0.2))

        if allowExit:
            def isFeasibleExit(L):
                geometry = self.buildCandidateGeometry(frame, R0, Lentry, L)
                if geometry is None or geometry["arcLength"] < self.lMinM:
                    return False
                if self.resolveSharedLine(exitBudget, L - L0exit, self.lMinM) < L - L0exit - 1e-6:
                    return False
                return self.evaluateSlew(baselineAxis, geometry["samplePoints"]) <= self.dMaxM
            Lexit, _ = self.bisectMaximize(isFeasibleExit, L0exit, max(1.0, L0exit*0.2))

        if Lentry - L0entry < 0.01 and Lexit - L0exit < 0.01:
            return {"feasible": False, "reason": "optSkipEnvelopeExhausted"}
        return {"feasible": True, "Rnew": R0, "Lentry": Lentry, "Lexit": Lexit}

    def solveInvertedShift(self, frame, R0, L0entry, L0exit, baselineAxis, entryBudget, exitBudget, allowEntry, allowExit):
        if L0entry <= 0 or L0exit <= 0:
            return {"feasible": False, "reason": "optSkipNoSpirals"}

        Rfloor = max(60.0, 0.5 * R0)
        _, deltaR0entry, _ = self.clothoidShiftAndFoot(L0entry, R0)
        _, deltaR0exit, _ = self.clothoidShiftAndFoot(L0exit, R0)

        # Bracket bound only, the strict slew check below is what actually enforces d_max
        def candidateAt(s):
            Rnew = max(Rfloor, R0 - s)
            Lentry = float(np.sqrt(max(0.0, 24.0*Rnew*(deltaR0entry + 2.0*s)))) if allowEntry else L0entry
            Lexit = float(np.sqrt(max(0.0, 24.0*Rnew*(deltaR0exit + 2.0*s)))) if allowExit else L0exit
            if allowEntry:
                Lentry = min(Lentry, L0entry + self.resolveSharedLine(entryBudget, Lentry - L0entry, self.lMinM))
            if allowExit:
                Lexit = min(Lexit, L0exit + self.resolveSharedLine(exitBudget, Lexit - L0exit, self.lMinM))
            return Rnew, Lentry, Lexit

        def isFeasible(s):
            Rnew, Lentry, Lexit = candidateAt(s)
            geometry = self.buildCandidateGeometry(frame, Rnew, Lentry, Lexit)
            if geometry is None or geometry["arcLength"] < self.lMinM:
                return False
            return self.evaluateSlew(baselineAxis, geometry["samplePoints"]) <= self.dMaxM

        sMax, _ = self.bisectMaximize(isFeasible, 0.0, max(0.05, self.dMaxM*0.2))
        if sMax < 0.01:
            return {"feasible": False, "reason": "optSkipEnvelopeExhausted"}

        Rnew, Lentry, Lexit = candidateAt(sMax)
        return {"feasible": True, "Rnew": Rnew, "Lentry": Lentry, "Lexit": Lexit}

    # --- Group solve orchestration and output emission ---

    def solveGroup(self, startIdx, endIdx, patternType, mode, lineBefore, lineAfter, runElements, allowExtendEntry=True, allowExtendExit=True):
        try:
            frame = self.buildFixedFrame(lineBefore, lineAfter)
        except OptimizerGeometryError:
            self.recordSkip(startIdx, endIdx, patternType, "optSkipParallelTangents")
            return

        if patternType == "lcl":
            arcElement = runElements[0]
            entrySpiral = exitSpiral = None
        else:
            entrySpiral, arcElement, exitSpiral = runElements

        R0 = float(arcElement["radius"])
        L0entry = float(entrySpiral["length"]) if entrySpiral else 0.0
        L0exit = float(exitSpiral["length"]) if exitSpiral else 0.0

        baselineAxis = self.sampleBaselineAxis(lineBefore, entrySpiral, arcElement, exitSpiral, lineAfter, frame, R0, L0entry, L0exit)
        entryBudget = self.availableLineBudget(lineBefore) if allowExtendEntry else 0.0
        exitBudget = self.availableLineBudget(lineAfter) if allowExtendExit else 0.0

        if mode == OPTIMIZATION_MODE_SHIFT_ARC:
            result = self.solveShiftArc(frame, R0, L0entry, L0exit, baselineAxis)
        elif mode == OPTIMIZATION_MODE_SHIFT_AND_EXTEND:
            result = self.solveShiftAndExtend(frame, R0, L0entry, L0exit, baselineAxis, entryBudget, exitBudget, allowExtendEntry, allowExtendExit)
        elif mode == OPTIMIZATION_MODE_EXTEND_SPIRALS:
            result = self.solveExtendSpirals(frame, R0, L0entry, L0exit, baselineAxis, entryBudget, exitBudget, allowExtendEntry, allowExtendExit)
        elif mode == OPTIMIZATION_MODE_INVERTED_SHIFT:
            result = self.solveInvertedShift(frame, R0, L0entry, L0exit, baselineAxis, entryBudget, exitBudget, allowExtendEntry, allowExtendExit)
        else:
            result = {"feasible": False, "reason": "optSkipPatternDisabled"}

        if not result["feasible"]:
            self.recordSkip(startIdx, endIdx, patternType, result.get("reason", "optSkipEnvelopeExhausted"))
            return

        Lentry, Lexit, Rnew = result["Lentry"], result["Lexit"], result["Rnew"]
        geometry = self.buildCandidateGeometry(frame, Rnew, Lentry, Lexit)
        if geometry is None:
            self.recordSkip(startIdx, endIdx, patternType, "optSkipNotClothoid")
            return

        slewMax = self.evaluateSlew(baselineAxis, geometry["samplePoints"])
        if slewMax > self.dMaxM + 1e-3:
            self.recordSkip(startIdx, endIdx, patternType, "optWarnEnvelopeExceeded")
            return

        if allowExtendEntry:
            self.consumeLine(lineBefore, max(0.0, Lentry - L0entry))
        if allowExtendExit:
            self.consumeLine(lineAfter, max(0.0, Lexit - L0exit))

        self.emitGroup(startIdx, endIdx, patternType, mode, lineBefore, lineAfter,
                        entrySpiral, arcElement, exitSpiral, geometry, R0, Rnew, L0entry, Lentry, L0exit, Lexit, slewMax)
        self.hasOptimizedAny = True

    def registerNewElement(self, k, staStart, staEnd, kappaStart, kappaEnd, radiusStart, radiusEnd, startXY, endXY, centerXY=None, piXY=None):
        self.newElementData[k] = {
            "staStart": staStart, "staEnd": staEnd,
            "curvatureStart": kappaStart, "curvatureEnd": kappaEnd,
            "radiusStart": radiusStart, "radiusEnd": radiusEnd,
            "startX": startXY[0], "startY": startXY[1],
            "endX": endXY[0], "endY": endXY[1],
            "centerX": centerXY[0] if centerXY else None, "centerY": centerXY[1] if centerXY else None,
            "piX": piXY[0] if piXY else startXY[0], "piY": piXY[1] if piXY else startXY[1],
        }

    def updateLineEndpoint(self, lineElement, updateStart, newPoint):
        if lineElement.get("isVirtual"):
            return
        entry = self.newLineEndpoints.setdefault(lineElement["elemIndex"], {})
        if updateStart:
            entry["startXY"] = newPoint
        else:
            entry["endXY"] = newPoint

    def arcLengthBaseline(self, arcElement):
        return (arcElement["staEnd"] - arcElement["staStart"]) * 1000.0

    # Unit tangent direction at samplePoints[index], approximated from the adjacent sample
    def tangentAtPoint(self, samplePoints, index):
        if len(samplePoints) < 2:
            return (1.0, 0.0)
        other = index + 1 if index + 1 < len(samplePoints) else index - 1
        direction = vecNormalize(vecSub(samplePoints[other], samplePoints[index]))
        return direction if other > index else vecScale(direction, -1.0)

    def emitGroup(self, startIdx, endIdx, patternType, mode, lineBefore, lineAfter,
                  entrySpiral, arcElement, exitSpiral, geometry, R0, Rnew, L0entry, Lentry, L0exit, Lexit, slewMax):
        groupStartStation = self.elements[startIdx]["staStart"]
        entryEndStation = groupStartStation + Lentry/1000.0
        arcEndStation = entryEndStation + geometry["arcLength"]/1000.0
        exitEndStation = arcEndStation + Lexit/1000.0

        curvSign = arcElement["curvSign"]
        entryKappaEnd = curvSign / Rnew if Rnew > 0 else 0.0
        arcKappa = curvSign / Rnew if Rnew > 0 else 0.0

        if entrySpiral is not None:
            entryPi = vecAdd(geometry["ts"], self.tangentAtPoint(geometry["entrySpiralPoints"], 0))
            self.registerNewElement(startIdx, groupStartStation, entryEndStation, 0.0, entryKappaEnd,
                                     np.inf, Rnew, geometry["ts"], geometry["arcStart"], piXY=entryPi)
            arcIdx = startIdx + 1
        else:
            arcIdx = startIdx

        self.registerNewElement(arcIdx, entryEndStation, arcEndStation, arcKappa, arcKappa,
                                 Rnew, Rnew, geometry["arcStart"], geometry["arcEnd"], centerXY=geometry["center"])

        if exitSpiral is not None:
            exitPi = vecAdd(geometry["arcEnd"], self.tangentAtPoint(geometry["exitSpiralPoints"], 0))
            self.registerNewElement(arcIdx+1, arcEndStation, exitEndStation, arcKappa, 0.0,
                                     Rnew, np.inf, geometry["arcEnd"], geometry["st"], piXY=exitPi)

        self.updateLineEndpoint(lineBefore, updateStart=False, newPoint=geometry["ts"])
        self.updateLineEndpoint(lineAfter, updateStart=True, newPoint=geometry["st"])

        lengthDelta = (Lentry - L0entry) + (Lexit - L0exit) + (geometry["arcLength"] - self.arcLengthBaseline(arcElement))

        self.summaryGroups.append({
            "groupIndex": len(self.summaryGroups), "patternType": patternType, "mode": mode,
            "startKm": float(groupStartStation), "endKm": float(exitEndStation), "status": "optOk",
            "radiusOldM": float(R0), "radiusNewM": float(Rnew),
            "spiralLengthsOldM": [float(L0entry), float(L0exit)], "spiralLengthsNewM": [float(Lentry), float(Lexit)],
            "offsetOldM": float(self.clothoidShiftAndFoot(L0entry, R0)[1]), "offsetNewM": float(geometry["deltaREntry"]),
            "slewMaxM": float(slewMax), "lengthDeltaM": float(lengthDelta),
        })

    def recordSkip(self, startIdx, endIdx, patternType, reasonCode):
        self.summaryGroups.append({
            "groupIndex": len(self.summaryGroups), "patternType": patternType or "unknown", "mode": OPTIMIZATION_MODE_NONE,
            "startKm": float(self.elements[startIdx]["staStart"]), "endKm": float(self.elements[endIdx-1]["staEnd"]),
            "status": reasonCode,
            "radiusOldM": None, "radiusNewM": None, "spiralLengthsOldM": None, "spiralLengthsNewM": None,
            "offsetOldM": None, "offsetNewM": None, "slewMaxM": None, "lengthDeltaM": None,
        })

    def buildSummary(self):
        optimizedGroups = [g for g in self.summaryGroups if g["status"] == "optOk"]
        slews = [g["slewMaxM"] for g in optimizedGroups]
        return {
            "modeLcl": self.modeLcl, "modeLscsl": self.modeLscsl, "dMaxM": self.dMaxM, "lMinM": self.lMinM,
            "maxSlewM": float(max(slews)) if slews else 0.0,
            "meanSlewM": float(sum(slews)/len(slews)) if slews else 0.0,
            "optimizedGroupCount": len(optimizedGroups),
            "skippedGroupCount": len(self.summaryGroups) - len(optimizedGroups),
            "groups": self.summaryGroups,
        }

    # --- Output assembly ---

    def radiusFromCurvature(self, kappa):
        kappa = abs(float(kappa))
        return 1.0 / kappa if kappa > 1e-12 else np.inf

    def assembleOutputs(self):
        stationHorizontalNew = [float(v) for v in self.lxml.get("stationHorizontal", [])]
        geometryTypeNew = list(self.lxml.get("geometryType", []))
        curvatureNew = [float(v) for v in self.lxml.get("curvature", [])]
        curvatureSignNew = [float(v) for v in self.lxml.get("curvatureSign", [])]
        # Derived from curvature rather than the parser's own "radius" array, which batch runs strip out
        radiusNew = [self.radiusFromCurvature(v) for v in curvatureNew]

        for k in range(len(self.elements)):
            override = self.newElementData.get(k)
            if override is None:
                continue
            pairIndex = 2 * k
            stationHorizontalNew[pairIndex] = override["staStart"]
            stationHorizontalNew[pairIndex+1] = override["staEnd"]
            curvatureNew[pairIndex] = override["curvatureStart"]
            curvatureNew[pairIndex+1] = override["curvatureEnd"]
            radiusNew[pairIndex] = override["radiusStart"]
            radiusNew[pairIndex+1] = override["radiusEnd"]

        self.stationHorizontalNewList = stationHorizontalNew

        lxml = self.lxml
        lxml["stationHorizontalNew"] = np.array(stationHorizontalNew, dtype=float)
        lxml["geometryTypeNew"] = np.array(geometryTypeNew)
        lxml["curvatureNew"] = np.array(curvatureNew, dtype=float)
        lxml["curvatureSignNew"] = np.array(curvatureSignNew, dtype=float)
        lxml["radiusNew"] = np.array(radiusNew, dtype=float)

        return self.buildOptimizedElementsDict()

    def buildOptimizedElementsDict(self):
        lineStartX, lineStartY, lineEndX, lineEndY, lineStationStart = [], [], [], [], []
        spiralStartX, spiralStartY, spiralPIX, spiralPIY, spiralEndX, spiralEndY = [], [], [], [], [], []
        spiralStationStart, spiralLength, spiralRadiusStart, spiralRadiusEnd, spiralRot = [], [], [], [], []
        curveStartX, curveStartY, curveCenterX, curveCenterY, curveEndX, curveEndY = [], [], [], [], [], []
        curveStationStart, curveRadius, curveRot = [], [], []

        for k, elem in enumerate(self.elements):
            override = self.newElementData.get(k)
            if elem["type"] == "Line":
                lineOverride = self.newLineEndpoints.get(k, {})
                startX, startY = lineOverride.get("startXY", (elem["startX"], elem["startY"]))
                endX, endY = lineOverride.get("endXY", (elem["endX"], elem["endY"]))
                lineStartX.append(startX); lineStartY.append(startY)
                lineEndX.append(endX); lineEndY.append(endY)
                lineStationStart.append(elem["staStart"])
            elif elem["type"] == "Spiral":
                if override:
                    spiralStartX.append(override["startX"]); spiralStartY.append(override["startY"])
                    spiralEndX.append(override["endX"]); spiralEndY.append(override["endY"])
                    spiralPIX.append(override["piX"]); spiralPIY.append(override["piY"])
                    spiralStationStart.append(override["staStart"])
                    spiralLength.append((override["staEnd"] - override["staStart"]) * 1000.0)
                    spiralRadiusStart.append(override["radiusStart"]); spiralRadiusEnd.append(override["radiusEnd"])
                else:
                    spiralStartX.append(elem["startX"]); spiralStartY.append(elem["startY"])
                    spiralEndX.append(elem["endX"]); spiralEndY.append(elem["endY"])
                    spiralPIX.append(elem["piX"]); spiralPIY.append(elem["piY"])
                    spiralStationStart.append(elem["staStart"])
                    spiralLength.append(elem["length"])
                    spiralRadiusStart.append(elem["radiusStart"]); spiralRadiusEnd.append(elem["radiusEnd"])
                spiralRot.append(elem["rot"])
            elif elem["type"] == "Curve":
                if override:
                    curveStartX.append(override["startX"]); curveStartY.append(override["startY"])
                    curveEndX.append(override["endX"]); curveEndY.append(override["endY"])
                    curveCenterX.append(override["centerX"]); curveCenterY.append(override["centerY"])
                    curveStationStart.append(override["staStart"])
                    curveRadius.append(override["radiusStart"])
                else:
                    curveStartX.append(elem["startX"]); curveStartY.append(elem["startY"])
                    curveEndX.append(elem["endX"]); curveEndY.append(elem["endY"])
                    curveCenterX.append(elem["centerX"]); curveCenterY.append(elem["centerY"])
                    curveStationStart.append(elem["staStart"])
                    curveRadius.append(elem["radius"])
                curveRot.append(elem["rot"])

        return {
            "lineStartX": np.array(lineStartX), "lineStartY": np.array(lineStartY),
            "lineEndX": np.array(lineEndX), "lineEndY": np.array(lineEndY),
            "lineStationStart": np.array(lineStationStart),
            "spiralStartX": np.array(spiralStartX), "spiralStartY": np.array(spiralStartY),
            "spiralPIX": np.array(spiralPIX), "spiralPIY": np.array(spiralPIY),
            "spiralEndX": np.array(spiralEndX), "spiralEndY": np.array(spiralEndY),
            "spiralStationStart": np.array(spiralStationStart), "spiralLength": np.array(spiralLength),
            "spiralRadiusStart": np.array(spiralRadiusStart), "spiralRadiusEnd": np.array(spiralRadiusEnd),
            "spiralRot": np.array(spiralRot),
            "curveStartX": np.array(curveStartX), "curveStartY": np.array(curveStartY),
            "curveCenterX": np.array(curveCenterX), "curveCenterY": np.array(curveCenterY),
            "curveEndX": np.array(curveEndX), "curveEndY": np.array(curveEndY),
            "curveStationStart": np.array(curveStationStart), "curveRadius": np.array(curveRadius),
            "curveRot": np.array(curveRot),
            "stationHorizontal": np.array(self.stationHorizontalNewList),
        }
