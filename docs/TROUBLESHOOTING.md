# Troubleshooting and FAQ — v0.4.12

**Where is Draw Rim Area?** Use **Image Editor → N → PhotoMatch → Rim PhotoMatch (Experimental) → 1. Photo & Edge**. The rectangle tool is available in the Image Editor, not the 3D Viewport.

**Detector finds the wrong ring:** Switch candidate using the arrows, crop the area more tightly, or use **Fallback: 8 Edge Clicks**. Confirm the physical ring type separately.

**Camera looks like it views the back of the rim:** A single circular contour produces pose ambiguity. Use **Try Other Pose**, verify your chosen ring reference and assumed focal length. The alternative pose is not necessarily a reliable front/rear toggle.

**Why does the rim still look wireframe in Solid mode?** An edge-only mesh has no faces. For old guides, go to **Advanced & Display → Fix Old Rig Wire Overlays**. In Blender, inspect Object Properties → Viewport Display → Wireframe. Choose Material Preview or Solid from **Blender's** controls.

**Why is Create Modeling Rig disabled?** A rig already exists. Update existing ring/ET guides from Rim Geometry, or remove the old rig collection if you need different topology, then create a new rig.

**Why doesn't an outer lip match an exact size?** Nominal rim diameter means bead-seat diameter; outer lip geometry is not fully known from nominal size. Use the advanced exact-diameter override if the real lip diameter is measured.

**My older match photo is the wrong aspect ratio:** Select its camera and click **View Selected Camera**. Scene render resolution is shared.

**Can old cameras be refined with their original clicked landmarks?** No. Old cameras and their photo backgrounds are preserved, but old photo-pair data are not archived.

**Error on add-on enable:** Restart Blender, remove older broken extension versions, and reinstall the latest extension ZIP. If errors persist, open an issue with Blender version, traceback and reproduction steps.
