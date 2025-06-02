import numpy as np
from sklearn.preprocessing import normalize
from sklearn.neighbors import NearestNeighbors
from sklearn.cluster import KMeans
from pymongo import MongoClient
from tqdm import tqdm
import json
client=MongoClient("mongodb://shuaicpu5.cse.ust.hk:27017/")
collection_source=client['contracts']['top_contracts']
docs=collection_source.find({'used':True},{'code_hash':1,'embedding':1,'code':1,'success':1,'contract_name':1,'implementation':1,'version':1,'optimization':1,'viaIR':1,'stg':1})
embeddings=[]
all_hashs=set()
texts=[]
comp_args=[]
for doc in tqdm(docs):
    if 'success' not in doc or doc['success'] == False:
        continue
    if 'implementation' in doc and doc['implementation']!='':
        continue
    code=doc['code']
    code_hash=doc['code_hash']
    embedding=doc['embedding']
    version=doc['version'].split('+')[0].replace('v','')
    opt=True if doc['optimization']=='1' else False
    via_ir=doc.get('viaIR', False)
    args={
        'contract_name': doc['contract_name'],
        'version': version,
        'opt': opt,
        'via_ir': via_ir,
        'stg': doc.get('stg', ''),
    }
    if code_hash in all_hashs:
        continue
    comp_args.append(args)
    all_hashs.add(code_hash)
    texts.append(code)
    embeddings.append(embedding)
# # =============================================
# # 1. 数据预处理
# # =============================================
# # 对嵌入向量进行L2归一化（重要！）
# embeddings_normalized = normalize(embeddings, axis=1, norm='l2')

# # =============================================
# # 2. 计算k近邻距离
# # =============================================
# # 参数设置
# N_NEIGHBORS = 10  # 观察最近邻的数量（建议值5-20）

# # 创建模型（注意n_neighbors设为N_NEIGHBORS+1以包含自身）
# nn = NearestNeighbors(
#     n_neighbors=N_NEIGHBORS + 1,
#     metric='cosine',  # 使用余弦距离
#     algorithm='brute'  # 适用于高维数据
# )
# nn.fit(embeddings_normalized)

# # 获取每个样本的邻居距离（包含自身）
# distances, indices = nn.kneighbors(embeddings_normalized)

# # =============================================
# # 3. 计算特征指标
# # =============================================
# # 排除自身（第一个邻居），计算平均距离
# avg_distances = distances[:, 1:].mean(axis=1)  # 形状 (8000,)

# # =============================================
# # 4. 选择最不一样的样本
# # =============================================
# # 获取距离最大的前100个索引
# selected_indices = np.argsort(avg_distances)[-100:][::-1]

# # 提取对应文本
# selected_texts = [texts[i] for i in selected_indices]

# all_texts = selected_texts

# 归一化
embeddings_norm = normalize(embeddings, axis=1, norm='l2')

# 聚类
n_clusters = 350
kmeans =  KMeans(
            n_clusters=n_clusters,
            init='k-means++',
            n_init=10,
            random_state=42
        )
kmeans.fit(embeddings_norm)
labels = kmeans.labels_

# 统计簇大小
cluster_counts = np.bincount(labels)
valid_clusters = np.where(cluster_counts >= 5)[0]

# 按大小排序，得到索引从大到小
sorted_ids = np.argsort(-cluster_counts[valid_clusters])[:150]

selected_clusters = valid_clusters[sorted_ids]
        
all_texts=[]
all_name=[]
for cid in selected_clusters:
    mask = (labels == cid)
    cluster_indices = np.where(mask)[0]
    
    # 计算到中心的距离
    cluster_samples = embeddings_norm[mask]
    center = kmeans.cluster_centers_[cid]
    distances = np.linalg.norm(cluster_samples - center, axis=1)
    sorted_indices = np.argsort(distances)
    for idx in sorted_indices:
        original_idx = cluster_indices[idx]
        lines= texts[original_idx].split('\n')
        if len(lines)>200 and comp_args[original_idx] not in all_name:
            all_texts.append(texts[original_idx])
            all_name.append(comp_args[original_idx])
            break
        else:
            continue
print(len(all_texts))
    # 选择最近样本
    # closest_idx = cluster_indices[np.argmin(distances)]
    # all_texts.append(code[closest_idx])
# =============================================
# 5. 结果验证
# =============================================
# print(f"最大平均距离样本索引: {selected_indices[:100]}")  # 打印前5个最异常样本索引
# print("示例最不一样的文本:")
save_path = '/home/liuhan/utils_download/most_unrelated'
cou=0
for i in range(100):
    num_tokens = len(all_texts[i].split('\n'))
    if (num_tokens) < 200:
        continue
    with open(f"{save_path}/most_unrelated_{i}.sol", 'w') as f:
        f.write(all_texts[i])
        # cou+=1
    with open(f"{save_path}/most_unrelated_{i}.json", 'w') as f:
        json.dump(all_name[i], f, indent=4)
    # cou+=1