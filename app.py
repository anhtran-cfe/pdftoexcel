import streamlit as st
import base64
import json
import pandas as pd
from io import BytesIO
import google.generativeai as genai
from typing import List, Dict, Any

# Page configuration
st.set_page_config(
    page_title="Chuyển đổi PDF sang Excel",
    page_icon="📄",
    layout="wide"
)

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'username' not in st.session_state:
    st.session_state.username = None

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        text-align: center;
        background: linear-gradient(90deg, #10b981 0%, #3b82f6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        text-align: center;
        color: #6b7280;
        margin-bottom: 2rem;
    }
    .stButton>button {
        width: 100%;
        background: linear-gradient(90deg, #10b981 0%, #3b82f6 100%);
        color: white;
        font-weight: 600;
        border-radius: 0.5rem;
        padding: 0.75rem;
        border: none;
    }
    .stButton>button:hover {
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    div[data-testid="stFileUploader"] {
        border: 2px dashed #3b82f6;
        border-radius: 1rem;
        padding: 2rem;
        background-color: #eff6ff;
    }
    .success-box {
        background-color: #d1fae5;
        border-left: 4px solid #10b981;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .info-box {
        background-color: #dbeafe;
        border-left: 4px solid #3b82f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .login-container {
        max-width: 450px;
        margin: 100px auto;
        padding: 3rem;
        background: white;
        border-radius: 1rem;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
    }
    .login-header {
        text-align: center;
        margin-bottom: 2rem;
    }
    .login-title {
        font-size: 2rem;
        font-weight: 700;
        color: #1f2937;
        margin-bottom: 0.5rem;
    }
    .login-subtitle {
        color: #6b7280;
        font-size: 1rem;
    }
</style>
""", unsafe_allow_html=True)

def verify_credentials(username: str, password: str) -> bool:
    """Verify username and password against secrets"""
    try:
        valid_users = st.secrets.get("users", {})
        if username in valid_users:
            return password == valid_users[username]
        return False
    except Exception as e:
        st.error(f"⚠️ Lỗi xác thực. Vui lòng liên hệ quản trị viên.")
        return False

def login_page():
    """Display login page"""
    st.markdown("""
        <div class='login-container'>
            <div class='login-header'>
                <div class='login-title'>🔐 Đăng nhập hệ thống</div>
                <div class='login-subtitle'>Công cụ chuyển đổi PDF sang Excel</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### Thông tin đăng nhập")
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input(
                "Tên đăng nhập",
                placeholder="Nhập tên đăng nhập",
                key="username_input"
            )
            password = st.text_input(
                "Mật khẩu",
                type="password",
                placeholder="Nhập mật khẩu",
                key="password_input"
            )
            
            st.markdown("<br>", unsafe_allow_html=True)
            submit = st.form_submit_button("🔓 Đăng nhập", use_container_width=True)
            
            if submit:
                if not username or not password:
                    st.warning("⚠️ Vui lòng nhập đầy đủ thông tin!")
                elif verify_credentials(username, password):
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.success(f"✅ Đăng nhập thành công! Chào mừng {username}")
                    st.rerun()
                else:
                    st.error("❌ Tên đăng nhập hoặc mật khẩu không đúng!")

def configure_api() -> bool:
    """Configure API with key from secrets"""
    try:
        api_key = st.secrets.get("GEMINI_API_KEY", "")
        if not api_key:
            st.error("⚠️ Lỗi cấu hình hệ thống. Vui lòng liên hệ quản trị viên.")
            return False
        genai.configure(api_key=api_key)
        return True
    except Exception as e:
        st.error(f"⚠️ Không thể khởi tạo hệ thống. Vui lòng liên hệ quản trị viên.")
        return False

def extract_table_from_pdf(pdf_file) -> List[List[str]]:
    """Extract table data from PDF using AI"""
    try:
        # Read PDF file
        pdf_data = pdf_file.read()
        pdf_base64 = base64.b64encode(pdf_data).decode('utf-8')
        
        # Configure model
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # Create prompt
        prompt = """
        Trích xuất TẤT CẢ các bảng từ tài liệu PDF này.
        
        Yêu cầu:
        1. Tìm và trích xuất tất cả các bảng trong tài liệu
        2. Giữ nguyên cấu trúc bảng gốc
        3. Dòng đầu tiên là tiêu đề cột
        4. Giữ nguyên định dạng số và văn bản
        5. Nếu có nhiều bảng, gộp tất cả lại
        
        Trả về JSON array với format:
        [
          ["Cột 1", "Cột 2", "Cột 3"],
          ["Giá trị 1", "Giá trị 2", "Giá trị 3"],
          ...
        ]
        
        CHỈ trả về JSON array, KHÔNG có text nào khác.
        """
        
        # Generate content
        response = model.generate_content([
            prompt,
            {
                'mime_type': 'application/pdf',
                'data': pdf_base64
            }
        ])
        
        # Parse response
        response_text = response.text.strip()
        
        # Remove markdown code blocks if present
        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
            response_text = response_text.strip()
        
        # Parse JSON
        try:
            table_data = json.loads(response_text)
            
            # Handle case where data is wrapped in another array
            if isinstance(table_data, list) and len(table_data) == 1 and isinstance(table_data[0], list):
                table_data = table_data[0]
            
            return table_data
            
        except json.JSONDecodeError as e:
            st.error(f"⚠️ Lỗi xử lý dữ liệu: Không thể chuyển đổi phản hồi thành bảng")
            st.warning(f"Nội dung nhận được: {response_text[:200]}...")
            return []
            
    except Exception as e:
        st.error(f"⚠️ Lỗi trong quá trình xử lý: {str(e)}")
        return []

def convert_to_csv(data: List[List[str]]) -> BytesIO:
    """Convert table data to CSV with UTF-8 BOM for Excel compatibility"""
    if not data:
        return None
    
    # Create DataFrame
    df = pd.DataFrame(data[1:], columns=data[0])
    
    # Create CSV with UTF-8 BOM
    csv_buffer = BytesIO()
    # Add BOM for Excel to recognize UTF-8
    csv_buffer.write('\ufeff'.encode('utf-8'))
    df.to_csv(csv_buffer, index=False, encoding='utf-8')
    csv_buffer.seek(0)
    
    return csv_buffer

def main_app():
    """Main application interface"""
    
    # Header with user info and logout
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown('<h1 class="main-header">📄 Chuyển đổi PDF sang Excel</h1>', unsafe_allow_html=True)
        st.markdown('<p class="sub-header">Trích xuất bảng dữ liệu từ file PDF tự động</p>', unsafe_allow_html=True)
    with col2:
        st.write("")
        st.write("")
        st.write(f"👤 **{st.session_state.username}**")
        if st.button("🚪 Đăng xuất", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.username = None
            if 'extracted_data' in st.session_state:
                del st.session_state['extracted_data']
            st.rerun()
    
    # Configure API
    if not configure_api():
        st.stop()
    
    # File upload section
    st.markdown("### 📤 Tải file PDF")
    uploaded_file = st.file_uploader(
        "Chọn file PDF cần chuyển đổi",
        type=['pdf'],
        help="Chọn file PDF chứa bảng dữ liệu cần trích xuất"
    )
    
    if uploaded_file is not None:
        # Display file info
        file_size = len(uploaded_file.getvalue()) / 1024 / 1024  # Convert to MB
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            <div class='info-box'>
                <strong>📄 Tên file:</strong> {uploaded_file.name}<br>
                <strong>📊 Kích thước:</strong> {file_size:.2f} MB
            </div>
            """, unsafe_allow_html=True)
        
        # Extract button
        if st.button("🚀 Trích xuất dữ liệu", use_container_width=True):
            with st.spinner("⏳ Đang xử lý file PDF... Vui lòng đợi trong giây lát."):
                extracted_data = extract_table_from_pdf(uploaded_file)
                
                if extracted_data and len(extracted_data) > 0:
                    st.session_state['extracted_data'] = extracted_data
                    st.markdown("""
                    <div class='success-box'>
                        ✅ <strong>Trích xuất thành công!</strong> Dữ liệu đã sẵn sàng để tải xuống.
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.error("❌ Không tìm thấy bảng dữ liệu trong file PDF. Vui lòng kiểm tra lại file.")
    
    # Display extracted data
    if 'extracted_data' in st.session_state:
        data = st.session_state['extracted_data']
        
        st.markdown("### 📊 Dữ liệu đã trích xuất")
        
        # Create DataFrame for display
        df = pd.DataFrame(data[1:], columns=data[0])
        
        # Display data
        st.dataframe(df, use_container_width=True, height=400)
        
        # Statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📋 Số dòng", len(df))
        with col2:
            st.metric("📊 Số cột", len(df.columns))
        with col3:
            st.metric("💾 Dung lượng", f"{len(str(df)) / 1024:.1f} KB")
        
        # Download button
        st.markdown("### 💾 Tải xuống")
        csv_data = convert_to_csv(data)
        
        if csv_data:
            st.download_button(
                label="📥 Tải xuống file Excel (CSV)",
                data=csv_data,
                file_name=f"{uploaded_file.name.replace('.pdf', '')}_extracted.csv",
                mime="text/csv",
                use_container_width=True
            )
            
            st.info("ℹ️ **Lưu ý:** File được tải xuống có định dạng CSV, có thể mở trực tiếp bằng Microsoft Excel hoặc Google Sheets.")

def main():
    """Main application entry point"""
    if not st.session_state.authenticated:
        login_page()
    else:
        main_app()

if __name__ == "__main__":
    main()
