from PIL import Image
import os
import re
import sys
import math
import glob
import shutil
import argparse
import xml.etree.ElementTree as ET

import common

TILE_SIZE = int(256)
HQ_TILE_SIZE = int(8192)
TOP_DIR = common.get_top_dir()
TILES_PER_SUBDIR = int(256)
TILE_SUBDIR_PREFIX = 'TileGroup'
METADATA_FILE = 'ImageProperties.xml'

def divisions_required(total_length, sub_length):
    precise = total_length/sub_length
    if total_length%sub_length == 0:
        precise = precise-1
    return int(math.ceil(precise)+1)

def max_zoom_level(size):
    '''size as x,y tuple'''
    max_divisions_required = divisions_required(max(size), TILE_SIZE)
    max_zoom_level = int(math.ceil(math.log(max_divisions_required, 2)+1))
    return max_zoom_level
    
def zoomify_order(image_size, output_dir):
    '''image_size must be tuple in (x, y) format, output_dir must be string'''
    print 'Moving files'
    # Get list of all files in dir
    tiles_moved = 0
    max_zoom = max_zoom_level(image_size)
    for loop_zoom in xrange(0, int(max_zoom)):
        area_size_multiplier = 2**(max_zoom-1-loop_zoom)
        area_side_length = TILE_SIZE*area_size_multiplier
        rows_required = divisions_required(image_size[1], area_side_length)
        cols_required = divisions_required(image_size[0], area_side_length)
        # Each row
        for loop_row in xrange(0, int(rows_required)):
            tile_origin_y = loop_row*area_side_length
            # Columns in row
            for loop_col in xrange(0, int(cols_required)):
                tile_id = str(loop_zoom)+'-'+str(loop_col)+'-'+str(loop_row)
                tile_subdir_suffix = str(int(math.floor(tiles_moved/TILES_PER_SUBDIR)))
                tile_subdir = os.path.join(output_dir, TILE_SUBDIR_PREFIX+tile_subdir_suffix)
                common.make_dir_if_not_found(tile_subdir)
                current_path = os.path.join(output_dir, tile_id+'.jpg')
                destination_path = os.path.join(tile_subdir, tile_id+'.jpg')
                try:
                    shutil.move(current_path, destination_path)
                except IOError:
                    continue
                tiles_moved = tiles_moved+1
    
def zoomify_slice(big_image, max_zoom_level, output_dir, min_zoom_level=0, offset=(0, 0)):
    '''big_image is an image object containing the image to be tiled
        max_zoom_level indicates how many zoom levels are required (important for directories)
        output_dir is the top dir for output
        offset is used to indicate the position of this slice in directory processing'''
    tiles_saved = 0 # Counter of how many tiles have been generated, for placement in sub-dirs
    #Zoom level
    for loop_zoom in xrange(min_zoom_level, int(max_zoom_level)):
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
                # 
                tile_id = str(loop_zoom)+'-'+str(loop_col+offset[1]*cols_required)+'-'+str(loop_row+offset[0]*rows_required)
                tile_save_path = os.path.join(output_dir, tile_id+'.jpg')
                
                # Crop, resize and save tile
                tile_raw = big_image.crop(box)
                tile_resampled = tile_raw.resize(area_resize)
                tile_resampled.save(tile_save_path)
                tiles_saved = tiles_saved+1
    return tiles_saved

def zoomify(path, output_dir):
    print '> Zoomifying', path
    # Write XML metadata file
    root = ET.Element('IMAGE_PROPERTIES')
    tiles_saved = 0
    
    #if path points to hq-format directory
    if os.path.isdir(path):
        metadata_path = os.path.join(path, METADATA_FILE)
        if os.path.isfile(metadata_path):
            file_dir = os.path.join(output_dir, os.path.basename(os.path.normpath(path)))
            common.make_dir_if_not_found(file_dir)
            tree_read = ET.parse(metadata_path)
            root_read = tree_read.getroot()
            # Trasform to integer values for use
            meta = {key: int(val) for key, val in root_read.attrib.iteritems()}
            rows = divisions_required(meta['HEIGHT'], meta['TILESIZE'])
            cols = divisions_required(meta['WIDTH'], meta['TILESIZE'])
            meta_size = tuple([meta['WIDTH'], meta['HEIGHT']])
            hq_zoom_range = int(math.ceil(math.log(meta['TILESIZE']/256, 2)))
            hq_zoom_max = max_zoom_level(meta_size)
            hq_zoom_min = hq_zoom_max-hq_zoom_range
            '''add this as file prefix z_level? str(hq_zoom_level)'''
            # Each row
            for loop_row in xrange(0, int(rows)):
                # Columns in row
                for loop_col in xrange(0, int(cols)):
                    tile_id = 'hq'+'-'+str(loop_col)+'-'+str(loop_row)
                    tile_open_path = os.path.join(path, tile_id+'.png')
                    print '>>', tile_id
                    hq_tile = Image.open(tile_open_path)
                    tiles_saved = tiles_saved + zoomify_slice(hq_tile, hq_zoom_max, file_dir, min_zoom_level=hq_zoom_min, offset=(loop_row, loop_col))
            
            zoomify_order(meta_size, file_dir)
            #Set metadata attributes
            root.attrib.update({'WIDTH': root_read.attrib['WIDTH'],
                               'HEIGHT': root_read.attrib['WIDTH'],
                               })
        else:
            print 'No metadata file found at', metadata_path
            return False
 
    #if just single image file
    else:
        file_prefix = str(os.path.split(path)[1]).split('.')
        file_dir = os.path.join(output_dir, file_prefix[0])
        common.make_dir_if_not_found(file_dir)
        # Open image and determine size, tiles and zoom levels required
        input_path = os.path.join(path)
        print '>> Single image'
        big_image = Image.open(input_path)

        # Tile Generation
        max_zoom = max_zoom_level(big_image.size)
        tiles_saved = zoomify_slice(big_image, max_zoom, file_dir)
        zoomify_order(big_image.size, file_dir)
        
        #Set metadata attributes
        root.attrib.update({'WIDTH': str(big_image.size[0]),
                           'HEIGHT': str(big_image.size[1]),
                           })
    
    root.attrib.update({'NUMTILES': str(tiles_saved),
                       'NUMIMAGES': str(1),
                       'VERSION': '1.8',
                       'TILESIZE': str(TILE_SIZE)
                       })
    tree = ET.ElementTree(root)
    tree.write(os.path.join(file_dir, METADATA_FILE))
    print root.attrib['WIDTH']+'x'+root.attrib['HEIGHT']+' image saved as '+root.attrib['NUMTILES'], root.attrib['TILESIZE']+'px tiles in '+str(int(math.ceil(tiles_saved/TILES_PER_SUBDIR)))+' subdirectories'

def main():
    parser = argparse.ArgumentParser(description='Make big map image from screenshots and connection data') #Parse arguments
    parser.add_argument('-i', '--input', default=None,
                        help='Input file or direcory. Default is ')
    parser.add_argument('-o', '--output', default=None,
                        help='Output direcory. Default is ')
    args = parser.parse_args()
    INPUT_PATH = args.input
    OUTPUT_PATH = args.output

    # Get directory names, make if they don't exist, check only one input file, get input file path
    directories = common.initialise_subdirs(['big_image', 'zoomify_tiles'])
    if INPUT_PATH is None:
        input_files = [os.path.join(directories[0], name) for name in os.listdir(directories[0])]
        if len(input_files) > 0:
            for file_path in input_files:
                zoomify(file_path, directories[1])
        else:
            sys.exit('No valid input images.')
    else:
        None
    
if __name__ == "__main__":
    main()