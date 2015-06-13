'''
OUTLINE OF PROGRAM

Define all variables and palette colors

Define custom functions
For each region:
    Take lowest numbered area and add as starting point
    For each area so far identified:
        For each area attached
            If not already found
                Calculate initial graph position, store to dict
                Add to list of identified areas
    Optimise graph positions
    Make big image depending on how many areas are present
    For each area:
        Add screenshot (or placeholder) to map
        For each node:
            Calculate connections and positions, store to dict
            
    Plot dicts to big image in desired order (to give correct layering)
    Save big image image
'''

# Get colour of image bg
''' Make icon an inverted rgb color of underlying image
screenshot_px_topleft = screenshot.getpixel((0,0))
ICON_COLOR = rgb_invert(screenshot_px_topleft)
'''

from PIL import Image, ImageDraw, ImageFont
import os
import sqlite3
import networkx as nx
import math
import sys
import warnings
import argparse
import xml.etree.ElementTree as ET

import common


''' PIXEL DATA
        import numpy as np
        px = np.asarray(screenshot.getdata())
        print px.shape
        '''


parser = argparse.ArgumentParser(description='Make big map image from screenshots and connection data') #Parse arguments
parser.add_argument('-p', '--palette', default='default',
                    help='Color palette and format options to use')
parser.add_argument('-r', '--region',
                    help='Region to render - default is all')
parser.add_argument('-s', '--scale', default=1.0, type=float,
                    help='Scale final image (1.0 is actual, 0.5 is half size)')
parser.add_argument('-k', '--k-value', default=3.0, type=float,
                    help='Spring constant passed to the Fruchterman-Reingold algorithm. Changes network shape')
parser.add_argument('-v', '--network-overlap', default=3.0, type=float,
                    help='Increases spacing between nodes (after position optimisation)')
parser.add_argument('--world', default=False, action='store_true',
                    help='Draw the whole world, starting with the region specified by -r (or first region chosen)')
parser.add_argument('--force', default=False, action='store_true',
                    help='Force map to be created and saved as a single image file. May cause crash or instability')
args = parser.parse_args()
PALETTE = args.palette
SPECIFIED_REGION = args.region
WORLD_MAP = args.world
FORCE_SINGLE = args.force
IMAGE_SCALE_FACTOR = args.scale
NETWORK_CONTRACTION = args.k_value # -k spring Konstant # Changes style of network
NETWORK_SPACING = args.network_overlap # -v network oVerlap # Changes distance between nodes
        
directories = common.initialise_subdirs(['assets', 'big_image'])
DB_LOCATION = common.get_db_path()

MODE = (1, 0)
'''
MODE = (a, b)
a: 0=width, 1=depth (order in which initial positions are calculated)
b: 0=final, 1=continuous, 2=none (how ofter spring_layout is calculated)
'''

'''
PALETTE = string
> default
> seamless - try and blend into the Rain World color palette as much as possible
> neon - easy to read, easy to follow map
> debug - awful colours, all detail shown

each color property is a dictionary with the palette name as keys, and must have a default
e.g. dict = {'default': (0, 0, 0), 'debug': (255, 0, 0)}
'''

#palettes
def pal_get(choices):
    if PALETTE in choices:
        return choices[PALETTE]
    else:
        return choices['default']
            
pal_skeleton_line = {'default': 0, 'debug': 6}
pal_detail_line = {'default': 9, 'debug': 12}
pal_font_size = {'default': 128, 'debug': 192}
pal_icon_scale = {'default': 1.0, 'debug': 3.0}

def region_property(region_key, property):
    conn = sqlite3.connect(DB_LOCATION)
    region_cursor = conn.cursor()
    region_cursor.execute('SELECT * FROM regions WHERE key = ?', (region_key,))
    value = region_cursor.fetchone()
    headers = region_cursor.description
    for i, h in enumerate(headers):
        if h[0] == property:
            return value[i]

def list_to_tuple(val_list):
    val_tuple = tuple(int(x) for x in val_list.split())
    return val_tuple
            
