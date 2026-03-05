"""convert.py — STIR → SimSET conversion and CLI entry point."""

from __future__ import annotations
import argparse
import os
import sys

from scanners import get_scanner, KNOWN_SCANNERS
from geometry import derive_physical_block_counts, compute_num_axial_simset_rings
from writers import write_blocparams, write_ringparams, write_detparams


def convert(
    scanner_key: str,
    outdir: str = ".",
    do_forced_interaction: bool = False,
) -> None:
    """Write .blocparams, .ringparams and .detparams for the named scanner into outdir."""
    scanner, phys = get_scanner(scanner_key)
    num_trans_blocks, phys_trans, phys_axial = derive_physical_block_counts(scanner, phys)
    num_axial_rings = compute_num_axial_simset_rings(scanner, phys_axial)

    os.makedirs(outdir, exist_ok=True)
    safe_name = scanner.get_name().lower().replace(" ", "_")

    bloc_path = os.path.join(outdir, f"{safe_name}.blocparams")
    ring_path = os.path.join(outdir, f"{safe_name}.ringparams")
    det_path  = os.path.join(outdir, f"{safe_name}.detparams")

    write_blocparams(bloc_path, scanner, phys, phys_trans, phys_axial)
    write_ringparams(ring_path, bloc_path, scanner, phys, num_trans_blocks, phys_axial)
    write_detparams(det_path, ring_path, scanner, phys, num_axial_rings, phys_axial,
                    do_forced_interaction=do_forced_interaction)


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(
        prog="stir_to_simset",
        description="Convert a STIR scanner definition to SimSET block-detector parameter files.",
    )
    parser.add_argument("--scanner", "-s", metavar="NAME",
                        help="Scanner name or alias (use --list to see options).")
    parser.add_argument("--outdir", "-o", metavar="DIR", default=".",
                        help="Output directory (default: current directory).")
    parser.add_argument("--list", "-l", action="store_true",
                        help="List known scanners and exit.")

    args = parser.parse_args(argv)

    if args.list:
        for name in sorted(KNOWN_SCANNERS):
            print(name)
        return

    if args.scanner is None:
        parser.print_help()
        sys.exit(0)

    convert(args.scanner, outdir=args.outdir)


if __name__ == "__main__":
    main()

