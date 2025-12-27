# 이 코드를 Google Colab에 복사해서 실행하세요.
# 런타임 유형: T4 GPU (필수)

import os
import time
import subprocess

# ---------------------------------------------------------
# 1. prepare_dataset.py 파일 자동 생성 (업로드 불필요!)
# ---------------------------------------------------------
prepare_dataset_code = r'''
import os
import json
import toml
import PyPDF2
import google.generativeai as genai
from tqdm import tqdm
import time
import argparse
import requests

def load_api_key():
    """Load Gemini API key from .streamlit/secrets.toml"""
    try:
        if os.path.exists(".streamlit/secrets.toml"):
            secrets = toml.load(".streamlit/secrets.toml")
            api_key = secrets.get("GOOGLE_API_KEY") or secrets.get("GEMINI_API_KEY")
            if not api_key and "connections" in secrets and "gemini" in secrets["connections"]:
                api_key = secrets["connections"]["gemini"].get("api_key")
            return api_key
    except:
        pass
    return os.getenv("GOOGLE_API_KEY")

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF file"""
    print(f"Extracting text from {pdf_path}...")
    text_chunks = []
    try:
        reader = PyPDF2.PdfReader(pdf_path)
        current_chunk = ""
        for page in tqdm(reader.pages, desc="Reading PDF"):
            text = page.extract_text()
            if not text: continue
            current_chunk += text + "\n"
            if len(current_chunk) > 1500:
                text_chunks.append(current_chunk)
                current_chunk = ""
        if current_chunk:
            text_chunks.append(current_chunk)
        return text_chunks
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return []

def generate_qa_pairs_ollama(chunk, model_name):
    """Generate Q&A pairs using local Ollama"""
    prompt = f"""
    당신은 대한민국 자치법규(Local Regulations) 전문가입니다.
    '자치법규 입안 길라잡이'의 다음 텍스트를 분석하세요.
    자치법규 입안에 대한 질문에 답변할 수 있는 모델을 파인튜닝하기 위해, 5-8개의 고품질 질문-답변(Q&A) 쌍을 생성해주세요.
    
    출력 형식은 'instruction', 'input', 'output' 키를 가진 JSON 객체의 리스트여야 합니다.
    **반드시 JSON 형식만 출력하세요. 다른 설명은 포함하지 마세요.**
    
    - 'instruction': 질문 또는 지시 사항
    - 'input': 필요한 경우 문맥 정보 (없으면 빈 문자열)
    - 'output': 상세한 답변 (반드시 한국어)
    
    텍스트 내용:
    {chunk[:5000]} 
    
    Output JSON:
    """
    
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model_name,
                "prompt": prompt,
                "stream": False,
                "format": "json"
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            text_response = result.get("response", "")
            if "```json" in text_response:
                text_response = text_response.split("```json")[1].split("```")[0]
            elif "```" in text_response:
                text_response = text_response.split("```")[1].split("```")[0]
            return json.loads(text_response)
        return []
    except Exception as e:
        print(f"Error generating Q&A with Ollama: {e}")
        return []

def main():
    pdf_path = "2022년_자치법규입안길라잡이.pdf"
    output_file = "training_data.jsonl"
    
    if not os.path.exists(pdf_path):
        print(f"File not found: {pdf_path}")
        return

    chunks = extract_text_from_pdf(pdf_path)
    print(f"Extracted {len(chunks)} chunks from PDF.")
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--engine", type=str, default="gemini")
    parser.add_argument("--ollama-model", type=str, default="llama3")
    args = parser.parse_args()

    all_data = []
    with open(output_file, 'w', encoding='utf-8') as f:
        for i, chunk in enumerate(tqdm(chunks, desc="Generating Data")):
            qa_pairs = []
            if args.dry_run:
                qa_pairs = [{"instruction": "Test", "input": "", "output": "Test"}]
            elif args.engine == "ollama":
                qa_pairs = generate_qa_pairs_ollama(chunk, args.ollama_model)
            
            for pair in qa_pairs:
                f.write(json.dumps(pair, ensure_ascii=False) + "\n")
                all_data.append(pair)
            
    print(f"Successfully generated {len(all_data)} training examples.")
    print(f"Saved to {output_file}")

if __name__ == "__main__":
    main()
'''

with open("prepare_dataset.py", "w", encoding="utf-8") as f:
    f.write(prepare_dataset_code)
print("✅ prepare_dataset.py 파일 생성 완료!")

# ---------------------------------------------------------
# 2. Ollama 설치 및 실행
# ---------------------------------------------------------
print("⏳ Ollama 설치 중...")
os.system("curl -fsSL https://ollama.com/install.sh | sh")

print("⏳ Ollama 서버 시작 중...")
subprocess.Popen(["ollama", "serve"])
time.sleep(10) 

# 3. 모델 다운로드 (Qwen 2.5)
print("⏳ Qwen 2.5 모델 다운로드 중... (약 3-5분 소요)")
os.system("ollama pull qwen2.5")

# ---------------------------------------------------------
# 4. PDF 파일 자동 찾기 및 이동
# ---------------------------------------------------------
import shutil

pdf_filename = "2022년_자치법규입안길라잡이.pdf"
found_path = None

# 현재 위치에 없으면 하위 폴더 검색
if not os.path.exists(pdf_filename):
    print(f"🔍 {pdf_filename} 파일을 찾는 중...")
    for root, dirs, files in os.walk("."):
        if pdf_filename in files:
            found_path = os.path.join(root, pdf_filename)
            print(f"✅ 파일을 찾았습니다: {found_path}")
            # 현재 위치로 이동
            try:
                shutil.move(found_path, pdf_filename)
                print(f"📦 파일을 현재 위치로 이동했습니다.")
            except Exception as e:
                print(f"⚠️ 파일 이동 실패 (복사 시도): {e}")
                try:
                    shutil.copy(found_path, pdf_filename)
                except:
                    pass
            break
else:
    print(f"✅ {pdf_filename} 파일이 현재 위치에 있습니다.")

# 5. 데이터 생성 실행
if not os.path.exists(pdf_filename):
    print("❌ [오류] PDF 파일이 아직 없습니다!")
    print("왼쪽 폴더 아이콘 클릭 -> '2022년_자치법규입안길라잡이.pdf' 파일을 드래그해서 넣어주세요.")
    # 현재 디렉토리 파일 목록 출력 (디버깅용)
    print("현재 폴더 파일 목록:", os.listdir("."))
else:
    print("🚀 데이터 생성 시작! (약 10-20분 소요)")
    os.system("pip install PyPDF2 tqdm google-generativeai")
    os.system("python prepare_dataset.py --engine ollama --ollama-model qwen2.5")
    print("🎉 생성 완료! 'training_data.jsonl' 파일을 다운로드하세요.")