def generate_palette(region_key):
    # Default palette
    values = {'title': (255, 255, 255),
              'bg': (0, 0, 0),
              'detail': (100, 100, 100),
              'skeleton': None,
              'icon': (200, 200, 200),
              'missing_screenshot_fg': (255, 255, 255)
              }
    # Derived values
    values.update({'missing_screenshot_bg': values['bg']
                   })
    
    # Overwrite defaults with new color schemes as required
    if PALETTE == 'seamless':
        # Get relevant values for each region from DB
        values.update({'title': list_to_tuple(region_property(region_key, 'rgb_highlight')),
                       'bg': list_to_tuple(region_property(region_key, 'rgb_edge')),
                       'detail': list_to_tuple(region_property(region_key, 'rgb_bg')),
                       'icon': list_to_tuple(region_property(region_key, 'rgb_lowlight'))
                       })
    elif PALETTE == 'neon':
        values.update({'title': (255, 0, 102),
                       'bg': tuple([int(float(x)/2) for x in list_to_tuple(region_property(region_key, 'rgb_edge'))]),
                       'detail': (0, 102, 255),
                       'icon': (0, 255, 102)
                       })
    elif PALETTE == 'debug':
        values.update({'title': (0, 0, 0),
                       'bg': (255, 255, 255),
                       'detail': (255, 0, 0),
                       'icon': (255, 63, 0),
                       'missing_screenshot_bg': (0, 255, 0),
                       'missing_screenshot_fg': (0, 0, 0),
                       'skeleton': (255, 255, 0)
                       })
    return values
     
# even numbers are best
LABEL_IMAGE_DIR = os.path.join(directories[0], 'labels')
MISSING_SCRN_OVERLAY_PATH = os.path.join(directories[0], 'misc', 'rain_mask.png')

DEFAULT_REGION = 'suburban'
RAW_SCREENSHOT_SIZE = (1366, 768)
HQ_TILE_LEVEL = int(5)
HQ_TILE_SIZE = 256*2**HQ_TILE_LEVEL
SCREENSHOT_RESIZE_RATIO = IMAGE_SCALE_FACTOR
ROUGH_SCREENSHOT_SIZE = tuple([int(RAW_SCREENSHOT_SIZE[x]*SCREENSHOT_RESIZE_RATIO) for x in range(2)])
IMAGE_PADDING = int(800*IMAGE_SCALE_FACTOR)
LABEL_IMAGE_INSET = int(100*IMAGE_SCALE_FACTOR)
LABEL_IMAGE_SPACING = int(20*IMAGE_SCALE_FACTOR)
LABEL_IMAGE_SCALE = pal_get(pal_icon_scale)*IMAGE_SCALE_FACTOR
FONT_SIZE = int(pal_get(pal_font_size)*IMAGE_SCALE_FACTOR)
SKELETON_LINE_WIDTH = int(pal_get(pal_skeleton_line)*IMAGE_SCALE_FACTOR)
DETAIL_LINE_WIDTH = int(pal_get(pal_detail_line)*IMAGE_SCALE_FACTOR)

LABEL_LINE_HEIGHT = FONT_SIZE+6
LABEL_LINE_OFFSET = int(FONT_SIZE/2)
FONT_PATH = os.path.join(directories[0], 'misc', 'saxmono.ttf')
font = ImageFont.truetype(font=FONT_PATH, size=FONT_SIZE)
METADATA_FILE = 'ImageProperties.xml'


# A networkx object is used to hold all properties

# Take location of screenshot and xth line, and return position. If x = 0 returns scrn
def label_line_topleft(scrn, x):
    return tuple([scrn[0]+(LABEL_LINE_OFFSET*x), scrn[1]-(LABEL_LINE_HEIGHT*x)])

def invert_rgb(rgb):
    return tuple([255-rgb[x] for x in range(3)])

def draw_network(draw, graph, position_dict, line_width, color, hq_position=(0, 0)):
    '''Takes an ImageDraw object, and uses it to draw a network as held by a networkx graph object & the node property 'position_dict' containing a (x,y) location tuple'''
    # Only draw if line_width > 0
    if line_width > 0:
        for edge in graph.edges():
            adj_start = tuple([graph.node[edge[0]][position_dict][x]-hq_position[x] for x in range(2)])
            adj_fin = tuple([graph.node[edge[1]][position_dict][x]-hq_position[x] for x in range(2)])
            draw.line([adj_start, adj_fin], fill=color, width=line_width)
        for node in graph.nodes():
            adj_tl = tuple(graph.node[node][position_dict][x]-hq_position[x]-line_width*2 for x in range(2))
            adj_br = tuple(graph.node[node][position_dict][x]-hq_position[x]+line_width*2 for x in range(2))
            draw.ellipse([adj_tl, adj_br], fill=color, outline=color)
    return None  

