import math
import time

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
# An L-C-L group has no transitions to extend, so only the arc shift is meaningful there
LCL_OPTIMIZATION_MODES = (OPTIMIZATION_MODE_SHIFT_ARC,)

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

# Segment window half width around each point's proportional index, measured worst case offset is two
SEGMENT_SEARCH_BAND = 16

# Lateral shift below this is treated as construction noise rather than a real slew
SLEW_VISIBLE_THRESHOLD_MM = 5.0

# Offsets below this are numerically zero, an exact comparison would count rounding dust as a shift
SLEW_ZERO_EPSILON_MM = 1e-6

# Two chainages closer than this are the same node, np.interp needs strictly increasing samples
CHAINAGE_EPSILON_KM = 1e-9

# An arc allowed to fall below L_min must beat its baseline by at least this margin
ARC_IMPROVEMENT_EPSILON_M = 1e-6

# Upper bound on an optimized transition length when the configuration does not name one
DEFAULT_LK_MAX_M = 250.0

# Bisection stops once the search bracket narrows below this, in meters
BISECTION_TOLERANCE_M = 1e-4

BISECTION_MAX_ITER = 60

# Newton steps used to invert the apex offset identity, it converges quadratically from a linear seed
NEWTON_MAX_ITER = 8

# Newton stops once the step falls below this, well under the reporting resolution
NEWTON_TOLERANCE_M = 1e-9

# Upper bound on halving steps inside a bracket, the tolerance break below normally ends it far sooner
BRACKET_REFINE_STEPS = 40

# Doublings allowed when the analytic seed turns out to still be feasible, keeps the search bounded
BRACKET_EXPAND_STEPS = 4


class OptimizerGeometryError(Exception):
    pass


def vecSub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def vecAdd(a, b):
    return (a[0] + b[0], a[1] + b[1])


def vecScale(a, s):
    return (a[0] * s, a[1] * s)


def vecLen(a):
    return math.hypot(a[0], a[1])


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


def clampUnit(value):
    if value < 0.0:
        return 0.0
    return 1.0 if value > 1.0 else value


def pointToSegmentDistance(p, a, b):
    ab = vecSub(b, a)
    abLen2 = vecDot(ab, ab)
    if abLen2 <= 1e-12:
        return vecLen(vecSub(p, a))
    t = clampUnit(vecDot(vecSub(p, a), ab) / abLen2)
    proj = vecAdd(a, vecScale(ab, t))
    return vecLen(vecSub(p, proj))


def pointToPolylineDistance(p, polyline):
    best = np.inf
    for k in range(1, len(polyline)):
        d = pointToSegmentDistance(p, polyline[k-1], polyline[k])
        if d < best:
            best = d
    return best


def closestPointOnSegment(p, a, b):
    ab = vecSub(b, a)
    abLen2 = vecDot(ab, ab)
    if abLen2 <= 1e-12:
        return a
    t = clampUnit(vecDot(vecSub(p, a), ab) / abLen2)
    return vecAdd(a, vecScale(ab, t))


# Split a polyline into the start, direction and squared length arrays every distance query needs
def prepareSegments(polyline):
    vertices = np.asarray(polyline, dtype=float)
    segmentStart = vertices[:-1]
    segmentVector = vertices[1:] - vertices[:-1]
    segmentLengthSq = np.einsum("ij,ij->i", segmentVector, segmentVector)
    # A degenerate segment collapses to its start point, guarding the division below
    safeLengthSq = np.where(segmentLengthSq <= 1e-12, 1.0, segmentLengthSq)
    return segmentStart, segmentVector, safeLengthSq, segmentLengthSq


# Perpendicular residual of every point against every segment, the shared kernel of both queries
def segmentResiduals(points, segments):
    segmentStart, segmentVector, safeLengthSq, segmentLengthSq = segments
    offsets = points[:, None, :] - segmentStart[None, :, :]
    travel = np.einsum("mij,ij->mi", offsets, segmentVector) / safeLengthSq
    # Degenerate segments must not project, their residual is the raw offset from the start point
    travel = np.where(segmentLengthSq[None, :] <= 1e-12, 0.0, np.clip(travel, 0.0, 1.0))
    residual = offsets - travel[:, :, None] * segmentVector[None, :, :]
    return residual, travel


# Segment indices to test per point, a band around the proportional mapping between both polylines
def bandedSegmentIndices(pointCount, segmentCount):
    window = 2 * SEGMENT_SEARCH_BAND + 1
    if pointCount < 1 or segmentCount <= window:
        return None
    centre = np.round(np.arange(pointCount) * (segmentCount - 1) / max(1, pointCount - 1))
    centre = np.clip(centre, SEGMENT_SEARCH_BAND, segmentCount - 1 - SEGMENT_SEARCH_BAND)
    offsets = np.arange(-SEGMENT_SEARCH_BAND, SEGMENT_SEARCH_BAND + 1)
    return (centre[:, None] + offsets[None, :]).astype(np.intp)


# Residuals restricted to the banded indices, returning None when the band cannot be trusted
def bandedResiduals(points, segments, indices):
    segmentStart, segmentVector, safeLengthSq, segmentLengthSq = segments
    localStart = segmentStart[indices]
    localVector = segmentVector[indices]
    offsets = points[:, None, :] - localStart
    travel = np.einsum("mij,mij->mi", offsets, localVector) / safeLengthSq[indices]
    travel = np.where(segmentLengthSq[indices] <= 1e-12, 0.0, np.clip(travel, 0.0, 1.0))
    residual = offsets - travel[:, :, None] * localVector
    distances = np.sqrt(np.einsum("mij,mij->mi", residual, residual))

    # A winner sitting on an unclipped band edge means the true minimum may lie outside the window
    localBest = distances.argmin(axis=1)
    onEdge = (localBest == 0) | (localBest == indices.shape[1] - 1)
    if np.any(onEdge):
        interiorEdge = onEdge & (indices[np.arange(indices.shape[0]), localBest] != 0) & \
                       (indices[np.arange(indices.shape[0]), localBest] != segmentLengthSq.shape[0] - 1)
        if np.any(interiorEdge):
            return None
    return distances, travel, localBest


