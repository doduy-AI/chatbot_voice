from core.config import settings
import google.generativeai as genai
import requests
import json
import re
import time



SYSTEM_PROMPT = """Emily (TTS Bot). NHIỆM VỤ TỐI THƯỢNG:
1. CẤM VIẾT SỐ: Phải viết 100% bằng chữ (Ví dụ: 5.000 -> năm nghìn, 180 -> một trăm tám mươi).
2. CẤM KÝ HIỆU & TIẾNG ANH: USD -> đô la, ounce -> ao nsơ, % -> phần trăm.
3. PHIÊN ÂM: YouTube -> Yu túp, Bitcoin -> Bít coi.
4. trả lời thêm nhấn nhá nhé đừng cụt ngủn
"""
class ASK_LLM:
    def __init__(self):
        genai.configure(api_key=settings.API_GEMINI)
        self.sessions = {}  
        self.model = genai.GenerativeModel(
            model_name="gemini-2.5-flash-lite",
            generation_config={
                "max_output_tokens":320,
                "temperature":0.3,
            }
            )
    def GEMINI(self, client_id, prompt):
        # Nếu client chưa có session → tạo mới
        if client_id not in self.sessions:
            self.sessions[client_id] = self.model.start_chat(history=[ {
                        "role": "user",
                        "parts": SYSTEM_PROMPT
                    }])
        chat = self.sessions[client_id]
        try:
            response = chat.send_message(prompt)
            text = response.text.strip()
            return text
        except Exception as e:
            print(f"[Gemini SDK Error] {e}")
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
                f"{context}" 
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