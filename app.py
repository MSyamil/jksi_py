import sys
import asyncio

# Fix NotImplementedError for Playwright subprocesses in Streamlit on Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import streamlit as st
import os
import json
import base64
from PIL import Image
import io

from config import Config
from ai_client import AIClient
from test_agent import TestAgent

# Set page configuration
st.set_page_config(
    page_title="AI-Powered QA Black Box Testing Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Premium Dark UI
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');
    
    /* Global Styles */
    .main .block-container {
        padding-top: 2rem;
    }
    
    html, body, [data-testid="stAppViewContainer"], .main {
        font-family: 'Outfit', sans-serif;
        background-color: #0d0f14;
        color: #e2e8f0;
    }
    
    /* Gradient Title */
    .gradient-text {
        background: linear-gradient(135deg, #a78bfa 0%, #6366f1 50%, #3b82f6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 3rem;
        margin-bottom: 0.5rem;
    }
    
    .subtitle {
        color: #94a3b8;
        font-size: 1.15rem;
        margin-bottom: 2rem;
        font-weight: 300;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #11141e !important;
        border-right: 1px solid #1e293b;
    }
    
    /* Glassmorphic cards */
    .glass-card {
        background: rgba(30, 41, 59, 0.4);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 20px -2px rgba(0,0,0,0.3);
    }
    
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }
    
    .badge-success {
        background-color: rgba(16, 185, 129, 0.15);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    
    .badge-pending {
        background-color: rgba(245, 158, 11, 0.15);
        color: #fbbf24;
        border: 1px solid rgba(245, 158, 11, 0.3);
    }
    
    .badge-healing {
        background-color: rgba(99, 102, 241, 0.15);
        color: #818cf8;
        border: 1px solid rgba(99, 102, 241, 0.3);
        animation: pulse 2s infinite;
    }
    
    .badge-fail {
        background-color: rgba(239, 68, 68, 0.15);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.3);
    }

    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
    
    /* Custom buttons */
    .stButton>button {
        background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.5rem 1.5rem !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3) !important;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(79, 70, 229, 0.4) !important;
    }
    
    /* Table headers */
    th {
        background-color: #1e293b !important;
        color: #f1f5f9 !important;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- SIDEBAR CONFIGURATION -----------------
st.sidebar.markdown("<h2 style='text-align: center; color: #a78bfa;'>⚙️ Konfigurasi AI QA</h2>", unsafe_allow_html=True)
st.sidebar.markdown("---")

# Load values from environment or config
api_provider = st.sidebar.selectbox(
    "Penyedia AI (LLM)",
    ["Gemini (Google)", "OpenAI (GPT)"],
    index=0 if Config.DEFAULT_PROVIDER == "gemini" else 1
)

provider_str = "gemini" if "Gemini" in api_provider else "openai"

# API Key inputs (disembunyikan di dalam expander agar tidak terlihat orang lain)
with st.sidebar.expander("🔑 Pengaturan API Key (Aman)", expanded=False):
    gemini_key = st.text_input(
        "Gemini API Key",
        value=Config.GEMINI_API_KEY,
        type="password",
        help="Dapatkan key gratis dari Google AI Studio."
    )

    openai_key = st.text_input(
        "OpenAI API Key",
        value=Config.OPENAI_API_KEY,
        type="password",
        help="Masukkan OpenAI API Key Anda (opsional)."
    )

# Model selection based on provider
if provider_str == "gemini":
    model_options = ["gemini-3.1-flash-lite", "gemini-2.5-flash", "gemini-3.5-flash", "gemini-2.0-flash"]
    default_idx = model_options.index(Config.DEFAULT_MODEL) if Config.DEFAULT_MODEL in model_options else 0
    active_model = st.sidebar.selectbox("Model Gemini", model_options, index=default_idx)
else:
    model_options = ["gpt-4o-mini", "gpt-4o"]
    active_model = st.sidebar.selectbox("Model OpenAI", model_options, index=0)

st.sidebar.markdown("<h4 style='color: #a78bfa;'>🌐 Pengaturan Browser</h4>", unsafe_allow_html=True)

headless_mode = st.sidebar.checkbox("Jalankan Headless (Tanpa Tampilan Browser)", value=Config.HEADLESS)
slow_mo = st.sidebar.slider("Delay Aksi Browser (Slow Mo - ms)", min_value=100, max_value=2000, value=Config.SLOW_MO, step=100)

# Dynamically update config on every rerun using the current values of widgets
Config.update_keys(
    gemini_key=gemini_key,
    openai_key=openai_key,
    provider=provider_str,
    model=active_model
)
Config.HEADLESS = headless_mode
Config.SLOW_MO = slow_mo

# Save settings back to config
if st.sidebar.button("💾 Simpan Pengaturan"):
    st.sidebar.success("Pengaturan berhasil disimpan!")

# Display current active credentials status
st.sidebar.markdown("---")
st.sidebar.markdown("### Status Koneksi")
active_key = Config.get_active_key()
if active_key:
    st.sidebar.markdown("🟢 **API Key terpasang**")
else:
    st.sidebar.markdown("🔴 **API Key belum dimasukkan**")

# ----------------- MAIN PAGE HEADER -----------------
st.markdown("<div class='gradient-text'>🤖 Generative AI Black Box Testing</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Uji Fungsional Otonom dan Self-Healing pada <b>SauceDemo Storefront</b> menggunakan Vision LLM</div>", unsafe_allow_html=True)

# ----------------- TABS SETUP -----------------
tab1, tab2, tab3, tab4 = st.tabs([
    "🚀 Autonomous Testing Agent", 
    "🛠️ Natural Language Scenario Builder", 
    "🔧 Self-Healing Demo", 
    "📊 Laporan Uji & Analisis AI"
])

# Utility for updating UI live
def render_step_details(step):
    """Render a step block with screenshot, thought, action, and status badge"""
    status = step["status"]
    badge_class = f"badge-{status}"
    
    # Map status to localized label
    status_label = {
        "pending": "⏳ Sedang Diproses...",
        "success": "✅ Sukses",
        "failed": "❌ Gagal",
        "healing": "🔧 Melakukan Self-Healing..."
    }.get(status, status.upper())

    st.markdown(f"""
    <div class="glass-card">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <h4 style="margin: 0; color: #a78bfa;">Langkah {step['step']}: {step['reason']}</h4>
            <span class="status-badge {badge_class}">{status_label}</span>
        </div>
        <p style="margin-top: 10px; margin-bottom: 5px; font-size: 0.95rem;"><b>Aksi:</b> <code>{step['action']}</code> pada selector <code>{step['selector']}</code> {f'dengan nilai "{step["value"]}"' if step["value"] else ''}</p>
        <p style="font-style: italic; color: #94a3b8; font-size: 0.9rem; margin-top: 0;"><b>Pemikiran AI (Reasoning):</b> {step['thought']}</p>
    """, unsafe_allow_html=True)
    
    # If there is healed log
    if step.get("healed_log"):
        st.info(step["healed_log"])

    # Show screenshot side-by-side or below
    if "screenshot" in step and step["screenshot"]:
        try:
            image = Image.open(io.BytesIO(step["screenshot"]))
            st.image(image, caption=f"Screenshot Browser pada Langkah {step['step']}", use_container_width=True)
        except Exception as e:
            st.error(f"Gagal memuat screenshot: {e}")
            
    st.markdown("</div>", unsafe_allow_html=True)

# ----------------- TAB 1: AUTONOMOUS AGENT -----------------
with tab1:
    st.markdown("### 🚀 Autonomous Testing Loop")
    st.markdown(
        "Ketikkan tujuan pengujian akhir (goal) Anda dalam bahasa alami. AI Agent akan secara otonom "
        "membaca visual dan DOM halaman SauceDemo, lalu memutuskan rangkaian tindakan berikutnya untuk mencapai target."
    )

    # Goal Presets
    goal_presets = [
        "Login dengan standard_user, cari ransel (backpack), tambahkan ke keranjang, dan lakukan checkout sampai selesai.",
        "Coba login dengan akun terblokir (locked_out_user) dan pastikan muncul pesan error yang sesuai.",
        "Login dengan standard_user, buka keranjang belanja Anda yang kosong, verifikasi halaman keranjang kosong, lalu klik continue shopping.",
        "Login dengan standard_user, tambahkan produk termurah ke keranjang, lalu verifikasi bahwa nama produk tersebut benar di halaman keranjang."
    ]
    
    selected_preset = st.selectbox("Pilih Contoh Skenario Uji (Preset):", goal_presets)
    custom_goal = st.text_area("Atau ketik tujuan uji khusus Anda sendiri:", value=selected_preset, height=80)

    # Check key before running
    if not Config.get_active_key():
        st.warning("⚠️ API Key belum diatur. Silakan masukkan API Key di menu sebelah kiri terlebih dahulu.")
        run_btn_disabled = True
    else:
        run_btn_disabled = False

    if st.button("🚀 Jalankan AI Agent Mandiri", disabled=run_btn_disabled):
        if not custom_goal.strip():
            st.error("Silakan masukkan tujuan pengujian.")
        else:
            status_box = st.empty()
            log_container = st.container()
            
            status_box.info("Browser sedang diinisialisasi... Mengarahkan ke SauceDemo...")
            
            # Step-by-step UI callback
            def agent_callback(step_detail):
                # We can store execution history in session state
                if "auto_steps" not in st.session_state:
                    st.session_state.auto_steps = []
                
                # Check if step is already in list (update it) or new
                step_idx = next((i for i, val in enumerate(st.session_state.auto_steps) if val["step"] == step_detail["step"]), None)
                if step_idx is not None:
                    st.session_state.auto_steps[step_idx] = step_detail
                else:
                    st.session_state.auto_steps.append(step_detail)
                
                # Force refresh log container
                with log_container:
                    st.empty()
                    for step in st.session_state.auto_steps:
                        render_step_details(step)
            
            # Clear previous run
            st.session_state.auto_steps = []
            
            # Run the agent
            agent = TestAgent()
            with st.spinner("AI Agent sedang berjalan dan mengambil keputusan..."):
                result = agent.run_autonomous_test(
                    goal=custom_goal,
                    provider=provider_str,
                    model=active_model,
                    ui_callback=agent_callback
                )
            
            # Report result
            if result["success"]:
                status_box.success(f"🎉 Sukses! {result['message']}")
                # Save to history for Tab 4 report
                if "test_history" not in st.session_state:
                    st.session_state.test_history = []
                st.session_state.test_history.append({
                    "goal": custom_goal,
                    "status": "Success",
                    "steps": len(result["steps"]),
                    "details": result["message"]
                })
            else:
                status_box.error(f"❌ Pengujian Berhenti: {result['message']}")
                if "test_history" not in st.session_state:
                    st.session_state.test_history = []
                st.session_state.test_history.append({
                    "goal": custom_goal,
                    "status": "Failed",
                    "steps": len(result["steps"]),
                    "details": result["message"]
                })

# ----------------- TAB 2: SCENARIO BUILDER -----------------
with tab2:
    st.markdown("### 🛠️ Natural Language Scenario Builder")
    st.markdown(
        "Ketik instruksi pengujian secara luas. AI akan menganalisis instruksi tersebut, membaginya menjadi "
        "rangkaian langkah pengujian Playwright terstruktur (Action, Selector, Value) secara instan, lalu mengeksekusinya."
    )

    scenario_prompt = st.text_area(
        "Tulis instruksi pengujian (misal: login standard_user, checkout T-Shirt merah):",
        value="Login menggunakan user 'standard_user', lalu checkout baju 'Sauce Labs Bolt T-Shirt' sampai selesai.",
        height=80
    )

    col1, col2 = st.columns([1, 2])
    
    with col1:
        if st.button("🛠️ 1. Buat Langkah Skrip", disabled=run_btn_disabled):
            with st.spinner("AI sedang menerjemahkan instruksi ke skrip uji..."):
                generated_steps = AIClient.generate_test_steps(
                    user_prompt=scenario_prompt,
                    provider=provider_str,
                    model=active_model
                )
                st.session_state.generated_steps = generated_steps
                
        if "generated_steps" in st.session_state and st.session_state.generated_steps:
            st.markdown("##### 📝 Langkah Terstruktur Hasil AI:")
            st.json(st.session_state.generated_steps)
            
    with col2:
        if "generated_steps" in st.session_state and st.session_state.generated_steps:
            if st.button("🚀 2. Jalankan Skenario Uji"):
                scenario_log = st.container()
                status_box_sc = st.empty()
                
                # Clear previous steps logs
                st.session_state.scenario_run_steps = []
                
                def scenario_callback(step_detail):
                    if "scenario_run_steps" not in st.session_state:
                        st.session_state.scenario_run_steps = []
                    
                    idx = next((i for i, val in enumerate(st.session_state.scenario_run_steps) if val["step"] == step_detail["step"]), None)
                    if idx is not None:
                        st.session_state.scenario_run_steps[idx] = step_detail
                    else:
                        st.session_state.scenario_run_steps.append(step_detail)
                        
                    with scenario_log:
                        st.empty()
                        for step in st.session_state.scenario_run_steps:
                            render_step_details(step)
                            
                agent = TestAgent()
                with st.spinner("Menjalankan langkah skenario pada browser..."):
                    res = agent.run_scenario_steps(
                        steps=st.session_state.generated_steps,
                        ui_callback=scenario_callback
                    )
                    
                if res["success"]:
                    status_box_sc.success(f"🎉 Skenario Berhasil Dijalankan! {res['message']}")
                else:
                    status_box_sc.error(f"❌ Skenario Gagal! {res['message']}")

# ----------------- TAB 3: SELF-HEALING DEMO -----------------
with tab3:
    st.markdown("### 🔧 Simulasi Self-Healing (Perbaikan Mandiri)")
    st.markdown(
        "Salah satu masalah utama QA Automation adalah **flaky tests** karena selector CSS berubah saat rilis kode baru. "
        "Tab ini mensimulasikan kegagalan selector. Kami sengaja merusak selector tombol checkout di bawah. "
        "AI akan menangkap error tersebut, mengekstrak DOM saat itu, memperbaiki selector secara real-time ke selector yang valid, dan melanjutkan test run."
    )

    # Standard steps template
    healed_steps = [
        {"step": 1, "description": "Ketik username 'standard_user'", "action": "type", "selector": "#user-name", "value": "standard_user"},
        {"step": 2, "description": "Ketik password 'secret_sauce'", "action": "type", "selector": "#password", "value": "secret_sauce"},
        {"step": 3, "description": "Klik tombol login", "action": "click", "selector": "#login-button", "value": ""},
        {"step": 4, "description": "Tambahkan Backpack ke keranjang", "action": "click", "selector": "button[name='add-to-cart-sauce-labs-backpack']", "value": ""},
        {"step": 5, "description": "Buka keranjang belanja", "action": "click", "selector": ".shopping_cart_link", "value": ""},
        {"step": 6, "description": "Klik tombol checkout", "action": "click", "selector": "#checkout", "value": ""}, # We will break this!
        {"step": 7, "description": "Verifikasi berhasil ke halaman form checkout", "action": "verify", "selector": "", "value": "Checkout: Your Information"}
    ]

    col_h1, col_h2 = st.columns([1, 2])
    with col_h1:
        st.markdown("##### 📋 Skrip Pengujian yang Dijalankan:")
        for s in healed_steps:
            if s["step"] == 6:
                st.markdown(f"**Step {s['step']}:** {s['description']} (Selector asli: `{s['selector']}` → *Akan dirusak*)")
            else:
                st.markdown(f"**Step {s['step']}:** {s['description']}")
                
        broken_selector_input = st.text_input("Simulasi Selector Rusak (Step 6):", value="#checkout-salah-selector")

    with col_h2:
        if st.button("🔧 Jalankan Tes dengan Self-Healing", disabled=run_btn_disabled):
            healing_log = st.container()
            status_box_h = st.empty()
            
            st.session_state.healing_run_steps = []
            
            def healing_callback(step_detail):
                if "healing_run_steps" not in st.session_state:
                    st.session_state.healing_run_steps = []
                
                idx = next((i for i, val in enumerate(st.session_state.healing_run_steps) if val["step"] == step_detail["step"]), None)
                if idx is not None:
                    st.session_state.healing_run_steps[idx] = step_detail
                else:
                    st.session_state.healing_run_steps.append(step_detail)
                    
                with healing_log:
                    st.empty()
                    for step in st.session_state.healing_run_steps:
                        render_step_details(step)
            
            agent = TestAgent()
            with st.spinner("Menjalankan tes dengan self-healing aktif..."):
                res = agent.run_self_healing_test(
                    steps=healed_steps,
                    simulate_broken_idx=6,
                    simulate_broken_selector=broken_selector_input,
                    provider=provider_str,
                    model=active_model,
                    ui_callback=healing_callback
                )
                
            if res["success"]:
                status_box_h.success(f"🎉 Sukses dengan Pemulihan AI! {res['message']}")
            else:
                status_box_h.error(f"❌ Kegagalan Uji: {res['message']}")

# ----------------- TAB 4: REPORT & DASHBOARD -----------------
with tab4:
    st.markdown("### 📊 Dasbor Kualitas Aplikasi (AI Report)")
    st.markdown(
        "Kumpulkan hasil dari sesi pengujian Anda dan dapatkan analisis kualitas aplikasi secara menyeluruh oleh AI. "
        "AI akan mengevaluasi pengalaman pengguna (UX), kecepatan alur, serta potensi bug pada situs SauceDemo berdasarkan riwayat uji."
    )

    # Simulated statistics
    col_stat1, col_stat2, col_stat3 = st.columns(3)
    
    # Get statistics from session state
    history_list = st.session_state.get("test_history", [])
    total_runs = len(history_list)
    success_runs = len([x for x in history_list if x["status"] == "Success"])
    failed_runs = total_runs - success_runs
    
    with col_stat1:
        st.metric("Total Pengujian Dijalankan", total_runs)
    with col_stat2:
        st.metric("Pengujian Sukses", success_runs, delta=f"{success_runs} sukses" if total_runs > 0 else None)
    with col_stat3:
        st.metric("Pengujian Gagal", failed_runs, delta=f"{failed_runs} gagal" if total_runs > 0 else None, delta_color="inverse")

    st.markdown("##### 📜 Riwayat Pengujian Sesi Ini")
    if total_runs > 0:
        st.table(history_list)
        
        # Ekspor ke Excel (.xlsx) menggunakan pandas
        import pandas as pd
        import io
        
        df = pd.DataFrame(history_list)
        df_display = df.rename(columns={
            "goal": "Tujuan Pengujian",
            "status": "Status Hasil",
            "steps": "Jumlah Langkah",
            "details": "Detail Hasil/Aksi Terakhir"
        })
        
        # Write Excel file to memory buffer
        buffer = io.BytesIO()
        try:
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_display.to_excel(writer, sheet_name='Laporan Pengujian', index=False)
            
            excel_data = buffer.getvalue()
            
            st.download_button(
                label="📥 Unduh Riwayat Pengujian (Excel .xlsx)",
                data=excel_data,
                file_name="Laporan_Riwayat_Pengujian_SauceDemo.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as ex:
            st.error(f"Gagal membuat file Excel: {ex}")
    else:
        st.info("Belum ada pengujian yang dijalankan pada sesi ini. Jalankan uji otonom di Tab 1 untuk memuat data.")

    # Call AI to generate Quality Assessment Report
    if st.button("📊 Dapatkan Laporan Kualitas berbasis AI", disabled=(total_runs == 0)):
        with st.spinner("AI sedang menganalisis sesi pengujian Anda untuk menyusun laporan kualitas..."):
            history_text = json.dumps(history_list, indent=2)
            
            report_prompt = f"""
Anda adalah QA Director & UX Evaluator. Berikut adalah riwayat ringkasan hasil pengujian otomatis berbasis AI yang baru saja dijalankan pada aplikasi web SauceDemo (https://www.saucedemo.com/):
```json
{history_text}
```

Tugas Anda adalah membuat **Laporan Evaluasi Kualitas Aplikasi (App Quality Evaluation Report)** yang profesional, meliputi:
1. **Analisis Hasil Pengujian**: Ringkasan singkat mengenai keberhasilan dan kegagalan pengujian.
2. **Evaluasi UX/UI SauceDemo**: Berdasarkan penjelajahan halaman login dan checkout, bagaimana penilaian kegunaan (usability) dan layout aplikasi ini?
3. **Analisis Ketangguhan (Robustness)**: Keandalan selector elemen. Mengapa self-healing diperlukan untuk aplikasi web modern dan bagaimana ia membantu mencegah kegagalan pengujian yang tidak perlu (flaky tests)?
4. **Rekomendasi Perbaikan**: Berikan saran perbaikan teknis atau fungsional untuk pengembang aplikasi.

Tulis laporan dalam format Markdown yang rapi dan elegan dalam Bahasa Indonesia.
"""
            try:
                if provider_str == "gemini":
                    genai_client = AIClient._get_gemini_client(Config.GEMINI_API_KEY)
                    model_instance = genai_client.GenerativeModel(active_model)
                    response = model_instance.generate_content(report_prompt)
                    report_content = response.text
                else:
                    openai_client = AIClient._get_openai_client(Config.OPENAI_API_KEY)
                    response = openai_client.chat.completions.create(
                        model=active_model,
                        messages=[{"role": "user", "content": report_prompt}]
                    )
                    report_content = response.choices[0].message.content
                
                st.markdown("---")
                st.markdown(report_content)
                
                # Option to download report
                st.download_button(
                    label="📥 Unduh Laporan Kualitas (Markdown)",
                    data=report_content,
                    file_name="Laporan_Kualitas_SauceDemo_AI.md",
                    mime="text/markdown"
                )
                
            except Exception as e:
                st.error(f"Gagal menghasilkan laporan kualitas AI: {e}")
