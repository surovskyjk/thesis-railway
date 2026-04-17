import numpy as np

class VehicleCalculator:
    def __init__(self, dataStorage):
        self.data = dataStorage

    def speedLimitsToTime(self):
        settings = self.data.get("settingsData", {})
        speedProfile = settings.get("speedLimitPlot", ["stationSpeed150", "speedLimits150"])
        trainMaxSpeed = float(settings.get("trainMaxSpeed", settings.get("vInit", [120])[0]))

        if speedProfile[0] == "unlimited":
            lxml = self.data.get("LandXML", {})
            stationHorizontal = lxml.get("stationHorizontal", np.array([]))
            if len(stationHorizontal) > 0:
                stationSpeedLimit = np.array([np.min(stationHorizontal), np.max(stationHorizontal)]) * 1000
                speedLimit = np.array([trainMaxSpeed, trainMaxSpeed])
            else:
                stationSpeedLimit = np.array([])
                speedLimit = np.array([])
        else:
            stationSpeedLimit = np.copy(self.data.get(speedProfile[0], []))
            if len(stationSpeedLimit) > 0:
                stationSpeedLimit = stationSpeedLimit * 1000
            speedLimit = np.copy(self.data.get(speedProfile[1], []))

        if len(speedLimit) > 0:
            speedLimit = np.clip(speedLimit, 0, trainMaxSpeed)

        if len(stationSpeedLimit) == 0:
            self.data["stationSpeedLimitM"] = np.array([])
            self.data["speedLimitsM"] = np.array([])
            self.data["speedLimitsT"] = np.array([])
            return

        speedLimitM = speedLimit / 3.6
        ds = np.diff(stationSpeedLimit)

        # Speed limit 0 check to prevent division by zero
        with np.errstate(divide='ignore', invalid='ignore'):
            dt = np.where(speedLimitM[:-1] > 0, ds / speedLimitM[:-1], 0)

        t = np.concatenate(([0], np.cumsum(dt)))

        self.data["stationSpeedLimitM"] = stationSpeedLimit
        self.data["speedLimitsM"] = speedLimitM
        self.data["speedLimitsT"] = t

    def calculateKinematics(self):
        """
        Calculates train kinematics using the equation of motion:
        acceleration = (F_traction - F_braking - F_resistance - F_track) / (mass * (1 + rot_mass_factor))
        """
        self.loadVehicleParameters()
        self.loadTrackData()

        if len(self.stationHorizontal) == 0:
            return

        # Discretization step in meters
        ds = 1.0
        
        # Simulation range based on horizontal alignment
        sStart = np.min(self.stationHorizontal) * 1000
        sEnd = np.max(self.stationHorizontal) * 1000
        stationsM = np.arange(sStart, sEnd + ds, ds)

        # Pre-calculate limits and track properties arrays for faster computing
        vLimitMps = np.zeros_like(stationsM)
        slopeArr = np.zeros_like(stationsM)
        curvArr = np.zeros_like(stationsM)
        
        for i, s in enumerate(stationsM):
            stationKm = s / 1000.0
            vLimitMps[i] = self.getSpeedLimitAt(stationKm) / 3.6
            slopeArr[i] = self.getSlopeAt(stationKm)
            curvArr[i] = self.getCurvatureAt(stationKm)

        # Apply explicit stops to vLimitMps
        for stop in self.trainStops:
            stopStationM = stop[0] * 1000.0
            idx = np.argmin(np.abs(stationsM - stopStationM))
            if np.abs(stationsM[idx] - stopStationM) <= ds:
                vLimitMps[idx] = 0.0

        # 1. Forward Pass (Acceleration and Cruising)
        vFwd = np.zeros_like(stationsM)
        vFwd[0] = min(vLimitMps[0], self.trainInitialSpeed / 3.6)
        for i in range(1, len(stationsM)):
            vPrev = vFwd[i-1]
            vPrevKmh = vPrev * 3.6

            # Evaluate forces (all in Newtons)
            forceTrac = self.getTractiveForce(vPrevKmh)
            forceRes = self.getVehicleResistance(vPrevKmh)
            forceTrack = self.getTrackResistance(slopeArr[i-1], curvArr[i-1])
            
            aFwd = (forceTrac - forceRes - forceTrack) / self.effectiveMass
            vNewSq = vPrev**2 + 2 * aFwd * ds
            
            vNew = np.sqrt(max(0.0, vNewSq))
            vFwd[i] = min(vNew, vLimitMps[i])

        # 2. Backward Pass (Braking to limits)
        vBwd = np.zeros_like(stationsM)
        vBwd[-1] = min(vLimitMps[-1], self.trainFinalSpeed / 3.6)
        
        for i in range(len(stationsM)-2, -1, -1):
            vNext = vBwd[i+1]
            vNextKmh = vNext * 3.6
            
            forceDyn = self.getDynamicBrakingForce(vNextKmh)
            forceMech = self.mechBrakeN
            forceBrake = forceDyn + forceMech
            
            forceRes = self.getVehicleResistance(vNextKmh)
            forceTrack = self.getTrackResistance(slopeArr[i], curvArr[i])
            
            # Braking deceleration (positive value) = total retarding forces / mass
            aDecel = (forceBrake + forceRes + forceTrack) / self.effectiveMass
            
            # Calculate required entry speed solving backwards
            vNewSq = vNext**2 + 2 * aDecel * ds
            vNew = np.sqrt(max(0.0, vNewSq))
            vBwd[i] = min(vNew, vLimitMps[i])

        # 3. Apply actual constrained speed curve
        vMps = np.minimum(vFwd, vBwd)

        # 4. Final Pass: Time and Acceleration calculations
        aMps2 = np.zeros_like(stationsM)
        tS = np.zeros_like(stationsM)
        forceTracArr = np.zeros_like(stationsM)
        forceBrakeArr = np.zeros_like(stationsM)
        forceResArr = np.zeros_like(stationsM)

        # Dwell times
        dwell_times = np.zeros_like(stationsM)
        applied_stop_indices = set()
        
        for stop in self.trainStops:
            stopStationM = stop[0] * 1000.0
            dwell_time = stop[1]
            idx = np.argmin(np.abs(stationsM - stopStationM))
            if np.abs(stationsM[idx] - stopStationM) <= ds:
                dwell_times[idx] += dwell_time
                applied_stop_indices.add(idx)

        # Automatic dwell times for contiguous 0 speed limit regions
        is_zero = (vLimitMps == 0)
        diff_zero = np.diff(is_zero.astype(int))
        zero_starts = np.where(diff_zero == 1)[0] + 1
        zero_ends = np.where(diff_zero == -1)[0]
        
        if len(is_zero) > 0:
            if is_zero[0]:
                zero_starts = np.insert(zero_starts, 0, 0)
            if is_zero[-1]:
                zero_ends = np.append(zero_ends, len(is_zero) - 1)

        for start, end in zip(zero_starts, zero_ends):
            region_indices = set(range(start, end + 1))
            if not region_indices.intersection(applied_stop_indices):
                dwell_times[start] += self.defaultDwellTime

        tS[0] = 0.0 + dwell_times[0]

        for i in range(1, len(stationsM)):
            vCurr = vMps[i]
            vPrev = vMps[i-1]
            vAvg = (vCurr + vPrev) / 2.0
            vAvgKmh = vAvg * 3.6
            
            if vAvg > 0.5: # Threshold to avoid near zero division 
                dt = ds / vAvg
                aMps2[i-1] = (vCurr**2 - vPrev**2) / (2 * ds)
            else:
                dt = ds / 0.5
                aMps2[i-1] = 0.0

            tS[i] = tS[i-1] + dt + dwell_times[i]

            # Calculate forces at this step
            F_res = self.getVehicleResistance(vAvgKmh) + self.getTrackResistance(slopeArr[i-1], curvArr[i-1])
            F_net = aMps2[i-1] * self.effectiveMass
            F_req = F_net + F_res
            
            forceResArr[i] = F_res
            if F_req > 0:
                forceTracArr[i] = min(F_req, self.getTractiveForce(vAvgKmh))
                forceBrakeArr[i] = 0.0
            else:
                forceTracArr[i] = 0.0
                forceBrakeArr[i] = abs(F_req)

        # Save last acceleration point for dimension match
        if len(aMps2) > 1:
            aMps2[-1] = aMps2[-2]
            forceTracArr[0] = forceTracArr[1]
            forceBrakeArr[0] = forceBrakeArr[1]
            forceResArr[0] = forceResArr[1]

        # Save calculated kinematics back to data storage
        self.data["kinematicsStationM"] = stationsM
        self.data["kinematicsSpeedM"] = vMps
        self.data["kinematicsTimeS"] = tS
        self.data["kinematicsAcceleration"] = aMps2
        self.data["kinematicsForceTractionKN"] = forceTracArr / 1000.0
        self.data["kinematicsForceBrakingKN"] = forceBrakeArr / 1000.0
        self.data["kinematicsForceResistanceKN"] = forceResArr / 1000.0

    def loadVehicleParameters(self):
        settings = self.data.get("settingsData", {})

        # Train parameters
        paramData = settings.get("trainParam", [["Placeholder BEMU", 1.08, 460]])
        if paramData and isinstance(paramData[0], (str, int, float)):
            paramData = [paramData]
        
        try:
            self.rotMass = float(paramData[0][1])
            self.massTonnes = float(paramData[0][2])
        except (IndexError, ValueError):
            self.rotMass = 1.08
            self.massTonnes = 460.0

        self.massKg = self.massTonnes * 1000.0

        # Determine effective mass: mass * (1 + rotMass)
        rotFactor = self.rotMass if self.rotMass >= 1.0 else (1.0 + self.rotMass)
        self.effectiveMass = self.massKg * rotFactor

        # Resistance coefficients (A, B, C)
        resData = settings.get("trainRes", [["Placeholder BEMU", 1, 1, 1]])
        if resData and isinstance(resData[0], (str, int, float)):
            resData = [resData]
        
        try:
            self.resA = float(resData[0][1])
            self.resB = float(resData[0][2])
            self.resC = float(resData[0][3])
        except (IndexError, ValueError):
            self.resA = self.resB = self.resC = 1.0

        # Traction coefficients
        tracData = settings.get("trainTrac", [["Placeholder BEMU", 0, 160, 1, 1, 1]])
        if tracData and isinstance(tracData[0], (str, int, float)):
            tracData = [tracData]
        self.trainTrac = tracData

        # Brake coefficients
        brakeData = settings.get("trainBrake", [["Placeholder BEMU", 0, 160, 0, 0, 0]])
        if brakeData and not isinstance(brakeData[0], list):
            brakeData = [brakeData]
        self.trainBrake = brakeData

        # Mechanical brake in N (input was in kN)
        self.mechBrakeN = float(settings.get("trainBrakeMech", 150.0)) * 1000.0
        
        self.trainInitialSpeed = float(settings.get("trainInitialSpeed", 0.0))
        self.trainFinalSpeed = float(settings.get("trainFinalSpeed", 0.0))
        self.defaultDwellTime = float(settings.get("defaultDwellTime", 30.0))
        self.trainStops = settings.get("trainStops", [])

    def loadTrackData(self):
        lxml = self.data.get("LandXML", {})
        self.stationHorizontal = lxml.get("stationHorizontal", np.array([]))
        self.curvature = lxml.get("curvature", np.array([]))
        self.stationVertical = lxml.get("stationVertical", np.array([]))
        self.slope = lxml.get("slope", np.array([]))

        # Retrieve speed limit profile
        settings = self.data.get("settingsData", {})
        speedProfile = settings.get("speedLimitPlot", ["stationSpeed150", "speedLimits150"])
        self.trainMaxSpeed = float(settings.get("trainMaxSpeed", settings.get("vInit", [120])[0]))

        if speedProfile[0] == "unlimited":
            if len(self.stationHorizontal) > 0:
                self.stationSpeedLimits = np.array([np.min(self.stationHorizontal), np.max(self.stationHorizontal)])
                self.speedLimits = np.array([self.trainMaxSpeed, self.trainMaxSpeed])
            else:
                self.stationSpeedLimits = np.array([])
                self.speedLimits = np.array([])
        else:
            self.stationSpeedLimits = self.data.get(speedProfile[0], np.array([]))
            self.speedLimits = self.data.get(speedProfile[1], np.array([]))

    def getSlopeAt(self, stationKm):
        if len(self.stationVertical) == 0 or len(self.slope) == 0:
            return 0.0
        # Interpolate slope as a step function (post)
        idx = np.searchsorted(self.stationVertical, stationKm, side='right') - 1
        idx = np.clip(idx, 0, len(self.slope) - 1)
        return self.slope[idx]

    def getCurvatureAt(self, stationKm):
        if len(self.stationHorizontal) == 0 or len(self.curvature) == 0:
            return 0.0
        # Linear interpolation for continuous curvature
        return np.interp(stationKm, self.stationHorizontal, self.curvature)

    def getSpeedLimitAt(self, stationKm):
        if len(self.stationSpeedLimits) == 0 or len(self.speedLimits) == 0:
            limit = self.trainMaxSpeed
        else:
            # Step function for speed limits (post)
            idx = np.searchsorted(self.stationSpeedLimits, stationKm, side='right') - 1
            idx = np.clip(idx, 0, len(self.speedLimits) - 1)
            limit = self.speedLimits[idx]
        return min(limit, self.trainMaxSpeed)

    def getTractiveForce(self, vKmh):
        """ Evaluates tractive force polynomial based on speed band. """
        for trac in self.trainTrac:
            try:
                vMin, vMax = float(trac[1]), float(trac[2])
                b0, b1, b2 = float(trac[3]), float(trac[4]), float(trac[5])
                
                if vMin <= vKmh <= vMax:
                    # Evaluates to Newtons: T = g * (b0 + b1*v + b2*v^2)
                    return 9.81 * (b0 + b1 * vKmh + b2 * (vKmh ** 2))
            except (IndexError, ValueError):
                continue
        return 0.0

    def getDynamicBrakingForce(self, vKmh):
        """ Evaluates dynamic braking force based on speed band. """
        for brk in self.trainBrake:
            try:
                vMin, vMax = float(brk[1]), float(brk[2])
                b0, b1, b2 = float(brk[3]), float(brk[4]), float(brk[5])
                
                if vMin <= vKmh <= vMax:
                    return 9.81 * (b0 + b1 * vKmh + b2 * (vKmh ** 2))
            except (IndexError, ValueError):
                continue
        return 0.0

    def getVehicleResistance(self, vKmh):
        """ Evaluates Davis equation for vehicle resistance, yields force in N. """
        o = self.resA + self.resB * vKmh + self.resC * (vKmh ** 2)
        return o * self.massTonnes * 9.81

    def getTrackResistance(self, slopePermille, curvature):
        """ Calculates track resistance forceTrack = forceGrad + forceCurve """
        g = 9.81
        # Force of gradient = m * g * (slope / 1000)
        forceGrad = self.massKg * g * (slopePermille / 1000.0)
        
        # Force of curvature based on typical empirical formula (e.g., Röckl approx 600/R)
        # Using F_curve (N) = mass_kg * g * 0.6 * |curvature|
        forceCurve = self.massKg * g * 0.6 * abs(curvature)
        
        return forceGrad + forceCurve