## server backend chatbot voice bytehome
# cách khởi tạo uv sync 
cách chạy :
  1 uv run python main.py
## chú ý nếu chưa có lọc âm thì cần cài 
cài đặt thư viện build 
sudo apt update
sudo apt install autoconf automake libtool pkg-config build-essential
##
git clone https://github.com/xiph/rnnoise
./autogen.sh
./configure
make

sưar lại đường dẫn trong file client trỏ đến file .so vừa mới build được 
