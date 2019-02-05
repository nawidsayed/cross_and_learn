import torch.utils.data as data
import torch
from torchvision import transforms
from collections import namedtuple

from PIL import Image
import os
import os.path
import numpy as np

class Cityscapes(data.Dataset):
  path_rescaled = "/net/hci-storage01/groupfolders/compvis/nsayed/data/cityscapes/rescaled"
  infos = ['images_fine', 'labels_fine']
  suffix = ['_leftImg8bit.png', '_gtFine_labelIds.png']

  def __init__(self, split='train', transform=None):
    self.split = split
    self.transform = transform
    self.path_images = os.path.join(self.path_rescaled, self.infos[0], self.split)
    self.path_labels = os.path.join(self.path_rescaled, self.infos[1], self.split)

    self.filenames = []

    for root, dirs, files in os.walk(self.path_labels):
      for file in files:
        self.filenames.append(file[:-20])


    self.len = len(self.filenames)

    Label = namedtuple( 'Label' , ['name', 'id', 'trainId', 'category', 'categoryId', 'hasInstances', 'ignoreInEval', 'color'])

    self.Label = Label

    self.labels = [
        #       name                     id    trainId   category            catId     hasInstances   ignoreInEval   color
        Label(  'unlabeled'            ,  0 ,      255 , 'void'            , 0       , False        , True         , (  0,  0,  0) ),
        Label(  'ego vehicle'          ,  1 ,      255 , 'void'            , 0       , False        , True         , (  0,  0,  0) ),
        Label(  'rectification border' ,  2 ,      255 , 'void'            , 0       , False        , True         , (  0,  0,  0) ),
        Label(  'out of roi'           ,  3 ,      255 , 'void'            , 0       , False        , True         , (  0,  0,  0) ),
        Label(  'static'               ,  4 ,      255 , 'void'            , 0       , False        , True         , (  0,  0,  0) ),
        Label(  'dynamic'              ,  5 ,      255 , 'void'            , 0       , False        , True         , (111, 74,  0) ),
        Label(  'ground'               ,  6 ,      255 , 'void'            , 0       , False        , True         , ( 81,  0, 81) ),
        Label(  'road'                 ,  7 ,        0 , 'flat'            , 1       , False        , False        , (128, 64,128) ),
        Label(  'sidewalk'             ,  8 ,        1 , 'flat'            , 1       , False        , False        , (244, 35,232) ),
        Label(  'parking'              ,  9 ,      255 , 'flat'            , 1       , False        , True         , (250,170,160) ),
        Label(  'rail track'           , 10 ,      255 , 'flat'            , 1       , False        , True         , (230,150,140) ),
        Label(  'building'             , 11 ,        2 , 'construction'    , 2       , False        , False        , ( 70, 70, 70) ),
        Label(  'wall'                 , 12 ,        3 , 'construction'    , 2       , False        , False        , (102,102,156) ),
        Label(  'fence'                , 13 ,        4 , 'construction'    , 2       , False        , False        , (190,153,153) ),
        Label(  'guard rail'           , 14 ,      255 , 'construction'    , 2       , False        , True         , (180,165,180) ),
        Label(  'bridge'               , 15 ,      255 , 'construction'    , 2       , False        , True         , (150,100,100) ),
        Label(  'tunnel'               , 16 ,      255 , 'construction'    , 2       , False        , True         , (150,120, 90) ),
        Label(  'pole'                 , 17 ,        5 , 'object'          , 3       , False        , False        , (153,153,153) ),
        Label(  'polegroup'            , 18 ,      255 , 'object'          , 3       , False        , True         , (153,153,153) ),
        Label(  'traffic light'        , 19 ,        6 , 'object'          , 3       , False        , False        , (250,170, 30) ),
        Label(  'traffic sign'         , 20 ,        7 , 'object'          , 3       , False        , False        , (220,220,  0) ),
        Label(  'vegetation'           , 21 ,        8 , 'nature'          , 4       , False        , False        , (107,142, 35) ),
        Label(  'terrain'              , 22 ,        9 , 'nature'          , 4       , False        , False        , (152,251,152) ),
        Label(  'sky'                  , 23 ,       10 , 'sky'             , 5       , False        , False        , ( 70,130,180) ),
        Label(  'person'               , 24 ,       11 , 'human'           , 6       , True         , False        , (220, 20, 60) ),
        Label(  'rider'                , 25 ,       12 , 'human'           , 6       , True         , False        , (255,  0,  0) ),
        Label(  'car'                  , 26 ,       13 , 'vehicle'         , 7       , True         , False        , (  0,  0,142) ),
        Label(  'truck'                , 27 ,       14 , 'vehicle'         , 7       , True         , False        , (  0,  0, 70) ),
        Label(  'bus'                  , 28 ,       15 , 'vehicle'         , 7       , True         , False        , (  0, 60,100) ),
        Label(  'caravan'              , 29 ,      255 , 'vehicle'         , 7       , True         , True         , (  0,  0, 90) ),
        Label(  'trailer'              , 30 ,      255 , 'vehicle'         , 7       , True         , True         , (  0,  0,110) ),
        Label(  'train'                , 31 ,       16 , 'vehicle'         , 7       , True         , False        , (  0, 80,100) ),
        Label(  'motorcycle'           , 32 ,       17 , 'vehicle'         , 7       , True         , False        , (  0,  0,230) ),
        Label(  'bicycle'              , 33 ,       18 , 'vehicle'         , 7       , True         , False        , (119, 11, 32) ),
        Label(  'license plate'        , -1 ,       -1 , 'vehicle'         , 7       , False        , True         , (  0,  0,142) ),
    ]

    self.id_to_color = {label.id: label.color for label in self.labels}



  def __len__(self):
    return self.len

  def __getitem__(self, index):
    filename = self.filenames[index]
    path_image = os.path.join(self.path_images, filename + self.suffix[0])
    path_label = os.path.join(self.path_labels, filename + self.suffix[1])

    image = Image.open(path_image)
    image.load()
    label = Image.open(path_label)
    label.load()
    if self.transform is not None:
      image = self.transform(image)  
    label = np.array(label).astype(np.int64)
    label = torch.LongTensor(label)

    return image, label

