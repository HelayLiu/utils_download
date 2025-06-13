from openai import OpenAI
import httpx
import time
from config import OPENAI_API_KEY
proxy = "http://127.0.0.1:20171"
client= OpenAI(api_key=OPENAI_API_KEY,http_client=httpx.Client(proxy=proxy))
# 步骤1：上传训练数据文件
def upload_file(file_path):
    with open(file_path, "rb") as file:
        response = client.files.create(
            file=file,
            purpose='fine-tune'
        )
    return response["id"]

# 假设我们的训练数据文件名为'training_data.jsonl'
file_id = upload_file("training_data.jsonl")
print(f"上传的文件ID: {file_id}")


# 步骤2：创建微调任务
def create_fine_tune_job(file_id, model="gpt-4o-mini"):
    response = client.fine_tuning.jobs(
        training_file=file_id,
        model=model,
        # 可以添加其他参数，如n_epochs, batch_size, learning_rate_multiplier等
        # 具体参数参考：https://platform.openai.com/docs/api-reference/fine-tunes/create
    )
    return response["id"]

fine_tune_job_id = create_fine_tune_job(file_id, model="gpt-4o-mini")
print(f"微调任务ID: {fine_tune_job_id}")

# 步骤3：监控微调任务状态
def monitor_fine_tune_job(job_id):
    while True:
        job_status = client.fine_tuning.jobs.retrieve(job_id)
        if job_status['status'] == 'succeeded':
            print("微调任务完成！")
            print(f"微调后的模型ID: {job_status['fine_tuned_model']}")
            break
        elif job_status['status'] in ['failed', 'cancelled']:
            print(f"微调任务失败或取消: {job_status}")
            break
        else:
            print(f"任务状态: {job_status['status']}, 等待10秒...")
            time.sleep(10)

monitor_fine_tune_job(fine_tune_job_id)

# 使用微调后的模型进行推理
def generate_text(prompt, model_id):
    response = client.chat.completions.create(
        model=model_id,
        prompt=prompt,
        max_tokens=100,
        temperature=0.7
    )
    return response.choices[0].text.strip()

