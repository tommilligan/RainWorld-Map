import argparse
import os
import sqlite3
import common, generate, zoomify

def main():
    # Default in and out directories
    directories = common.initialise_subdirs(['assets', 'big_image', 'zoomify_tiles'])

    parser = argparse.ArgumentParser(description='Make big map image from screenshots and connection data') #Parse arguments 
    
    parser.add_argument('-o', '--output', default=None,
                        help='Output direcory. Default is "../'+directories[2]+'"')
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
    
    OUTPUT_PATH = os.path.realpath(os.path.join(os.getcwd(), directories[2]))
    if args.output:
        OUTPUT_PATH = os.path.realpath(os.path.join(os.getcwd(), args.output))   

    # Take location of screenshot and xth line, and return position. If x = 0 returns scrn
    conn = sqlite3.connect(common.get_db_path())
    region_cursor = conn.cursor()
    if args.region or args.world:
        region_cursor.execute('SELECT key FROM regions WHERE name = ?', (args.region.lower(),))
        region = region_cursor.fetchone()
        if region:
            big_image_path = generate.draw_map(region[0],
                             palette_name=args.palette,
                             image_scale_factor=args.scale,
                             network_contraction=args.k_value,
                             network_overlap=args.network_overlap,
                             draw_world=args.world,
                             single_image=args.force
                             )
            zoomify.zoomify(big_image_path, OUTPUT_PATH)
        else:
            print args.region, 'not found in region database'
    else:
        region_cursor.execute('SELECT key FROM regions ORDER BY key ASC')
        regions = region_cursor.fetchall()
        # print region maps separately
        for region in regions:
            big_image_path = generate.draw_map(region[0],
                             palette_name=args.palette,
                             image_scale_factor=args.scale,
                             network_contraction=args.k_value,
                             network_overlap=args.network_overlap,
                             draw_world=args.world,
                             single_image=args.force
                             )
            zoomify.zoomify(big_image_path, OUTPUT_PATH)
    
if __name__ == "__main__":
    main()