import argparse
import os
import sqlite3
import shutil
import common, generate, zoomify

def main():
    # Default in and out directories
    directories = common.initialise_subdirs(['assets', 'spring_seq'])

    parser = argparse.ArgumentParser(description='Show the spring process')
    parser.add_argument('-r', '--region', required=True,
                        help='Region to render - default is all')
    parser.add_argument('-p', '--property', required=True, choices=['k', 'v', 'i'],
                        help='Property to increment')
    parser.add_argument('-k', '--k-value', default=3.0, type=float,
                        help='Spring constant passed to the Fruchterman-Reingold algorithm. Changes network shape, default is 3')
    parser.add_argument('-v', '--network-overlap', default=3.0, type=float,
                        help='Increases spacing between nodes (after position optimisation), default is 3')
    parser.add_argument('-i', '--iterations', default=50, type=int,
                        help='Number of iterations for Fruchterman-Reingold algorithm, default is 50')
    parser.add_argument('-m', '--min', default=1, type=float,
                        help='First value  of specified property, default is 1')
    parser.add_argument('-s', '--step', default=1, type=float,
                        help='Step of specified property, default is 1')
    parser.add_argument('-n', '--num_steps', default=10, type=int,
                        help='Number of steps of specified property, default is 10')
    args = parser.parse_args()
    
    # Take location of screenshot and xth line, and return position. If x = 0 returns scrn
    conn = sqlite3.connect(common.get_db_path())
    region_cursor = conn.cursor()
    region_keys = []

    region_cursor.execute('SELECT key FROM regions WHERE name = ?', (args.region.lower(),))
    region = region_cursor.fetchone()
    if region:
        region_keys = [region[0]]
    else:
        print args.region, 'not found in region database'
        return False
    
    a = {'k': args.k_value,
         'v': args.network_overlap,
         'i': args.iterations
         }
    
    for region_key in region_keys:
        common.renew_dir(directories[1])
        for a[args.property] in [(x*args.step)+args.min for x in range(0, args.num_steps)]:
            # Properties that must be int
            if args.property == 'i':
                a[args.property] = int(a[args.property])
            big_image_path = generate.draw_map(region_key,
                             image_scale_factor=0.05,
                             network_contraction=a['k'],
                             network_overlap=a['v'],
                             iterations=a['i']
                             )
            a_name = '%.3f' % a[args.property]
            shutil.move(os.path.join(big_image_path, 'hq-0-0.png'), os.path.join(directories[1], args.property+'-'+a_name+'.png'))

if __name__ == "__main__":
    main()