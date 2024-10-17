import streamlit as st
import calendar
import datetime
from typing import Dict, Any
import pandas as pd
import hashlib
from dataclasses import dataclass, field
import json
import os
import requests
import base64

# Token ve repo bilgileri
GITHUB_TOKEN = "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"
REPO_OWNER = "umitcaninz"
REPO_NAME = "takvim"
FILE_PATH = "data.json"
BRANCH = "main"

@dataclass
class Event:
    date: datetime.date
    description: str
    is_new: bool = True

    def to_dict(self):
        return {
            "date": self.date.isoformat(),
            "description": self.description,
            "is_new": self.is_new
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            date=datetime.date.fromisoformat(data["date"]),
            description=data["description"],
            is_new=data["is_new"]
        )

@dataclass
class DataStore:
    etkinlikler: Dict[str, Event] = field(default_factory=dict)
    duyurular: Dict[str, Event] = field(default_factory=dict)
    haberler: Dict[str, Event] = field(default_factory=dict)

    def to_dict(self):
        return {
            "etkinlikler": {k: v.to_dict() for k, v in self.etkinlikler.items()},
            "duyurular": {k: v.to_dict() for k, v in self.duyurular.items()},
            "haberler": {k: v.to_dict() for k, v in self.haberler.items()}
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            etkinlikler={k: Event.from_dict(v) for k, v in data["etkinlikler"].items()},
            duyurular={k: Event.from_dict(v) for k, v in data["duyurular"].items()},
            haberler={k: Event.from_dict(v) for k, v in data["haberler"].items()}
        )

@dataclass
class AppState:
    data_store: DataStore = field(default_factory=DataStore)
    is_admin: bool = False

def save_data(data_store: DataStore):
    with open("data.json", "w") as f:
        json.dump(data_store.to_dict(), f)

def load_data() -> DataStore:
    if os.path.exists("data.json"):
        with open("data.json", "r") as f:
            data = json.load(f)
        return DataStore.from_dict(data)
    return DataStore()

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
    .new-event {{
        background-color: #FFFF99;
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
                cell_style = ""
                if date_str in data_dict:
                    event = data_dict[date_str]
                    event_class = "new-event" if event.is_new else ""
                    event_html = f'<span class="event-dot"></span><div class="event-description {event_class}">{event.description[:15]}...</div>'
                    cell_style = 'style="background-color: #FFFF99;"'
                html += f'<td {cell_style}><div class="day-number">{day}</div>{event_html}</td>'
            else:
                html += '<td></td>'
        html += "</tr>"

    html += "</table>"
    return html

def update_github_file(file_content: dict):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    # Mevcut dosya bilgilerini al
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        file_info = response.json()
        sha = file_info['sha']  # Dosyanın SHA'sı, güncelleme için gerekli
    else:
        raise Exception("GitHub dosyası alınamadı.")
    
    # Yeni içerik JSON formatına çevrilip Base64 ile encode edilir
    new_content = json.dumps(file_content, indent=2)
    encoded_content = base64.b64encode(new_content.encode("utf-8")).decode("utf-8")
    
    # GitHub'a dosya güncelleme isteği gönderilir
    update_data = {
        "message": "Takvim güncellendi",
        "content": encoded_content,
        "sha": sha,
        "branch": BRANCH
    }
    
    update_response = requests.put(url, headers=headers, json=update_data)
    if update_response.status_code == 200:
        st.success("GitHub dosyası başarıyla güncellendi!")
    else:
        st.error(f"GitHub güncellemesi başarısız oldu: {update_response.json()}")

def add_item(date: datetime.date, text: str, data_dict: Dict[str, Event]) -> None:
    date_str = date.isoformat()
    if date_str in data_dict:
        st.warning(f"Bu tarih zaten işaretli: {date}")
    else:
        data_dict[date_str] = Event(date, text)
        st.success(f"Eklendi: {date} - {text}")
        save_data(st.session_state.app_state.data_store)
        
        # GitHub dosyasını güncelle
        update_github_file(st.session_state.app_state.data_store.to_dict())

def main():
    st.set_page_config(page_title="ARDEK Takvimi", layout="wide", initial_sidebar_state="collapsed")
    if 'app_state' not in st.session_state:
        st.session_state.app_state = AppState(data_store=load_data())
    app_state = st.session_state.app_state
    st.title("ARDEK Etkinlikler, Duyurular ve Haberler Takvimi")
    menu = ["Etkinlikler", "Duyurular", "Haberler"]
    choice = st.selectbox("Kategori Seçin", menu, index=0)  
    col1, col2 = st.columns([2, 3])
    
    with col1:
        st.header(choice)
        year = st.selectbox("Yıl", range(datetime.datetime.now().year, datetime.datetime.now().year + 5))
        turkish_months = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
        month = st.selectbox("Ay", range(1, 13), index=9, format_func=lambda x: turkish_months[x-1])
        data_dict = getattr(app_state.data_store, choice.lower())
        calendar_html = create_calendar_html(year, month, data_dict)
        st.markdown(calendar_html, unsafe_allow_html=True)

    with col2:
        st.header("Ekle")
        date_input = st.date_input("Tarih Seçin", datetime.date.today())
        text_input = st.text_input("Açıklama Girin")
        if st.button("Ekle"):
            if text_input:
                add_item(date_input, text_input, getattr(app_state.data_store, choice.lower()))
            else:
                st.warning("Açıklama alanı boş olamaz.")

if __name__ == "__main__":
    main()
