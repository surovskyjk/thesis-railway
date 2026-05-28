# COYPU

A desktop application for railway track geometry analysis and train performance simulation, developed as part of a master's thesis. The tool follows the Czech railway standard CSN 73 6360-1.

Built with Python and PySide6.

---

## Main Features

- Parse and visualize LandXML horizontal alignment files (lines, spirals, curves; cant; vertical profile)
- Parse line speed limits from XML TTP files (Czech national infrastructure registry format)
- Append multiple LandXML or TTP files to build a longer corridor
- Design cant (D) and calculate permissible speed profiles for four speed profiles (difference in global max cant deficiency): V100, V130, V150, VK
- Enforce norm limits: cant ramp gradient (n), rate of change of cant deficiency (nI), abrupt change of cant deficiency (deltaI)
- Simulate train kinematics using a forward-backward pass algorithm with traction, resistance, and braking
- Interactive map viewer showing the alignment geometry coloured by speed
- Multi-language UI: Czech, English, German
- Export geometry report (text) and kinematics results (CSV)

---

## Application Settings

The following parameters can be adjusted in the Settings dialog:

- `vInit` - initial trial speed for the iterative geometry solver [km/h]
- `maxD` - maximum permissible cant [mm]
- `iterationStep` - speed reduction step per solver iteration [km/h]
- `maxIterations` - maximum number of solver iterations
- `designApproach` - norm approach used for limit lookup (standard / alternative)
- EPSG code - coordinate reference system of the input LandXML file

---

## Norm Limit Tables (Configurable, CSV Import/Export)

The geometry solver uses four speed-dependent norm limit tables. Each can be edited in the Settings dialog and imported or exported as CSV.

- `I` - maximum permissible cant deficiency by speed range and design approach [mm]
- `DI` - maximum permissible sudden cant deficiency change (deltaI) [mm]
- `nLin` - cant ramp slope limits (n), governing the rate of D change along a spiral
- `nILin` - cant deficiency change rate coefficient (nI), governing the rate of I change along a spiral

CSV format for geometry limits: one row per speed band, first column is the section identifier (`I`, `DI`, `nLin`, or `nILin`), followed by the numerical values. A header row is expected and skipped on import.

---

## Vehicle Data (CSV Import/Export)

Vehicle parameters can be imported and exported as a single CSV file. The file uses a section identifier in the first column:

- `Res` - Davis resistance coefficients: name, A, B, C [N/kN]
- `Trac` - Traction curve segments: name, V_bottom, V_top, b0, b1, b2 (piecewise polynomial F = b0 + b1*v + b2*v^2 [kN], V [km/h])
- `Param` - Train parameters: name, rotational mass factor, total weight [t], train length [m]

Multiple vehicles can be defined; each is simulated independently.

---

## Train Stops (CSV Import/Export)

Scheduled stops can be imported and exported via CSV with columns: station [km], dwell time [s], name.

---

## Geometry Calculation

The geometry engine uses an iterative convergence loop that starts from `vInit` and reduces the trial speed in discrete steps until the computed permissible speed matches the trial speed.

Within each iteration:

- Stage 1 - designs cant D for each alignment element based on the equilibrium cant formula, constrained by the cant ramp slope (n limit) through a forward and backward sweep; the less aggressive sweep is applied
- Stage 2 - designs cant deficiency I for each element constrained by nI and deltaI limits; again a forward and backward sweep are performed and the stricter result is used
- Stage 3 - enforces D continuity at zero-length element boundaries (element pair junctions)
- cantDefSpeed - computes an additional speed limit for spirals from the physical I change across the spiral, using both the nI-based formula and the virtual deltaI approach; the more lenient of the two is applied
- Stage 4 - computes the permissible speed for each element pair from the D+I formula; if the computed speed is lower than the trial speed, the trial speed is reduced and the loop repeats

Two calculation modes are available:

- Design mode (`runCalculationLoop`) - calculates optimal D for the given speed, then derives I and the permissible speed; produces one output profile using the default speed profile
- As-built mode (`runCalculationLoopI`) - uses the measured cant from the LandXML file directly; derives I and permissible speed for all four speed profiles (V100, V130, V150, VK)

After convergence, D and I values are rounded and the final speed is verified against the D+I formula.

---

## Vehicle Kinematics Simulation

Train motion is simulated by numerical integration of the equation of motion at 1 m intervals along the alignment.

- Forward pass - accelerates the train from initial speed using tractive effort, subtracting vehicle resistance, gradient resistance, and curve resistance; speed is capped at the permissible speed profile at each step
- Backward pass - applies braking from the end of the section or from each speed reduction point, using a constant deceleration value
- Final speed profile - element-wise minimum of the forward and backward passes
- Train length look-ahead - the speed limit applied at each point is the minimum over a sliding window equal to the train length, so the full train must fit within each speed restriction

Track resistance components:

- Gradient resistance - proportional to slope [N/t per per-mille]
- Curve resistance - Rockl formula based on curve radius

Vehicle resistance uses the Davis equation: F_res = A + B*v + C*v^2

Traction is defined as a piecewise polynomial over speed bands: F_trac = b0 + b1*v + b2*v^2

Train stops are enforced by setting the speed limit to zero at the stop station. A configurable dwell time is added to the travel time.

---

## Project Structure

- `main.py` - application entry point
- `gui.py` - main window, menus, plot canvases
- `gui_overlay.py` - settings and vehicle dialogs
- `geometry_engine.py` - cant design and permissible speed calculation
- `vehicle_engine.py` - train kinematics simulation
- `readfile.py` - LandXML and XML TTP parsers, coordinate transformations
- `map_viewer.py` - interactive Folium map widget
- `default_values.py` - built-in default norm limits and vehicle parameters
- `lang.py` - UI strings for Czech, English, and German
- `tests/` - unit tests for geometry engine functions
