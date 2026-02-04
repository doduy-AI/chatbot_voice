import re

def split_and_label(text):
    if not text:
        return []

    # Quy tắc 1: Có dấu -> VI
    vi_pattern = re.compile(r'[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệđìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ]', re.I)
    # Quy tắc 2: Có ký tự ngoại lệ -> EN
    en_pattern = re.compile(r'[fzwj]', re.I)

    words = text.split()
    raw_tags = []

    # Bước 1: Gán nhãn thô
    for w in words:
        clean = w.lower().strip(".,!?")
        if vi_pattern.search(clean):
            tag = "VI"
        elif en_pattern.search(clean):
            tag = "EN"
        else:
            tag = "NOSIGN"
        raw_tags.append({"text": w, "tag": tag})

    # Bước 2: Áp dụng luật Sandwich (Kẹp giữa đầu và cuối)
    final_labels = []
    i = 0
    while i < len(raw_tags):
        if raw_tags[i]["tag"] == "NOSIGN":
            start = i
            while i < len(raw_tags) and raw_tags[i]["tag"] == "NOSIGN":
                i += 1
            count = i - start
            
            # --- LUẬT SANDWICH MỚI ---
            # Kiểm tra xem có từ VI ở CẢ TRƯỚC và SAU không
            has_leader = (start > 0 and raw_tags[start-1]["tag"] == "VI")
            has_follower = (i < len(raw_tags) and raw_tags[i]["tag"] == "VI")
            is_sandwiched = has_leader and has_follower

            # Áp dụng luật của bạn:
            # 1. Nếu cụm >= 3 từ -> EN
            if count >= 4:
                lang = "EN"
            # 2. Nếu là 1-2 từ và phải được KẸP GIỮA (Sandwich) -> VI
            elif is_sandwiched:
                lang = "VI"
            # 3. Nếu đứng đầu, đứng cuối, hoặc đơn lẻ không được kẹp -> EN
            else:
                lang = "EN"
            
            for j in range(start, i):
                final_labels.append({"text": raw_tags[j]["text"], "lang": lang})
        else:
            final_labels.append({"text": raw_tags[i]["text"], "lang": raw_tags[i]["tag"]})
            i += 1

    return _merge_segments(final_labels)

def _merge_segments(labels):
    if not labels: return []
    segments = []
    current = labels[0]
    for i in range(1, len(labels)):
        if labels[i]["lang"] == current["lang"]:
            current["text"] += " " + labels[i]["text"]
        else:
            segments.append({"lang": current["lang"], "text": current["text"]})
            current = labels[i]
    segments.append({"lang": current["lang"], "text": current["text"]})
    return segments