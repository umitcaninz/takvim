import streamlit as st
import calendar
import datetime
from typing import Dict, Any
import pandas as pd
import hashlib
from dataclasses import dataclass, field

@dataclass
class Event:
    date: datetime.date
    description: str

@dataclass
class DataStore:
    etkinlikler: Dict[str, Event] = field(default_factory=dict)
    duyurular: Dict[str, Event] = field(default_factory=dict)
    haberler: Dict[str, Event] = field(default_factory=dict)

@dataclass
class AppState:
    data_store: DataStore = field(default_factory=DataStore)
    is_admin: bool = False

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(input_password: str, hashed_password: str) -> bool:
    return hash_password(input_password) == hashed_password

def create_calendar_html(year: int, month: int, data_dict: Dict[str, Event]):
    cal = calendar.monthcalendar(year, month)
    turkish_months = ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
    month_name = turkish_months[month]
    
    html = f"""
    <style>
    .calendar {{
        font-family: Arial, sans-serif;
        border-collapse: collapse;
        width: 100%;
    }}
    .calendar th, .calendar td {{
        border: 1px solid #ddd;
        padding: 4px;
        text-align: center;
    }}
    .calendar th {{
        background-color: #f2f2f2;
    }}
    .calendar td {{
        height: 60px;
        vertical-align: top;
    }}
    .day-number {{
        font-size: 14px;
        font-weight: bold;
    }}
    .event-dot {{
        height: 8px;
        width: 8px;
        background-color: #4CAF50;
        border-radius: 50%;
        display: inline-block;
        margin-left: 5px;
    }}
    .event-description {{
        font-size: 10px;
        color: #666;
        margin-top: 2px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }}
    </style>
    <table class="calendar">
    <tr><th colspan="7">{month_name} {year}</th></tr>
    <tr>
        <th>Pzt</th>
        <th>Sal</th>
        <th>Çar</th>
        <th>Per</th>
        <th>Cum</th>
        <th>Cmt</th>
        <th>Paz</th>
    </tr>
    """
    
    for week in cal:
        html += "<tr>"
        for day in week:
            if day != 0:
                date = datetime.date(year, month, day)
                date_str = date.isoformat()
                event_html = ""
                if date_str in data_dict:
                    event = data_dict[date_str]
                    event_html = f'<span class="event-dot"></span><div class="event-description">{event.description[:15]}...</div>'
                html += f'<td><div class="day-number">{day}</div>{event_html}</td>'
            else:
                html += '<td></td>'
        html += "</tr>"
    
    html += "</table>"
    return html

def add_item(date: datetime.date, text: str, data_dict: Dict[str, Event]) -> None:
    date_str = date.isoformat()
    if date_str in data_dict:
        st.warning(f"Bu tarih zaten işaretli: {date}")
    else:
        data_dict[date_str] = Event(date, text)
        st.success(f"Eklendi: {date} - {text}")

def main():
    st.set_page_config(page_title="Etkinlik Takvimi", layout="wide")

    if 'app_state' not in st.session_state:
        st.session_state.app_state = AppState()

    app_state = st.session_state.app_state

    st.title("Etkinlikler, Duyurular ve Haberler Takvimi")

    with st.sidebar:
        st.header("Kontrol Paneli")
        if not app_state.is_admin:
            with st.expander("Admin Girişi"):
                password = st.text_input("Şifre", type="password")
                if st.button("Giriş"):
                    if verify_password(password, hash_password("admin123")):
                        app_state.is_admin = True
                        st.success("Admin girişi başarılı!")
                    else:
                        st.error("Hatalı şifre!")
        else:
            st.success("Admin olarak giriş yapıldı")
            if st.button("Çıkış Yap"):
                app_state.is_admin = False

        menu = ["Etkinlikler", "Duyurular", "Haberler"]
        choice = st.selectbox("Kategori Seçin", menu)

    col1, col2 = st.columns([2, 3])

    with col1:
        st.header(choice)
        year = st.selectbox("Yıl", range(datetime.datetime.now().year, datetime.datetime.now().year + 5))
        turkish_months = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
        month = st.selectbox("Ay", range(1, 13), format_func=lambda x: turkish_months[x-1])

        data_dict = getattr(app_state.data_store, choice.lower())
        calendar_html = create_calendar_html(year, month, data_dict)
        st.components.v1.html(calendar_html, height=500, scrolling=True)

    with col2:
        if app_state.is_admin:
            with st.expander(f"Yeni {choice[:-1]} Ekle", expanded=True):
                date = st.date_input("Tarih")
                text = st.text_area("Açıklama")
                if st.button("Ekle"):
                    add_item(date, text, data_dict)

        with st.expander(f"Mevcut {choice}", expanded=True):
            if data_dict:
                df = pd.DataFrame([(date, event.description) for date, event in data_dict.items()],
                                  columns=['Tarih', 'Açıklama'])
                df['Tarih'] = pd.to_datetime(df['Tarih'])
                df = df.sort_values('Tarih')
                df['Tarih'] = df['Tarih'].dt.strftime('%d.%m.%Y')  # Sadece gün, ay ve yıl
                
                # CSS ile tablo stilini özelleştirme
                st.markdown("""
                <style>
                .dataframe td {
                    white-space: normal;
                    max-width: none !important;
                    word-wrap: break-word;
                }
                .dataframe th {
                    white-space: normal;
                    max-width: none !important;
                    word-wrap: break-word;
                }
                </style>
                """, unsafe_allow_html=True)
                
                # Özel genişlik ve yükseklik ayarları ile dataframe'i gösterme
                st.dataframe(df, hide_index=True, use_container_width=True, height=400)
            else:
                st.info(f"Henüz {choice.lower()} eklenmemiş.")

    if not app_state.is_admin:
        st.info("İçerik eklemek veya düzenlemek için admin girişi yapmalısınız.")

if __name__ == "__main__":
    main()
