import os
import random
import shutil
path='/home/liuhan/smartbugs-wild/contracts'
save_path='/home/liuhan/smartbugs-wild/random_contracts'
os.makedirs(save_path, exist_ok=True)
files=os.listdir(path)
random.shuffle(files)
for i, file in enumerate(files):
    if i >= 5000:
        break
    src=os.path.join(path, file)
    dst=os.path.join(save_path, file)
    shutil.copy(src, dst)