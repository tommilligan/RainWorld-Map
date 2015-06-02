from PIL import Image
import os
import sys
import math
import glob
import shutil

import common

def divisions_required(total_length, sub_length):
    precise = total_length/sub_length
    if total_length%sub_length == 0:
        precise = precise-1
    return int(math.ceil(precise)+1)

TILE_SIZE = 256 # must be integer
TOP_DIR = common.get_top_dir()
TILES_PER_SUBDIR = 256
TILE_SUBDIR_PREFIX = 'TileGroup'

# Get directory names, make if they don't exist, check only one input file, get input file path
directories = common.initialise_subdirs(['big_image', 'zoomify_tiles'])
input_files = glob.glob(os.path.join(directories[0],'*.jpg'))
if len(input_files) != 1:
    sys.exit('Only one input .jpg file is allowed in the input directry')

# Open image and determine size, tiles and zoom levels required
input_path = os.path.join(directories[0],input_files[0])
big_image = Image.open(input_path)
max_divisions_required = max(divisions_required(big_image.size[0], TILE_SIZE), divisions_required(big_image.size[1], TILE_SIZE))
max_zoom_level = int(math.ceil(math.log(max_divisions_required, 2)+1))
print big_image.size

# Tile Generation
# Zoom level
tiles_saved = 0 # Couter of how many tiles have been generated, for placement in sub-dirs
for loop_zoom in xrange(0, int(max_zoom_level)):
    area_size_multiplier = 2**(max_zoom_level-1-loop_zoom)
    area_side_length = TILE_SIZE*area_size_multiplier
    rows_required = divisions_required(big_image.size[1], area_side_length)
    cols_required = divisions_required(big_image.size[0], area_side_length)
    area_resize_ratio = TILE_SIZE/area_side_length
    print str(loop_zoom)+'#'+str(area_side_length)
    # Each row
    for loop_row in xrange(0, int(rows_required)):
        tile_origin_y = loop_row*area_side_length
        # Columns in row
        for loop_col in xrange(0, int(cols_required)):
            tile_origin_x = loop_col*area_side_length
            box = (tile_origin_x,
                   tile_origin_y,
                   min(tile_origin_x+area_side_length, big_image.size[0]),
                   min(tile_origin_y+area_side_length, big_image.size[1])
                   )
            # Calculate details of tile to save
            area_size_actual = (box[2]-box[0], box[3]-box[1])
            area_resize = tuple(d/area_size_multiplier for d in area_size_actual)
            tile_id = str(loop_zoom)+'-'+str(loop_col)+'-'+str(loop_row)
            tile_subdir_suffix = str(int(math.floor(tiles_saved/TILES_PER_SUBDIR)))
            tile_subdir = os.path.join(directories[1], TILE_SUBDIR_PREFIX+tile_subdir_suffix)
            common.make_dir_if_not_found(tile_subdir)
            tile_save_path = os.path.join(tile_subdir, tile_id+'.jpg')
            
            # Crop, resize and save tile
            tile_raw = big_image.crop(box)
            tile_resampled = tile_raw.resize(area_resize)
            tile_resampled.save(tile_save_path)
            tiles_saved = tiles_saved+1

# Write XML metadata file
with open(os.path.join(directories[1], 'ImageProperties.xml'), 'w') as f:
    f.write('<IMAGE_PROPERTIES WIDTH="'+str(big_image.size[0])+'" HEIGHT="'+str(big_image.size[1])+'" NUMTILES="'+str(tiles_saved)+'" NUMIMAGES="1" VERSION="1.8" TILESIZE="'+str(TILES_PER_SUBDIR)+'"/>')

print str(big_image.size[0])+'x'+str(big_image.size[1])+' image saved as '+str(tiles_saved)+' tiles in '+str(int(math.ceil(tiles_saved/TILES_PER_SUBDIR)))+' subdirectories' 