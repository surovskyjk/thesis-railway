# COYPU

**https://github.com/surovskyjk/COYPU**

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
- Interactive map viewer showing the alignment coloured by selected speed profile (TTP, V100, V130, V150, VK) with a colour-scale legend, a basemap selector, an OpenRailwayMap overlay with adjustable transparency, and markers for every scheduled stop
- Ribbon command bar (Project, Geometry, Simulation, View, Data series, Settings) with generated vector icons, compact labels and full-text tooltips
- Dockable, floatable and tabbed panels: workflow guide, XML source viewers with code folding, parsed data tables, plots and help
- All plots rendered with pyqtgraph, each with its own context menu offering the native export (SVG / PNG / CSV) plus detach to a large window, interaction modes, grid and station marker toggles, and series highlighting
- Chainage crosshair synchronised between the geometry plot, the speed profile, the longitudinal profile and the map
- Light and dark themes following the operating system, with a manual override
- Dock layout, theme and language persisted between sessions
- Multi-language UI: Czech, English, German
- Export geometry report (Text, PDF, Markdown or LaTeX) and kinematics results (CSV)
- Batch processing: merge several LandXML files with rebased chainage, run a matrix of stopping patterns x design approaches x an optional sensitivity sweep as isolated background variants, compare them on a dedicated overlay dashboard, and export every report, protocol and comparison table as one ZIP archive
- Native `.coypu` project files: one compressed archive holding the project metadata, every merged alignment with its raw imported assets, stops and TTP data, vehicle configurations, the cached GPK and cant deficiency results, and the saved viewport state, so a reopened project restores its plots without recalculating
- Extended project metadata dialog: title, author, contract number, date, notes, target norm, optional track / definition section and TUDU codes, and the coordinate system descriptor reused by the LandXML export
- Export the designed alignment back to LandXML 1.2 including the application header, the coordinate system, the horizontal geometry, the newly calculated cant D with its design speeds, and a vertical profile whose curve tangents are guaranteed never to overlap
- Unsaved changes tracker in the window title, a recent projects list, and a background recovery snapshot written every five minutes and offered for restore after a crash

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

## Vehicle Catalog and CSV Format

The `vehicles/` folder in the repository root is a catalog of ready-made vehicle CSV files, scanned automatically on
startup and offered as presets in the Vehicle Settings dialog and the standalone Vehicle Catalog browser. Drop an
extra CSV into `vehicles/` (next to the executable when running a packaged build) to add it to the catalog on the
next launch.

Vehicle parameters can also be imported and exported per vehicle as a single CSV file. The file uses a section
identifier in the first column:

- `Meta` - single line key/value metadata: `vehicleName`, `maxSpeedKmh`, `massTonnes`, `lengthM`, `brakeDecelMs2`,
  `maxTractiveForceKN` (informational only, does not clip the curve). Optional - a file without `Meta` rows still
  imports using the `Param`/`Res` values below.
- `Res` - Davis resistance coefficients: name, A, B, C [N/kN]
- `Trac` - Traction curve segments: name, V_bottom, V_top, b0, b1, b2 (piecewise polynomial F = b0 + b1*v + b2*v^2 [kN], V [km/h])
- `Param` - Train parameters: name, rotational mass factor, total weight [t], train length [m]

Multiple vehicles can be defined per project (1 to 5); each is simulated independently.

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

## Batch Processing and Variant Comparison

The Batch page runs many track variants unattended and compares them side by side.

