import re
import langid
def split_and_label(text):
    # Regex nhận diện dấu tiếng Việt và ký tự ngoại lệ
    vi_sign_pattern = re.compile(r'[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệđìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ]', re.I)
    en_char_pattern = re.compile(r'[fzwj]', re.I)

    words = text.split()
    if not words: return []

    # Bước 1: Phân loại thô từng từ
    raw_tags = []
    for w in words:
        clean = w.lower().strip(".,!?")
        if vi_sign_pattern.search(clean):
            tag = "VI"
        elif en_char_pattern.search(clean):
            tag = "EN"
        else:
            tag = "NO_SIGN" # Chờ xét luật kẹp
        raw_tags.append({"text": w, "tag": tag})

    # Bước 2: Áp dụng Luật Kẹp (Sandwich Logic)
    # Chúng ta duyệt để xác định các ông "NO_SIGN"
    final_labels = []
    i = 0
    while i < len(raw_tags):
        if raw_tags[i]["tag"] == "NO_SIGN":
            # Đếm xem có bao nhiêu từ NO_SIGN liên tiếp
            start = i
            while i < len(raw_tags) and raw_tags[i]["tag"] == "NO_SIGN":
                i += 1
            count = i - start
            
            # Kiểm tra bối cảnh xung quanh cụm NO_SIGN này
            prev_is_vi = (start > 0 and raw_tags[start-1]["tag"] == "VI")
            next_is_vi = (i < len(raw_tags) and raw_tags[i]["tag"] == "VI")
            
            # Áp dụng luật của bạn:
            # Nếu 1 từ đơn lẻ và bị kẹp giữa (hoặc đứng cạnh) VI -> VI
            # Ngược lại, nếu >= 2 từ -> EN
            if count == 1 and (prev_is_vi or next_is_vi):
                current_lang = "VI"
            else:
                current_lang = "EN"
            
            for j in range(start, i):
                final_labels.append({"text": raw_tags[j]["text"], "lang": current_lang})
        else:
            final_labels.append({"text": raw_tags[i]["text"], "lang": raw_tags[i]["tag"]})
            i += 1

    # Bước 3: Gom nhóm các từ cùng nhãn đứng cạnh nhau để Streaming
    if not final_labels: return []
    segments = []
    curr = final_labels[0]
    for i in range(1, len(final_labels)):
        if final_labels[i]["lang"] == curr["lang"]:
            curr["text"] += " " + final_labels[i]["text"]
        else:
            segments.append(curr)
            curr = final_labels[i]
    segments.append(curr)
    
    return segments