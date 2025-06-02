# pip3 install transformers
# python3 deepseek_tokenizer.py
import transformers
def token_number(text):
	chat_tokenizer_dir = "/home/liuhan/utils_download/deepseek_v3_tokenizer"

	tokenizer = transformers.AutoTokenizer.from_pretrained( 
			chat_tokenizer_dir, trust_remote_code=True
			)

	result = tokenizer.encode(text)
	return len(result)
