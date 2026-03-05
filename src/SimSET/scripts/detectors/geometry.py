"""
geometry.py
===========
Pure geometric calculations for the STIR → SimSET conversion.

No file I/O.  No dependency on the writers.  All functions take plain numbers
or dataclass instances and return plain numbers.  This makes the module
straightforward to unit-test in isolation.

Unit convention: inputs and outputs in cm unless a function is explicitly
named _mm or takes a mm argument.  The single source-of-truth conversion is
mm_to_cm().
"""

from __future__ import annotations
import math
import stir
from scanners import PhysicalSpec


def mm_to_cm(v: float) -> float:
    return v / 10.0


def derive_physical_block_counts(
    scanner: stir.Scanner,
    phys: PhysicalSpec,
) -> tuple[int, int, int]:
    """Return (num_trans_blocks, phys_trans, phys_axial)."""
    n_trans = scanner.get_num_transaxial_crystals_per_block()
    n_virt_trans = scanner.get_num_virtual_transaxial_crystals_per_block()
    phys_trans = (
        phys.phys_trans_crystals_per_block
        if phys.phys_trans_crystals_per_block > 0
        else n_trans - n_virt_trans
    )
    num_trans_blocks = scanner.get_num_detectors_per_ring() // n_trans

    n_axial = scanner.get_num_axial_crystals_per_block()
    n_virt_axial = scanner.get_num_virtual_axial_crystals_per_block()
    phys_axial = (
        phys.phys_axial_crystals_per_block
        if phys.phys_axial_crystals_per_block > 0
        else n_axial - n_virt_axial
    )

    return num_trans_blocks, phys_trans, phys_axial


def compute_num_axial_simset_rings(
    scanner: stir.Scanner,
    phys_axial_per_block: int,
) -> int:
    """Number of SimSET rings needed to cover the full axial FOV."""
    num_virtual_axial_total = (
        scanner.get_num_axial_blocks_per_bucket()
        * scanner.get_num_virtual_axial_crystals_per_block()
    )
    phys_ring_rows = scanner.get_num_rings() - num_virtual_axial_total
    return round(phys_ring_rows / phys_axial_per_block)


# ---------------------------------------------------------------------------
# Crystal boundary generation
# ---------------------------------------------------------------------------

def crystal_boundaries(
    n_crystals: int,
    pitch_cm: float,
    wrap_cm: float,
) -> list[float]:
    """
    Compute the y or z boundary coordinates for a row of N crystals.

    SimSET's block layer uses a flat list of boundary change-points.  Between
    each pair of consecutive change-points the material is uniform.  Boundaries
    come in pairs — one at the start of each crystal, one at the end — creating
    an alternating wrap / crystal / wrap / crystal pattern.

    Parameters
    ----------
    n_crystals : int
        Number of crystals in this direction.
    pitch_cm : float
        Centre-to-centre crystal pitch (cm).
    wrap_cm : float
        Thickness of the wrap/reflector on each side of a crystal (cm).

    Returns
    -------
    list of float
        2 × n_crystals boundary coordinates, centred on 0, in ascending order.
        The resulting segment sequence is:
            [outer wrap | crystal 0 | wrap | crystal 1 | ... | outer wrap]
    """
    boundaries: list[float] = []
    start = -n_crystals * pitch_cm / 2.0
    crystal_size = pitch_cm - 2.0 * wrap_cm
    for i in range(n_crystals):
        lo = start + i * pitch_cm + wrap_cm
        hi = lo + crystal_size
        boundaries.append(round(lo, 8))
        boundaries.append(round(hi, 8))
    return boundaries


def is_active_segment(seg_y: int, seg_z: int) -> bool:
    """
    Return True if a material element at (seg_y, seg_z) is an active crystal.

    In the alternating wrap/crystal pattern produced by crystal_boundaries(),
    odd-indexed segments (1, 3, 5, …) are crystals; even-indexed segments are
    wrap or housing.  An element is active only when both y and z fall on a
    crystal segment.
    """
    return (seg_y % 2 == 1) and (seg_z % 2 == 1)


# ---------------------------------------------------------------------------
# Block dimension helpers
# ---------------------------------------------------------------------------

def block_dimensions_cm(
    phys: PhysicalSpec,
    phys_trans: int,
    phys_axial: int,
) -> dict[str, float]:
    """
    Compute the outer block dimensions and layer x-boundaries in cm.

    Returns a dict with keys:
        x_total    - full radial extent of the block
        y_half     - half-width in transaxial direction
        z_half     - half-height in axial direction
        x_front    - radial position of crystal layer front face (= housing_front)
        x_back     - radial position of crystal layer back face (= housing_front + crystal_depth)
    """
    c_t = mm_to_cm(phys.crystal_trans_size_mm)
    c_a = mm_to_cm(phys.crystal_axial_size_mm)
    h_f = mm_to_cm(phys.housing_front_mm)
    h_b = mm_to_cm(phys.housing_back_mm)
    h_s = mm_to_cm(phys.side_housing_mm)
    c_d = mm_to_cm(phys.crystal_depth_mm)

    return {
        "x_total": h_f + c_d + h_b,
        "y_half":  phys_trans * c_t / 2.0 + h_s,
        "z_half":  phys_axial * c_a / 2.0 + h_s,
        "x_front": h_f,
        "x_back":  h_f + c_d,
    }


def axial_block_pitch_cm(phys: PhysicalSpec, phys_axial: int) -> float:
    """
    Axial centre-to-centre pitch of SimSET rings (cm).

    This is the total axial height of one detector block including its side
    housing on both faces.
    """
    c_a = mm_to_cm(phys.crystal_axial_size_mm)
    h_s = mm_to_cm(phys.side_housing_mm)
    return phys_axial * c_a + 2.0 * h_s