# Largest distance from any candidate point to the baseline polyline, fully vectorized
def maxDistanceToPolyline(candidatePoints, segments):
    points = np.asarray(candidatePoints, dtype=float)
    if points.size == 0:
        return 0.0

    indices = bandedSegmentIndices(points.shape[0], segments[0].shape[0])
    if indices is not None:
        banded = bandedResiduals(points, segments, indices)
        if banded is not None:
            return float(banded[0].min(axis=1).max())

    residual, _ = segmentResiduals(points, segments)
    distances = np.sqrt(np.einsum("mij,mij->mi", residual, residual))
    return float(distances.min(axis=1).max())


# Distance, nearest baseline point and that segment's unit direction for every candidate point
def nearestOnPolyline(candidatePoints, segments):
    segmentStart, segmentVector, _, _ = segments
    points = np.asarray(candidatePoints, dtype=float)
    rowIndex = np.arange(points.shape[0])

    bestIndex = None
    indices = bandedSegmentIndices(points.shape[0], segmentStart.shape[0])
    if indices is not None:
        banded = bandedResiduals(points, segments, indices)
        if banded is not None:
            distances, travel, localBest = banded
            bestIndex = indices[rowIndex, localBest]
            bestDistance = distances[rowIndex, localBest]
            bestTravel = travel[rowIndex, localBest]

    if bestIndex is None:
        residual, travel = segmentResiduals(points, segments)
        distances = np.sqrt(np.einsum("mij,mij->mi", residual, residual))
        bestIndex = distances.argmin(axis=1)
        bestDistance = distances[rowIndex, bestIndex]
        bestTravel = travel[rowIndex, bestIndex]

    bestPoint = segmentStart[bestIndex] + bestTravel[:, None] * segmentVector[bestIndex]
    bestVector = segmentVector[bestIndex]
    bestNorm = np.sqrt(np.einsum("ij,ij->i", bestVector, bestVector))
    bestNorm = np.where(bestNorm <= 1e-12, 1.0, bestNorm)
    return bestDistance, bestPoint, bestVector / bestNorm[:, None]


# Distance, the baseline point it was measured to and that segment's direction, used to sign a slew
def pointToPolylineNearest(p, polyline):
    best = np.inf
    bestPoint = polyline[0] if polyline else p
    bestDirection = (1.0, 0.0)
    for k in range(1, len(polyline)):
        candidate = closestPointOnSegment(p, polyline[k-1], polyline[k])
        d = vecLen(vecSub(p, candidate))
        if d < best:
            best = d
            bestPoint = candidate
            bestDirection = vecNormalize(vecSub(polyline[k], polyline[k-1]))
    return best, bestPoint, bestDirection


# Map a chainage from the imported alignment onto the active one, identity while nothing moved
def projectChainageKm(lxml, stationKm):
    baselineKm = (lxml or {}).get("chainageMapBaselineKm")
    activeKm = (lxml or {}).get("chainageMapActiveKm")
    if baselineKm is None or activeKm is None:
        return float(stationKm)
    baselineKm = np.asarray(baselineKm, dtype=float)
    activeKm = np.asarray(activeKm, dtype=float)
    if baselineKm.size < 2 or baselineKm.size != activeKm.size:
        return float(stationKm)
    return float(np.interp(float(stationKm), baselineKm, activeKm))