def get_area_screenshot(area):
    screenshot_path = os.path.join(directories[0], 'areas', str(area)+'.jpg')
    to_return = None
    if os.path.isfile(screenshot_path):
        to_return = Image.open(screenshot_path)
    else:
        mask = Image.open(MISSING_SCRN_OVERLAY_PATH)
        base = Image.new('RGBA', mask.size, color=image_palette['missing_screenshot_bg'])
        overlay = Image.new('RGBA', mask.size, color=image_palette['missing_screenshot_fg'])
        base.paste(overlay, box=(0,0), mask=mask)
        to_return = base
    if SCREENSHOT_RESIZE_RATIO != 1.0:
        to_return = to_return.resize(tuple([int(to_return.size[x]*SCREENSHOT_RESIZE_RATIO) for x in range(2)]))
    return to_return
    
def draw_map(region_key):
    conn = sqlite3.connect(DB_LOCATION)
    region_cursor = conn.cursor()
    region_cursor.execute('SELECT key, name, default_area FROM regions WHERE key = ?', (region_key,))
    region = region_cursor.fetchone()
    print '>', region[1].upper()
    print '>> Calculating network'
    initial_area = None
    if region[2]:
        initial_area = region[2]
    else:
        area_cursor = conn.cursor()
        area_cursor.execute('SELECT key FROM areas WHERE region = ? ORDER BY key ASC', (region[0],))
        initial_area = area_cursor.fetchone()[0]
        if not initial_area:
            print 'Region has no areas'
            return False
    # Initialise graph, and add area with lowest id as the origin room
    G = nx.Graph()
    G.add_node(initial_area)
    G.node[initial_area]['pos_rough'] = (0, 0)
    pos_rough = {initial_area: (0, 0)}
    pos_to_expand = [initial_area]
    
    # as areas are found, add them to a list to be searched, and search them
    while len(pos_to_expand) > 0:
        # Order in which area initial positions are calculated
        if MODE[0] == 0:
            area = pos_to_expand.pop(0)
        elif MODE[0] == 1:
            area = pos_to_expand.pop()
        else:
            sys.exit('Invalid MODE specified')
        
        # for each linking area (SQL lookup)
        node_cursor = conn.cursor()
        node_cursor.execute('SELECT x_pos, y_pos, link_key FROM nodes WHERE area = ? ORDER BY key ASC', (area,))
        for node in node_cursor:
            # look up link_node key (and link_node's area key)
            link_cursor = conn.cursor()
            link_cursor.execute('SELECT x_pos, y_pos, area FROM nodes WHERE key = ?', (node[2],))
            link_node = link_cursor.fetchone()
            #if link_node is specified and exists
            if link_node:
                # if link_node's area key not in pos list
                if link_node[2] not in pos_rough:
                    # add to graph as node
                    G.add_node(area)
                    # calculate a relative position for new area from initial area
                    relative_px = tuple(node[x]-link_node[x] for x in range(2))
                    # store this as as an absolute set of coordinates
                    absolute_px = tuple(pos_rough[area][x]+relative_px[x] for x in range(2))
                    # add room to pos list (key, (x_pos, y_pos))
                    pos_rough.update({link_node[2] : absolute_px})
                    # if same region (NOT region-gate), further search needed, add to pos_to_expand
                    link_cursor = conn.cursor()
                    link_cursor.execute('SELECT region FROM areas WHERE key = ?', (link_node[2],))
                    link_region = link_cursor.fetchone()
                    if link_region:
                        # If linked area is in same region OR world-map flag is set, add to list of areas to expand upon
                        if (link_region[0] == region[0]) and (WORLD_MAP is False):
                            pos_to_expand.append(link_node[2])
                    else:
                        print 'ERROR: Linked region '+str(link_node[2])+' not found in areas list'
                        return False
                        
                # if link_node's area key is in pos list, it is already scheduled to be searched
                else:
                    None
                # add edge whether area already has position set
                G.add_edge(area, link_node[2])

                # OPTIONAL continuous spring adjustment during addition
                if MODE[1] == 1:
                    pos_rough = nx.spring_layout(G, pos=pos_rough)
                else:
                    None
    
    pos_spring = {}
    if MODE[1] == 2:
        # do not optimise
        # max & min value of both dimensions in rough layout
        pos_rough_max =  max([max(pos_rough.values(), key=lambda x: x[d])[d] for d in range(2)])
        pos_rough_min =  min([min(pos_rough.values(), key=lambda x: x[d])[d] for d in range(2)])
        pos_rough_range = float(pos_rough_max-pos_rough_min)
        # scale to 0-1 space in both dimensions
        for key, pos in pos_rough.iteritems():
            pos_spring.update({key: tuple([float(pos[d]-pos_rough_min)/pos_rough_range for d in range(2)])})
    else:
        # optimise node positions using Fruchterman-Reingold force-directed algorithm
        opt_dist_default = 1/math.sqrt(len(pos_rough))
        opt_dist = opt_dist_default/NETWORK_CONTRACTION
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            # WARNING pos_spring generates a numpy based FutureWarning
            pos_spring = nx.spring_layout(G, pos=pos_rough, k=opt_dist)
    
    # pull pos_spring optimised values into networkx object
    for key in G.nodes():
        G.node[key]['pos_spring'] = pos_spring[key]
    
    # make image using positions given
    SCALE = int(max(ROUGH_SCREENSHOT_SIZE)*math.sqrt(len(G.nodes()))*NETWORK_SPACING)
    image_size_init = (SCALE+IMAGE_PADDING*4, SCALE+IMAGE_PADDING*2)

    # convert pos_spring (0-1 space) to image space (px)
    image_origin = tuple(int(math.floor(image_size_init[x]/2)) for x in range(2))
    for key in G.nodes():
        G.node[key]['pos_px'] = tuple(math.floor((G.node[key]['pos_spring'][x]-0.5)*SCALE)+image_origin[x] for x in range(2))
    
    #initialised detailed node graph for position collection
    H = nx.Graph()
    
    #Read data from database and image files into networkx object for later drawing
    for key in G.nodes():
        pos = G.node[key]['pos_px']
        label_cursor = conn.cursor()
        label_cursor.execute('SELECT name, type FROM areas WHERE key = ?', (key,))
        label = label_cursor.fetchone()
        G.node[key]['name'] = label[0].upper()
        #print '>>> Area', key, G.node[key]['name']
        
        screenshot_path = os.path.join(directories[0], 'areas', str(area)+'.jpg')
        G.node[key]['screenshot'] = get_area_screenshot(key)
        G.node[key]['pos_topleft_px'] = tuple(int(math.floor(pos[x]-G.node[key]['screenshot'].size[x]/2)) for x in range(2))
        
        #detail edges added to graph & dict objects to be drawn later
        node_cursor = conn.cursor()
        node_cursor.execute('SELECT x_pos, y_pos, link_key, key FROM nodes WHERE area = ? ORDER BY key ASC', (key,))
        for node in node_cursor:
            # if node is not already in detail_graph
            if not H.has_node(node[3]):
                #add node to detailed graph and store position
                H.add_node(node[3])
                node_pos = tuple([pos[x]+node[x]*SCREENSHOT_RESIZE_RATIO for x in range(2)])
                H.node[node[3]]['pos_detail_px'] = node_pos
                # look up connecting node id -> area id
                link_cursor = conn.cursor()
                link_cursor.execute('SELECT x_pos, y_pos, area FROM nodes WHERE key = ?', (node[2],))
                link_node = link_cursor.fetchone()
                # add connecting node and edge (if node available)
                if link_node:
                    H.add_node(node[2])
                    H.add_edge(node[2], node[3])
                    link_area_pos = G.node[link_node[2]]['pos_px']
                    link_node_pos = tuple([link_area_pos[x]+link_node[x]*SCREENSHOT_RESIZE_RATIO for x in range(2)])
                    H.node[node[2]]['pos_detail_px'] = link_node_pos        
        # save room type
        if label[1]:
            G.node[key]['type'] = label[1]
        else:
            G.node[key]['type'] = None
    
    #Drawing
    image_palette = generate_palette(region_key)
    # New image errors above arbitrary size (OS limit on single process memory ~2gb)
    #To avoid causing a MemoryError, the map is drawn in hq tiles of 8192px (256**5) maximum edge length
    images_required = tuple([int(math.ceil(float(image_size_init[x])/float(HQ_TILE_SIZE))) for x in range(2)])
    print '>> Total image size:', str(image_size_init[0])+'x'+str(image_size_init[1])+', splitting to', images_required[0]*images_required[1], str(HQ_TILE_SIZE)+'x'+str(HQ_TILE_SIZE),'hq image tiles' 
    
    region_dir = os.path.join(directories[1], region[1])
    common.make_dir_if_not_found(region_dir)
    
    #row strips
    for row in range(images_required[1]):
        #col strips
        for col in range(images_required[0]):
            hq_name = 'hq-'+str(col)+'-'+str(row)+'.png'
            hq_position = tuple([HQ_TILE_SIZE*col, HQ_TILE_SIZE*row])
            hq_spec = ([min(hq_position[x]+HQ_TILE_SIZE, image_size_init[x])-hq_position[x] for x in range(2)])
            with warnings.catch_warnings():
                # WARNING Image.new generates a DecompressionBomb warning with large file sizes
                warnings.simplefilter("ignore")
                big_image = Image.new('RGBA', hq_spec, color=image_palette['bg'])
            big_draw = ImageDraw.Draw(big_image)
            
            #composite screenshots onto image
            for key in G.nodes():
                if G.node[key]['name']:
                    box_adj = tuple([G.node[key]['pos_topleft_px'][x]-hq_position[x] for x in range(2)])
                    big_image.paste(G.node[key]['screenshot'], box=box_adj)
            
            #draw skeleton edges if color specified in palette
            if image_palette['skeleton']:
                draw_network(big_draw, G, 'pos_px', SKELETON_LINE_WIDTH, image_palette['skeleton'], hq_position=hq_position)
                   
            #draw detail edges
            draw_network(big_draw, H, 'pos_detail_px', DETAIL_LINE_WIDTH, image_palette['detail'], hq_position=hq_position)
            
            #draw titles
            for key in G.nodes():
                if G.node[key]['name']:
                    text = G.node[key]['name']
                    if PALETTE == 'debug':
                        text = text+' ('+str(key)+')'
                    adj_topleft_px = tuple([G.node[key]['pos_topleft_px'][x]-hq_position[x] for x in range(2)])
                    big_draw.text(label_line_topleft(adj_topleft_px, 1), text, font=font, fill=image_palette['title'])
            
            #draw labels and icons
            for key in G.nodes():
                if G.node[key]['type']:
                    label_list = sorted(G.node[key]['type'].split(), reverse=True)
                    label_text = str('/'.join(label_list)+' room').upper()
                    adj_topleft_px = tuple([G.node[key]['pos_topleft_px'][x]-hq_position[x] for x in range(2)])
                    big_draw.text(label_line_topleft(adj_topleft_px, 2), label_text, font=font, fill=image_palette['icon'])
                    label_col_current_height = 0
                    for label in label_list:
                        # Load icon mask
                        label_path = os.path.join(LABEL_IMAGE_DIR, label+'.png')
                        if os.path.isfile(label_path):
                            label_mask = Image.open(label_path)
                            
                            label_mask = label_mask.resize(tuple([int(label_mask.size[x]*LABEL_IMAGE_SCALE) for x in range (2)]))
                            label_image = Image.new('RGB', label_mask.size, color=image_palette['icon']) 
                            # Centre labels and add padding
                            label_topleft = tuple([int(G.node[key]['pos_topleft_px'][0]+LABEL_IMAGE_INSET-(0.5*label_mask.size[0]))-hq_position[0], int(G.node[key]['pos_topleft_px'][1]+label_col_current_height+LABEL_IMAGE_SPACING)-hq_position[1]])
                            big_image.paste(label_image, box=label_topleft, mask=label_mask)
                            label_col_current_height = label_col_current_height+LABEL_IMAGE_SPACING+label_mask.size[1]
              
            # save
            print '>> Saving', hq_name
            big_image_path = os.path.join(region_dir, hq_name)
            big_image.save(big_image_path, quality=100)
    
    # Write XML metadata file
    root = ET.Element('IMAGE_PROPERTIES')
    root.attrib = {'WIDTH': str(image_size_init[0]),
                   'HEIGHT': str(image_size_init[1]),
                   'NUMTILES': str(images_required[0]*images_required[1]),
                   'NUMIMAGES': str(1),
                   'TILESIZE': str(HQ_TILE_SIZE)
                   }
    tree = ET.ElementTree(root)
    tree.write(os.path.join(region_dir, METADATA_FILE))
    return None

conn = sqlite3.connect(DB_LOCATION)
region_cursor = conn.cursor()
if SPECIFIED_REGION or WORLD_MAP:
    region_cursor.execute('SELECT key FROM regions WHERE name = ?', (SPECIFIED_REGION.lower(),))
    region = region_cursor.fetchone()
    if region:
        draw_map(region[0])
else:
    region_cursor.execute('SELECT key FROM regions ORDER BY key ASC')
    regions = region_cursor.fetchall()
    # print region maps separately
    for region in regions:
        draw_map(region[0])