# transform = transforms.ToTensor()
# city = Cityscapes(transform=transform)

# print(city[4])






































# conv1  Parameter containing:
# (0 ,0 ,.,.) = 
#  -0.0235  0.1406  0.0623  0.1223 -0.1414
#  -0.1052 -0.0559  0.1411 -0.0999 -0.0746
#  -0.1153 -0.0293 -0.0887 -0.0317 -0.0437
#   0.0480 -0.0292  0.1232  0.0110  0.0980
#  -0.0229 -0.0528  0.0524  0.0069 -0.0836

# (0 ,1 ,.,.) = 
#  -0.0160  0.1069 -0.0765 -0.1337  0.0097
#   0.0482  0.1171 -0.0234 -0.0121  0.0166
#  -0.0196 -0.1017  0.1242 -0.0854  0.0787
#   0.0851  0.0611  0.1324  0.0856 -0.0528
#  -0.1152  0.0544  0.0051  0.1065  0.1032

# (1 ,0 ,.,.) = 
#   0.1116  0.0931 -0.1174  0.0932 -0.1304
#  -0.0642 -0.0934 -0.1247  0.1070  0.0482
#  -0.1136  0.0263 -0.0223  0.0486  0.1295
#  -0.0250  0.0094 -0.0855  0.0543 -0.0595
#  -0.0522 -0.1012  0.0528  0.0801  0.0946

# (1 ,1 ,.,.) = 
#  -0.0247 -0.1362 -0.1318  0.0708  0.0351
#   0.1383  0.0454  0.0702 -0.0570 -0.0621
#  -0.0152  0.0818 -0.0786 -0.1122 -0.1207
#  -0.0147 -0.0087  0.1156 -0.1142 -0.0584
#   0.1141 -0.0600 -0.1076 -0.1046  0.0070


# conv1  Parameter containing:
# (0 ,0 ,.,.) = 
#   0.0054  0.1714  0.0949  0.1568 -0.1051
#  -0.0777 -0.0266  0.1723 -0.0669 -0.0397
#  -0.0892 -0.0013 -0.0589 -0.0000 -0.0102
#   0.0727 -0.0026  0.1516  0.0412  0.1301
#   0.0005 -0.0276  0.0794  0.0358 -0.0529

