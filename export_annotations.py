from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import os
import logging
import numpy as np

import geopandas as gpd
import pandas as pd
import shapely

import matplotlib.pyplot as plt
import openslide

from matplotlib import colors as mcolors
from cytomine import Cytomine
import warnings
from cytomine.lib import *
import requests
import wget
from PIL import Image

Image.warnings.simplefilter('error', Image.DecompressionBombWarning)
warnings.simplefilter(action='ignore', category=FutureWarning)
Image.MAX_IMAGE_PIXELS = None

# parse input arguments
parser = argparse.ArgumentParser(description='Extract a series of annotations and corresponding image from cytomine')
parser.add_argument("-u", "--id_user", dest='id_user', default=7531, type=int, help="UserID related to annotations")
parser.add_argument("-p", "--id_project", dest='id_project', default=1553, type=int, help="ProjectID with annotations")
parser.add_argument("-i", "--id_image", dest='id_image', default=None, type=int, required=True,
                    help="ProjectID with annotations")
parser.add_argument("-o", "--out_dir", dest='out_dir', default=os.getcwd(), help="Output directory")
parser.add_argument("-c", "--annotation_config", dest='annotation_config', default='annotation_config',
                    help="Annotation config file")

parser.add_argument("-v", "--verbose",
                    dest="logLevel",
                    choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                    default="INFO",
                    help="Set the logging level")
parser.add_argument("-d", "--download_url_base",dest="download_url_base",
                    default="http://cytomine.com/image/download?fif=",help="Url base address, will be used to download images")

args = parser.parse_args()

if args.logLevel:
    logging.basicConfig(level=getattr(logging, args.logLevel))

id_user = args.id_user
id_project = args.id_project
id_image = args.id_image
out_dir = args.out_dir
download_url_base = args.download_url_base

# Assert the environment variables are set
cytomine_host = os.environ['CYTOMINE_HOST'].strip()
cytomine_public_key = os.environ['CYTOMINE_PUBLIC_KEY'].strip()
cytomine_private_key = os.environ['CYTOMINE_PRIVATE_KEY'].strip()  # type: str

if cytomine_host == None or cytomine_public_key == None or cytomine_private_key == None:
    print("ERROR: Environment variables are unset!!!!\n"
          "Make sure CYTOMINE_HOST, CYTOMINE_PUBLIC_KEY, and CYTOMINE_PRIVATE_KEY environments are set!")

# Get color -> annotationTerm mapping
if not os.path.isfile(args.annotation_config):
    print("ERROR: You must specify an annotation config file!!!!\n")
else:
    annotation_config = args.annotation_config

colors = dict(mcolors.BASE_COLORS, **mcolors.CSS4_COLORS)
color_df = pd.DataFrame()
color_list = []
with open(annotation_config, 'r') as f:
    for line in f:
        if line[:1] in '0123456789':
            id, name, color = line.strip().split("\t")
            tmp = pd.DataFrame(data={'id': [id], 'name': [name], 'color': [color], 'hex': [colors[color]]})
            color_df = color_df.append(tmp)
            color_list.append(color)
        else:
            pass

# Set the ID to an int
color_df = color_df.astype(dtype={'id': 'int64'})

conn = Cytomine(cytomine_host, cytomine_public_key, cytomine_private_key, base_path='/api/', working_path='.',verbose=True)

annotations = conn.get_annotations(
    id_project=id_project,
    id_user=id_user,
    id_image=id_image,
    showWKT=True,
    showMeta=True,
    showGIS=True,
    reviewed_only=False)

# Get dataframe of annotations objects
df = pd.DataFrame()
for x in range(len(annotations)):
    tmp_df = pd.read_json(annotations[x].to_json())
    tmp_df['location'] = tmp_df['location'].apply(shapely.wkt.loads)
    if tmp_df.term.__len__() > 0:
        tmp_df['color_name'] = color_df.color[color_df.id == tmp_df['term'].tolist()[0]] # annotation color
        tmp_df['termName'] = color_df.name[color_df.id == tmp_df['term'].tolist()[0]]  # annotation name/ cell type
        df = df.append(gpd.GeoDataFrame(tmp_df, geometry='location'))


