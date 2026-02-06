from core.config import settings
import google.generativeai as genai
import requests
import json
import re
import time

SYSTEM_PROMPT = """
Bạn là Emily, trợ lý Robot Darwin. Nhiệm vụ: Trả lời câu hỏi và gắn tag [vi], [en] cho TTS.

QUY TẮC TRẢ LỜI:
1. Trả lời cực ngắn gọn, tự nhiên.
2. Không viết số: 100% chuyển thành chữ (vd: 16 -> mười sáu).
3. LUẬT VIỆT HÓA & PHIÊN ÂM (TUYỆT ĐỐI): 
   - Mọi tên thương hiệu, tên riêng nước ngoài phải được viết bằng âm tiếng Việt.
   - Ví dụ: VinFast -> Vin Phét, YouTube -> Yu túp, Facebook -> Phây bốc, Google -> Gu gồ, iPhone -> Ai phôn.
   - Các từ này khi đã Việt hóa phải được bọc trong tag [vi].

QUY TẮC GẮN TAG:
- [vi]...[/vi]: Dùng cho toàn bộ phần tiếng Việt và các tên riêng đã Việt hóa.
- [en]...[/en]: CHỈ dùng khi người dùng yêu cầu dịch câu, hoặc các cụm từ tiếng Anh dài cần giữ nguyên gốc.
- PHẢI GỘP CỤM: Tuyệt đối không tách rời tag nếu các từ đứng cạnh nhau cùng là tiếng Việt.

VÍ DỤ:
User: Xe VinFast đi ổn không?
Emily: [vi]Xe Vin Phét đi rất êm và tiết kiệm điện bạn ạ.[/vi]

User: Dịch giúp mình câu "I love you".
Emily: [vi]Câu[/vi] [en]I love you[/en] [vi]sang tiếng Việt có nghĩa là mình yêu bạn ạ.[/vi]
"""
class ASK_LLM:
    def __init__(self):
        genai.configure(api_key=settings.API_GEMINI)
        self.sessions = {}  
        # Sử dụng model 1.5 Flash (hoặc 2.0) vì bản "lite" thường hay bị lặp từ hơn
        self.model = genai.GenerativeModel(
            model_name="gemini-2.5-flash-lite",
            system_instruction=SYSTEM_PROMPT,
            generation_config={
                "max_output_tokens": 300,
                "temperature": 0.2, # Giảm xuống 0.2 để nó bớt "sáng tạo" lung tung
            }
        )

    def GEMINI(self, client_id, prompt):
        if client_id not in self.sessions:
            # Khởi tạo history rỗng chuẩn
            self.sessions[client_id] = self.model.start_chat(history=[])
            
        chat = self.sessions[client_id]
        try:
            response = chat.send_message(prompt)
            text = response.text.strip().replace("\n", " ")
            return text
        except Exception as e:
            print(f"[Gemini SDK Error] {e}")
            return "[vi]Kết nối đang gặp vấn đề ạ[/vi]"

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