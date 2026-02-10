import torch
from transformers import pipeline
import re

# Khởi tạo pipeline (giữ nguyên model mạnh nhất)
pipe = pipeline("text-classification", model="papluca/xlm-roberta-base-language-detection", device=-1)

def transformer_robot_labeling(text):
    if not text.strip(): return ""

    # 1. Tách từ và chuẩn bị nhãn
    words = re.findall(r'\w+|[^\w\s]', text)
    confidences = [] # Lưu xác suất để hậu xử lý

    vi_chars = 'àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ'

    for i, word in enumerate(words):
        clean = word.lower()
        
        # Nếu là dấu câu hoặc từ có dấu tiếng Việt -> Chốt luôn là VI
        if not re.match(r'\w+', clean) or any(c in vi_chars for c in clean):
            confidences.append({'lang': 'vi', 'score': 1.0})
            continue

        # Lấy ngữ cảnh rộng hơn (Window size = 3) để Transformer không bị "cận thị"
        context = words[max(0, i-2) : min(len(words), i+3)]
        context_text = " ".join(context)
        
        pred = pipe(context_text)[0]
        lang = 'en' if pred['label'] == 'en' else 'vi'
        confidences.append({'lang': lang, 'score': pred['score']})

    # 2. THUẬT TOÁN GOM CỤM (SMOOTHING) - Quan trọng nhất để trị lỗi "linh tinh"
    refined_labels = [c['lang'] for c in confidences]
    n = len(refined_labels)

    # Chạy 2 lượt để khử nhiễu đơn lẻ (ví dụ: vi-vi-en-vi-vi -> vi-vi-vi-vi-vi)
    for _ in range(2):
        for i in range(1, n - 1):
            if refined_labels[i-1] == refined_labels[i+1]:
                refined_labels[i] = refined_labels[i-1]

    # 3. ĐÓNG GÓI KẾT QUẢ (Fix lỗi I don't know bị chia cắt)
    result = []
    if not words: return ""
    
    curr_lang = refined_labels[0]
    curr_chunk = [words[0]]

    for i in range(1, n):
        # Nếu từ hiện tại là từ cực ngắn (1-2 ký tự) và từ sau là curr_lang -> Gom luôn
        if i < n - 1 and len(words[i]) <= 2 and refined_labels[i+1] == curr_lang:
            refined_labels[i] = curr_lang

        if refined_labels[i] == curr_lang:
            curr_chunk.append(words[i])
        else:
            chunk_text = " ".join(curr_chunk).replace(" ,", ",").replace(" .", ".")
            result.append(f"[{curr_lang}]{chunk_text}[/{curr_lang}]")
            curr_lang = refined_labels[i]
            curr_chunk = [words[i]]
            
    result.append(f"[{curr_lang}]{' '.join(curr_chunk)}[/{curr_lang}]")
    return " ".join(result).replace(" [", "[").replace("] ", "]")

# Test lại phát nữa xem AI còn "ngu" không
print(transformer_robot_labeling("I don't know tại sao nó lại bị lỗi nữa."))
print(transformer_robot_labeling("Cuộc thi này rất khó nhưng I will try my best để thi đấu."))