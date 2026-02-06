import re

def split_and_label(text):
    if not text:
        return []

    # 1. Bóc tách nội dung từ tag [vi]...[/vi] và [en]...[/en]
    pattern = re.compile(r'\[(\w+)\](.*?)\[\/\1\]', re.IGNORECASE | re.DOTALL)
    matches = pattern.findall(text)
    
    # Chuyển đổi thành cấu trúc nhãn thô
    raw_labels = [{"lang": m[0].upper(), "text": m[1].strip()} for m in matches]

    # 2. Hợp nhất các đoạn cùng ngôn ngữ đứng cạnh nhau
    return _merge_segments(raw_labels)

def _merge_segments(labels):
    if not labels: 
        return []
    
    segments = []
    current = labels[0].copy()
    
    for i in range(1, len(labels)):
        if labels[i]["lang"] == current["lang"]:
            # Nối text nếu cùng nhãn lang
            current["text"] += " " + labels[i]["text"]
        else:
            segments.append(current)
            current = labels[i].copy()
            
    segments.append(current)
    return segments