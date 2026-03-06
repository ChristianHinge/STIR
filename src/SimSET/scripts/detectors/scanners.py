"""
scanners.py — SimSET material table, PhysicalSpec, and scanner registry.

Scanner geometry (ring counts, radii, energy resolution, etc.) is read
directly from STIR via stir.Scanner.get_scanner_from_name().  Only the
SimSET-specific physical details that STIR does not know (crystal materials,
housing thicknesses, wrap) are stored here in PhysicalSpec.

Adding a new scanner
--------------------
1. Verify STIR knows the scanner: stir.Scanner.get_scanner_from_name("Name").
2. Create a PhysicalSpec from datasheets / literature.
3. Call _register("Canonical STIR Name", phys).
   Use the exact string returned by stir.Scanner.get_name().
"""

from __future__ import annotations
import copy
import stir
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# SimSET material index table (default phg_att_table)
# ---------------------------------------------------------------------------

SIMSET_MATERIALS: dict[str, int] = {
    "air":                   0,
    "water":                 1,
    "blood":                 2,
    "bone":                  3,
    "brain":                 4,
    "heart":                 5,
    "lung":                  6,
    "muscle":                7,
    "lead":                  8,
    "NaI":                   9,
    "BGO":                  10,
    "iron":                 11,
    "graphite":             12,
    "tin":                  13,
    "GI_tract":             14,
    "con_tissue":           15,
    "copper":               16,
    "perfect_absorber":     17,
    "LSO":                  18,
    "GSO":                  19,
    "aluminum":             20,
    "tungsten":             21,
    "liver":                22,
    "fat":                  23,
    "LaBr3":                24,
    "polycarbonateLowVisc": 25,
    "polyethyleneNEMA":     26,
    "polymethylMethacryl":  27,
    "polystyreneFibers":    28,
    "LYSO":                 29,
}


# ---------------------------------------------------------------------------
# PhysicalSpec
# ---------------------------------------------------------------------------

@dataclass
class PhysicalSpec:
    """
    Scanner-specific physical parameters not available in STIR.

    These cover the material composition and mechanical microstructure of the
    detector block — things that STIR ignores because they are irrelevant to
    sinogram reconstruction, but that SimSET needs for photon transport.

    All distances are in mm.
    """

    # ---- Crystal (scintillator) dimensions ----------------------------------
    crystal_depth_mm: float = 20.0
    """Radial depth of each crystal element (x-direction in SimSET, mm)."""

    crystal_trans_size_mm: float = -1.0
    """Centre-to-centre transaxial crystal pitch (y-direction, mm).
    -1 means 'derive from STIR ring_spacing / block pitch' — must be overridden
    for scanners where STIR does not store transaxial_crystal_spacing."""

    crystal_axial_size_mm: float = -1.0
    """Centre-to-centre axial crystal pitch (z-direction, mm).
    -1 means 'derive from STIR ring_spacing' — must be overridden for scanners
    where STIR does not store axial_crystal_spacing."""

    # ---- Inter-crystal reflector / wrap -------------------------------------
    wrap_thickness_mm: float = 0.04
    """Thickness of the reflector / wrapping on each side of a crystal (mm).
    This is doubled between adjacent crystals (each crystal carries its own wrap).
    Typical values: 0.04–0.10 mm (ESR film, Teflon tape, or air gap)."""

    wrap_material: int = SIMSET_MATERIALS["air"]
    """SimSET material index for the inter-crystal reflector.
    Air (0) is a conservative default; use aluminum (20) or tungsten (21)
    for light-tight wrapped detectors."""

    # ---- Radial housing layers (front and back of crystal array) ------------
    housing_front_mm: float = 1.0
    """Thickness of the inactive radial layer in front of the crystal array (mm).
    Represents the detector window, EMI shielding, or light guide entrance."""

    housing_back_mm: float = 1.0
    """Thickness of the inactive radial layer behind the crystal array (mm).
    Represents the SiPM/PMT coupling layer, PCB, or backplate."""

    # ---- Transaxial/axial side housing --------------------------------------
    side_housing_mm: float = 0.5
    """Thickness of inactive housing surrounding the crystal array on the
    transaxial and axial faces of the block (mm)."""

    housing_material: int = SIMSET_MATERIALS["aluminum"]
    """SimSET material index for all housing layers (front, back, sides)."""

    # ---- Crystal material ---------------------------------------------------
    crystal_material: int = SIMSET_MATERIALS["LSO"]
    """SimSET material index of the scintillator crystal.
    Common values: BGO=10, LSO=18, GSO=19, NaI=9, LaBr3=24."""

    # ---- Physical crystal count per block -----------------------------------
    # These are the *physical* crystal counts, i.e. after removing virtual
    # gap crystals that STIR injects into its block counts.
    # Set to -1 to let geometry.py derive them automatically from STIR params.
    phys_trans_crystals_per_block: int = -1
    """Physical crystals per block in the transaxial direction.
    -1 = auto-derive from STIRScanner (num_transaxial_crystals_per_block
    minus num_virtual_transaxial_per_block)."""

    phys_axial_crystals_per_block: int = -1
    """Physical crystals per block in the axial direction.
    -1 = auto-derive from STIRScanner.  For scanners with STIR 'super-blocks'
    (e.g. Quadra) this must be set explicitly."""


# ---------------------------------------------------------------------------
# Registry: canonical STIR scanner name → PhysicalSpec
# ---------------------------------------------------------------------------

KNOWN_SCANNERS: dict[str, PhysicalSpec] = {}


