import os
import requests
from tqdm import tqdm

def download_file(url, filename):
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    
    with open(filename, 'wb') as file, tqdm(
        desc=filename,
        total=total_size,
        unit='iB',
        unit_scale=True,
        unit_divisor=1024,
    ) as progress_bar:
        for data in response.iter_content(chunk_size=1024):
            size = file.write(data)
            progress_bar.update(size)

def main():
    # 모델 URL (Hugging Face에서 다운로드)
    model_url = "https://huggingface.co/TheBloke/OpenHermes-2.5-Mistral-7B-GGUF/resolve/main/openhermes-2.5-mistral-7b.Q4_K_M.gguf"
    model_filename = "openhermes-2.5-mistral-7b.Q4_K_M.gguf"
    
    print(f"모델 파일 다운로드를 시작합니다: {model_filename}")
    download_file(model_url, model_filename)
    print("다운로드가 완료되었습니다!")

if __name__ == "__main__":
    main() 