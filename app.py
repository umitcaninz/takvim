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

GITHUB_REPO = "umitcaninz/takvim"

def get_github_file(file_path):
    url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{file_path}"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Hata durumunda istisna fırlatır
        return response.text
    except requests.RequestException as e:
        st.error(f"GitHub'dan dosya alınırken hata oluştu: {str(e)}")
        st.error(f"URL: {url}")
        return None

def save_data(data_store: DataStore):
    with open("data.json", "w") as f:
        json.dump(data_store.to_dict(), f, indent=2)
    st.success("Veriler yerel olarak kaydedildi. Lütfen data.json dosyasını GitHub'a manuel olarak yükleyin.")

def load_data() -> DataStore:
    content = get_github_file("data.json")
    if content:
        try:
            data = json.loads(content)
            return DataStore.from_dict(data)
        except json.JSONDecodeError as e:
            st.error(f"JSON dosyası okunamadı: {str(e)}")
            st.error(f"Dosya içeriği: {content}")
    else:
        st.warning("GitHub'dan data.json dosyası okunamadı. Boş bir veri yapısı kullanılıyor.")
    return DataStore()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(input_password: str, hashed_password: str) -> bool:
    return hash_password(input_password) == hashed_password

def create_calendar_html(year: int, month: int, data_dict: Dict[str, Event]):
    # Bu fonksiyon aynı kalacak, değişiklik yok
    # Fonksiyonun içeriğini buraya ekleyin
    pass

def add_item(date: datetime.date, text: str, data_dict: Dict[str, Event]) -> None:
    date_str = date.isoformat()
    if date_str in data_dict:
        st.warning(f"Bu tarih zaten işaretli: {date}")
    else:
        data_dict[date_str] = Event(date, text)
        st.success(f"Eklendi: {date} - {text}")
        save_data(st.session_state.app_state.data_store)

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
                for date_str, event in sorted(data_dict.items(), key=lambda x: x[1].date):
                    date = event.date.strftime('%d.%m.%Y')
                    text_color = "#FF4B4B" if event.is_new else "#000000"
                    st.markdown(f"<h4 style='color: {text_color};'>{date}</h4>", unsafe_allow_html=True)
                    st.markdown(f"<p style='color: {text_color};'>{event.description}</p>", unsafe_allow_html=True)
                    st.markdown("---")
                    event.is_new = False
            else:
                st.info(f"Henüz {choice.lower()} eklenmemiş.")

    if not app_state.is_admin:
        st.sidebar.info("İçerik eklemek veya düzenlemek için admin girişi yapmalısınız.")

    st.sidebar.info("""
    Verileri güncellemek için:
    1. Uygulamada değişiklik yapın.
    2. Yerel data.json dosyasını GitHub'a yükleyin.
    3. Uygulamayı yeniden başlatın veya sayfayı yenileyin.
    """)

    with st.sidebar:
        st.header("Admin Girişi")
        if not app_state.is_admin:
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

if __name__ == "__main__":
    main()
