# RainWorld-Map

# Installation
The following dependencies are required on Python 2 (tested v2.7.9). Several sub-dependencies are required, notably numpy. 
- Pillow (tested v2.8.1)
- networkx (tested v1.9.1)

This build was tested on Windows 7. Most packages can be installed with ```pip install```; where necessary, Windows installation binaries were used from http://www.lfd.uci.edu/~gohlke/pythonlibs/

# Running
```generate.py``` is used to produce large ```.png``` images, by compiling screenshots, labels and other resources from the ```assets``` folder.
The network is generated using the ```networkx``` and connection data from the ```network.db``` file.
Resulting images are placed in the ```big_image``` directory.

```zoomify.py``` generates tiles and associated meta-data in the required directory structure for Zoomify compatibility.
Place images to process in the ```big_image``` directory.
Output will be generated in the ```zoomify_tiles``` directory.

# Assets
This is the store for images and other files used during map creation.
```network.db``` stores regions, areas and nodes as uniquely keyed items.
Links between nodes are stored bidirectionally by key.
Node coordinates are in image-standard cartesian coordinates, i.e. y increases moving down the image. ```0,0``` is the centre of the image.
This exclusive and necessary bidirectional linkage can be checked by running ```verify.py```.

# Todo List
```
Implement adaptive colour palette for "seamless" (and new palette "easyread") depending on region
Generally improve colour palette system - maybe migrate to DB?
Look at circumnavigating size limit on image generation; options:
    C++ codebase? (probably not)
    Partial image writing after position generation?
        Adapt zoomify.py to handle multiple large slices
        Ensure slices written in easy-to-handle 256**x dimensions
```
        