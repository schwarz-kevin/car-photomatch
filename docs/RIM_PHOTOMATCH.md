# Rim PhotoMatch — Experimental tutorial (v0.4.12)

This feature helps you model a wheel rim from a photograph. It is **not** an automatic 3D reconstruction system, and the camera result is ambiguous when only a single ring is detected.

## Choose the photographed ring

1. Open **Image Editor → N → PhotoMatch → Rim PhotoMatch (Experimental)**.
2. Expand **1. Photo & Edge** and **Load Rim Photograph**.
3. Click **Draw Rim Area** and drag a loose box around the rim. Run **Detect Rim Edges**.
4. Pick the candidate that follows a **real circular physical feature**. The score is a ranking, not proof that it found the correct edge.
5. If necessary use **Fallback: 8 Edge Clicks**. The eight clicks fit an ellipse but do not identify whether you clicked a front or rear ring.

## Configure geometry and optional guides

1. Under **2. Rim Geometry**, set nominal rim diameter (inches) and rim width (inches).
2. Select **Detected Ring** to describe the circle chosen in the photograph: Front/Rear Bead Seat, Front/Rear Outer Lip, Center Bore, Hub Face, or Other / Manual.
3. The measured ring's size is inferred **only** when sufficient dimensions are known. Outer lip size may be approximated; use **Advanced & Display → Use Exact Diameter** when you know the true diameter.
4. Set **Rim Circle Vertices**.
5. Optionally enable **Lug / Bolt Pattern Guides**, then enter lug count, **PCD (mm)**, hole diameter (mm), and **Lug Vertices**. All lug guide circles are combined into one edge-loop mesh object.
6. Optionally enable **ET / Hub Guide**, and supply ET (signed mm) and center bore diameter. **ET** positions the mounting face relative to the nominal wheel center, not relative to an arbitrary outer lip.
7. Click **Create Modeling Rig** beneath those settings, directly above **3. Camera**. If you already have a rig, use Update Ring Guides or remove the existing construction collection before rebuilding for topology changes.

## Estimate the camera

1. Expand **3. Camera**; supply an **assumed focal length** in millimeters.
2. Click **Estimate Rim Camera** and **View Rim Camera**.
3. Compare the guide edges to the photo; try the alternate pose where useful. Photographing a circular rim from the front versus rear can be ambiguous, especially with a nearly frontal view.
4. For best accuracy use real measurements of the exact ring selected. A nominal 19-inch wheel has a **482.6 mm bead-seat diameter**, not necessarily a 482.6 mm outer lip.

## Photo overlays and display

In **Reference Photo Display**, adjust photo opacity and placement (in front of / behind geometry). **Blender itself** controls Solid, Wireframe, Material Preview, Rendered and X-Ray. To repair forced wire overlays on guides built by older versions, open **Advanced & Display → Fix Old Rig Wire Overlays**.

## Known limitations

- Rim candidates can be wrong under reflections, partially occluded edges and spoke clutter.
- A single fitted ellipse with an assumed focal length can admit multiple camera poses.
- Rim width is measured between bead seats and does not determine every rim feature's axial depth.
- Known wheel width and ET can determine mounting-plane position only relative to correctly identified reference planes.
- Existing car photomatch cameras are not modified by the rim workflow, but the scene uses a shared render resolution.
