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

import common


''' PIXEL DATA
        import numpy as np
        px = np.asarray(screenshot.getdata())
        print px.shape
        '''


directories = common.initialise_subdirs(['assets', 'big_image'])
DB_LOCATION = common.get_db_path()

MODE = (1, 0)
'''
MODE = (a, b)
a: 0=width, 1=depth (order in which initial positions are calculated)
b: 0=final, 1=continuous, 2=none (how ofter spring_layout is calculated)
'''

PALETTE = sys.argv[1]
'''
PALETTE = string
> default
> seamless - try and blend into the Rain World color palette as much as possible
> neon - easy to read, easy to follow map
> debug - awful colours, all detail shown

each color property is a dictionary with the palette name as keys, and must have a default
e.g. dict = {'default': (0, 0, 0), 'debug': (255, 0, 0)}
'''
def pal_get(choices):
    if PALETTE in choices:
        return choices[PALETTE]
    else:
        return choices['default']

#palettes
pal_background_col = {
            'default': (0, 0, 0),
            'debug': (0, 31, 0),
            'seamless': (26, 11, 32),
            'neon': (16, 7, 19)
            }
pal_skeleton_col = {
            'default': (255, 255, 255),
            'debug': (255, 255, 0),
            'neon': (255, 0, 102)
            }
pal_detail_col = {
            'default': (255, 255, 255),
            'debug': (255, 0, 0),
            'seamless': (215, 207, 222),
            'neon': (0, 102, 255)
            }
pal_title_col = {
            'default': (255, 255, 255),
            'neon': (255, 0, 102),
            'seamless': (241, 17, 228)
            }
pal_subtitle_col = {
            'default': (255, 255, 255),
            'debug': (255, 63, 0),
            'neon': (0, 255, 102),
            'seamless': (131, 45, 118)
            }
pal_missing_scrn_bg_col = {
            'default': (168, 255, 255),
            'debug': (0, 255, 0),
            'neon': pal_background_col['neon'],
            'seamless': pal_background_col['seamless']
            }
pal_missing_scrn_overlay_col = {
            'default': pal_missing_scrn_bg_col['default'],
            'debug': (0, 0, 0),
            'neon': pal_title_col['neon'],
            'seamless': (255, 255, 255)
            }
pal_skeleton_line = {'default': 0, 'debug': 6}
pal_detail_line = {'default': 9, 'debug': 12}
pal_font_size = {'default': 128, 'debug': 192}
pal_icon_scale = {'default': 1, 'debug': 3}
        
# even numbers are best
BACKGROUND_COLOR = pal_get(pal_background_col)
SKELETON_COLOR = pal_get(pal_skeleton_col)
DETAIL_COLOR = pal_get(pal_detail_col)
SKELETON_LINE_WIDTH = pal_get(pal_skeleton_line)
DETAIL_LINE_WIDTH = pal_get(pal_detail_line)
FONT_PATH = os.path.join(directories[0], 'misc', 'saxmono.ttf')
FONT_SIZE = pal_get(pal_font_size)
TITLE_COLOR = pal_get(pal_title_col)
SUBTITLE_COLOR = pal_get(pal_subtitle_col)
LABEL_IMAGE_COLOR = SUBTITLE_COLOR
LABEL_IMAGE_DIR = os.path.join(directories[0], 'labels')
MISSING_SCRN_BG_COLOR = pal_get(pal_missing_scrn_bg_col)
MISSING_SCRN_OVERLAY_COLOR = pal_get(pal_missing_scrn_overlay_col)
MISSING_SCRN_OVERLAY_PATH = os.path.join(directories[0], 'misc', 'rain_mask.png')

