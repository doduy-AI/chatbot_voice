import asyncio
import re
import time
from google import genai
from google.genai import types

API_KEY = "AIzaSyAxAqsWaqN6UKkQZ9SK6ZVF0W27qbWsLvQ" 
MODEL_NAME = "gemini-2.5-flash-preview-09-2025"




class EmilyDarwin:
    def __init__(self):
        self.client = genai.Client(api_key=API_KEY)
        
        # Cấu hình System Prompt chặt chẽ

        sys_promt= """Quy tắc:\n"
            "1. Tuyệt đối không sử dụng chữ số Ả RẬP (0–9). Mọi số phải được viết đầy đủ bằng chữ tiếng Việt.\n"
            "2. Toàn bộ nội dung tiếng Việt phải được bọc hoàn chỉnh trong thẻ [vi]...[/vi]"
            "3. Toàn bộ nội dung tiếng Anh (kể cả tên riêng, thuật ngữ, viết hoa) phải được bọc hoàn chỉnh trong thẻ [en]...[/en]."
            "Ví dụ: [vi]Chào bạn, tôi là[/vi] [en]Robot Darwin[/en]. [vi]Bạn thích[/vi] [en]YouTube[/en] [vi]không?[/vi]\n"
            "4. Không được để bất kỳ ký tự nào (kể cả dấu câu) nằm ngoài các thẻ [vi] hoặc [en]"
            "Ví dụ: [vi]Chào bạn, tôi là[/vi] [en]Robot Darwin[/en]. [vi]Bạn thích[/vi] [en]YouTube[/en] [vi]không?[/vi]"
            "5. Quy tắc phụ: Không dùng Markdown. Trả lời tối đa bốn câu. Không sử dụng viết tắt không chính thức (ví dụ: ko, kg, vs)."""
    

        # Tạo chat session
        self.chat = self.client.chats.create(
            model=MODEL_NAME,
            config=types.GenerateContentConfig(
                system_instruction=sys_promt,
                temperature=0.7
            )
        )

    def get_full_response(self, user_input):

        try:
            response = self.chat.send_message(user_input)
            if response.text:
                return response.text.strip()
            return "[vi]Xin lỗi, tôi chưa nghĩ ra câu trả lời.[/vi]"
            
        except Exception as e:
            print(f"Lỗi API: {e}")
            return "[vi]Hệ thống đang gặp sự cố kết nối.[/vi]"


async def main():
    bot = EmilyDarwin()
    print("--- Robot Darwin Đã Sẵn Sàng (Chế độ Full Text) ---")
    
    while True:
        try:
            query = input("\nDuy: ")
            if query.lower() in ['exit', 'quit', 'thoát']:
                break

            print("Emily đang suy nghĩ...", end="", flush=True)
            start_time = time.time()

            # --- GỌI HÀM LẤY FULL TEXT ---
            # Vì hàm trên đã return string, ta gán thẳng vào biến.
            full_response = bot.get_full_response(query)
            
            latency = time.time() - start_time
            
            # Xóa dòng "đang suy nghĩ" và in kết quả
            print(f"\rEmily: {full_response}") 
            print(f"[⚡ Thời gian xử lý: {latency:.2f}s]")
            
            # Lúc này full_response là String chuẩn, đưa vào TTS thoải mái
            print(f"🔊 [TTS Full]: {full_response}")
            return full_response

        except Exception as e:
            print(f"\n❌ Lỗi hệ thống: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nĐã tắt Robot.")