class AlignmentOptimizer:
    # config keys: dMaxM, lMinM, modeLcl, modeLscsl
    def __init__(self, lxml, config, progressCallback=None):
        self.lxml = lxml
        self.progressCallback = progressCallback
        self.timingMs = {"curveSolvingMs": 0.0, "samplingMs": 0.0}
        self.dMaxM = float(config.get("dMaxM", 0.5))
        self.lMinM = float(config.get("lMinM", 25.0))
        self.lkMaxM = float(config.get("lkMaxM", DEFAULT_LK_MAX_M))
        self.modeLcl = config.get("modeLcl", OPTIMIZATION_MODE_NONE)
        self.modeLscsl = config.get("modeLscsl", OPTIMIZATION_MODE_NONE)
        self.elements = []
        self.groups = []
        self.summaryGroups = []
        self.lineRemainingLength = {}
        self.newElementData = {}
        self.newLineEndpoints = {}
        self.hasOptimizedAny = False
        self.slewSamples = []
        self.baselineSegmentCache = None
        self.elementStationsKm = []
        self.hasClampedChainage = False
        # Per group solve state, refreshed by solveGroup before any candidate is evaluated
        self.baselineArcLengthM = 0.0
        self.groupLineBefore = None
        self.groupLineAfter = None
        self.baselineEntryStraightM = 0.0
        self.baselineExitStraightM = 0.0
        self.wasRelaxationBlockedByTangent = False

    def run(self):
        self.buildElementList()
        self.findGroups()

        groupCount = len(self.groups)
        solveStarted = time.perf_counter()
        for groupIndex, groupRange in enumerate(self.groups):
            self.optimizeGroup(groupRange)
            if self.progressCallback is not None:
                self.progressCallback(groupIndex + 1, groupCount)
        solveElapsedMs = (time.perf_counter() - solveStarted) * 1000.0
        # Sampling is measured inside recordSlewProfile, so solving is whatever is left over
        self.timingMs["curveSolvingMs"] = max(0.0, solveElapsedMs - self.timingMs["samplingMs"])

        # Element lengths are final here, so the whole corridor is re-chained before anything
        # reads a station, keeping stationHorizontalNew monotonic end to end
        if self.hasOptimizedAny:
            self.rebuildCumulativeChainage()
            self.resolveGroupStations()
            self.resolveSlewSampleStations()

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

        # A stale project or preset may still carry a spiral mode for a group that has no spirals
        if patternType == "lcl" and mode not in LCL_OPTIMIZATION_MODES:
            self.recordSkip(startIdx, endIdx, patternType, "optSkipNoSpirals")
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

    # Segment arrays are fixed for the whole solve of one group, so they are built once and reused
    def baselineSegmentsFor(self, baselineAxis):
        cached = self.baselineSegmentCache
        if cached is not None and cached[0] is baselineAxis:
            return cached[1]
        segments = prepareSegments(baselineAxis)
        self.baselineSegmentCache = (baselineAxis, segments)
        return segments

    def evaluateSlew(self, baselineAxis, candidatePoints):
        return maxDistanceToPolyline(candidatePoints, self.baselineSegmentsFor(baselineAxis))

    # --- Lateral slew profile ---

    # Human readable element sequence of one group, used by the slew report table
    def describeElementPattern(self, patternType):
        return "L-C-L" if patternType == "lcl" else "L-S-C-S-L"

    # Signed perpendicular offsets of an accepted candidate axis, run once per optimized group
    def recordSlewProfile(self, groupSlot, frame, geometry, baselineAxis):
        samplingStarted = time.perf_counter()
        try:
            return self.recordSlewProfileSamples(groupSlot, frame, geometry, baselineAxis)
        finally:
            self.timingMs["samplingMs"] += (time.perf_counter() - samplingStarted) * 1000.0

    def recordSlewProfileSamples(self, groupSlot, frame, geometry, baselineAxis):
        samplePoints = geometry["samplePoints"]
        if len(samplePoints) < 2:
            return 0.0, 0.0

        vertices = np.asarray(samplePoints, dtype=float)
        steps = np.sqrt(np.einsum("ij,ij->i", np.diff(vertices, axis=0), np.diff(vertices, axis=0)))
        cumulativeLength = np.concatenate(([0.0], np.cumsum(steps)))
        totalChordLength = float(cumulativeLength[-1])
        if totalChordLength <= 1e-9:
            return 0.0, 0.0

        turnSign = frame["turnSign"]

        points = np.asarray(samplePoints, dtype=float)
        distances, nearestPoints, baselineDirections = nearestOnPolyline(
            points, self.baselineSegmentsFor(baselineAxis))
        offsetDirections = points - nearestPoints
        # Offsetting towards the arc centre enlarges the radius, the opposite side cuts towards the PI apex
        towardsCentre = (baselineDirections[:, 0] * offsetDirections[:, 1] -
                         baselineDirections[:, 1] * offsetDirections[:, 0]) * turnSign
        # Positive slew points towards the centre of curvature, away from the PI apex, enlarging R
        slewSigns = np.where(towardsCentre > 0, 1.0, -1.0)
        # Chord sampling runs marginally short of the true arc, so positions are kept as a group fraction
        fractions = np.asarray(cumulativeLength, dtype=float) / totalChordLength
        offsetsMm = slewSigns * distances * 1000.0

        groupSamples = list(zip(fractions.tolist(), offsetsMm.tolist()))
        peakSample = max(groupSamples, key=lambda sample: abs(sample[1]))
        # Zero anchors keep the plotted profile flat between optimized groups
        self.slewSamples.append((groupSlot, 0.0, 0.0))
        self.slewSamples.extend((groupSlot, fraction, offsetMm) for fraction, offsetMm in groupSamples)
        self.slewSamples.append((groupSlot, 1.0, 0.0))
        return peakSample[0], peakSample[1]

    # Collapse every recorded sample into the plot ready arrays and the corridor wide aggregates
    def buildSlewProfile(self):
        if not self.slewSamples:
            return {
                "slewProfileStationKm": np.array([], dtype=float),
                "slewProfileOffsetMm": np.array([], dtype=float),
                "shiftedLengthKm": 0.0,
                "meanSlewCurvedM": 0.0,
                "maxSlewStationKm": None,
            }

        ordered = sorted(self.slewSamples, key=lambda sample: sample[0])
        stationKm = np.array([sample[0] for sample in ordered], dtype=float)
        offsetMm = np.array([sample[1] for sample in ordered], dtype=float)

        shiftedLengthKm = 0.0
        for index in range(1, len(stationKm)):
            spanKm = float(stationKm[index] - stationKm[index-1])
            # A span counts as shifted only when both of its ends clear the visibility threshold
            if spanKm > 0 and min(abs(offsetMm[index]), abs(offsetMm[index-1])) > SLEW_VISIBLE_THRESHOLD_MM:
                shiftedLengthKm += spanKm

        curvedOffsets = np.abs(offsetMm[np.abs(offsetMm) > SLEW_ZERO_EPSILON_MM])
        peakIndex = int(np.argmax(np.abs(offsetMm)))

        return {
            "slewProfileStationKm": stationKm,
            "slewProfileOffsetMm": offsetMm,
            "shiftedLengthKm": float(shiftedLengthKm),
            "meanSlewCurvedM": float(np.mean(curvedOffsets) / 1000.0) if curvedOffsets.size else 0.0,
            "maxSlewStationKm": float(stationKm[peakIndex]),
        }

    # --- Cumulative chainage rebuild ---

    # New length in metres of one element, from the optimizer override or the untouched baseline
    def elementLengthM(self, k):
        override = self.newElementData.get(k)
        if override is not None:
            return float(override["lengthM"])

        element = self.elements[k]
        baselineLengthM = (element["staEnd"] - element["staStart"]) * 1000.0
        endpoints = self.newLineEndpoints.get(k)
        if element["type"] != "Line" or not endpoints:
            return float(baselineLengthM)

        # A moved straight keeps its stationing length minus whatever the neighbouring curves consumed
        startX, startY = endpoints.get("startXY", (element["startX"], element["startY"]))
        endX, endY = endpoints.get("endXY", (element["endX"], element["endY"]))
        newChordM = float(np.hypot(endX - startX, endY - startY))
        return float(baselineLengthM - (self.lineBaselineLength(element) - newChordM))

    # Walk every element from the alignment start so the station array is monotonic by construction
    def rebuildCumulativeChainage(self):
        stations = []
        runningStationKm = float(self.elements[0]["staStart"]) if self.elements else 0.0
        for k in range(len(self.elements)):
            lengthM = self.elementLengthM(k)
            # A negative length would mean the solver overspent a tangent, never emit a retrograde step
            if lengthM < 0.0:
                self.hasClampedChainage = True
                lengthM = 0.0
            lengthKm = lengthM / 1000.0
            stations.append((runningStationKm, runningStationKm + lengthKm))
            runningStationKm += lengthKm
        self.elementStationsKm = stations

    # Re-chained group boundaries, replacing the provisional stations recorded during the solve
    def resolveGroupStations(self):
        for group in self.summaryGroups:
            startIdx = group.get("startElemIndex")
            endIdx = group.get("endElemIndex")
            if startIdx is None or endIdx is None:
                continue
            group["startKm"] = float(self.elementStationsKm[startIdx][0])
            group["endKm"] = float(self.elementStationsKm[endIdx-1][1])
            peakFraction = group.get("slewPeakFraction")
            if peakFraction is None:
                continue
            group["slewMaxStationKm"] = float(
                group["startKm"] + peakFraction * (group["endKm"] - group["startKm"]))

    # Place every recorded group fraction onto the re-chained corridor
    def resolveSlewSampleStations(self):
        resolved = []
        for groupSlot, fraction, offsetMm in self.slewSamples:
            group = self.summaryGroups[groupSlot]
            spanKm = group["endKm"] - group["startKm"]
            resolved.append((group["startKm"] + fraction * spanKm, offsetMm))
        self.slewSamples = resolved

    # Monotone piecewise linear map from baseline chainage onto the re-chained active alignment
    def buildChainageMap(self):
        mapBaselineKm, mapActiveKm = [], []
        nodes = [(float(self.elements[0]["staStart"]), float(self.elementStationsKm[0][0]))]
        for k, element in enumerate(self.elements):
            nodes.append((float(element["staEnd"]), float(self.elementStationsKm[k][1])))

        for baselineStationKm, activeStationKm in nodes:
            # Zero length elements share a node, so the later value simply replaces the earlier one
            if mapBaselineKm and baselineStationKm <= mapBaselineKm[-1] + CHAINAGE_EPSILON_KM:
                mapBaselineKm[-1] = baselineStationKm
                mapActiveKm[-1] = activeStationKm
                continue
            mapBaselineKm.append(baselineStationKm)
            mapActiveKm.append(activeStationKm)

        return (np.array(mapBaselineKm, dtype=float), np.array(mapActiveKm, dtype=float))

    # Full chainage span of the imported alignment, the denominator of the shifted length share
    def evaluatedLengthKm(self):
        stations = self.lxml.get("stationHorizontal", [])
        if len(stations) < 2:
            return 0.0
        return float(max(stations) - min(stations))

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

    # --- Closed form envelope solving ---

    # Arc length follows directly from the deflection minus the two spiral angles, no geometry build
    def arcLengthFor(self, frame, radius, entryLength, exitLength):
        return radius * abs(frame["deflection"]) - 0.5 * (entryLength + exitLength)

    # Smallest radius whose arc still satisfies the minimum element length
    def minimumRadiusForArcLength(self, frame, entryLength, exitLength, minimumLength):
        deflection = abs(frame["deflection"])
        if deflection < 1e-12:
            return np.inf
        return (minimumLength + 0.5 * (entryLength + exitLength)) / deflection

    # Longest combined spiral length whose arc still satisfies the minimum element length
    def maximumSpiralSumForArcLength(self, frame, radius, minimumLength):
        return 2.0 * (radius * abs(frame["deflection"]) - minimumLength)

    # Mean of the entry and exit clothoid shifts at one radius
    def meanClothoidShift(self, radius, entryLength, exitLength):
        return 0.5 * (self.clothoidShiftAndFoot(entryLength, radius)[1] +
                      self.clothoidShiftAndFoot(exitLength, radius)[1])

    # Derivative of the mean clothoid shift with respect to radius, used by the Newton step
    def meanClothoidShiftDerivative(self, radius, entryLength, exitLength):
        if radius <= 0:
            return 0.0
        total = 0.0
        for length in (entryLength, exitLength):
            if length > 0:
                total += -(length**2)/(24.0*radius**2) + 3.0*(length**4)/(2688.0*radius**4)
        return 0.5 * total

    # Lateral offset at the arc apex against the baseline, both inscribed in the same fixed tangents
    def slewApexFor(self, frame, radius, entryLength, exitLength, radiusOld, entryOld, exitOld):
        secantHalf = 1.0 / math.cos(0.5 * abs(frame["deflection"]))
        return ((radius - radiusOld) * (secantHalf - 1.0) +
                (self.meanClothoidShift(radius, entryLength, exitLength) -
                 self.meanClothoidShift(radiusOld, entryOld, exitOld)) * secantHalf)

    # Radius whose apex offset exactly reaches the envelope, Newton on the analytic derivative
    def solveRadiusForEnvelope(self, frame, radiusOld, entryLength, exitLength, targetSlew):
        secantHalf = 1.0 / math.cos(0.5 * abs(frame["deflection"]))
        # A near straight deflection makes the apex identity degenerate, no analytic seed exists
        if secantHalf - 1.0 < 1e-6:
            return None

        baselineShift = self.meanClothoidShift(radiusOld, entryLength, exitLength)
        # Linear root ignoring the clothoid shift term, always within centimetres of the answer
        radius = radiusOld + targetSlew / (secantHalf - 1.0)
        for _ in range(NEWTON_MAX_ITER):
            residual = ((radius - radiusOld) * (secantHalf - 1.0) +
                        (self.meanClothoidShift(radius, entryLength, exitLength) - baselineShift) * secantHalf
                        - targetSlew)
            derivative = ((secantHalf - 1.0) +
                          secantHalf * self.meanClothoidShiftDerivative(radius, entryLength, exitLength))
            if abs(derivative) < 1e-12:
                return None
            step = residual / derivative
            radius -= step
            if radius <= 0:
                return None
            if abs(step) < NEWTON_TOLERANCE_M:
                break
        return radius

    # --- Bracketed search ---

    # Largest feasible value inside an analytically seeded bracket, bounded work unlike bisectMaximize
    def refineWithinBracket(self, feasibleFn, lowValue, seedValue, expandStep):
        if not feasibleFn(lowValue):
            return lowValue, False

        low = lowValue
        high = seedValue
        if feasibleFn(high):
            low = high
            # The seed was conservative, so step outward a bounded number of times to find the ceiling
            for _ in range(BRACKET_EXPAND_STEPS):
                high = low + expandStep
                if not feasibleFn(high):
                    break
                low = high
                expandStep *= 2.0
            else:
                return low, True

        for _ in range(BRACKET_REFINE_STEPS):
            if high - low < BISECTION_TOLERANCE_M:
                break
            mid = 0.5 * (low + high)
            if feasibleFn(mid):
                low = mid
            else:
                high = mid
        return low, True

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

    # --- Minimum element length gates ---

    # Closed form gate, cheap enough to run before any geometry is sampled
    def isArcLengthAcceptable(self, frame, radius, entryLength, exitLength):
        arcLengthM = self.arcLengthFor(frame, radius, entryLength, exitLength)
        if arcLengthM >= self.lMinM:
            return True
        # An arc already under L_min may stay there as long as the optimization does not shorten it
        return arcLengthM >= self.baselineArcLengthM - ARC_IMPROVEMENT_EPSILON_M

    # Lowest arc length the search may aim for, the relaxation moves the floor down to the baseline
    def effectiveArcFloorM(self):
        return min(self.lMinM, self.baselineArcLengthM)

    # Remaining length of one bounding straight once the curve's tangent point has moved onto it
    def straightLengthAfter(self, lineElement, tangentPoint, isLineBefore):
        if lineElement is None or lineElement.get("isVirtual"):
            return np.inf
        endpoints = self.newLineEndpoints.get(lineElement["elemIndex"], {})
        if isLineBefore:
            fixedPoint = endpoints.get("startXY", (lineElement["startX"], lineElement["startY"]))
        else:
            fixedPoint = endpoints.get("endXY", (lineElement["endX"], lineElement["endY"]))
        return float(np.hypot(tangentPoint[0] - fixedPoint[0], tangentPoint[1] - fixedPoint[1]))

    # Both bounding straights must still hold L_min for the sub L_min arc relaxation to apply
    def boundingStraightsKeepReserve(self, geometry):
        candidates = ((self.straightLengthAfter(self.groupLineBefore, geometry["ts"], True),
                       self.baselineEntryStraightM),
                      (self.straightLengthAfter(self.groupLineAfter, geometry["st"], False),
                       self.baselineExitStraightM))
        isSupported = True
        for candidateLengthM, baselineLengthM in candidates:
            if candidateLengthM >= self.lMinM:
                continue
            isSupported = False
            # Only a straight the optimization itself pushed under L_min is worth reporting as such
            if baselineLengthM >= self.lMinM:
                self.wasRelaxationBlockedByTangent = True
        return isSupported

    # Geometry aware half of the gate, only a relaxed arc has to prove the straights still fit
    def isCandidateSupported(self, frame, radius, entryLength, exitLength, geometry):
        if self.arcLengthFor(frame, radius, entryLength, exitLength) >= self.lMinM:
            return True
        return self.boundingStraightsKeepReserve(geometry)

    # Envelope exhaustion and a blocked relaxation look the same to the search, so they are named apart
    def exhaustionReason(self):
        return "optSkipShortTangent" if self.wasRelaxationBlockedByTangent else "optSkipEnvelopeExhausted"

    # --- Mode solvers ---

    def solveShiftArc(self, frame, R0, L0entry, L0exit, baselineAxis):
        def isFeasible(R):
            # The arc length gate is closed form, so an infeasible radius costs no sampled geometry
            if not self.isArcLengthAcceptable(frame, R, L0entry, L0exit):
                return False
            geometry = self.buildCandidateGeometry(frame, R, L0entry, L0exit)
            if geometry is None:
                return False
            if not self.isCandidateSupported(frame, R, L0entry, L0exit, geometry):
                return False
            return self.evaluateSlew(baselineAxis, geometry["samplePoints"]) <= self.dMaxM

        if not isFeasible(R0):
            # A blocked relaxation is a tangent problem, not a minimum arc length problem
            reason = "optSkipShortTangent" if self.wasRelaxationBlockedByTangent else "optSkipLMinViolated"
            return {"feasible": False, "reason": reason}

        analyticRadius = self.solveRadiusForEnvelope(frame, R0, L0entry, L0exit, self.dMaxM)
        if analyticRadius is None or analyticRadius <= R0:
            Rnew, _ = self.bisectMaximize(isFeasible, R0, max(1.0, R0*0.1))
        else:
            Rnew, _ = self.refineWithinBracket(isFeasible, R0, analyticRadius,
                                               max(0.05, (analyticRadius - R0) * 0.05))

        if Rnew - R0 < 0.01:
            return {"feasible": False, "reason": self.exhaustionReason()}
        return {"feasible": True, "Rnew": Rnew, "Lentry": L0entry, "Lexit": L0exit}

    # Largest spiral length allowed by the shared tangent budget, the arc floor and L_k,max
    def spiralLengthCeiling(self, frame, radius, ownLength, otherLength, budget):
        byBudget = ownLength + self.resolveSharedLine(budget, np.inf, self.lMinM)
        byArc = self.maximumSpiralSumForArcLength(frame, radius, self.effectiveArcFloorM()) - otherLength
        return max(ownLength, min(byBudget, byArc, self.lkMaxM))

    # Transition lengths that keep the spiral angle L/(2R) of the imported curve at a new radius
    def coupledSpiralLengths(self, R0, L0entry, L0exit, radius, entryBudget, exitBudget, allowEntry, allowExit):
        scale = radius / R0 if R0 > 0 else 1.0
        Lentry, Lexit = L0entry, L0exit

        if allowEntry and L0entry > 0:
            Lentry = min(max(L0entry * scale, L0entry), self.lkMaxM)
            Lentry = L0entry + self.resolveSharedLine(entryBudget, Lentry - L0entry, self.lMinM)
        if allowExit and L0exit > 0:
            Lexit = min(max(L0exit * scale, L0exit), self.lkMaxM)
            Lexit = L0exit + self.resolveSharedLine(exitBudget, Lexit - L0exit, self.lMinM)

        return Lentry, Lexit

    def solveShiftAndExtend(self, frame, R0, L0entry, L0exit, baselineAxis, entryBudget, exitBudget, allowEntry, allowExit):
        # Solving the radius first would spend the whole envelope before the clothoids were looked at,
        # which is why this mode used to collapse onto mode 3. Radius and transitions therefore grow
        # together off one parameter, holding the spiral angle constant, and a capped transition
        # simply leaves the remaining envelope to the radius alone.
        def candidateAt(radius):
            return self.coupledSpiralLengths(R0, L0entry, L0exit, radius,
                                             entryBudget, exitBudget, allowEntry, allowExit)

        def isFeasible(radius):
            Lentry, Lexit = candidateAt(radius)
            if not self.isArcLengthAcceptable(frame, radius, Lentry, Lexit):
                return False
            geometry = self.buildCandidateGeometry(frame, radius, Lentry, Lexit)
            if geometry is None:
                return False
            if not self.isCandidateSupported(frame, radius, Lentry, Lexit, geometry):
                return False
            return self.evaluateSlew(baselineAxis, geometry["samplePoints"]) <= self.dMaxM

        if not isFeasible(R0):
            reason = "optSkipShortTangent" if self.wasRelaxationBlockedByTangent else "optSkipLMinViolated"
            return {"feasible": False, "reason": reason}

        # The fixed spiral seed overshoots because coupled growth spends more envelope, the bracket copes
        analyticRadius = self.solveRadiusForEnvelope(frame, R0, L0entry, L0exit, self.dMaxM)
        if analyticRadius is None or analyticRadius <= R0:
            Rnew, _ = self.bisectMaximize(isFeasible, R0, max(1.0, R0*0.1))
        else:
            Rnew, _ = self.refineWithinBracket(isFeasible, R0, analyticRadius,
                                               max(0.05, (analyticRadius - R0) * 0.05))

        Lentry, Lexit = candidateAt(Rnew)
        if Rnew - R0 < 0.01 and Lentry - L0entry < 0.01 and Lexit - L0exit < 0.01:
            return {"feasible": False, "reason": self.exhaustionReason()}

        return {"feasible": True, "Rnew": Rnew, "Lentry": Lentry, "Lexit": Lexit}

    def solveExtendSpirals(self, frame, R0, L0entry, L0exit, baselineAxis, entryBudget, exitBudget, allowEntry, allowExit):
        if L0entry <= 0 or L0exit <= 0:
            return {"feasible": False, "reason": "optSkipNoSpirals"}

        Lentry, Lexit = L0entry, L0exit

        if allowEntry:
            def isFeasibleEntry(L):
                if L > self.lkMaxM:
                    return False
                if not self.isArcLengthAcceptable(frame, R0, L, Lexit):
                    return False
                if self.resolveSharedLine(entryBudget, L - L0entry, self.lMinM) < L - L0entry - 1e-6:
                    return False
                geometry = self.buildCandidateGeometry(frame, R0, L, Lexit)
                if geometry is None:
                    return False
                if not self.isCandidateSupported(frame, R0, L, Lexit, geometry):
                    return False
                return self.evaluateSlew(baselineAxis, geometry["samplePoints"]) <= self.dMaxM
            ceiling = self.spiralLengthCeiling(frame, R0, L0entry, Lexit, entryBudget)
            Lentry, _ = self.refineWithinBracket(isFeasibleEntry, L0entry, ceiling, max(1.0, L0entry*0.2))

        if allowExit:
            def isFeasibleExit(L):
                if L > self.lkMaxM:
                    return False
                if not self.isArcLengthAcceptable(frame, R0, Lentry, L):
                    return False
                if self.resolveSharedLine(exitBudget, L - L0exit, self.lMinM) < L - L0exit - 1e-6:
                    return False
                geometry = self.buildCandidateGeometry(frame, R0, Lentry, L)
                if geometry is None:
                    return False
                if not self.isCandidateSupported(frame, R0, Lentry, L, geometry):
                    return False
                return self.evaluateSlew(baselineAxis, geometry["samplePoints"]) <= self.dMaxM
            ceiling = self.spiralLengthCeiling(frame, R0, L0exit, Lentry, exitBudget)
            Lexit, _ = self.refineWithinBracket(isFeasibleExit, L0exit, ceiling, max(1.0, L0exit*0.2))

        if Lentry - L0entry < 0.01 and Lexit - L0exit < 0.01:
            return {"feasible": False, "reason": self.exhaustionReason()}
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
            # A transition never grows past the configured ceiling, whatever the envelope still allows
            return Rnew, min(Lentry, max(L0entry, self.lkMaxM)), min(Lexit, max(L0exit, self.lkMaxM))

        def isFeasible(s):
            Rnew, Lentry, Lexit = candidateAt(s)
            if not self.isArcLengthAcceptable(frame, Rnew, Lentry, Lexit):
                return False
            geometry = self.buildCandidateGeometry(frame, Rnew, Lentry, Lexit)
            if geometry is None:
                return False
            if not self.isCandidateSupported(frame, Rnew, Lentry, Lexit, geometry):
                return False
            return self.evaluateSlew(baselineAxis, geometry["samplePoints"]) <= self.dMaxM

        # The radius floor bounds the shift, so the bracket is known before any sampling
        sMax, _ = self.refineWithinBracket(isFeasible, 0.0, R0 - Rfloor, max(0.05, self.dMaxM*0.2))
        if sMax < 0.01:
            return {"feasible": False, "reason": self.exhaustionReason()}

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

        # Gates below compare against this group's own baseline, so prime it before any candidate runs
        self.baselineArcLengthM = self.arcLengthBaseline(arcElement)
        self.groupLineBefore = lineBefore
        self.groupLineAfter = lineAfter
        self.baselineEntryStraightM = self.availableLineBudget(lineBefore)
        self.baselineExitStraightM = self.availableLineBudget(lineAfter)
        self.wasRelaxationBlockedByTangent = False

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
            self.recordSkip(startIdx, endIdx, patternType, result.get("reason", self.exhaustionReason()))
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
                        entrySpiral, arcElement, exitSpiral, geometry, R0, Rnew, L0entry, Lentry, L0exit, Lexit, slewMax,
                        frame, baselineAxis)
        self.hasOptimizedAny = True

    def registerNewElement(self, k, staStart, staEnd, kappaStart, kappaEnd, radiusStart, radiusEnd, startXY, endXY, centerXY=None, piXY=None, lengthM=None):
        self.newElementData[k] = {
            "staStart": staStart, "staEnd": staEnd,
            # The intrinsic length survives re-chaining, the provisional stations above do not
            "lengthM": float(lengthM) if lengthM is not None else float((staEnd - staStart) * 1000.0),
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
                  entrySpiral, arcElement, exitSpiral, geometry, R0, Rnew, L0entry, Lentry, L0exit, Lexit, slewMax,
                  frame, baselineAxis):
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
                                     np.inf, Rnew, geometry["ts"], geometry["arcStart"], piXY=entryPi,
                                     lengthM=Lentry)
            arcIdx = startIdx + 1
        else:
            arcIdx = startIdx

        self.registerNewElement(arcIdx, entryEndStation, arcEndStation, arcKappa, arcKappa,
                                 Rnew, Rnew, geometry["arcStart"], geometry["arcEnd"], centerXY=geometry["center"],
                                 lengthM=geometry["arcLength"])

        if exitSpiral is not None:
            exitPi = vecAdd(geometry["arcEnd"], self.tangentAtPoint(geometry["exitSpiralPoints"], 0))
            self.registerNewElement(arcIdx+1, arcEndStation, exitEndStation, arcKappa, 0.0,
                                     Rnew, np.inf, geometry["arcEnd"], geometry["st"], piXY=exitPi,
                                     lengthM=Lexit)

        self.updateLineEndpoint(lineBefore, updateStart=False, newPoint=geometry["ts"])
        self.updateLineEndpoint(lineAfter, updateStart=True, newPoint=geometry["st"])

        lengthDelta = (Lentry - L0entry) + (Lexit - L0exit) + (geometry["arcLength"] - self.arcLengthBaseline(arcElement))
        # Samples are recorded as a fraction of the group so re-chaining can place them afterwards
        groupSlot = len(self.summaryGroups)
        slewPeakFraction, _ = self.recordSlewProfile(groupSlot, frame, geometry, baselineAxis)

        self.summaryGroups.append({
            "groupIndex": len(self.summaryGroups), "patternType": patternType, "mode": mode,
            "elementPattern": self.describeElementPattern(patternType),
            "startElemIndex": int(startIdx), "endElemIndex": int(endIdx),
            "slewPeakFraction": float(slewPeakFraction),
            "startKm": float(groupStartStation), "endKm": float(exitEndStation), "status": "optOk",
            "radiusOldM": float(R0), "radiusNewM": float(Rnew),
            "spiralLengthsOldM": [float(L0entry), float(L0exit)], "spiralLengthsNewM": [float(Lentry), float(Lexit)],
            "offsetOldM": float(self.clothoidShiftAndFoot(L0entry, R0)[1]), "offsetNewM": float(geometry["deltaREntry"]),
            "slewMaxM": float(slewMax), "slewMaxStationKm": float(groupStartStation), "lengthDeltaM": float(lengthDelta),
        })

    def recordSkip(self, startIdx, endIdx, patternType, reasonCode):
        self.summaryGroups.append({
            "groupIndex": len(self.summaryGroups), "patternType": patternType or "unknown", "mode": OPTIMIZATION_MODE_NONE,
            "elementPattern": self.describeElementPattern(patternType),
            "startElemIndex": int(startIdx), "endElemIndex": int(endIdx),
            "startKm": float(self.elements[startIdx]["staStart"]), "endKm": float(self.elements[endIdx-1]["staEnd"]),
            "status": reasonCode,
            "radiusOldM": None, "radiusNewM": None, "spiralLengthsOldM": None, "spiralLengthsNewM": None,
            "offsetOldM": None, "offsetNewM": None, "slewMaxM": None, "slewMaxStationKm": None, "lengthDeltaM": None,
        })

    def buildSummary(self):
        optimizedGroups = [g for g in self.summaryGroups if g["status"] == "optOk"]
        slews = [g["slewMaxM"] for g in optimizedGroups]
        profile = self.buildSlewProfile()
        evaluatedLengthKm = self.evaluatedLengthKm()
        shiftedLengthKm = profile["shiftedLengthKm"]
        return {
            "modeLcl": self.modeLcl, "modeLscsl": self.modeLscsl, "dMaxM": self.dMaxM, "lMinM": self.lMinM,
            "maxSlewM": float(max(slews)) if slews else 0.0,
            "meanSlewM": float(sum(slews)/len(slews)) if slews else 0.0,
            "optimizedGroupCount": len(optimizedGroups),
            "skippedGroupCount": len(self.summaryGroups) - len(optimizedGroups),
            "evaluatedLengthKm": evaluatedLengthKm,
            "shiftedLengthKm": shiftedLengthKm,
            "shiftedLengthPercent": (100.0 * shiftedLengthKm / evaluatedLengthKm) if evaluatedLengthKm > 0 else 0.0,
            "maxSlewStationKm": profile["maxSlewStationKm"],
            "meanSlewCurvedM": profile["meanSlewCurvedM"],
            "slewProfileStationKm": profile["slewProfileStationKm"],
            "slewProfileOffsetMm": profile["slewProfileOffsetMm"],
            "timingMs": dict(self.timingMs),
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
            pairIndex = 2 * k
            # Every element takes its re-chained station, not just the ones the optimizer touched
            stationHorizontalNew[pairIndex] = self.elementStationsKm[k][0]
            stationHorizontalNew[pairIndex+1] = self.elementStationsKm[k][1]

            override = self.newElementData.get(k)
            if override is None:
                continue
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

        # The map lets stops, markers and reports follow the alignment onto its new stationing
        chainageMapBaselineKm, chainageMapActiveKm = self.buildChainageMap()
        lxml["chainageMapBaselineKm"] = chainageMapBaselineKm
        lxml["chainageMapActiveKm"] = chainageMapActiveKm

        return self.buildOptimizedElementsDict()

    def buildOptimizedElementsDict(self):
        lineStartX, lineStartY, lineEndX, lineEndY, lineStationStart = [], [], [], [], []
        spiralStartX, spiralStartY, spiralPIX, spiralPIY, spiralEndX, spiralEndY = [], [], [], [], [], []
        spiralStationStart, spiralLength, spiralRadiusStart, spiralRadiusEnd, spiralRot = [], [], [], [], []
        curveStartX, curveStartY, curveCenterX, curveCenterY, curveEndX, curveEndY = [], [], [], [], [], []
        curveStationStart, curveRadius, curveRot = [], [], []

        for k, elem in enumerate(self.elements):
            override = self.newElementData.get(k)
            # Stationing always comes from the re-chained array so every element type stays in step
            staStart = self.elementStationsKm[k][0]
            if elem["type"] == "Line":
                lineOverride = self.newLineEndpoints.get(k, {})
                startX, startY = lineOverride.get("startXY", (elem["startX"], elem["startY"]))
                endX, endY = lineOverride.get("endXY", (elem["endX"], elem["endY"]))
                lineStartX.append(startX); lineStartY.append(startY)
                lineEndX.append(endX); lineEndY.append(endY)
                lineStationStart.append(staStart)
            elif elem["type"] == "Spiral":
                if override:
                    spiralStartX.append(override["startX"]); spiralStartY.append(override["startY"])
                    spiralEndX.append(override["endX"]); spiralEndY.append(override["endY"])
                    spiralPIX.append(override["piX"]); spiralPIY.append(override["piY"])
                    spiralStationStart.append(staStart)
                    spiralLength.append(override["lengthM"])
                    spiralRadiusStart.append(override["radiusStart"]); spiralRadiusEnd.append(override["radiusEnd"])
                else:
                    spiralStartX.append(elem["startX"]); spiralStartY.append(elem["startY"])
                    spiralEndX.append(elem["endX"]); spiralEndY.append(elem["endY"])
                    spiralPIX.append(elem["piX"]); spiralPIY.append(elem["piY"])
                    spiralStationStart.append(staStart)
                    spiralLength.append(elem["length"])
                    spiralRadiusStart.append(elem["radiusStart"]); spiralRadiusEnd.append(elem["radiusEnd"])
                spiralRot.append(elem["rot"])
            elif elem["type"] == "Curve":
                if override:
                    curveStartX.append(override["startX"]); curveStartY.append(override["startY"])
                    curveEndX.append(override["endX"]); curveEndY.append(override["endY"])
                    curveCenterX.append(override["centerX"]); curveCenterY.append(override["centerY"])
                    curveStationStart.append(staStart)
                    curveRadius.append(override["radiusStart"])
                else:
                    curveStartX.append(elem["startX"]); curveStartY.append(elem["startY"])
                    curveEndX.append(elem["endX"]); curveEndY.append(elem["endY"])
                    curveCenterX.append(elem["centerX"]); curveCenterY.append(elem["centerY"])
                    curveStationStart.append(staStart)
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