# (0 ,1 ,.,.) = 
#  -0.0211 -0.0929 -0.3408 -0.4097 -0.3080
#   0.1890  0.1120 -0.3595 -0.3454 -0.3939
#   0.1002  0.1717  0.2948  0.1605  0.3301
#   0.0666  0.2223  0.4640  0.4246  0.1210
#   0.0964  0.0444 -0.0561  0.0950  0.2401

# (1 ,0 ,.,.) = 
#   0.0570  0.0348 -0.1795  0.0271 -0.2007
#  -0.1208 -0.1537 -0.1888  0.0388 -0.0241
#  -0.1724 -0.0361 -0.0886 -0.0218  0.0550
#  -0.0861 -0.0554 -0.1542 -0.0184 -0.1364
#  -0.1158 -0.1686 -0.0184  0.0049  0.0153

# (1 ,1 ,.,.) = 
#   0.1910  0.1735 -0.0234  0.0061 -0.1295
#   0.2648  0.2073  0.0773 -0.2017 -0.2756
#   0.3927  0.2789 -0.1814 -0.2754 -0.3279
#   0.4226  0.0142 -0.1504 -0.3263 -0.2990
#   0.2457 -0.1608 -0.2266 -0.2586 -0.1818


# conv2  Parameter containing:
# (0 ,0 ,.,.) = 
# 1.00000e-02 *
#   5.8910 -0.5075 -0.8858  0.5862 -1.9443
#   3.7771  0.9748 -2.7105 -4.7241 -0.1233
#   5.6926  1.2537 -2.3577 -6.1281  5.7279
#   1.1825 -3.5621 -0.8389 -3.1787  3.8878
#   4.6018 -2.3370 -3.3486  4.9697  3.9857

# (0 ,1 ,.,.) = 
# 1.00000e-02 *
#   0.9848  0.5553 -3.9970 -3.9053  3.6420
#   1.1237  1.4171 -5.7157 -5.6427 -6.1238
#  -1.0095 -5.6958  2.2651 -1.2723  5.2949
#   0.9728 -6.3195  4.6488  6.0306  3.6197
#  -1.5611 -3.1028  5.9929 -5.2841  1.3246

# (1 ,0 ,.,.) = 
# 1.00000e-02 *
#   2.1799 -1.9568  3.5281  3.7516  0.1602
#  -0.6812  1.4580  3.5765 -5.7470  6.2040
#  -0.6818 -2.5267  5.9199 -4.5157 -1.7764
#   5.0762  0.6835  0.5257 -1.1213  6.0050
#   5.8951  1.7279 -3.7561  6.2476  6.2338

# (1 ,1 ,.,.) = 
# 1.00000e-02 *
#   0.5828  2.0137  0.3343  3.9096 -4.6115
#  -0.5294 -1.8252  4.8991 -5.9929  0.4292
#  -4.2957  0.9775  3.1071  5.2810 -5.9400
#  -2.3509 -1.6881  2.8604  4.5834  3.8610
#   2.4372 -0.2522  2.4152 -0.1572 -3.9385


# conv2  Parameter containing:
# (0 ,0 ,.,.) = 
#   6.1461e-02 -1.3072e-03 -3.9872e-03  1.1724e-02 -1.2705e-02
#   3.9284e-02  1.2479e-02 -2.3270e-02 -4.2417e-02  4.4680e-03
#   5.7289e-02  1.4117e-02 -2.0893e-02 -5.7607e-02  6.1830e-02
#   1.0923e-02 -3.5305e-02 -6.9699e-03 -2.9377e-02  4.2164e-02
#   4.3739e-02 -2.4432e-02 -3.3444e-02  5.0729e-02  4.1766e-02

# (0 ,1 ,.,.) = 
#  -6.7266e-02 -1.3847e-01 -1.1663e-01  3.3803e-02 -6.3961e-02
#  -2.8351e-02 -7.9705e-02 -1.5564e-01 -1.3131e-01 -8.0375e-02
#   2.1123e-02  4.2267e-03  1.2916e-01  9.9200e-02  1.5675e-01
#   9.0292e-02  6.1852e-02  2.0588e-01  1.9696e-01  1.3399e-01
#   4.0742e-02  1.9759e-02  1.2490e-01 -3.5137e-02  5.1859e-02