- Multi-LandXML merger - select several LandXML files in one picker; they are concatenated end to end with chainage rebased so file N+1 continues where file N ends (or kept as imported for genuinely contiguous surveys), with a warning if a junction gap exceeds 100 m
- Variant matrix - cross a set of station CSV stopping patterns (e.g. Regional vs Express) with a set of design-approach combinations (standard / limit / minmax per I, deltaI, n, nI), optionally stepping one further parameter (D_max, cant gradient, braking deceleration, ...) across a `[min, max, step]` range
- Isolated execution - every variant runs the unmodified `GeometryCalculator` and `VehicleCalculator` engines against its own deep-copied data on a background thread, so the ribbon stays responsive and a failed or cancelled variant never aborts the rest of the batch
- Variant Comparison Dashboard - a third central view overlaying every variant's speed profile v(s) and cant deficiency I(s) on synchronised pyqtgraph plots, plus side-by-side summary and inter-station travel-time tables
- Presets - a batch configuration (files, stopping patterns, approaches, sweep, output formats) can be saved to and reloaded from a JSON preset
- ZIP export - packages every variant's report, calculation protocol, raw CSV data and comparison matrices, plus the overlay plot images, into one structured archive; reports can be written as Text, PDF, Markdown or LaTeX

---

## Project Structure

- `main.py` - application entry point
- `gui.py` - main window, ribbon, docks and data flow
- `gui_overlay.py` - settings and vehicle dialogs, detached plot window
- `geometry_engine.py` - cant design and permissible speed calculation
- `vehicle_engine.py` - train kinematics simulation
- `readfile.py` - LandXML and XML TTP parsers, coordinate transformations
- `map_viewer.py` - interactive Folium map widget with floating map controls
- `plot_widgets.py` - shared pyqtgraph base widget, context menus and navigation toolbar
- `graphs_dock.py` - linked track geometry and speed profile plots
- `profile_dock.py` - longitudinal profile plot with gradient annotations
- `kinematics_dock.py` - four linked kinematics plots
- `workflow_dock.py` - seven step workflow guide
- `help_dock.py` - in-application documentation panel rendering this file
- `xml_editor.py` - XML source viewer with folding and syntax highlighting
- `ribbon.py` - ribbon command bar widgets
- `lazy_dock.py` - dock widget with deferred rendering and a title bar menu
- `theme_manager.py` - operating system theme detection and application styling
- `icons.py` - programmatically generated vector icons and text badges
- `default_values.py` - built-in default norm limits and vehicle parameters
- `translations/` - external JSON translation files (cz.json, en.json, de.json)
- `translation_manager.py` - discovers and loads translation JSON files at runtime
- `resource_paths.py` - shared helper for locating bundled and writable resources
- `shortcut_manager.py` - loads `config/shortcuts.json`, applies shortcuts, resolves typed commands
- `settings_dialog.py` - dialog for editing command aliases and keyboard shortcuts
- `config/shortcuts.json` - external command name, alias, and keyboard shortcut mappings
- `landxml_merger.py` - chainage-rebasing concatenation of several parsed LandXML alignments
- `project_metadata.py` - project metadata model and the Project Properties dialog
- `project_file.py` - native `.coypu` archive format, recent projects list and recovery snapshot paths
- `landxml_exporter.py` - LandXML 1.2 writer for the horizontal geometry, calculated cant and vertical profile
- `batch_config.py` - batch configuration schema, JSON preset persistence, variant cross-product expansion
- `batch_metrics.py` - headless travel-time, track-length and variant metric helpers shared by the track stats dock
- `batch_runner.py` - isolated per-variant execution and the QThread worker/controller running a batch
- `batch_results.py` - holds the most recently run batch's results, outside the live project data
- `batch_dialog.py` - batch configuration modal (track sources, stopping patterns, approaches, sensitivity, output)
- `batch_progress.py` - progress dialog shown while a batch runs and while the archive is packaged
- `variant_dashboard.py` - overlay plots and comparison tables for the Variant Comparison Dashboard
- `report_formats.py` - renders a report's lines to Text, Markdown, LaTeX, CSV or PDF
- `batch_export.py` - assembles a batch's reports, protocols and comparison data into one ZIP archive
- `tests/` - unit tests for the geometry engine, vehicle catalog, and batch processing modules

---

## Repository

Source code: https://github.com/surovskyjk/COYPU
