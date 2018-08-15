import argparse
import os
import logging
import numpy as np

import geopandas as gpd
import pandas as pd
import shapely
import re
import matplotlib.pyplot as plt
import openslide

from matplotlib import colors as mcolors
from cytomine import Cytomine
import warnings
from cytomine.lib import *
import requests
import wget
from PIL import Image

'''
First step is separate lines according to the image id, appears like this.
"image": 123214 
'''
out_base_dir = 'H:\\PathologicalImages\\AnnotationLog\\out\\'
annotation_log = "H:\\PathologicalImages\\AnnotationLog\\Annotations.dat"

line_cnt=0
with open(annotation_log, "r") as fp:
    log = fp.readline()
    line_cnt+=1
    while log.strip("\n"):
        match_txt = re.search("image\":[\d]+",log).group(0)
        id_txt = match_txt[7:]
        ann_fp = open(out_base_dir+id_txt+".txt",'a')
        idx1 = log.index("{")
        idx2 = log.rindex("}")
        m_txt = log[idx1:idx2 + 1]
        ann_fp.write(m_txt+"\n")
        ann_fp.close()
        log = fp.readline()
        line_cnt += 1
        print("processing %d line" % line_cnt)

'''
Second step is crop the json out, appears like this:
{"class": "be.cytomine.ontology.UserAnnotation",-----------}
see the implementation in convert2mask.py
'''