# (1 ,0 ,.,.) = 
#   4.4474e-03 -4.3016e-02  5.7373e-03  1.8741e-03 -4.0140e-02
#  -2.3083e-02 -7.7865e-03  7.3020e-03 -9.2031e-02  2.1379e-02
#  -2.2010e-02 -4.6554e-02  3.1816e-02 -7.8639e-02 -5.7346e-02
#   3.6648e-02 -1.3375e-02 -2.1049e-02 -4.3617e-02  2.1547e-02
#   4.5914e-02 -1.8532e-03 -6.2790e-02  3.1148e-02  2.4911e-02

# (1 ,1 ,.,.) = 
#   4.9040e-02  7.8627e-02 -8.1242e-02 -5.1593e-02 -1.1105e-01
#   1.1897e-01  2.5484e-02  9.8524e-02  2.0176e-02 -2.4216e-02
#   1.5022e-02 -5.3485e-02  3.4373e-02 -1.9813e-03 -1.5893e-01
#   8.7387e-02 -6.5741e-02 -1.1662e-01 -4.0378e-02 -6.8947e-02
#   1.5064e-01  9.3375e-02 -2.6968e-02 -5.3428e-04 -1.1279e-01





# conv1  Parameter containing:
# (0 ,0 ,.,.) = 
#  -0.0235  0.1406  0.0623  0.1223 -0.1414
#  -0.1052 -0.0559  0.1411 -0.0999 -0.0746
#  -0.1153 -0.0293 -0.0887 -0.0317 -0.0437
#   0.0480 -0.0292  0.1232  0.0110  0.0980
#  -0.0229 -0.0528  0.0524  0.0069 -0.0836

# (0 ,1 ,.,.) = 
#  -0.0160  0.1069 -0.0765 -0.1337  0.0097
#   0.0482  0.1171 -0.0234 -0.0121  0.0166
#  -0.0196 -0.1017  0.1242 -0.0854  0.0787
#   0.0851  0.0611  0.1324  0.0856 -0.0528
#  -0.1152  0.0544  0.0051  0.1065  0.1032
# [torch.cuda.FloatTensor of size 1x2x5x5 (GPU 0)]

# conv2  Parameter containing:
# (0 ,0 ,.,.) = 
#   0.0931 -0.1174  0.0932 -0.1304 -0.0642
#  -0.0934 -0.1247  0.1070  0.0482 -0.1136
#   0.0263 -0.0223  0.0486  0.1295 -0.0250
#   0.0094 -0.0855  0.0543 -0.0595 -0.0522
#  -0.1012  0.0528  0.0801  0.0946 -0.0247

# (0 ,1 ,.,.) = 
#  -0.1362 -0.1318  0.0708  0.0351  0.1383
#   0.0454  0.0702 -0.0570 -0.0621 -0.0152
#   0.0818 -0.0786 -0.1122 -0.1207 -0.0147
#  -0.0087  0.1156 -0.1142 -0.0584  0.1141
#  -0.0600 -0.1076 -0.1046  0.0070 -0.1359
#      ⋮ 

# (1 ,0 ,.,.) = 
#  -0.1178  0.0506  0.1179 -0.0816  0.1161
#  -0.0663 -0.0569 -0.0024  0.0239 -0.1263
#   0.0186  0.0210  0.0322 -0.0999  0.1291
#   0.0253 -0.0676  0.0565 -0.0761 -0.1125
#   0.0095 -0.0243  0.1273  0.0550 -0.0020

# (1 ,1 ,.,.) = 
#  -0.0243  0.0115 -0.1273  0.0751  0.0102
#  -0.1286  0.0463 -0.1018  0.0042  0.0827
#   0.1258 -0.1330  0.0245  0.1084  0.1141
#   0.0115 -0.1025 -0.0147 -0.1020  0.1109
#   0.0869 -0.0346 -0.0289  0.0109 -0.0947
#      ⋮ 