def _register(canonical_name: str, phys: PhysicalSpec) -> None:
    KNOWN_SCANNERS[canonical_name] = phys


def get_scanner(key: str) -> tuple[stir.Scanner, PhysicalSpec]:
    """
    Return a (stir.Scanner, PhysicalSpec) pair for the named scanner.

    stir.Scanner handles name/alias lookup; PhysicalSpec is looked up by the
    canonical name STIR returns.  Raises ValueError if the scanner has no
    registered PhysicalSpec.
    """
    scanner = stir.Scanner.get_scanner_from_name(key)
    name = scanner.get_name()
    if name not in KNOWN_SCANNERS:
        raise ValueError(
            f"No SimSET PhysicalSpec registered for '{name}'.\n"
            f"Supported scanners: {sorted(KNOWN_SCANNERS)}"
        )
    return scanner, copy.deepcopy(KNOWN_SCANNERS[name])


# ===========================================================================
# Siemens Biograph mMR
# ===========================================================================
# Physical spec: Delso et al., J Nucl Med 2011; 52(8):1198-1203
_register("Siemens mMR", PhysicalSpec(
    crystal_depth_mm=20.0,
    crystal_trans_size_mm=4.17,
    crystal_axial_size_mm=4.0625,
    wrap_thickness_mm=0.04,
    housing_front_mm=0.5,
    housing_back_mm=0.5,
    side_housing_mm=0.5,
    crystal_material=SIMSET_MATERIALS["LSO"],
    housing_material=SIMSET_MATERIALS["aluminum"],
    wrap_material=SIMSET_MATERIALS["air"],
    phys_trans_crystals_per_block=8,
    phys_axial_crystals_per_block=8,
))


# ===========================================================================
# Siemens Biograph mCT
# ===========================================================================
# Physical spec: Jakoby et al., Phys Med Biol 2011; 56(8):2375
_register("Siemens mCT", PhysicalSpec(
    crystal_depth_mm=22.0,
    crystal_trans_size_mm=4.0,
    crystal_axial_size_mm=4.054,
    wrap_thickness_mm=0.04,
    housing_front_mm=0.5,
    housing_back_mm=0.5,
    side_housing_mm=0.5,
    crystal_material=SIMSET_MATERIALS["LSO"],
    housing_material=SIMSET_MATERIALS["aluminum"],
    wrap_material=SIMSET_MATERIALS["air"],
    phys_trans_crystals_per_block=13,
    phys_axial_crystals_per_block=13,
))


# ===========================================================================
# Siemens Vision 600
# ===========================================================================
# Physical spec: van Sluis et al., J Nucl Med 2019; 60(9):1302-1310
_register("Siemens Vision 600", PhysicalSpec(
    crystal_depth_mm=20.0,
    crystal_trans_size_mm=3.2,
    crystal_axial_size_mm=3.29114,
    wrap_thickness_mm=0.04,
    housing_front_mm=0.5,
    housing_back_mm=0.5,
    side_housing_mm=0.3,
    crystal_material=SIMSET_MATERIALS["LSO"],
    housing_material=SIMSET_MATERIALS["aluminum"],
    wrap_material=SIMSET_MATERIALS["air"],
    phys_trans_crystals_per_block=20,
    phys_axial_crystals_per_block=10,
))


# ===========================================================================
# Siemens Quadra
# ===========================================================================
# STIR encodes the Quadra's axial structure as a "super-block" of 81 crystals
# (8 physical mini-blocks × 10 + 1 virtual gap).  phys_axial_crystals_per_block
# must therefore be set explicitly to 10 (one physical mini-block per SimSET ring).
# Physical spec: Prenosil et al., J Nucl Med 2022; 63(3):476-484
_register("Siemens Quadra", PhysicalSpec(
    crystal_depth_mm=20.0,
    crystal_trans_size_mm=3.2,
    crystal_axial_size_mm=3.2,
    wrap_thickness_mm=0.04,
    housing_front_mm=0.5,
    housing_back_mm=0.5,
    side_housing_mm=0.3,
    crystal_material=SIMSET_MATERIALS["LSO"],
    housing_material=SIMSET_MATERIALS["aluminum"],
    wrap_material=SIMSET_MATERIALS["air"],
    phys_trans_crystals_per_block=20,
    phys_axial_crystals_per_block=10,
))


# ===========================================================================
# Siemens ECAT EXACT HR+ (ECAT 962)
# ===========================================================================
# Physical spec: "Performance evaluation of the whole-body PET scanner
# ECAT EXACT HR+", OSTI report 513192, 1996.
# Crystal: BGO, 4.05 (axial) × 4.39 (transaxial) × 30 mm (depth).
# 8×8 physical crystals per block; no virtual crystals.
# Axial crystal pitch = 4.85 mm (= STIR ring_spacing); physical crystal
# axial face is 4.05 mm, leaving ~0.8 mm for reflector/dead material.
# Note: "ECAT HR+" is a STIR alias; canonical name is "ECAT 962".
_register("ECAT 962", PhysicalSpec(
    crystal_depth_mm=30.0,
    crystal_trans_size_mm=4.492,
    crystal_axial_size_mm=4.85,        # centre-to-centre pitch = STIR ring_spacing
    wrap_thickness_mm=0.04,
    housing_front_mm=1.0,
    housing_back_mm=1.0,
    side_housing_mm=0.0,
    crystal_material=SIMSET_MATERIALS["BGO"],
    housing_material=SIMSET_MATERIALS["aluminum"],
    wrap_material=SIMSET_MATERIALS["air"],
    phys_trans_crystals_per_block=8,
    phys_axial_crystals_per_block=8,
))