SCREENSHOT_RESIZE_RATIO = 1.0
RAW_SCREENSHOT_SIZE = (1366, 768)
ROUGH_SCREENSHOT_SIZE = tuple([int(RAW_SCREENSHOT_SIZE[x]*SCREENSHOT_RESIZE_RATIO) for x in range(2)])
NETWORK_CONTRACTION = 2.2 # Changes style of network # 2.2 works
NETWORK_SPACING = 2.25 #WANT THIS BIGGER IF POSSIBLE! # 2.25 works
IMAGE_PADDING = 800
LABEL_IMAGE_INSET = 100
LABEL_IMAGE_SPACING = 20
LABEL_IMAGE_SCALE = pal_get(pal_icon_scale)
LABEL_LINE_HEIGHT = FONT_SIZE+6
LABEL_LINE_OFFSET = int(FONT_SIZE/2)

# Warning Supression
if PALETTE is not 'debug':
    #Dealing with large images - DecompressionBomb warning is expected and supressed
    warnings.simplefilter('ignore', Image.DecompressionBombWarning)
    #Warning of upgrade in future - will not affect code
    #warnings.simplefilter('ignore', FutureWarning)

# Take location of screenshot and xth line, and return position. If x = 0 returns scrn
def label_line_topleft(scrn, x):
    return tuple([scrn[0]+(LABEL_LINE_OFFSET*x), scrn[1]-(LABEL_LINE_HEIGHT*x)])

def invert_rgb(rgb):
    return tuple([255-rgb[x] for x in range(3)])

def draw_network(draw, graph, position_dict, line_width, color):
    '''Takes an ImageDraw object, and uses it to draw a network as held by a networkx graph object & a node keyed position dictonary'''
    # Only draw if line_width > 0
    if line_width > 0:
        for edge in graph.edges():
            draw.line([position_dict[edge[0]], position_dict[edge[1]]], fill=color, width=line_width)
        for node in graph.nodes():
            draw.ellipse([tuple(position_dict[node][x]-line_width*2 for x in range(2)), tuple(position_dict[node][x]+line_width*2 for x in range(2))], fill=color, outline=color)
    return None  

def get_area_screenshot(area):
    screenshot_path = os.path.join(directories[0], 'areas', str(area)+'.jpg')
    if os.path.isfile(screenshot_path):
        return Image.open(screenshot_path)
    else:
        mask = Image.open(MISSING_SCRN_OVERLAY_PATH)
        base = Image.new('RGBA', mask.size, color=MISSING_SCRN_BG_COLOR)
        overlay = Image.new('RGBA', mask.size, color=MISSING_SCRN_OVERLAY_COLOR)
        base.paste(overlay, box=(0,0), mask=mask)
        return base
    