# (2 ,0 ,.,.) = 
#   0.0431  0.1209 -0.0392 -0.0431  0.0201
#   0.0709  0.0390  0.0639 -0.1057  0.1084
#   0.0538  0.0350  0.0418  0.0710 -0.0413
#  -0.0427  0.0745 -0.0651 -0.0406  0.1120
#   0.0715 -0.0203  0.1079  0.1315 -0.1381

# (2 ,1 ,.,.) = 
#   0.0462 -0.0005  0.0344 -0.1205 -0.1090
#   0.0812  0.1271 -0.1233 -0.0142 -0.0409
#   0.0222  0.1250 -0.0260 -0.0340 -0.0744
#   0.0744  0.1141  0.0768  0.0208 -0.0562
#  -0.1406  0.0771  0.0331 -0.0982 -0.0490

# conv1  Parameter containing:
# (0 ,0 ,.,.) = 
#   0.0530  0.2266  0.1587  0.2302 -0.0212
#  -0.0246  0.0342  0.2417  0.0120  0.0496
#  -0.0297  0.0659  0.0168  0.0853  0.0856
#   0.1396  0.0719  0.2348  0.1339  0.2332
#   0.0757  0.0552  0.1709  0.1368  0.0586

# (0 ,1 ,.,.) = 
#   0.0668 -0.0203 -0.2868 -0.1345 -0.0955
#  -0.1637  0.1580  0.0998  0.0153 -0.1114
#  -0.2532  0.2243  0.3532  0.3563  0.1676
#  -0.0619  0.3482  0.8729  0.8697  0.1354
#  -0.1767  0.0452  0.3269  0.5184  0.4830
# [torch.cuda.FloatTensor of size 1x2x5x5 (GPU 0)]

# conv2  Parameter containing:
# (0 ,0 ,.,.) = 
#   0.1218 -0.0835  0.1327 -0.0849 -0.0123
#  -0.0621 -0.0882  0.1490  0.0963 -0.0592
#   0.0606  0.0171  0.0936  0.1805  0.0325
#   0.0470 -0.0427  0.1027 -0.0051  0.0086
#  -0.0598  0.0994  0.1323  0.1529  0.0399

# (0 ,1 ,.,.) = 
#  -0.1356 -0.1324  0.0957  0.0564  0.1485
#   0.0837  0.1572  0.1935 -0.0345  0.0674
#   0.1423  0.1132  0.0070 -0.3575 -0.2641
#  -0.3060 -0.2432 -0.5280 -0.0427  0.1100
#   0.1058 -0.4053 -0.0069  0.1937 -0.1080
#      ⋮ 

# (1 ,0 ,.,.) = 
#  -0.1112  0.0601  0.1303 -0.0666  0.1335
#  -0.0618 -0.0493  0.0080  0.0369 -0.1109
#   0.0210  0.0263  0.0404 -0.0891  0.1424
#   0.0252 -0.0646  0.0623 -0.0676 -0.1016
#   0.0069 -0.0239  0.1305  0.0609  0.0064

# (1 ,1 ,.,.) = 
#   0.0076 -0.0107 -0.2767  0.0569  0.1773
#   0.0824 -0.0589 -0.4136  0.2148  0.0233
#   0.2529 -0.3451 -0.0161  0.3163  0.0036
#  -0.0047 -0.2661 -0.1144  0.0710  0.0281
#  -0.0342  0.1222 -0.0615  0.0459 -0.2497
#      ⋮ 

# (2 ,0 ,.,.) = 
#   0.0149  0.0864 -0.0809 -0.0929 -0.0388
#   0.0380 -0.0003  0.0174 -0.1603  0.0447
#   0.0151 -0.0100 -0.0104  0.0106 -0.1107
#  -0.0880  0.0229 -0.1239 -0.1075  0.0360
#   0.0187 -0.0794  0.0415  0.0570 -0.2216

# (2 ,1 ,.,.) = 
#  -0.0204 -0.0785 -0.0161 -0.0209  0.1583
#   0.1191  0.0977 -0.2040 -0.2625 -0.0872
#   0.0102  0.3383  0.1285 -0.0363 -0.0030
#  -0.1710  0.0647  0.1879  0.2316 -0.0485
#  -0.2280 -0.1323 -0.1643  0.0106 -0.0086
