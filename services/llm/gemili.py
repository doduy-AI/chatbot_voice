from core.config import settings
import google.generativeai as genai
import requests
import json
import re
import time
from services.llm.code_debug_llm import EmilyDarwin

bot = EmilyDarwin()

SYSTEM_PROMPT = (
    "Quy tắc:\n"
    "1. Tuyệt đối không sử dụng chữ số Ả RẬP (0–9). Mọi số phải được viết đầy đủ bằng chữ tiếng Việt.\n"
    "2. Toàn bộ nội dung tiếng Việt phải được bọc hoàn chỉnh trong thẻ [vi]...[/vi]"
    "3. Toàn bộ nội dung tiếng Anh (kể cả tên riêng, thuật ngữ, viết hoa) phải được bọc hoàn chỉnh trong thẻ [en]...[/en]."
    "Ví dụ: [vi]Chào bạn, tôi là[/vi] [en]Robot Darwin[/en]. [vi]Bạn thích[/vi] [en]YouTube[/en] [vi]không?[/vi]\n"
    "4. Không được để bất kỳ ký tự nào (kể cả dấu câu) nằm ngoài các thẻ [vi] hoặc [en]"
    "Ví dụ: [vi]Chào bạn, tôi là[/vi] [en]Robot bytehome[/en]. [vi]Bạn thích[/vi] [en]YouTube[/en] [vi]không?[/vi]"
    "5. Quy tắc phụ: Không dùng Markdown. Trả lời tối đa bốn câu. Không sử dụng viết tắt không chính thức (ví dụ: ko, kg, vs)."
),

class ASK_LLM:
    def __init__(self):
        genai.configure(api_key=settings.API_GEMINI)
        self.sessions = {}  
        self.max_history_len = 4
        self.model = genai.GenerativeModel(
            model_name="gemini-2.5-flash-lite-preview-09-2025", 
            system_instruction=SYSTEM_PROMPT,
            generation_config={
                # "temperature": 0.3,
            }
        )
    def GEMINI(self, client_id, prompt):
        # 1. Khởi tạo hoặc lấy lịch sử hiện có
        # if client_id not in self.sessions:
        #     self.sessions[client_id] = []
        # history = self.sessions[client_id]
        try:
            text = bot.get_full_response(prompt)
            print("[text llm ]",text)
            # chat = self.model.start_chat(history=history)
            # response = chat.send_message(prompt)
            # text = response.text.strip().replace("\n", " ")
            # history.append({"role": "user", "parts": [prompt]})
            # history.append({"role": "model", "parts": [text]})
            # if len(history) > self.max_history_len:
            #     self.sessions[client_id] = history[-self.max_history_len:]
            # else:
            #     self.sessions[client_id] = history

            return text
        except Exception as e:
            print(f"[Gemini SDK Error] {e}")
            if "context_leghth" in str(e).lower():
                self.sessions[client_id] = []
            return "[vi]Kết nối đang gặp vấn đề ạ[/vi]"
    def OLLAMA(self, client_id, prompt):
        # 1. Khởi tạo session nếu chưa có
        if client_id not in self.sessions:
            self.sessions[client_id] = []
        context = ""
        for msg in self.sessions[client_id]:
            role = "Người dùng" if msg["role"] == "user" else "Trợ lý"
            context += f"{role}: {msg['content']}\n"
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
                self.sessions[client_id].append({"role": "user", "content": prompt})
                self.sessions[client_id].append({"role": "assistant", "content": ai_response})
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