# get the bounding box of the target region
target_pd = df[df.termName == 'Target Region']
# Make sure there is only 1 target region annotated per image
if target_pd.values.shape[0] != 1:
    print('ERROR: {} has more than 1 target region!!!!'.format(str(id_image)))
target_df = df.location[df.termName == 'Target Region'].bounds
minx = int(target_df.minx)
miny = int(target_df.miny)
maxx = int(target_df.maxx)
maxy = int(target_df.maxy)

target_h = maxy - miny
target_w = maxx - minx

## get the bounding box of all the annotation
a_minx = minx
a_miny = miny
a_maxx = maxx
a_maxy = maxy

tmp = df.location.bounds
if int(min(tmp.minx)) < a_minx:
    a_minx = int(min(tmp.minx))
if int(min(tmp.miny)) < a_miny:
    a_miny = int(min(tmp.miny))
if int(max(tmp.maxx)) > a_maxx:
    a_maxx = int(max(tmp.maxx))
if int(max(tmp.maxy)) > a_maxy:
    a_maxy = int(max(tmp.maxy))
ann_h = a_maxy - a_miny
ann_w = a_maxx - a_minx

# get all the colors
num_color = len(color_list)
for c_idx in range(num_color):
    tmp = df[df.color_name == color_list[c_idx]]

# # Plot all the annotations
num_subplots = len(color_list)# Plot with least important first
f, ax = plt.subplots(frameon=False)
f.tight_layout(pad=0, h_pad=0, w_pad=0)
ax.set_xlim(a_minx, a_maxx)
ax.set_ylim(a_miny, a_maxy)
for sub_plot in range(num_subplots):
    tmp = df[df.color_name == color_list[sub_plot]]
    try:
        gpd.plotting.plot_dataframe(df=tmp, ax=ax, color=color_list[sub_plot])
    except TypeError:
        pass
ax.set_axis_off()
DPI = f.get_dpi()
plt.subplots_adjust(left=0, bottom=0, right=1, top=1,wspace=0, hspace=0)
f.set_size_inches(ann_w / DPI, ann_h / DPI)

f.savefig("Mask_tmp.png", pad_inches='tight')

# Clip the target region from the entire annotation
ann_Img_tmp = Image.open("Mask_tmp.png")
M = np.array(ann_Img_tmp)
Ow= minx-a_minx
Oh= a_maxy-maxy
t = M[Oh:Oh+target_h,Ow:Ow+target_w,:,]
im = Image.fromarray(t)
xy_coords = str(minx) + "_" + str(miny) + "_" + str(maxx) + "_" + str(maxy)
out_name = str(id_project) + "_" + str(id_image) + "_" + xy_coords + "_mask.png"
out_name = os.path.join(out_dir, out_name)
im.save(out_name, "png")

#Get image instances from project
image_instances = ImageInstanceCollection()
image_instances.project  =  id_project
image_instances  =  conn.fetch(image_instances)
images = image_instances.data()

#Go through all images
img = [i for i in images if i.id == id_image]
if not image.__sizeof__() == 1:
    pass
image = img[0]
# print("image id: %d width: %d height: %d resolution: %f magnification: %d filename: %s" %(image.id,image.width,image.height,image.resolution,image.magnification,image.filename))
url = download_url_base + image.fullPath
print("Downloading image from %s" % url)
print("The image file size usually occupy more than 1GB, so downloading will last several minutes, be patient!")
r = requests.get(url)
f_name = url[url.rfind("/")+1:-1]
with open(f_name, 'wb') as f:
    f.write(r.content) # save the whole slide image
# read the original whole slide image, parse it and get the target patch at level 0
sd_fix = openslide.OpenSlide(f_name)
dim = sd_fix.dimensions
Img = sd_fix.read_region((minx, dim[1]-maxy), 0, (target_w, target_h))# get patch from level 0
out_name = str(id_project) + "_" + str(id_image) + "_" + xy_coords + "_img.png"
out_name = os.path.join(out_dir, out_name)
im.save(out_name)
Img.save(out_name, "png")

