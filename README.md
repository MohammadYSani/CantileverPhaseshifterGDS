Cantilever Piezo-Optomechanical Phase Shifters (GDS)

This repository contains Python code (using gdsfactory
) for designing piezo-optomechanical cantilever phase shifters.
The devices reproduce the structures presented in Piezo-optomechanical cantilever modulators for VLSI visible photonics (Dong et al., 2022).

The code generates GDS layouts of serpentine waveguides on released cantilever plates, including multilayer stacks and release-hole arrays.

Installation

It’s recommended to use a virtual environment:

python -m venv .venv
source .venv/bin/activate   # Linux/Mac
.venv\Scripts\activate      # Windows


Then install this package:

# for development (changes in src/ are reflected immediately)
pip install -e .

# or for normal installation
pip install .


This makes the piezo_pic package importable anywhere.

Usage
Running an example

To build the serpentine cantilever design and export to GDS:

python examples/build_serpentine.py


This will generate a GDS file (e.g. cantilever_piezo_designs.gds) in the working directory.

Importing in Python

You can also use the library directly:

import piezo_pic
from piezo_pic.cells import serpentine_multilayer

# create a serpentine cantilever with custom parameters
c = serpentine_multilayer(width_core_um=0.4, n_loops=6)
c.show()

Project Structure

src/piezo_pic/ — the main package

geometry/ — low-level geometry (paths, serpentine)

features/ — extra features (release holes, etc.)

cells/ — parametric gdsfactory cells (cantilever stacks, serpentine multilayer)

tech/ — process layers and default parameters

io/ — writing/export helpers

utils/ — shared utilities

examples/ — ready-to-run scripts (e.g. build_serpentine.py)

tests/ — unit tests to verify geometry and exports

Reference

Dong et al., Piezo-optomechanical cantilever modulators for VLSI visible photonics, arXiv:2201.12447 (2022).