conn = sqlite3.connect(DB_LOCATION)
region_cursor = conn.cursor()
region_cursor.execute('SELECT key, name FROM regions ORDER BY key ASC')
regions = region_cursor.fetchall()
# print region maps separately
for region in regions:
    print '>', region[1].upper()
    print '> Calculating network'
    area_cursor = conn.cursor()
    area_cursor.execute('SELECT key FROM areas WHERE region = ? ORDER BY key ASC', (region[0],))
    initial_area = area_cursor.fetchone()
    
    # Initialise graph, and add area with lowest id as the origin room
    G = nx.Graph()
    G.add_node(initial_area[0])
    pos_rough = {initial_area[0]: (0, 0)}
    pos_to_expand = [initial_area[0]]
    # for each area in pos list
    #for area, position in pos_rough.iteritems():
    while len(pos_to_expand) > 0:
        # Order in which area initial positions are calculated
        if MODE[0] == 0:
            area = pos_to_expand.pop(0)
        elif MODE[0] == 1:
            area = pos_to_expand.pop()
        else:
            sys.exit('Invalid MODE specified')
        node_cursor = conn.cursor()
        node_cursor.execute('SELECT x_pos, y_pos, link_key FROM nodes WHERE area = ? ORDER BY key ASC', (area,))
        # for each linking area (SQL lookup)
        for node in node_cursor:
            # look up connecting node id -> area id
            link_cursor = conn.cursor()
            link_cursor.execute('SELECT x_pos, y_pos, area FROM nodes WHERE key = ?', (node[2],))
            link_node = link_cursor.fetchone()
            #if link node is specified and exists
            if link_node:
                # if linking area not in pos list
                if link_node[2] not in pos_rough:
                    # add to graph as node
                    G.add_node(area)
                    # calculate an initial position for room from initial room
                    relative_px = tuple(node[x]-link_node[x] for x in range(2))
                    absolute_px = tuple(pos_rough[area][x]+relative_px[x] for x in range(2))
                    # add room to pos list (key, (x_pos, y_pos))
                    pos_rough.update({link_node[2] : absolute_px})
                    # if same region (NOT region-gate), further search needed, add to pos_to_expand
                    link_cursor = conn.cursor()
                    link_cursor.execute('SELECT region FROM areas WHERE key = ?', (link_node[2],))
                    link_region = link_cursor.fetchone()
                    if link_region[0] == region[0]:
                        pos_to_expand.append(link_node[2])
                else:
                    None
                # add edge whether area already has position or not
                G.add_edge(area, link_node[2])

                # continuous spring adjustment during addition
                if MODE[1] == 1:
                    pos_rough = nx.spring_layout(G, pos=pos_rough)
                else:
                    None
    
    pos_spring = {}
    if MODE[1] == 2:
        # do not optimise
        # max value of both dimensions in rough layout
        pos_rough_max =  max([max(pos_rough.values(), key=lambda x: x[d])[d] for d in range(2)])
        pos_rough_min =  min([min(pos_rough.values(), key=lambda x: x[d])[d] for d in range(2)])
        pos_rough_range = float(pos_rough_max-pos_rough_min)
        for key, pos in pos_rough.iteritems():
            pos_spring.update({key: tuple([float(pos[d]-pos_rough_min)/pos_rough_range for d in range(2)])})
    else:
        # optimise node positions using Fruchterman-Reingold force-directed algorithm
        opt_dist_default = 1/math.sqrt(len(pos_rough))
        opt_dist = opt_dist_default/NETWORK_CONTRACTION
        # this will generate FutureWarning
        pos_spring = nx.spring_layout(G, pos=pos_rough, k=opt_dist)
    '''
    print pos_rough
    print pos_spring
    '''
    
    print '> Making image'
    # make image using positions given
    SCALE = int(max(ROUGH_SCREENSHOT_SIZE)*math.sqrt(len(G.nodes()))*NETWORK_SPACING)
    image_size_init = (SCALE+IMAGE_PADDING*4, SCALE+IMAGE_PADDING*2)
    image_origin = tuple(math.floor(image_size_init[x]/2) for x in range(2))
    # scale up coords to image size and centre (origin)
    pos_px = {key: tuple(math.floor((pos[x]-0.5)*SCALE)+image_origin[x]
              for x in range(2))
              for key, pos in pos_spring.iteritems()
              }
    
    # New image errors above arbitrary size. 
    # Tested at (22454, 20454) 459274116 pixels
    est_px = image_size_init[0]*image_size_init[1]
    print '>> Properties:', image_size_init, est_px, 'pixels'
    print '>> Estimated uncompressed size:', float(est_px*4)/float(1024**3), 'GB'
    big_image = Image.new('RGBA', image_size_init, color=BACKGROUND_COLOR)
    big_draw = ImageDraw.Draw(big_image)
    font = ImageFont.truetype(font=FONT_PATH, size=FONT_SIZE)
    #DEPRECATED font = ImageFont.load_default()
    
    # draw nodes
    '''
    look at scale|spring k value for overlapping nodes?
    '''
    print '>> Pasting areas'
    #initialised detailed node graph for position collection
    H = nx.Graph()
    pos_detail_px = {}
    
    #initialise other dicts
    area_name_dict = {}
    area_type_dict = {}
    pos_topleft_px = {}
    
    for key, pos in pos_px.iteritems():
        label_cursor = conn.cursor()
        label_cursor.execute('SELECT name, type FROM areas WHERE key = ?', (key,))
        label = label_cursor.fetchone()
        label_name = label[0].upper()
        #name added to dict for later
        area_name_dict.update({key: label_name})
        print '>>> Area', key, label_name
        
        screenshot_path = os.path.join(directories[0], 'areas', str(area)+'.jpg')
        screenshot = get_area_screenshot(key)
        screenshot_topleft = tuple(int(math.floor(pos[x]-screenshot.size[x]/2)) for x in range(2))
        #topleft coordinate added to dict for later
        pos_topleft_px.update({key: screenshot_topleft})
        
        #add screenshot to composite image
        big_image.paste(screenshot, box=screenshot_topleft)
        
        #detail edges added to graph & dict objects to be drawn later
        node_cursor = conn.cursor()
        node_cursor.execute('SELECT x_pos, y_pos, link_key, key FROM nodes WHERE area = ? ORDER BY key ASC', (key,))
        for node in node_cursor:
            # if node is not already in detail_graph
            if not H.has_node(node[3]):
                #add node to detailed graph and store position
                H.add_node(node[3])
                node_pos = tuple([pos[x]+node[x] for x in range(2)])
                #save to node keyed dict to draw later
                pos_detail_px.update({node[3]: node_pos})
                # look up connecting node id -> area id
                link_cursor = conn.cursor()
                link_cursor.execute('SELECT x_pos, y_pos, area FROM nodes WHERE key = ?', (node[2],))
                link_node = link_cursor.fetchone()
                # add connecting node and edge (if node available)
                if link_node:
                    H.add_node(node[2])
                    H.add_edge(node[2], node[3])
                    link_area_pos = pos_px[link_node[2]]
                    link_node_pos = tuple([link_area_pos[x]+link_node[x] for x in range(2)])
                    #save to node keyed dict to draw later
                    pos_detail_px.update({node[2]: link_node_pos})
                
        # if room has type, save for later
        if label[1]:
            area_type_dict.update({key: label[1]})
        else:
            None
    
    print '>> Drawing extras'
    #draw skeleton edges
    draw_network(big_draw, G, pos_px, SKELETON_LINE_WIDTH, SKELETON_COLOR)
           
    #draw detail edges
    draw_network(big_draw, H, pos_detail_px, DETAIL_LINE_WIDTH, DETAIL_COLOR)
    
    #draw titles
    for key, text in area_name_dict.iteritems():
        if PALETTE == 'debug':
            text = text+' ('+str(key)+')'
        big_draw.text(label_line_topleft(pos_topleft_px[key], 1), text, font=font, fill=TITLE_COLOR)
        
    #draw labels and icons
    for key, text in area_type_dict.iteritems():
        label_list = sorted(text.split(), reverse=True)
        label_text = str('/'.join(label_list)+' room').upper()
        big_draw.text(label_line_topleft(pos_topleft_px[key], 2), label_text, font=font, fill=SUBTITLE_COLOR)
        label_col_current_height = 0
        for label in label_list:
            # Load icon mask
            label_path = os.path.join(LABEL_IMAGE_DIR, label+'.png')
            if os.path.isfile(label_path):
                label_mask = Image.open(label_path)
                label_mask = label_mask.resize(tuple([label_mask.size[x]*LABEL_IMAGE_SCALE for x in range (2)]))
                label_image = Image.new('RGB', label_mask.size, color=LABEL_IMAGE_COLOR) 
                # Centre labels and add padding
                label_topleft = tuple([int(pos_topleft_px[key][0]+LABEL_IMAGE_INSET-(0.5*label_mask.size[0])), int(pos_topleft_px[key][1]+label_col_current_height+LABEL_IMAGE_SPACING)])
                big_image.paste(label_image, box=label_topleft, mask=label_mask)
                label_col_current_height = label_col_current_height+LABEL_IMAGE_SPACING+label_mask.size[1]
    
    # save
    print '>> Saving'
    big_image_path = os.path.join(directories[1], region[1]+'.png')
    big_image.save(big_image_path, quality=100)
