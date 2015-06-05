# RainWorld-Map

# Installation
The following dependencies are required:
- Pillow (tested v2.8.1)
- networkx (tested v1.9.1)

Install the libjpeg-turbo library, available at: http://www.libjpeg-turbo.org/Documentation/OfficialBinaries. Tested with version 1.4.

# Running
Place one .jpg image to process in the z_input directory. Run src/zoomify.py. Output will be generated in Zoomify format in the z_output directory.

# DB
Stores regions, areas and nodes as uniquely keyed items. Links between nodes are stored bidirectionally by key. This exclusive and necessary bidirectional linkage can be checked by running src/verify.py