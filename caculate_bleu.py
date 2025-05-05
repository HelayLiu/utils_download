from nltk.translate.bleu_score import sentence_bleu
import nltk
from tqdm import tqdm
import os
from bert_score import score
from rouge import Rouge


def calculate_2gram_bleu(sentence1, sentence2):
    # 分词（假设输入为英文，按空格分割）
    reference = [sentence1.split()]
    candidate = sentence2.split()
    
    # 计算2-gram BLEU（权重设为[0, 1]表示仅用2-gram）
    score = sentence_bleu(reference, candidate, weights=(0, 1))
    return score

# # 示例输入
# sentence1 = "the cat is sitting on the mat"  # 参考句
# sentence2 = "the cat is on the mat"          # 候选句

# # 计算BLEU
# bleu_score = calculate_2gram_bleu(sentence1, sentence2)
# print(f"2-gram BLEU Score: {bleu_score:.4f}")

if __name__ == "__main__":
    temp_cou=''
    root_path = f"/home/liuhan/utils_download/similar_code{temp_cou}"
    os.makedirs(root_path, exist_ok=True)
    cou=0
    average_g = 0
    average_wog = 0
    all_ref=[]
    all_g=[]
    all_wg=[]
    for file in tqdm(os.listdir(root_path)):
        if file.endswith('_gpt4omini_withgraph.txt'):
            reference_file = file.replace("_gpt4omini_withgraph.txt","")
            reference_path = os.path.join(root_path,reference_file)
            with open(reference_path,'r') as f:
                reference_content=f.read()

            anthor_file = file.split('_gpt4omini_withgraph.txt')[0] + '_gpt4omini_withoutgraph.txt'
            general_file = file.split('_gpt4omini_withgraph.txt')[0] + '_gpt_o3_mini.txt'
            file1_path = os.path.join(root_path, file)
            file2_path = os.path.join(root_path, anthor_file)
            file3_path = os.path.join(root_path, general_file)
            with open(file1_path, 'r') as f:
                file1_content = f.read()
            with open(file2_path, 'r') as f:
                file2_content = f.read()
            with open(file3_path, 'r') as f:
                file3_content = f.read()
            # 计算BLEU分数
            # bleu_score_g = calculate_2gram_bleu(general_file, file1_content)
            # average_bleu_g+= bleu_score_g
            # bleu_score_wog = calculate_2gram_bleu(general_file, file2_content)
            # average_bleu_wog+= bleu_score_wog
            # all_ref.append(file3_content)
            # all_g.append(file1_content)
            # all_wg.append(file2_content)
            rouge = Rouge()
            scores = rouge.get_scores(file1_content, file3_content)[0]['rouge-l']
            average_g+=scores['f']
            scores = rouge.get_scores(file2_content, file3_content)[0]['rouge-l']
            average_wog+=scores['f']
    #         P, R, F1 = score(file1_content, general_file, lang="en")
    #         average_g+=F1
    #         P, R, F1 = score(file2_content, general_file, lang="en")
    #         average_wog+=F1
    print(average_wog/10)
    print(average_g/10)
    # P, R, F1 = score(all_g, all_ref, lang="en")
    # print(F1.mean())
    # P, R, F1 = score(all_wg, all_ref, lang="en")
    # print(F1.mean())
