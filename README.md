# RainWorld-Map

# Installation
The following dependencies are required on Python 2 (tested v2.7.9). Several sub-dependencies, notably numpy and scipy. 
- Pillow (tested v2.8.1)
- networkx (tested v1.9.1)
- scikit-image (tested v0.11.3)
- pypeaks (tested v0.2.7)

This build was tested on Windows 7. Most packages can be installed with ```pip install```; where necessary, Windows installation binaries were used from http://www.lfd.uci.edu/~gohlke/pythonlibs/

# Running
```generate.py``` is used to produce a large .png image, using screenshots, labels and other resources from the ```assets``` folder. The network is generated using networkx from the ```network.db``` file. Resulting images are placed in the ```big_image``` directory.

```zoomify.py``` generates tiles and associated meta-data in the required directory structure for zoomify compatibility. Place images to process in the ```big_image``` directory. Output will be generated in the ```zoomify_tiles```` directory.

# Assets
This is the store for images and other files used during map creation.
```network.db``` tores regions, areas and nodes as uniquely keyed items. Links between nodes are stored bidirectionally by key. Node coordinates are in image-standard cartesian coordinates, i.e. y increase moving down the image. 0,0 is the centre of the image. This exclusive and necessary bidirectional linkage can be checked by running ```verify.py```