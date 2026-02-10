import numpy as np
import re
import os
import pathlib

# ==========================================
# 1. Vá lỗi tương thích NumPy 2.x
# ==========================================
original_array = np.array
def patched_array(obj, *args, **kwargs):
    if 'copy' in kwargs:
        kwargs.pop('copy')
    return original_array(obj, *args, **kwargs)
np.array = patched_array
# ==========================================

import fasttext

# 2. Định nghĩa đường dẫn model thông minh
BASE_DIR = pathlib.Path(__file__).parent.resolve()
MODEL_PATH = str(BASE_DIR.parent / "dataset" / "lid.176.bin")

# Thử fallback: nếu không có file ở trên, tìm cùng thư mục
if not os.path.exists(MODEL_PATH):
    MODEL_PATH = str(BASE_DIR / "dataset" / "lid.176.bin")

# Cho phép override bằng biến môi trường (dùng khi deploy server)
MODEL_PATH = os.getenv("FASTTEXT_MODEL", MODEL_PATH)

if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f" Không tìm thấy model FastText tại: {MODEL_PATH}")

ft_model = fasttext.load_model(MODEL_PATH)


# ==========================================
# 3. Danh sách từ tiếng Anh phổ biến (mở rộng)
# ==========================================
COMMON_EN_WORDS = set("""
i me my myself we our ours ourselves you your yours yourself yourselves 
he him his himself she her hers herself it its itself they them their theirs themselves 
is am are was were be being been have has had having do does did doing 
a an the and but if or because as until while of at by for with about against between into 
through during before after above below to from up down in out on off over under again 
further then once here there when where why how all any both each few more most other some 
such no nor not only own same so than too very can will just don should now
""".split())


# ==========================================
# 4. Hàm chính
# ==========================================
def robot_labeling(text: str, debug: bool = False) -> str:
    # 1. Tách ký tự đặc biệt để tránh nhiễu model
    text = re.sub(r'([\"\'\(\)\*\:\,\.\?\!])', r' \1 ', text)
    words = text.split()
    if not words:
        return ""

    vi_chars = 'àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ'

    # -----------------------------
    # BATCH PREDICT để tăng tốc
    # -----------------------------
    def batch_predict(words, batch_size=16):
        results = []
        for i in range(0, len(words), batch_size):
            batch = words[i:i+batch_size]
            labels, probs = ft_model.predict(batch, k=1)
            for lbl, pr in zip(labels, probs):
                lang = lbl[0].replace('__label__', '')
                prob = pr[0]
                results.append((lang, prob))
        return results

    predictions = batch_predict(words)

    raw_labels = []
    for w, (lang, prob) in zip(words, predictions):
        clean = w.strip("\"'().,:;*").lower()
        if not clean:
            raw_labels.append('vi')
            continue

        has_vi = any(c in vi_chars for c in clean)
        if has_vi:
            raw_labels.append('vi')
        elif clean in COMMON_EN_WORDS:
            raw_labels.append('en')
        else:
            raw_labels.append('en' if lang == 'en' and prob > 0.4 else 'vi')

    # -----------------------------
    # 2. Logic “keo dính” thông minh (đã cập nhật)
    # -----------------------------
    refined_labels = list(raw_labels)
    for i in range(1, len(refined_labels) - 1):
        prev, curr, nxt = refined_labels[i-1], refined_labels[i], refined_labels[i+1]
        word_lower = words[i].lower()

        # 🔹 Quy tắc 1: nếu là 'vi' không dấu, kẹp giữa 2 'en' → thành 'en'
        if curr == 'vi' and not any(c in vi_chars for c in word_lower):
            if (prev == nxt == 'en') or (prev == 'en' and predictions[i-1][1] > 0.7):
                refined_labels[i] = 'en'

        # 🔹 Quy tắc 2: nếu là 'en' kẹp giữa 2 'vi' → thành 'vi'
        elif curr == 'en' and prev == nxt == 'vi':
            refined_labels[i] = 'vi'

    # -----------------------------
    # 3. Gom cụm & xử lý dấu câu
    # -----------------------------
    def clean_chunk(chunk_list):
        chunk_str = " ".join(chunk_list)
        return re.sub(r'\s+([\"\'\(\)\*\:\,\.\?\!])', r'\1', chunk_str)

    result = []
    curr_lang = refined_labels[0]
    curr_chunk = [words[0]]

    for i in range(1, len(refined_labels)):
        if refined_labels[i] == curr_lang:
            curr_chunk.append(words[i])
        else:
            processed_text = clean_chunk(curr_chunk)
            result.append(f"[{curr_lang}]{processed_text}[/{curr_lang}]")
            curr_lang = refined_labels[i]
            curr_chunk = [words[i]]

    processed_text = clean_chunk(curr_chunk)
    result.append(f"[{curr_lang}]{processed_text}[/{curr_lang}]")

    return " ".join(result)



