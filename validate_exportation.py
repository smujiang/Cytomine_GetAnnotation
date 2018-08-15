from PIL import Image
import numpy as np
Image.MAX_IMAGE_PIXELS = None

img_name = "1553_397997_76836_21519_104676_28613_img.png" # Change it before your test
mask_name = "1553_397997_76836_21519_104676_28613_mask.png" # Change it before your test
init_pos = [100,100] # Change it before your test
patch_size = [2800,2800] # Change it before your test
# patch_size = [3080,3080] # Change it before your test

img = Image.open(img_name)
I = np.array(img)
I_patch = I[init_pos[0]:(init_pos[0]+patch_size[0]),init_pos[1]:(init_pos[1]+patch_size[1]),:]
im1 = Image.fromarray(I_patch)
if im1.mode == "RGB":
    a_channel = Image.new('L', im1.size, 255)   # 'L' 8-bit pixels, black and white
    im1.putalpha(a_channel)
im1.save("Img_patch_val.png")

mask = Image.open(mask_name)
M = np.array(mask)
M_patch = M[init_pos[0]:(init_pos[0]+patch_size[0]),init_pos[1]:(init_pos[1]+patch_size[1]),:]
im2 = Image.fromarray(M_patch)
im2.save("Mask_patch_val.png")
blended= Image.blend(im1, im2, alpha=0.7)
# blended.show()
blended.save("Blended_patch.png")