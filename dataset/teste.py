import os

path = r"\\srvbmflserver\BARRAMANSA\PUBLICO_BM\Rodrigo\Videos_col"


for item in os.listdir(path):
    print(item[:-4])