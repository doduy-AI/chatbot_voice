from core.config import settings
import requests
import json
import re

class ASK_LLM:
    def __init__(self):
        self.key = settings.API_GEMINI 
        # API Endpoint cho Gemini 2.5 Flash
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.key}"
        self.url_llm = settings.URL_LLM
        self.sessions = {}
    # def clean_text(self, text):
    #     """Xóa các ký tự markdown để Vieneu đọc mượt hơn"""
    #     if not text: return ""
    #     # Xóa dấu sao, dấu thăng, v.v.
    #     return re.sub(r'[\*\#\_]', '', text).strip()

    def GEMINI(self, prompt):
        headers = {"Content-Type": "application/json"}
        
        payload = {
            "contents": [
                {
                    "parts": [{"text": f"Trả lời bằng tiếng việt ngắn ngọn, không dùng tiếng trung quốc , không dùng emoji, không dùng markdown: {prompt}"}]
                }
            ],
            "generationConfig": {
                "maxOutputTokens": 900,
                "temperature": 0.7, # Để 0.3 cho giọng văn tự nhiên hơn một chút so với 0.0
                "topP": 0.9
            }
        }

        try:
            res = requests.post(self.url, headers=headers, json=payload, timeout=10)
            res.raise_for_status()
            data = res.json()

            # Cách lấy text an toàn hơn để tránh lỗi NoneType
            candidates = data.get("candidates", [])
            if not candidates:
                return "Tôi chưa nghĩ ra câu trả lời, bạn thử lại nhé."

            parts = candidates[0].get("content", {}).get("parts", [])
            raw_text = parts[0].get("text", "") if parts else ""

            return raw_text
            
        except Exception as e:
            print(f"--- [LLM Error] {e} ---")
            return "Kết nối với trí tuệ nhân tạo đang gặp chút vấn đề."
        

    def OLLAMA(self, client_id, prompt):
        # 1. Khởi tạo session nếu chưa có
        if client_id not in self.sessions:
            self.sessions[client_id] = []

        # 2. Xây dựng chuỗi ngữ cảnh từ lịch sử đã lưu
        # Chúng ta sẽ biến các câu đối thoại cũ thành một đoạn văn bản
        context = ""
        for msg in self.sessions[client_id]:
            role = "Người dùng" if msg["role"] == "user" else "Trợ lý"
            context += f"{role}: {msg['content']}\n"

        # 3. Cập nhật payload: Chèn context vào trước câu hỏi hiện tại
        url = self.url_llm
        headers = {"Content-Type": "application/json"}
        payload = {
            "prompt": (
                "Hãy luôn luôn trả lời bằng tiếng Việt tự nhiên,trả lời ngắn ngọn 1 , 2 câu, không viết tắt, không emoji, không markdown.\n"
                "Dưới đây là lịch sử cuộc trò chuyện để bạn nắm ngữ cảnh:\n"
                f"{context}" # Chèn toàn bộ lịch sử vào đây
                f"Người dùng: {prompt}\n"
                "Trợ lý:"
            ),
            "options": {
                "num_predict": 50,   
                "temperature": 0.3,   
                "top_k": 20,
                "stop": ["Người dùng:", "\n"] 
            }
        }

        try:
            with requests.post(url, headers=headers, json=payload, stream=True, timeout=60) as r:
                r.raise_for_status()
                full_text = ""
                for line in r.iter_lines(decode_unicode=True):
                    if line:
                        full_text += line

                ai_response = full_text.strip() if full_text else "Không có phản hồi từ mô hình."

                # 4. LƯU LỊCH SỬ (QUAN TRỌNG)
                # Lưu câu hỏi của user
                self.sessions[client_id].append({"role": "user", "content": prompt})
                # Lưu câu trả lời của AI
                self.sessions[client_id].append({"role": "assistant", "content": ai_response})

                # 5. Cắt tỉa lịch sử để prompt không bị quá dài (Giữ 6 tin nhắn gần nhất = 3 cặp đối thoại)
                if len(self.sessions[client_id]) > 6:
                    self.sessions[client_id] = self.sessions[client_id][-6:]

                return ai_response

        except Exception as e:
            print(f"--- [OLLAMA Error] {e} ---")
            return "Kết nối với mô hình Ollama đang gặp vấn đề."
        


    
    def clear_session(self, client_id):
        """Xóa lịch sử hội thoại khi người dùng ngắt kết nối"""
        if client_id in self.sessions:
            del self.sessions[client_id]
            print(f"--- [LLM] Đã xóa bộ nhớ đệm của {client_id} ---")