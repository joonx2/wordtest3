# 기본 모듈
from fnmatch import translate
import logging
from pickle import NONE
from tkinter import CURRENT

import theme_colors

logging.basicConfig(
    level=logging.DEBUG,  # 모든 수준에서 로깅
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logging.getLogger("fontTools").setLevel(logging.WARNING)
logging.debug("로깅 초기화 완료")

import sys
import platform as sys_platform
import os
import inspect
from pathlib import Path
import re  # 정규 표현식 모듈
import csv
import json
import glob
import random
import subprocess
import time
from datetime import datetime, timedelta
import io
import urllib.parse
import webbrowser
from OpenGL.GL import *
import pygame

# PyQt5 관련 모듈
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import (QMargins, pyqtSlot, QTimer, QTime, Qt, QMetaObject, QThread, QPropertyAnimation, QVariantAnimation, QEventLoop, QThread, pyqtSignal, QSize, QPoint)
from PyQt5.QtGui import (QBrush, QColor, QTextDocument, QTextCursor, QTextCharFormat, QFont, QKeyEvent, QPixmap, QTextTableFormat, QTextLength, QFontMetrics,    
                         QPainter, QOpenGLContext, QSurfaceFormat, QIcon, QWindow, QPalette, QLinearGradient, QStandardItem, QStandardItemModel, QFontDatabase)
from PyQt5.QtWidgets import (QApplication, QMainWindow, QFileDialog, QMessageBox, QListView, 
                             QTableWidgetItem, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QStyle, QSizePolicy, QDialogButtonBox, 
                             QPushButton, QListWidget, QRadioButton, QSpinBox, QWidget, QSlider, QOpenGLWidget, QStyledItemDelegate, QGraphicsOpacityEffect)
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog
from collections import OrderedDict
from fontTools.ttLib import TTFont, TTCollection
import winreg

import pyqtgraph as pg

# gTTS 모듈
from gtts import gTTS
from gtts.lang import tts_langs

# pydub 및 오디오 관련 모듈
import threading
from pydub.playback import play, _play_with_simpleaudio
from pydub import AudioSegment
import sounddevice as sd
from multiprocessing import Process
import pyaudio
import wave
import numpy as np
from io import BytesIO

#자체생성 클래스
from WaveFormopenGL import WaveformGLWidget  # 새로 만든 파일에서 클래스 가져오기
from WaveFormPyQtGraph import GraphWidget

# 생성된 UI 모듈
from MainForm import Ui_MainWindow, CustomTitleBar # Ui_MainWindow는 pyuic5로 생성된 파일의 클래스입니다.
from theme_colors import THEME_COLORS
from apply_languages import LANGUAGES
from language_code_fordate import language_locale_map

SETTINGS_FILE = "settings.json"
DEFAULT_LEARN_LANGUAGE = 'en'
DEFAULT_BASE_LANGUAGE = 'ko'
MP3_FOLDER = "mp3"

class FontPixmapCache:
    def __init__(self, max_size=100):
        self.cache = OrderedDict()
        self.max_size = max_size

    def get(self, font_name):
        if font_name in self.cache:
            self.cache.move_to_end(font_name)  # 최근 사용한 항목 앞으로
            return self.cache[font_name]
        return None

    def put(self, font_name, pixmap):
        self.cache[font_name] = pixmap
        self.cache.move_to_end(font_name)
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)  # 가장 오래된 항목 제거

    def invalidate(self):
        self.cache.clear()

class HoverEventFilter(QtCore.QObject):
    def __init__(self, on_enter, on_leave):
        super().__init__()
        self.on_enter = on_enter
        self.on_leave = on_leave

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.Enter:
            self.on_enter(obj)
        elif event.type() == QtCore.QEvent.Leave:
            self.on_leave(obj)
        return False  # 이벤트 계속 진행시킴 (True면 이벤트 멈춤)
    
class AudioGenerationThread(QThread):
    progress_signal = pyqtSignal(int)  # ✅ 진행 상태 업데이트
    finished_signal = pyqtSignal()  # ✅ 완료 신호

    def __init__(self, parent, tbWordList, create_audio_file, sanitize_filename, MP3_FOLDER, cbbLangToLearn, cbbBaseLang):
        super().__init__(parent)
        self.tbWordList = tbWordList
        self.create_audio_file = create_audio_file
        self.sanitize_filename = sanitize_filename
        self.MP3_FOLDER = MP3_FOLDER
        self.cbbLangToLearn = cbbLangToLearn
        self.cbbBaseLang = cbbBaseLang

    def run(self):
        """🎵 백그라운드에서 MP3 파일 생성"""
        row_count = self.tbWordList.rowCount()

        for row in range(row_count):
            word_item = self.tbWordList.item(row, 1)
            meaning_item = self.tbWordList.item(row, 2)

            if word_item and meaning_item:
                word = word_item.text().strip()
                meaning = meaning_item.text().strip()

                word_mp3_file = os.path.join(self.MP3_FOLDER, f"{self.sanitize_filename(word)}_{self.cbbLangToLearn.currentData()}.mp3")
                meaning_mp3_file = os.path.join(self.MP3_FOLDER, f"{self.sanitize_filename(meaning)}_{self.cbbBaseLang.currentData()}.mp3")

                # ✅ 음성 파일 생성 (백그라운드 실행)
                self.create_audio_file(word, self.cbbLangToLearn.currentData(), word_mp3_file)
                self.create_audio_file(meaning, self.cbbBaseLang.currentData(), meaning_mp3_file)

                # ✅ 진행률 업데이트
                progress = int((row + 1) / row_count * 100)
                self.progress_signal.emit(progress)

        # ✅ 완료 신호
        self.finished_signal.emit()

class FontPreviewDelegate(QStyledItemDelegate):
    def __init__(self, preview_map, render_func, theme: str = "light", parent=None):
        super().__init__(parent)
        self.preview_map = preview_map
        self.render_func = render_func
        self.theme = theme
        self.preview_cache = FontPixmapCache(max_size=100)

    def sizeHint(self, option, index):
        return QSize(150, 24)  # ✅ 높이 24px 정도로 제한

    def paint(self, painter, option, index):
        font_name = index.data()
        pixmap = self.preview_cache.get(font_name)

        if not pixmap:
            pixmap = self.render_pixmap(font_name, theme=self.theme)
            self.preview_cache.put(font_name, pixmap)

        # 상태 표시
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        elif option.state & QStyle.State_MouseOver:
            painter.fillRect(option.rect, option.palette.light())

        # 중앙 정렬 제거 → 위아래 정렬 부담 감소
        painter.drawPixmap(option.rect.left() + 5, option.rect.top() + 2, pixmap)

    def render_pixmap(self, font_name: str, height: int = 22, theme: str = "light") -> QPixmap:
        font = QFont(font_name)
        font.setPointSize(height - 6)
        current_theme = THEME_COLORS[theme]

        color = QColor(f"{current_theme['main_text']}")

        metrics = QFontMetrics(font)
        width = metrics.width(font_name) + 12
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setFont(font)
        painter.setPen(color)  # ✅ 명시적 색상
        painter.drawText(pixmap.rect(), Qt.AlignVCenter | Qt.AlignLeft, font_name)
        painter.end()

        return pixmap

    def invalidate_cache(self):
        self.preview_cache.cache.clear()

class ThemedDialog(QDialog):
    """📌 메인 스타일을 자동으로 상속받는 QDialog"""
    update_signal = pyqtSignal(str)  # ✅ 메인 스레드에 신호를 보낼 수 있음
    def __init__(self, title="제목", parent=None, theme=None):
        super().__init__(parent)

        self.theme = theme if theme else THEME_COLORS.get("기본", {})
        self.parent = parent
        self.update_signal.emit("press_minimize_button")
        self.update_signal.emit("press_maximize_button")  # ✅ 이렇게 사용 가능
        self.update_signal.emit("press_close_button")  # ✅ 이렇게 사용 가능

        # ✅ 기존 타이틀바 제거 & 모달 설정
        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)

        # ✅ 🔹 **메인 레이아웃을 직접 설정**
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(5, 5, 10, 10)

        # ✅ 🔹 커스텀 타이틀바 추가
        self.title_bar = CustomTitleBar(self, title, self.theme, "dialog")
        if hasattr(self.title_bar, "minimize_button") and self.title_bar.minimize_button is not None:
            self.parent.apply_hover_events(self.title_bar.minimize_button, self.parent.animated_hover_start, self.parent.animated_hover_end)
        if hasattr(self.title_bar, "maximize_button") and self.title_bar.maximize_button is not None:
            self.parent.apply_hover_events(self.title_bar.maximize_button, self.parent.animated_hover_start, self.parent.animated_hover_end)
        if hasattr(self.title_bar, "close_button") and self.title_bar.close_button is not None:
            self.parent.apply_hover_events(self.title_bar.close_button, self.parent.animated_hover_start, self.parent.animated_hover_end)      
        self.main_layout.addWidget(self.title_bar)

        # ✅ 🔹 콘텐츠를 감싸는 위젯 추가 (개행 효과)
        self.content_widget = QWidget(self)
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 10)  # ✅ 아래쪽 여백 추가 (개행 느낌)
        self.content_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)  # ✅ 크기 자동 조절
        self.main_layout.addWidget(self.content_widget)  # ✅ `content_widget`을 `main_layout`에 추가

        # ✅ 🔹 버튼을 추가할 레이아웃 (아래쪽 배치)
        self.button_layout = QHBoxLayout()
        self.main_layout.addLayout(self.button_layout)  # ✅ 버튼을 항상 아래쪽에 추가

        # ✅ 🔹 레이아웃을 `QDialog`에 적용
        self.setLayout(self.main_layout)

class ThemedButton(QPushButton):
    def __init__(self, text, parent=None, theme_name="basic"):
        """📌 테마가 자동 적용되는 버튼"""
        super().__init__(text, parent)
        self.theme_name = theme_name  # ✅ 테마 이름 저장
        self.apply_theme()  # ✅ 생성 시 테마 적용

    def apply_theme(self):
        """🎨 현재 테마에 맞게 버튼 스타일 적용"""
        font_family = QApplication.font().family()
        theme = THEME_COLORS.get(self.theme_name, THEME_COLORS["basic"])
        self.setStyleSheet(f"""
            QPushButton {{
                font-family: {font_family};
                background-color: {theme['button_bg']};
                color: {theme['button_text']};
                border: 0px solid;
                border-radius: 4px;
                padding: 6px 12px;
            }}
            QPushButton:hover {{
                background-color: {theme['button_hover_bg']};
            }}
            QPushButton:disabled {{
                background-color: {theme['button_disible_bg']};
            }}
        """)

    def change_theme(self, new_theme_name):
        """🌈 테마 변경 메서드"""
        self.theme_name = new_theme_name
        self.apply_theme()  # ✅ 새로운 테마 적용
        
class AnimationThread(QThread):
    update_signal = pyqtSignal(str)  # ✅ 애니메이션 색상 업데이트 신호 (QColor → CSS 색상 문자열)

    def __init__(self, widget, end_color, duration=200):
        super().__init__()
        self.widget = widget  # ✅ 애니메이션 적용 대상
        self.end_color = QColor(end_color)  # ✅ 도착 색상
        self.duration = duration
        self.steps = 10  # ✅ 애니메이션 단계
        self.interval = self.duration // self.steps
        self.running = True

        # ✅ 현재 배경색을 가져와 시작 색상으로 설정
        self.start_color = self.get_current_background_color(widget)

    def run(self):
        """ 🎬 애니메이션 실행 """
        color_delta = [
            (self.end_color.red() - self.start_color.red()) / self.steps,
            (self.end_color.green() - self.start_color.green()) / self.steps,
            (self.end_color.blue() - self.start_color.blue()) / self.steps
        ]

        for step in range(self.steps + 1):
            if not self.running:
                break  # 🚨 애니메이션 중단
            new_color = QColor(
                int(self.start_color.red() + color_delta[0] * step),
                int(self.start_color.green() + color_delta[1] * step),
                int(self.start_color.blue() + color_delta[2] * step)
            )
            self.update_signal.emit(new_color.name())  # ✅ CSS 색상 문자열 전송
            self.msleep(self.interval)  # ✅ 단계 간격 대기

    def stop(self):
        """ ⏹ 애니메이션 정지 """
        self.running = False
        self.quit()
        self.wait()

    def get_current_background_color(self, widget):
        """ 🎨 현재 버튼의 배경색 가져오기 (CSS에서 추출) """
        current_style = widget.styleSheet()
        match = re.search(r"background-color:\s*(#[0-9A-Fa-f]{6});", current_style, flags=re.IGNORECASE)
        return QColor(match.group(1)) if match else QColor("#000000")  # ✅ 기본값: 검정
    
class OpenGLContextLoader(QOpenGLWidget):
    """OpenGL 환경을 로드하고 초기화하는 클래스"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

        # ✅ OpenGL 위젯을 숨김
        self.setAttribute(Qt.WA_DontShowOnScreen)  # Qt가 화면에 표시하지 않도록 설정
        self.setFixedSize(1, 1)  # 매우 작은 크기로 설정하여 영향 최소화

    def initializeGL(self):
        """OpenGL 컨텍스트 설정 및 로드"""
        self.makeCurrent()  # ✅ 현재 OpenGL 컨텍스트 활성화

        # ✅ OpenGL 버전 및 환경 설정
        format = QSurfaceFormat()
        format.setRenderableType(QSurfaceFormat.OpenGL)
        format.setVersion(2, 0)  # OpenGL 3.3 이상 버전 사용
        format.setProfile(QSurfaceFormat.CoreProfile)
        QSurfaceFormat.setDefaultFormat(format)

        try:
            self.print_opengl_info()
        except:
            self.parent.graphicEnv = "Not openGL"
            
        print(self.parent.graphicEnv)

    def print_opengl_info(self):
        """OpenGL 정보 출력"""
        from OpenGL.GL import glGetString, GL_VERSION, GL_RENDERER, GL_VENDOR
        print(f"🔹 OpenGL Version: {glGetString(GL_VERSION).decode()}")
        print(f"🔹 Renderer: {glGetString(GL_RENDERER).decode()}")
        print(f"🔹 Vendor: {glGetString(GL_VENDOR).decode()}")
        self.parent.graphicEnv = "openGL"
        
class AudioEditor_PyQtGraph(ThemedDialog):
    def __init__(self, file_path=None, data=None, parent=None, theme_name="basic", lang="한국어"):
        self.lang_texts = LANGUAGES[lang]
        title = self.lang_texts["Custom_QDialog_label_title"]["text_audio_edit"]
        super().__init__(title, parent=parent, theme=theme_name)
        self.theme = theme_name
        print("오디오에디터_PyQtGraph 시작")
        self.audio_data = data if data else AudioSegment.from_file(file_path) # 오디오 파일 로드
        #print(f"self.audio_data: {self.audio_data}")
        self.adjusted_audio_data = self.audio_data
        self.adjusted_audio_metadata = None
        self.sample_rate = self.audio_data.frame_rate  # 샘플 레이트 저장
        self.audio_samples = None
        self.audio_metadata = None
        self.current_frame = 0  # 🎯 현재 재생 위치
        self.speedFactor = 0
        self.parent = parent

        self.init_ui()
        
    def init_ui(self):
        # 창 설정
        self.resize(800, 400)

        # 레이아웃 추가
        layout = self.layout()

        # DirectX 파형 위젯 추가
        #print("파형그리기 위한 데이터 넘기기")
        self.waveform_widget = GraphWidget(self.audio_data)
        #print("파형그리기 위한 데이터 넘기기 완료")
        layout.addWidget(self.waveform_widget)
        
        # AudioEditor_PyQtGraph __init__ 내에 핸들 생성 후에 추가:
        self.waveform_widget.start_handle.sigPositionChanged.connect(self.update_mid_bounds)
        self.waveform_widget.end_handle.sigPositionChanged.connect(self.update_mid_bounds)

        label_layout = QHBoxLayout()
        
        self.start_label = QLabel(self.lang_texts["Custom_QDialog_label_content"]["audio_editor_start"]) #QLabel(f"시작: {self.waveform_widget.start_time:.2f}s")
        self.mid_label = QLabel(self.lang_texts["Custom_QDialog_label_content"]["audio_editor_current"]) #QLabel(f"현재 위치: {self.waveform_widget.mid_time:.2f}s")
        self.end_label = QLabel(self.lang_texts["Custom_QDialog_label_content"]["audio_editor_end"]) #QLabel(f"끝: {self.waveform_widget.end_time:.2f}s")
        label_layout.addWidget(self.start_label)
        label_layout.addStretch()
        label_layout.addWidget(self.mid_label)
        label_layout.addStretch()
        label_layout.addWidget(self.end_label)
        layout.addLayout(label_layout)

        # 버튼 추가
        button_layout = QHBoxLayout()
        self.play_button = QPushButton(self.lang_texts["Custom_QDialog_buttons"]["text_play"], self)
        self.play_button.clicked.connect(self.play_audio)
        self.play_button.setToolTip(self.lang_texts["Custom_QDialog_buttons"]["text_play_t"])
        self.stop_button = QPushButton(self.lang_texts["Custom_QDialog_buttons"]["text_stop"], self)
        self.stop_button.clicked.connect(self.stop_audio)
        self.stop_button.setToolTip(self.lang_texts["Custom_QDialog_buttons"]["text_stop_t"])
        self.save_button = QPushButton(self.lang_texts["Custom_QDialog_buttons"]["text_area_save"], self)
        self.save_button.clicked.connect(self.save_audio)
        self.save_button.setToolTip(self.lang_texts["Custom_QDialog_buttons"]["text_area_save_t"])
        self.exit_button = QPushButton(self.lang_texts["Custom_QDialog_buttons"]["text_exit"], self)
        self.exit_button.clicked.connect(self.close)
        self.exit_button.setToolTip(self.lang_texts["Custom_QDialog_buttons"]["text_exit_t"])
        self.parent.apply_theme_toButtons(self.theme, self.play_button)
        self.parent.apply_theme_toButtons(self.theme, self.stop_button)
        self.parent.apply_theme_toButtons(self.theme, self.save_button)
        self.parent.apply_theme_toButtons(self.theme, self.exit_button)
        self.parent.apply_hover_events(self.play_button, self.parent.animated_hover_start, self.parent.animated_hover_end)
        self.parent.apply_hover_events(self.stop_button, self.parent.animated_hover_start, self.parent.animated_hover_end)
        self.parent.apply_hover_events(self.save_button, self.parent.animated_hover_start, self.parent.animated_hover_end)
        self.parent.apply_hover_events(self.exit_button, self.parent.animated_hover_start, self.parent.animated_hover_end)
        button_layout.addWidget(self.play_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.exit_button)
        layout.addLayout(button_layout)
        
        slider_layout = QHBoxLayout()
        self.speed_label = QLabel(self.lang_texts["Custom_QDialog_label_content"]["audio_editor_speed_control"])
        self.speed_slider = QSlider()
        self.speed_slider.setOrientation(QtCore.Qt.Horizontal)
        self.speed_slider.setRange(10, 300)
        self.speed_slider.setValue(100)  # 기본값 100 (1배)
        self.txt_speed_slider = QtWidgets.QLineEdit()
        self.txt_speed_slider.setObjectName("txt_speed_slider")
        self.txt_speed_slider.setMinimumSize(QtCore.QSize(55, 25))
        self.txt_speed_slider.setMaximumSize(QtCore.QSize(55, 25))
        self.txt_speed_slider.textChanged.connect(lambda: self.validate_numeric_input(self.txt_speed_slider))
        self.txt_speed_slider.textChanged.connect(lambda: self.update_slider_from_textbox(self.txt_speed_slider, self.speed_slider))
        self.txt_speed_slider.setText("100")
        self.speedFactor = 1
        slider_layout.addWidget(self.speed_label)
        slider_layout.addWidget(self.speed_slider)
        slider_layout.addWidget(self.txt_speed_slider)
        layout.addLayout(slider_layout)
        self.speed_slider.valueChanged.connect(self.update_speed)
        
        # QTimer 생성: 50ms 간격으로 미들 핸들의 위치를 업데이트
        self.timer = QTimer()
        self.timer.setInterval(20)
        self.timer.timeout.connect(self.update_mid_handle)
        
        # 재생 상태 관련 변수 초기화
        self.play_start_time = None      # 재생 시작 시각 (time.time() 기준)
        self.play_total_duration = None  # 재생 구간의 총 길이(초)
        self.play_start_time_sec = None  # 재생 구간 시작 시간 (초) - 전체 오디오 시간 기준
        self.play_mid_time_sec = None    # 재생 미드 핸들 (초)
        self.play_end_time_sec = None    # 재생 구간 끝 시간 (초)
        self.paused_elapsed_time = 0     # 일시정지 시 저장한 재생 경과 시간 (초)
        self.is_closing = False  # ✅ 중복 실행 방지용 플래그 추가
        
        self.get_handle_values()
        self.update_labels()
        # ✅ 부모의 스타일시트를 가져와 적용
        if self.parent:
            self.setStyleSheet(self.parent.styleSheet())

    def update_slider_from_textbox(self, text_edit, slider):
        """QLineEdit의 값이 변경될 때 슬라이드바에 적용"""
        text = text_edit.text().strip()  # QLineEdit의 텍스트를 가져옴
    
        # 입력 값이 숫자인지 확인하고 숫자인 경우 슬라이드바에 값 적용
        if text.isdigit():
            value = int(text)
            # 슬라이드바 범위 내에서만 값을 적용
            if slider.minimum() <= value <= slider.maximum():
                slider.setValue(value)
            else:
                # 값이 범위를 벗어나면 슬라이드바의 최대값 또는 최소값으로 설정
                slider.setValue(slider.maximum() if value > slider.maximum() else slider.minimum())
        
    def update_speed(self):
        """슬라이드바 값에 따라 볼륨을 업데이트하는 함수"""
        speed_value = self.speed_slider.value()  # 슬라이드바 값(0~500)을 0.0~5.0으로 변환
        speed_display = f"{speed_value:.0f}"
        #print(f"update_speed speed_value?: {speed_value}")
    
        # 텍스트 박스에 볼륨 값 표시
        self.txt_speed_slider.setText(speed_display)
    
        # 볼륨 값을 숫자로 저장 (FFmpeg에 사용할 값)
        self.speedFactor = float(speed_value / 100) # 볼륨 배율은 float로 처리해야 함
        #print(f"update_speed self.speedFactor?: {self.speedFactor}")
        
    # QTextEdit의 경우, 숫자가 아닌 입력을 실시간으로 감지하여 처리하는 방식
    def validate_numeric_input(self, text_edit, max_length=6):
        """입력된 텍스트가 숫자 또는 소숫점 형태이고 최대 글자 수를 넘지 않도록 확인하는 함수"""
        text = text_edit.text()

        # 소숫점 숫자 형식 확인: 숫자만 입력되거나, '123.45' 같은 소숫점 형식인지 확인
        if not re.fullmatch(r'\d*\.?\d*', text):  # 정규식: 숫자 0개 이상 + '.' 0~1개 + 숫자 0개 이상
            text_edit.blockSignals(True)
            text_edit.setText('')  # 잘못된 입력일 경우 초기화
            text_edit.blockSignals(False)
        elif len(text) > max_length:
            text_edit.blockSignals(True)
            text_edit.setText(text[:max_length])
            text_edit.setCursorPosition(len(text[:max_length]))
            text_edit.blockSignals(False)
        
    def closeEvent(self, event):
        close = self.close_app(event)
        if not close:
            event.ignore()
        else:
            event.accept()
    
    def close_app(self, event):
        """
        Exit 버튼을 눌렀을 때 실행되는 함수:
        - 재생 중인 오디오를 멈추고
        - 타이머를 중지한 후
        - 창을 안전하게 종료합니다.
        """
        import gc  # 가비지 컬렉션 (선택 사항)

        # 오디오 재생 중이면 중지
        sd.stop()

        # 타이머 정리
        if self.timer.isActive():
            self.timer.stop()

        # QMessageBox로 종료 확인 (선택 사항)
        QApplication.beep()
        msg_box = ThemedDialog(self.lang_texts["Custom_QDialog_label_title"]["text_exit"], self.parent, self.theme)
        label = QLabel(self.lang_texts["Custom_QDialog_label_content"]["audio_editor_done"], msg_box)
        msg_box.content_layout.setContentsMargins(15, 5, 15, 5)
        msg_box.content_layout.addWidget(label)
        ok_button = QPushButton(self.lang_texts["Custom_QDialog_buttons"]["text_exit"])
        ok_button.setProperty("result", 1)  # ✅ 반환 값 지정
        ok_button.clicked.connect(lambda: msg_box.done(1))  # "끝내기" 클릭 시 1 반환
        cancel_button = QPushButton(self.lang_texts["Custom_QDialog_buttons"]["text_cancel"])
        cancel_button.setProperty("result", 2)  # ✅ 반환 값 지정
        cancel_button.clicked.connect(lambda: msg_box.done(2))  # "취소" 클릭 시 2 반환
        self.parent.apply_theme_toButtons(self.theme, ok_button)
        self.parent.apply_theme_toButtons(self.theme, cancel_button)
        self.parent.apply_hover_events(ok_button, self.parent.animated_hover_start, self.parent.animated_hover_end)
        self.parent.apply_hover_events(cancel_button, self.parent.animated_hover_start, self.parent.animated_hover_end)
        msg_box.button_layout.addWidget(ok_button)
        msg_box.button_layout.addWidget(cancel_button)
        result = msg_box.exec_() #if문 있으면 써야

        if result == 1:
            # 리소스 정리 (선택 사항)
            del self.audio_data  # AudioSegment 제거
            del self.waveform_widget  # 그래픽 리소스 해제
            gc.collect()  # 가비지 컬렉션 실행
            
            if not self.is_closing:  # ✅ 중복 실행 방지
                self.is_closing = True
                #print("✅ 애플리케이션 종료")
                # 창 닫기
            msg_box.close()
            event.accept()
            return True
        else:
            msg_box.close()
            if event is not None:  
                msg_box.close()  # 🎯 창 닫힘 방지
            else:
                return False
            return
        
    # 기존 play_audio, pause_audio, update_mid_handle 메서드는 그대로 두고, save_audio 메서드를 추가합니다.
    def save_audio(self):
        """
        저장 버튼 클릭 시:
          - 스타트핸들과 엔드핸들의 위치에 따라 오디오 구간을 추출하고,
          - 사용자가 파일 이름과 위치를 지정할 수 있도록 QFileDialog를 띄운 후,
          - 해당 구간을 mp3 형식으로 저장합니다.
        """
        # 파일 저장 다이얼로그 열기
        filename, _ = QFileDialog.getSaveFileName(
            self, "저장", "", "MP3 Files (*.mp3)"
        )
        if not filename:
            return  # 사용자가 취소한 경우

        # 만약 파일 확장자가 없으면 .mp3를 붙여줍니다.
        if not filename.lower().endswith('.mp3'):
            filename += ".mp3"

        # 전체 오디오 길이(초)
        total_duration = self.audio_data.duration_seconds

        # 플롯의 x축 범위 (GraphWidget에서 저장된 값)
        x0, x1 = self.waveform_widget.x_range

        # 스타트핸들과 엔드핸들의 현재 위치 (x좌표)
        start_x = self.waveform_widget.start_handle.value()
        end_x = self.waveform_widget.end_handle.value()

        # x좌표를 시간(초)으로 매핑
        start_time_sec = ((start_x - x0) / (x1 - x0)) * total_duration
        end_time_sec = ((end_x - x0) / (x1 - x0)) * total_duration

        # 밀리초 단위로 변환 (pydub 슬라이싱은 밀리초 단위)
        start_ms = int(start_time_sec * 1000)
        end_ms = int(end_time_sec * 1000)

        # 오디오 구간 추출
        segment = self.audio_data[start_ms:end_ms]

        try:
            # mp3 형식으로 저장 (ffmpeg가 설치되어 있어야 함)
            segment.export(filename, format="mp3")
            QApplication.beep()
            msg_box = ThemedDialog(self.lang_texts["Custom_QDialog_label_title"]["text_save"], self, self.theme)

                            # ✅ 메시지 라벨 추가
            label = QLabel(self.lang_texts["Custom_QDialog_label_content"]["audio_editor_save_succesed"], msg_box)
            msg_box.content_layout.setContentsMargins(15, 5, 15, 5)
            msg_box.content_layout.addWidget(label)

                            # ✅ 확인 버튼 추가
            ok_button = QPushButton(self.lang_texts["Custom_QDialog_buttons"]["text_ok"])
            ok_button.setProperty("result", 1)  # ✅ 반환 값 지정
            ok_button.clicked.connect(msg_box.accept)  # ✅ 클릭하면 다이얼로그 닫힘

                            # ✅ 버튼 스타일 적용
            self.parent.apply_theme_toButtons(self.theme, ok_button)
            self.parent.apply_hover_events(ok_button, self.parent.animated_hover_start, self.parent.animated_hover_end)

                            # ✅ 버튼을 다이얼로그에 추가
            msg_box.button_layout.addWidget(ok_button)

            msg_box.exec_()

        except Exception as e:
            QApplication.beep()
            msg_box = ThemedDialog(self.lang_texts["Custom_QDialog_label_title"]["text_save"], self, self.theme)

                            # ✅ 메시지 라벨 추가
            label = QLabel(f"{self.lang_texts['Custom_QDialog_label_title']['text_save']} {str(e)}", msg_box)
            msg_box.content_layout.setContentsMargins(15, 5, 15, 5)
            msg_box.content_layout.addWidget(label)

                            # ✅ 확인 버튼 추가
            ok_button = QPushButton(self.lang_texts["Custom_QDialog_buttons"]["text_ok"])
            ok_button.setProperty("result", 1)  # ✅ 반환 값 지정
            ok_button.clicked.connect(msg_box.accept)  # ✅ 클릭하면 다이얼로그 닫힘

                            # ✅ 버튼 스타일 적용
            self.parent.apply_theme_toButtons(self.theme, ok_button)
            self.parent.apply_hover_events(ok_button, self.parent.animated_hover_start, self.parent.animated_hover_end)

                            # ✅ 버튼을 다이얼로그에 추가
            msg_box.button_layout.addWidget(ok_button)

            msg_box.exec_()
            
    def update_mid_bounds(self):
        """
        스타트핸들과 엔드핸들의 위치가 변경될 때마다 미들핸들의 이동 범위를 업데이트합니다.
        """
        start_x = self.waveform_widget.start_handle.value()
        end_x = self.waveform_widget.end_handle.value()
        self.waveform_widget.mid_handle.setBounds((start_x, end_x))
        # 만약 현재 미들핸들의 값이 범위를 벗어난 경우, 클램핑 처리
        current_mid = self.waveform_widget.mid_handle.value()
        if current_mid < start_x:
            self.waveform_widget.mid_handle.setValue(start_x)
        elif current_mid > end_x:
            self.waveform_widget.mid_handle.setValue(end_x)

    def get_audio_metadata(self, audio_segment):
        """📌 `AudioSegment` 또는 파일에서 오디오 메타데이터 추출"""
    
        metadata = {
            "frame_rate": 44100,  # 기본 샘플레이트 (Hz)
            "channels": 1,        # 기본 채널 (모노)
            "sample_width": 2,    # 기본 샘플 크기 (16-bit)
            "bit_rate": 128000    # 기본 비트레이트 (128 kbps)
        }

        if isinstance(audio_segment, AudioSegment):
            # ✅ `AudioSegment` 객체에서 직접 추출
            metadata["frame_rate"] = audio_segment.frame_rate
            metadata["channels"] = audio_segment.channels
            metadata["sample_width"] = audio_segment.sample_width
            #print(f"🎵 `AudioSegment`에서 메타데이터 추출 완료: {metadata}")

            # ✅ 비트레이트는 `AudioSegment`에서 직접 추출 불가능 → FFmpeg 사용 필요
            return metadata

        elif isinstance(audio_segment, str):  # ✅ 파일 경로인 경우 (MP3, WAV 등)
            try:
                ffprobe_cmd = [
                    "ffprobe", "-v", "error",
                    "-select_streams", "a:0",
                    "-show_entries", "stream=sample_rate,channels,bit_rate",
                    "-of", "json",
                    audio_segment
                ]
                result = subprocess.run(ffprobe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                probe_data = json.loads(result.stdout)

                if "streams" in probe_data and len(probe_data["streams"]) > 0:
                    audio_stream = probe_data["streams"][0]
                    metadata["frame_rate"] = audio_stream.get("sample_rate", metadata["frame_rate"])
                    metadata["channels"] = audio_stream.get("channels", metadata["channels"])
                    metadata["bit_rate"] = audio_stream.get("bit_rate", metadata["bit_rate"])

                #print(f"🔍 파일에서 메타데이터 추출 완료: {metadata}")

            except Exception as e:
                print(f"🚨 메타데이터 추출 중 오류 발생: {e}")

        return metadata  # ✅ 최종 메타데이터 반환
    
    def get_handle_values(self):
        total_duration = self.audio_data.duration_seconds  # 전체 오디오 길이(초)
        
        # 플롯의 x축 범위 (GraphWidget에서 저장됨; 보통 x0=0, x1은 downsampled 데이터 길이)
        x0, x1 = self.waveform_widget.x_range
        
        # 핸들의 현재 위치로 재생 구간을 결정
        start_x = self.waveform_widget.start_handle.value()
        mid_x = self.waveform_widget.mid_handle.value()
        end_x   = self.waveform_widget.end_handle.value()
        
        # x좌표 → 시간(초) 매핑:
        self.play_start_time_sec = ((start_x - x0) / (x1 - x0)) * total_duration
        self.play_mid_time_sec = ((mid_x - x0) / (x1 - x0)) * total_duration
        self.play_end_time_sec   = ((end_x - x0) / (x1 - x0)) * total_duration
        
        # 재생 구간의 총 길이 (초)
        self.play_total_duration = (self.play_end_time_sec - self.play_start_time_sec) / self.speedFactor
        #print(f"오디오 총 길이: {self.play_total_duration}")
        
    def update_labels(self):
        self.start_label.setText(f"{self.lang_texts['Custom_QDialog_label_content']['audio_editor_start']} {self.play_start_time_sec:.2f}s")
        self.mid_label.setText(f"{self.lang_texts['Custom_QDialog_label_content']['audio_editor_current']} {self.play_mid_time_sec:.2f}s")
        self.end_label.setText(f"{self.lang_texts['Custom_QDialog_label_content']['audio_editor_end']} {self.play_end_time_sec:.2f}s")

    def play_audio(self):
        """
        재생 버튼 클릭 시:
          - 스타트핸들과 엔드핸들 위치에 따라 재생 구간을 AudioSegment에서 추출
          - 일시정지한 적이 있으면 그 지점부터 재생을 재개하고, 그렇지 않으면 구간 시작부터 재생
          - sounddevice를 사용하여 오디오를 재생 (비차단 방식)
          - 재생 시작 시각을 기록하고 QTimer를 시작하여 미들핸들 위치를 업데이트함
        """
        self.get_handle_values()
        
        self.adjusted_audio_data = self.audio_data
        self.adjusted_audio_metadata = None
        self.sample_rate = self.audio_data.frame_rate  # 샘플 레이트 저장
        self.audio_samples = None
        self.audio_metadata = None

        # 만약 이전에 일시정지한 적이 있다면, 그 지점부터 재생
        resume_offset = self.paused_elapsed_time  # paused_elapsed_time는 0이면 처음부터 재생
        # 만약 재생이 이미 끝났었다면(paused_offset >= total 구간 길이), 초기화
        if resume_offset >= self.play_total_duration:
            resume_offset = 0
            self.paused_elapsed_time = 0
            # 미들핸들을 스타트핸들 위치로 복원
            self.waveform_widget.mid_handle.setValue(self.waveform_widget.start_handle.value())
        
        # pydub은 밀리초 단위로 슬라이싱하므로, 초를 밀리초로 변환
        start_ms = int((self.play_start_time_sec + resume_offset) * 1000)
        end_ms   = int(self.play_end_time_sec * 1000)
        playback_segment = self.audio_data[start_ms:end_ms]

        # ✅ `AudioSegment`를 WAV 바이트 스트림으로 변환
        audio_io = io.BytesIO()
        playback_segment.export(audio_io, format="wav")  # 🔥 WAV 변환
        audio_io.seek(0)  # 🔥 포인터를 처음으로 이동
    
        metadata = self.get_audio_metadata(self.audio_data)
        
        # 샘플레이트, 채널, 비트레이트를 가져옴
        sample_rate = metadata.get('sample_rate', 44100)  # 기본값 44100 Hz
        channels = metadata.get('channels', 1)          # 기본 채널 수
        bit_rate = metadata.get('bit_rate', 128000)       # 기본 비트레이트 128 kbps
        current_pitch = 1
        
        # ✅ ffmpeg 필터 설정 (속도, 피치 적용)
        filters = f"asetrate={float(sample_rate)}*{current_pitch},atempo={self.speedFactor}"
        speed_factor = self.speedFactor 

        # 🧠 속도 필터 구성
        speed_factor = self.build_atempo_filters(speed_factor)
        # 🧠 리스트일 경우 각각 atempo= 붙여주기
        if isinstance(speed_factor, list):
            atempo_filters = ",".join([f"atempo={val}" for val in speed_factor])
        else:
            atempo_filters = f"atempo={speed_factor}"

        filter_chain = f"volume=1.0,{atempo_filters}"
    
        command = [
            "ffmpeg",
            "-i", "pipe:0",  # ✅ 🔥 `AudioSegment`를 직접 입력받기 위해 `pipe:0` 사용
            "-filter:a", filter_chain,
            "-f", "s16le",
            "-acodec", "pcm_s16le",  # PCM 데이터 변환
            "-ac", str(channels),  # 채널 설정
            "-ar", str(sample_rate),  # 샘플레이트 설정
            "-b:a", str(bit_rate),  # 비트레이트 설정
            "-y", "pipe:1"  # ✅ 🔥 `pipe:1`을 사용하여 출력 데이터를 받음
        ]
        '''        
        # playback_segment를 NumPy 배열로 변환
        data = np.array(playback_segment.get_array_of_samples())
        if playback_segment.channels > 1:
            data = data.reshape((-1, playback_segment.channels))
        
        # sounddevice를 사용하여 오디오 재생 (비차단 방식)
        sd.play(data, samplerate=playback_segment.frame_rate)
        '''        

        # FFmpeg 프로세스를 실행하여 변환된 오디오 데이터를 파이프로 받아옴
        proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            # ✅ WAV 데이터를 FFmpeg에 전달하고 변환된 오디오를 받음
            output_audio, _ = proc.communicate(input=audio_io.read())
        
            # ✅ NumPy 배열로 변환하여 sounddevice로 재생
            audio_array = np.frombuffer(output_audio, dtype=np.int16)
            sd.play(audio_array, samplerate=float(sample_rate))

        except BrokenPipeError:
            print("🚨 FFmpeg 파이프 오류 발생!")

        # 재생 시작 시각 갱신: 만약 재개하는 경우, 보정하여 기록
        self.play_start_time = time.time() - resume_offset
        # 타이머 시작: 재생 위치 업데이트를 위해
        self.timer.start()
        # 일시정지 상태 초기화
        self.paused_elapsed_time = 0

    def build_atempo_filters(self, rate):
        filters = []
        while rate < 0.5 and len(filters) < 5:  # 최대 5개까지만 반복
            filters.append("0.5")
            rate *= 2
        filters.append(f"{rate:.6f}")
        return filters
        
    def stop_audio(self):
        """
        Pause 버튼 클릭 시:
          - 현재 재생 중인 오디오를 정지 (sounddevice stop)
          - QTimer를 멈추고, 현재 재생 경과 시간을 저장하여 나중에 재개 시 사용
          - 미들핸들의 위치는 그대로 유지됨
        """
        sd.stop()
        self.timer.stop()
        if self.play_start_time is not None:
            elapsed = time.time() - self.play_start_time
            self.paused_elapsed_time = elapsed
            # 만약 재생 구간의 총 길이를 넘겼다면(즉, 재생이 끝났다면),
            # 미들핸들을 스타트핸들 위치로 복원
            if self.paused_elapsed_time >= self.play_total_duration:
                self.paused_elapsed_time = 0
                x0, x1 = self.waveform_widget.x_range
                self.waveform_widget.mid_handle.setValue(self.waveform_widget.start_handle.value())
                
    def update_mid_handle(self):
        """
        QTimer 타이머 콜백:
          - 재생 경과 시간에 따라 미들핸들의 x좌표를 업데이트함.
          - 계산된 위치를 스타트핸들과 엔드핸들 사이로 클램핑(clamp) 처리함.
        """
        elapsed = time.time() - self.play_start_time
        if elapsed >= self.play_total_duration:
            self.timer.stop()
            self.waveform_widget.mid_handle.setValue(self.waveform_widget.end_handle.value())
            return

        # 재생 구간 내 비율 계산
        proportion = elapsed / self.play_total_duration

        # 스타트핸들과 엔드핸들의 현재 x좌표
        start_x = self.waveform_widget.start_handle.value()
        end_x = self.waveform_widget.end_handle.value()
        # 계산된 미들핸들 위치
        new_x = start_x + proportion * (end_x - start_x)
        # 클램핑: new_x가 start_x보다 작거나 end_x보다 크지 않도록 제한
        new_x = max(min(new_x, end_x), start_x)
        self.waveform_widget.mid_handle.setValue(new_x)
        self.get_handle_values()
        self.update_labels()
    
class AudioEditor_openGL(ThemedDialog):
    update_signal = pyqtSignal(str)  # ✅ 여기에 직접 정의!
    def __init__(self, file_path=None, data=None, parent=None, theme_name="basic", lang="한국어"):
        self.lang_texts = LANGUAGES[lang]
        title = self.lang_texts["Custom_QDialog_label_title"]["text_audio_edit"]
        super().__init__(title, parent=parent, theme=theme_name)
        self.theme = theme_name
        self.audio_data = data if data else AudioSegment.from_file(file_path) # 오디오 파일 로드
        self.adjusted_audio_data = self.audio_data
        self.adjusted_audio_metadata = None
        self.sample_rate = self.audio_data.frame_rate  # 샘플 레이트 저장
        #print(f"초기 샘플레이트?: {self.sample_rate}")
        self.audio_samples = None
        self.audio_metadata = None
        self.current_frame = 0  # 🎯 현재 재생 위치
        self.speedFactor = 0
        self.is_playing = False
        self.parent = parent
        
        self.init_ui()

    def init_ui(self):
        self.resize(850, 500)
        self.parent.update_signal.connect(self.update_signal.emit)  # ThemedDialog의 시그널을 위로 전달

        # 레이아웃 설정
        layout = self.layout()

        # WaveformGLWidget 추가
        self.waveform_widget = WaveformGLWidget(self.audio_data, self)
        layout.addWidget(self.waveform_widget, stretch=1)

        # 라벨 추가
        label_layout = QHBoxLayout()
        
        self.start_label = QLabel(f"{self.lang_texts['Custom_QDialog_label_content']['audio_editor_start']} {self.waveform_widget.start_time:.2f}s")
        self.mid_label = QLabel(f"{self.lang_texts['Custom_QDialog_label_content']['audio_editor_current']} {self.waveform_widget.mid_time:.2f}s")
        self.end_label = QLabel(f"{self.lang_texts['Custom_QDialog_label_content']['audio_editor_end']} {self.waveform_widget.end_time:.2f}s")
        label_layout.addWidget(self.start_label)
        label_layout.addStretch()
        label_layout.addWidget(self.mid_label)
        label_layout.addStretch()
        label_layout.addWidget(self.end_label)
        layout.addLayout(label_layout)

        # 버튼 추가
        button_layout = QHBoxLayout()
        self.play_button = ThemedButton(self.lang_texts["Custom_QDialog_buttons"]["text_play"], self, self.theme)
        self.play_button.clicked.connect(self.play_audio)
        self.play_button.setToolTip(self.lang_texts["Custom_QDialog_buttons"]["text_play_t"])
        self.stop_button = ThemedButton(self.lang_texts["Custom_QDialog_buttons"]["text_stop"], self, self.theme)
        self.stop_button.clicked.connect(lambda: self.stop_audio(True))
        self.stop_button.setToolTip(self.lang_texts["Custom_QDialog_buttons"]["text_stop_t"])
        self.save_button = ThemedButton(self.lang_texts["Custom_QDialog_buttons"]["text_area_save"], self, self.theme)
        self.save_button.clicked.connect(self.save_selected_audio)
        self.save_button.setToolTip(self.lang_texts["Custom_QDialog_buttons"]["text_area_save_t"])
        self.exit_button = ThemedButton(self.lang_texts["Custom_QDialog_buttons"]["text_exit"], self, self.theme)
        self.exit_button.clicked.connect(self.close)
        self.exit_button.setToolTip(self.lang_texts["Custom_QDialog_buttons"]["text_exit_t"])
        self.parent.apply_hover_events(self.play_button, self.parent.animated_hover_start, self.parent.animated_hover_end)
        self.parent.apply_hover_events(self.stop_button, self.parent.animated_hover_start, self.parent.animated_hover_end)
        self.parent.apply_hover_events(self.save_button, self.parent.animated_hover_start, self.parent.animated_hover_end)
        self.parent.apply_hover_events(self.exit_button, self.parent.animated_hover_start, self.parent.animated_hover_end)
        button_layout.addWidget(self.play_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.exit_button)
        layout.addLayout(button_layout)
        
        slider_layout = QHBoxLayout()
        self.speed_label = QLabel(self.lang_texts["Custom_QDialog_label_content"]["audio_editor_speed_control"])
        self.speed_slider = QSlider()
        self.speed_slider.setOrientation(QtCore.Qt.Horizontal)
        self.speed_slider.setRange(10, 300)
        self.speed_slider.setValue(100)  # 기본값 100 (1배)
        self.txt_speed_slider = QtWidgets.QLineEdit()
        self.txt_speed_slider.setObjectName("txt_speed_slider")
        self.txt_speed_slider.setMinimumSize(QtCore.QSize(55, 25))
        self.txt_speed_slider.setMaximumSize(QtCore.QSize(55, 25))
        self.txt_speed_slider.textChanged.connect(lambda: self.validate_numeric_input(self.txt_speed_slider))
        self.txt_speed_slider.textChanged.connect(lambda: self.update_slider_from_textbox(self.txt_speed_slider, self.speed_slider))
        self.txt_speed_slider.setText("100")
        self.speedFactor = 1
        slider_layout.addWidget(self.speed_label)
        slider_layout.addWidget(self.speed_slider)
        slider_layout.addWidget(self.txt_speed_slider)
        layout.addLayout(slider_layout)
        self.speed_slider.valueChanged.connect(self.update_speed)
        
        self.update_labels()

        self.start_real_time = None
        self.mid_handle_timer = QTimer(self.parent)
        self.mid_handle_timer.timeout.connect(lambda: self.update_mid_handle())
        self.elapsed_audio_time = 0.0  # 오디오 재생 경과 시간 (초 단위)
        self.timer_interval = None  # 타이머 간격 (초 단위, 16ms → 0.016s)
        self.zero_to_start_handle = 0
        self.playback_finished = True  # 🛑 재생이 끝난 경우
        self.last_time = None
        self.is_closing = False  # ✅ 중복 실행 방지용 플래그 추가
        
        total_frames = int(self.get_audio_duration() * self.sample_rate)
        self.standard_start_sample = self.gpu_to_frames(-1, total_frames)
        self.standard_end_sample = self.gpu_to_frames(1, total_frames)
        self.audio_metadata = self.extract_audio_metadata(self.audio_data)
        
        # ✅ 부모의 스타일시트를 가져와 적용
        if self.parent:
            self.setStyleSheet(self.parent.styleSheet())
            
    def update_slider_from_textbox(self, text_edit, slider):
        """QLineEdit의 값이 변경될 때 슬라이드바에 적용"""
        text = text_edit.text().strip()  # QLineEdit의 텍스트를 가져옴
    
        # 입력 값이 숫자인지 확인하고 숫자인 경우 슬라이드바에 값 적용
        if text.isdigit():
            value = int(text)
            # 슬라이드바 범위 내에서만 값을 적용
            if slider.minimum() <= value <= slider.maximum():
                slider.setValue(value)
            else:
                # 값이 범위를 벗어나면 슬라이드바의 최대값 또는 최소값으로 설정
                slider.setValue(slider.maximum() if value > slider.maximum() else slider.minimum())
        
    def update_speed(self):
        """슬라이드바 값에 따라 볼륨을 업데이트하는 함수"""
        speed_value = self.speed_slider.value()  # 슬라이드바 값(0~500)을 0.0~5.0으로 변환
        speed_display = f"{speed_value:.0f}"
        #print(f"update_speed speed_value?: {speed_value}")
    
        # 텍스트 박스에 볼륨 값 표시
        self.txt_speed_slider.setText(speed_display)
    
        # 볼륨 값을 숫자로 저장 (FFmpeg에 사용할 값)
        self.speedFactor = float(speed_value / 100) # 볼륨 배율은 float로 처리해야 함
        #print(f"update_speed self.speedFactor?: {self.speedFactor}")
        
    # QTextEdit의 경우, 숫자가 아닌 입력을 실시간으로 감지하여 처리하는 방식
    def validate_numeric_input(self, text_edit, max_length=6):
        """입력된 텍스트가 숫자 또는 소숫점 형태이고 최대 글자 수를 넘지 않도록 확인하는 함수"""
        text = text_edit.text()

        # 소숫점 숫자 형식 확인: 숫자만 입력되거나, '123.45' 같은 소숫점 형식인지 확인
        if not re.fullmatch(r'\d*\.?\d*', text):  # 정규식: 숫자 0개 이상 + '.' 0~1개 + 숫자 0개 이상
            text_edit.blockSignals(True)
            text_edit.setText('')  # 잘못된 입력일 경우 초기화
            text_edit.blockSignals(False)
        elif len(text) > max_length:
            text_edit.blockSignals(True)
            text_edit.setText(text[:max_length])
            text_edit.setCursorPosition(len(text[:max_length]))
            text_edit.blockSignals(False)
        
    def update_mid_handle(self):
        """ 🎯 미드핸들 위치 업데이트 (실시간 오디오 진행 반영) """
        self.waveform_widget.update()
        self.update_labels()
        
    def save_selected_audio(self):
        """ 🎵 선택된 범위 (스타트핸들 ~ 엔드핸들)만 저장 """
        if self.audio_data is None:
            return  # 🚨 오디오 데이터가 없으면 종료

        # ✅ 먼저 기본 시스템 다이얼로그 시도
        filepath, _ = QFileDialog.getSaveFileName(self, "Save Selected Audio",
                                                  filter="MP3 files (*.mp3);;WAV files (*.wav)")

        if not filepath:  
            return  # ✅ 취소되면 그대로 종료 (두 번째 다이얼로그 호출 X)

        total_frames = self.get_total_frames()

        # ✅ GPU 좌표를 샘플 프레임 단위로 변환
        start_sample = self.gpu_to_frames(self.waveform_widget.start_time, total_frames)
        end_sample = self.gpu_to_frames(self.waveform_widget.end_time, total_frames)

        if start_sample >= end_sample:
            return  # 🚨 잘못된 범위일 경우 종료

        # ✅ NumPy 배열 변환 후 선택한 범위만 추출
        samples = np.array(self.audio_data.get_array_of_samples())
        selected_samples = samples[start_sample:end_sample]

        # ✅ 선택한 데이터를 AudioSegment로 변환
        selected_audio = AudioSegment(
            selected_samples.tobytes(), frame_rate=self.audio_data.frame_rate,
            sample_width=self.audio_data.sample_width, channels=self.audio_data.channels
        )

        # ✅ 임시 WAV 파일로 저장
        temp_wave_filename = "temp.wav"
        selected_audio.export(temp_wave_filename, format="wav")

        # ✅ MP3 변환
        if filepath.endswith('.mp3'):
            command = [
                'ffmpeg',
                '-y',
                '-i', temp_wave_filename,  # 임시 WAV 파일 입력
                '-vn',  # 비디오 스트림 없음
                '-ar', str(self.audio_data.frame_rate),  # 샘플 레이트 설정
                '-ac', str(self.audio_data.channels),  # 오디오 채널 설정
                '-b:a', '192k',  # 오디오 비트레이트 설정
                filepath
            ]
            subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
            os.remove(temp_wave_filename)  # ✅ 변환 후 임시 파일 삭제
        else:
            os.rename(temp_wave_filename, filepath)  # ✅ WAV 파일 저장
        
    def process_audio_with_ffmpeg(self, audio_source, metadata):
        """📌 오디오 데이터를 FFmpeg으로 변환 후 원래 메타데이터 적용"""

        #print(f"process_audio_with_ffmpeg audio_source?~? {audio_source}")

        # ✅ `AudioSegment`를 WAV 바이트 스트림으로 변환
        audio_io = io.BytesIO()
        if isinstance(audio_source, AudioSegment):
            audio_source.export(audio_io, format="wav")  # 🔥 WAV로 변환
        else:
            with open(audio_source, "rb") as f:
                audio_io.write(f.read())  # 🔥 파일을 읽어서 바이너리로 변환
        audio_io.seek(0)  # 🔥 스트림 포인터를 처음으로 이동

        # ✅ 랜덤 또는 설정된 피치 & 속도 조절 값 가져오기
        pitch_factor = 55 / 100  # ✅ 피치 설정 값 (예: 1.2)
        speed_factor = self.speedFactor  # ✅ 속도 설정 값 (예: 0.8)

        # ✅ 샘플레이트 기반 asetrate 조정
        original_sample_rate = metadata["frame_rate"]
        adjusted_sample_rate = int(original_sample_rate * 1.8375 * pitch_factor)  # ✅ 🔥 정수 변환
        final_sample_rate = int(adjusted_sample_rate * speed_factor)  # ✅ 🔥 최종 샘플레이트 적용
        bit_rate = metadata.get("bit_rate", "192k")

        #print(f"process_audio_with_ffmpeg 최종샘플레이트?:?: {final_sample_rate}")

        # 🧠 속도 필터 구성
        speed_factor = self.build_atempo_filters(speed_factor)
        # 🧠 리스트일 경우 각각 atempo= 붙여주기
        if isinstance(speed_factor, list):
            atempo_filters = ",".join([f"atempo={val}" for val in speed_factor])
        else:
            atempo_filters = f"atempo={speed_factor}"

        filter_chain = f"asetrate={adjusted_sample_rate},{atempo_filters}"

        # 🛠️ 최종 명령
        ffmpeg_process = subprocess.Popen(
            [
                "ffmpeg", "-i", "pipe:0",
                "-filter:a", filter_chain,
                "-ac", str(metadata["channels"]),
                "-ar", str(final_sample_rate),
                "-acodec", "pcm_s16le",
                "-b:a", str(bit_rate),
                "-f", "wav", "pipe:1"
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )

        #print("✅ FFmpeg 프로세스 실행됨")

        # ✅ FFmpeg에 데이터를 전달하고 변환된 오디오를 받음
        try:
            output_audio, _ = ffmpeg_process.communicate(input=audio_io.read())  # 🔥 FFmpeg이 데이터 읽고 종료되도록 함
            #print("✅ FFmpeg 변환 완료")
            processed_audio = AudioSegment.from_file(io.BytesIO(output_audio), format="wav")
            #print(f"processed_audio 설정완료***: {processed_audio}")

            # ✅ 🔥 속도 빠를 때 배열 범위 초과 오류 방지 (배열 크기 조정)
            processed_samples = np.array(processed_audio.get_array_of_samples(), dtype=np.float32)
            original_length = len(processed_samples)
            expected_length = int(original_length / self.speedFactor)  # ✅ 예상 크기 조정
            if expected_length < original_length:
                processed_samples = np.pad(processed_samples, (0, original_length - expected_length), mode='constant')

        except BrokenPipeError:
            print("🚨 FFmpeg 파이프 오류 발생!")

        #print(f"processed_audio 반환!!??: {processed_audio}")
        return processed_audio  # ✅ 변환된 `AudioSegment` 반환

    def build_atempo_filters(self, rate):
        filters = []
        while rate < 0.5 and len(filters) < 5:  # 최대 5개까지만 반복
            filters.append("0.5")
            rate *= 2
        filters.append(f"{rate:.6f}")
        return filters

    def play_audio(self):
        """오디오 재생"""
        if self.is_playing:
            return  # 이미 재생 중이면 실행하지 않음
        
        self.adjusted_audio_data = self.audio_data
        self.adjusted_audio_metadata = None
        self.sample_rate = self.audio_data.frame_rate  # 샘플 레이트 저장
        self.audio_samples = None
        self.audio_metadata = None
        self.audio_metadata = self.extract_audio_metadata(self.audio_data)
        
        # ✅ 🔥 기존 스트림이 존재하면 먼저 정리
        if hasattr(self, 'stream') and self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception as e:
                print(f"🚨 스트림 종료 중 오류 발생: {e}")
            finally:
                self.stream = None  # ✅ 🔥 스트림 객체 초기화
            
        self.is_playing = True
        self.adjusted_audio_data = self.process_audio_with_ffmpeg(self.audio_data, self.audio_metadata)
        #print(f"play_audio self.sample_rate? ::: {self.sample_rate}")
        self.adjusted_audio_metadata = self.extract_audio_metadata(self.adjusted_audio_data)
        self.sample_rate = self.adjusted_audio_data.frame_rate # 샘플 레이트 저장
        #print(f"조정된 샘플레이트>??> {self.sample_rate}")
        
        total_frames = int(self.get_audio_duration() * self.sample_rate)

        # OpenGL 좌표를 직접 프레임으로 변환
        self.start_sample = self.gpu_to_frames(self.waveform_widget.start_time, total_frames)
        self.end_sample = self.gpu_to_frames(self.waveform_widget.end_time, total_frames)

        # 🎯 재생 위치 초기화
        # ✅ 기존 재생 위치 유지 (일시 정지 후 재개)
        if self.playback_finished:
            #print("🔄 재생이 끝나서 처음부터 다시 시작")
            self.current_frame = self.start_sample  # 🎯 처음부터 재생
            self.playback_finished = False  # 🔄 다시 정상 재생 모드로 변경
        
        #print(f"🎵 재생 시작: {self.start_sample} ~ {self.end_sample} 프레임")
        
        self.stream = sd.OutputStream(
            samplerate=self.sample_rate,
            channels=self.adjusted_audio_metadata["channels"],
            callback=self.callback
        )
        self.stream.start()  # 🎯 스트림 시작
        #print(f"🧵 타이머 실행 스레드: {threading.current_thread().name}")  # 스레드 정보 출력
        self.mid_handle_timer.start(16)
        #print("🎵 재생 시작됨")

    def callback(self, outdata, frames, callback_time, status):
        """ 🎵 사운드디바이스 콜백 함수 (비동기 재생) """
        if status:
            print(status)  # 🚨 에러 메시지 출력
    
        if not self.is_playing:
            outdata[:] = np.zeros_like(outdata)  # 🎯 정지 상태일 때는 무음 출력
            return

        # ✅ 변환이 한 번만 이루어지도록 처리
        if self.audio_samples is None:
            if isinstance(self.adjusted_audio_data, AudioSegment):
                #print("🔄 AudioSegment → NumPy 변환 수행")  # 🎯 변환 여부 디버깅
                samples = np.array(self.adjusted_audio_data.get_array_of_samples(), dtype=np.float32)
                samples /= np.iinfo(np.int16).max  # 🎯 정규화 (16-bit PCM 기준)
                self.audio_samples = samples  # 🎯 NumPy 변환 후 저장
            else:
                self.audio_samples = self.adjusted_audio_data  # 이미 NumPy 데이터일 경우

        # ✅ 현재 프레임 범위 계산
        start_idx = self.start_sample
        end_idx = self.end_sample
        current_idx = self.current_frame
        #blocksize = self.get_dynamic_blocksize(current_idx, end_idx, blocksize_default=frames)
        next_frame = min(self.current_frame + frames, self.end_sample)  # 🎯 동적으로 결정된 블록 크기 적용
        remaining_frames = self.end_sample - current_idx  # 🎯 남은 프레임 수 계산
        #print(f"시작위치: {start_idx}, 끝위치: {end_idx}, 현재위치: {current_idx}, 블록크기: {blocksize}")

        #print(f"현재샘플: {current_idx}, 마지막샘플: {end_idx}")
    
        # ✅ 채널 확인 후 데이터 맞추기 (모노 or 스테레오)
        if self.audio_samples.ndim == 1:  # 🔥 모노 오디오
            outdata[:next_frame - current_idx, 0] = self.audio_samples[current_idx:next_frame]
        else:  # 🔥 스테레오 오디오
            outdata[:next_frame - current_idx] = self.audio_samples[current_idx:next_frame]

        # 🎯 미드핸들 업데이트 (UI 반영)
        gpu_x_position = self.frame_to_gpu_x(self.current_frame, self.standard_end_sample - self.standard_start_sample)
        self.waveform_widget.mid_time = gpu_x_position

        # ✅ 종료 핸들(end_handle) 도달하면 재생 종료
        if remaining_frames < frames:  # 🎯 마지막 블록이 남은 프레임보다 클 경우
            #print(f"🛑 종료 예정: 남은 프레임 {remaining_frames}, 블록 크기 {frames}")
            self.current_frame = self.end_sample  # ✅ 재생 위치를 정확히 끝으로 설정
            from functools import partial
            QTimer.singleShot(0, partial(self.stop_audio, False))  # ✅ self 전달 문제 해결
            return
        else:
            self.current_frame = next_frame # 🎯 재생 위치 업데이트

    def extract_audio_metadata(self, audio_segment):
        """📌 `AudioSegment` 또는 파일에서 오디오 메타데이터 추출"""
    
        metadata = {
            "frame_rate": 44100,  # 기본 샘플레이트 (Hz)
            "channels": 1,        # 기본 채널 (모노)
            "sample_width": 2,    # 기본 샘플 크기 (16-bit)
            "bit_rate": 128000    # 기본 비트레이트 (128 kbps)
        }

        if isinstance(audio_segment, AudioSegment):
            # ✅ `AudioSegment` 객체에서 직접 추출
            metadata["frame_rate"] = audio_segment.frame_rate
            metadata["channels"] = audio_segment.channels
            metadata["sample_width"] = audio_segment.sample_width
            #print(f"🎵 `AudioSegment`에서 메타데이터 추출 완료: {metadata}")

            # ✅ 비트레이트는 `AudioSegment`에서 직접 추출 불가능 → FFmpeg 사용 필요
            return metadata

        elif isinstance(audio_segment, str):  # ✅ 파일 경로인 경우 (MP3, WAV 등)
            try:
                ffprobe_cmd = [
                    "ffprobe", "-v", "error",
                    "-select_streams", "a:0",
                    "-show_entries", "stream=sample_rate,channels,bit_rate",
                    "-of", "json",
                    audio_segment
                ]
                result = subprocess.run(ffprobe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                probe_data = json.loads(result.stdout)

                if "streams" in probe_data and len(probe_data["streams"]) > 0:
                    audio_stream = probe_data["streams"][0]
                    metadata["frame_rate"] = audio_stream.get("sample_rate", metadata["frame_rate"])
                    metadata["channels"] = audio_stream.get("channels", metadata["channels"])
                    metadata["bit_rate"] = audio_stream.get("bit_rate", metadata["bit_rate"])

                #print(f"🔍 파일에서 메타데이터 추출 완료: {metadata}")

            except Exception as e:
                print(f"🚨 메타데이터 추출 중 오류 발생: {e}")

        return metadata  # ✅ 최종 메타데이터 반환

    @pyqtSlot()
    def mid_handle_timer_stop(self):
        self.mid_handle_timer.stop()

    def stop_audio(self, user_stop=True):
        """ 🎯 오디오 정지 (사용자 정지 or 자동 종료 구분) """
        if not self.is_playing:
            #print("이미 멈춰있으면 실행 안 함")
            return  # 이미 멈춰있으면 실행 안 함

        self.is_playing = False  # ✅ 재생 상태 변경
        #print("self.is_playing")
        
        import threading
        #print(f"🧵 타이머 정지 시도 스레드: {threading.current_thread().name}")  # 🔍 스레드 확인

        # ✅ 현재 스레드가 메인 스레드인지 확인 후 타이머 중지
        if threading.current_thread().name == "MainThread":
            self.mid_handle_timer.stop()
            #print("이미 메인쓰레드에 있으므로 정지함")
        else:
            #print("🚨 타이머 정지를 메인 스레드에서 실행하도록 예약")
            QTimer.singleShot(16, lambda: QMetaObject.invokeMethod(self, "mid_handle_timer_stop", Qt.QueuedConnection))
        
        if user_stop:  # 🎯 사용자가 정지 버튼을 눌렀다면
            self.playback_finished = False
            #print("유저 일시정지")
            self.stream.stop()
            #print("일시정지")
        else:  # 🎯 오디오가 끝나서 자동 정지되었다면
            self.playback_finished = True  # 🛑 재생이 끝난 경우    
            #print("끝에 도달해서 정지")
            self.stream.stop()
            #print("스트림 일시정지")
            self.current_frame = self.start_sample  # ⬅ 처음으로 되돌리기
            #print("현재프레임 초기화")
            self.waveform_widget.mid_time = self.waveform_widget.start_time  # ⬅ 미드핸들 초기화
            #print("미들핸들 초기화")
            self.waveform_widget.update()
            #print("🛑 재생 완료, 스트림 종료됨")

    def gpu_to_frames(self, gpu_x, total_frames):
        """ 🎯 OpenGL 좌표(-1 ~ 1)를 정수형 샘플 프레임으로 변환 """
        if total_frames <= 0:
            #print("🚨 유효하지 않은 total_frames 값:", total_frames)
            return 0  # 🚨 잘못된 변환 방지

        frame = round(((gpu_x + 1) / 2) * total_frames)  # 🎯 반올림하여 정수 값 반환
        frame = max(0, min(frame, total_frames - 1))  # ✅ 0 ~ total_frames-1 범위 보장
        #print(f"🎯 변환된 프레임: {frame} (총 프레임: {total_frames})")
        return frame

    def frame_to_gpu_x(self, frame, total_frames):
        """ 🎯 현재 프레임을 OpenGL 좌표(-1 ~ 1)로 변환 (전체 프레임 기준) """
        if total_frames == 0:
            return -1.0  # 🚨 프레임이 없으면 -1로 설정 (오류 방지)

        gpu_x = (frame / total_frames) * 2.0 - 1.0
        #print(f"전달받은 프레임: {frame}, 총 프레임: {total_frames}, 반환값: {gpu_x}")

        return gpu_x

    def update_labels(self, event=None):
        """ 🎯 핸들 위치에 따라 라벨 업데이트 """
        audio_duration = self.get_audio_duration()
        # 좌표 변환 (-1 ~ 1 범위를 0 ~ audio_duration 으로 변환)
        start_sec = ((self.waveform_widget.start_time + 1.0) / 2.0) * audio_duration
        mid_sec = ((self.waveform_widget.mid_time + 1.0) / 2.0) * audio_duration
        end_sec = ((self.waveform_widget.end_time + 1.0) / 2.0) * audio_duration
        
        # 🔹 소수점 2자리까지 표시
        self.start_label.setText(f"{self.lang_texts['Custom_QDialog_label_content']['audio_editor_start']} {start_sec:.2f}s")
        self.mid_label.setText(f"{self.lang_texts['Custom_QDialog_label_content']['audio_editor_current']} {mid_sec:.2f}s")
        self.end_label.setText(f"{self.lang_texts['Custom_QDialog_label_content']['audio_editor_end']} {end_sec:.2f}s")
        
    def get_audio_duration(self):
        """ 🎯 정확한 오디오 길이 반환 (초) """
        if isinstance(self.adjusted_audio_data, AudioSegment):
            duration_sec = self.adjusted_audio_data.duration_seconds  # ✅ `pydub` 기본 제공 메서드 사용
        else:
            num_samples = self.adjusted_audio_data.shape[0]  # ✅ NumPy 배열 길이 가져오기
            num_channels = 1  # 기본 모노 설정 (오디오 채널 확인 필요)
            if len(self.adjusted_audio_data.shape) > 1:  # 🔹 스테레오(2채널) 여부 확인
                num_channels = self.adjusted_audio_data.shape[1]
        
            duration_sec = num_samples / (self.sample_rate * num_channels)  # ✅ 샘플 개수 → 시간 변환
        #print(f"오디오 길이?: duration_sec ::: {duration_sec}")
        return duration_sec

    def get_total_frames(self):
        """ 🎵 오디오 길이 (샘플 단위) 반환 """
        total_samples = len(self.adjusted_audio_data.get_array_of_samples())  # ✅ 샘플 개수 가져오기
        #print(f"🔢 총 샘플 수: {total_samples}")
        return int(total_samples)  # ✅ 정수형으로 변환
    
    def closeEvent(self, event):
        close = self.close_app(event)
        if not close:
            event.ignore()
        else:
            event.accept()

    def close_app(self, event):
        """ 🛑 AudioEditor 닫힐 때 모든 자원 정리 """
        #print("🛑 AudioEditor 닫힘 → 자원 해제 시작")
        QApplication.beep()
        msg_box = ThemedDialog(self.lang_texts["Custom_QDialog_label_title"]["text_exit"], self.parent, self.theme)
        label = QLabel(self.lang_texts["Custom_QDialog_label_content"]["audio_editor_done"], msg_box)
        msg_box.content_layout.setContentsMargins(15, 5, 15, 5)
        msg_box.content_layout.addWidget(label)
        ok_button = QPushButton(self.lang_texts["Custom_QDialog_buttons"]["text_exit"])
        ok_button.setProperty("result", 1)  # ✅ 반환 값 지정
        ok_button.clicked.connect(lambda: msg_box.done(1))  # "끝내기" 클릭 시 1 반환
        cancel_button = QPushButton(self.lang_texts["Custom_QDialog_buttons"]["text_cancel"])
        cancel_button.setProperty("result", 2)  # ✅ 반환 값 지정
        cancel_button.clicked.connect(lambda: msg_box.done(2))  # "취소" 클릭 시 2 반환
        self.parent.apply_theme_toButtons(self.theme, ok_button)
        self.parent.apply_theme_toButtons(self.theme, cancel_button)
        self.parent.apply_hover_events(ok_button, self.parent.animated_hover_start, self.parent.animated_hover_end)
        self.parent.apply_hover_events(cancel_button, self.parent.animated_hover_start, self.parent.animated_hover_end)
        msg_box.button_layout.addWidget(ok_button)
        msg_box.button_layout.addWidget(cancel_button)
        result = msg_box.exec_() #if문 있으면 써야

        if result == 1:
                    # ✅ 백그라운드 스레드 종료
            if hasattr(self, "thread") and isinstance(self.thread, QThread):
                if self.thread.isRunning():
                            #print("🛑 백그라운드 스레드 종료 중...")
                    self.thread.quit()
                    self.thread.wait()
                                    #print("✅ 백그라운드 스레드 종료 완료")

                    # ✅ 오디오 스트림 닫기
            if hasattr(self, "stream") and self.stream is not None:
                            #print("🛑 오디오 스트림 종료 중...")
                self.stream.stop()
                self.stream.close()
                self.stream = None  # ✅ 스트림 객체 초기화
                            #print("✅ 오디오 스트림 종료 완료")

                # ✅ OpenGL 리소스 정리
            if hasattr(self, "waveform_widget"):
                            #print("🛑 OpenGL 위젯 제거 중...")
                self.waveform_widget.deleteLater()
                self.waveform_widget = None
                            #print("✅ OpenGL 위젯 제거 완료")

                    # ✅ 타이머 정리
            if hasattr(self, "mid_handle_timer"):
                            #print("🛑 타이머 정리 중...")
                self.mid_handle_timer.stop()
                self.mid_handle_timer.deleteLater()
                self.mid_handle_timer = None
                            #print("✅ 타이머 정리 완료")

                    # ✅ 오디오 데이터 정리 (필요한 경우)
            if hasattr(self, "audio_data"):
                    #print("🛑 오디오 데이터 초기화 중...")
                self.audio_data = None
                self.adjusted_audio_data = None
                    #print("✅ 오디오 데이터 초기화 완료")

                    #print("🛑 자원 정리 완료 → AudioEditor 닫기")
            msg_box.close()
            event.accept()
            return True
        else:
            msg_box.close()
            if event is not None:  
                msg_box.close()  # 🎯 창 닫힘 방지
            else:
                return False
            return
        
class Recorder: #녹음 클래스
    def __init__(self, main_window, filename="output.wav", rate=44100, channels=1, format=pyaudio.paInt16, chunk=1024):
        self.main_window = main_window
        self.filename = filename
        self.rate = rate
        self.channels = channels
        self.format = format
        self.chunk = chunk
        self.frames = []
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.recording = False

    def start_recording(self, device_id):
        self.recording = True
        """녹음을 시작하고 선택된 장치를 설정"""
        self.frames = []  # 기존 프레임 초기화
        self.stream = self.audio.open(format=self.format,
                                      channels=self.channels,
                                      rate=self.rate,
                                      input=True,
                                      input_device_index=device_id,  # 선택한 장치 ID
                                      frames_per_buffer=self.chunk)
        #print(f"녹음 시작 - 장치 ID: {device_id}")
        
        def recording_loop():
            while self.recording:
                data = self.stream.read(self.chunk)
                self.frames.append(data)

        thread = threading.Thread(target=recording_loop)
        thread.start()
    
    def stop_recording(self):
        """녹음을 중지하고 스트림을 닫음"""
        self.recording = False
        #print("녹음 종료")
        self.stream.stop_stream()
        self.stream.close()
        self.stream = None
        self.increase_volume()
        
        recorded_temp = self.return_temp_wave()
        return recorded_temp
        #self.save_recording()
        
    def increase_volume(self):
        # 오디오 데이터를 numpy 배열로 변환
        audio_data = np.frombuffer(b''.join(self.frames), dtype=np.int16)
        # 볼륨을 증가시킴 (예: 1.5배). 클리핑 방지를 위해 최대값을 체크
        amplified_audio_data = np.minimum(np.int16(audio_data * 1.5), np.iinfo(np.int16).max)
        # 변경된 데이터를 다시 frames 리스트로 변환
        self.frames = [amplified_audio_data.tobytes()]
        
    def return_temp_wave(self):
        """녹음된 데이터를 AudioSegment로 변환하여 반환"""
        # WAV 파일 포맷으로 메모리에 저장
        wav_buffer = BytesIO()
        with wave.open(wav_buffer, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.audio.get_sample_size(self.format))
            wf.setframerate(self.rate)
            wf.writeframes(b''.join(self.frames))
    
        wav_buffer.seek(0)  # 버퍼의 시작 위치로 이동
        # AudioSegment 객체로 변환
        audio_data = AudioSegment.from_file(wav_buffer, format="wav")
        return audio_data

    def save_recording(self):
        """녹음 파일을 저장"""
        filepath, _ = QFileDialog.getSaveFileName(self.main_window, "Save Recording",
                                                  filter="MP3 files (*.mp3);;WAV files (*.wav)")
        if not filepath:
            return  # 사용자가 저장을 취소한 경우

        # 임시 파일로 WAV 파일 저장
        temp_wave_filename = 'temp.wav'
        with wave.open(temp_wave_filename, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.audio.get_sample_size(self.format))
            wf.setframerate(self.rate)
            wf.writeframes(b''.join(self.frames))
        #print("임시 WAV 파일 생성 완료")

        # MP3로 저장
        if filepath.endswith('.mp3'):
            command = [
                'ffmpeg',
                '-y',
                '-i', temp_wave_filename,  # 임시 WAV 파일 입력
                '-vn',  # 비디오 스트림 없음
                '-ar', str(self.rate),  # 샘플 레이트 설정
                '-ac', str(self.channels),  # 오디오 채널 설정
                '-b:a', '192k',  # 오디오 비트레이트 설정
                filepath
            ]
            subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
            os.remove(temp_wave_filename)  # 임시 파일 삭제
            #print(f"MP3 파일 저장됨: {filepath}")
        else:
            # WAV로 저장
            os.rename(temp_wave_filename, filepath)
            #print(f"WAV 파일 저장됨: {filepath}")
            
    def get_device_list(self):
        device_list = []
        p = pyaudio.PyAudio()
        info = p.get_host_api_info_by_index(0)
        numdevices = info.get('deviceCount')

        for i in range(0, numdevices):
            device_info = p.get_device_info_by_host_api_device_index(0, i)
            if device_info.get('maxInputChannels') > 0:  # 입력 채널이 1 이상인 장치만
                device_list.append((device_info.get('name'), i))  # 이름과 ID를 튜플로 저장
        p.terminate()
    
        return device_list  # 튜플 리스트 반환
    
    def open_save_dialog(self, recorded_data):
        """녹음된 데이터를 저장창을 통해 저장"""
        # 파일 저장 다이얼로그 띄우기
        options = QFileDialog.Options()
        save_path, _ = QFileDialog.getSaveFileName(None, "Save Audio File", "", 
                                                   "MP3 Files (*.mp3);;All Files (*)", options=options)
        if save_path:
            # 녹음 데이터를 파일로 저장
            recorded_data.export(save_path, format="mp3")
            #print(f"파일 저장됨: {save_path}")
            
class PrintOptionsDialog(ThemedDialog): #인쇄 클래스
    def __init__(self, parent=None, theme=None, lang="한국어"):
        self.lang_texts = LANGUAGES[lang]
        title = self.lang_texts["Custom_QDialog_label_title"]["text_PrintOptionsDialog"]
        super().__init__(title, parent, theme)
        self.setGeometry(100, 100, 300, 200)

        # 옵션 레이아웃 구성
        layout = self.layout()

        # 인쇄 항목 선택
        self.word_radio = QRadioButton(self.lang_texts["Custom_QDialog_label_content"]["PrintOptionsDialog_wordonly"])
        self.meaning_radio = QRadioButton(self.lang_texts["Custom_QDialog_label_content"]["PrintOptionsDialog_meaningonly"])
        self.both_radio = QRadioButton(self.lang_texts["Custom_QDialog_label_content"]["PrintOptionsDialog_wordmeaning"])
        self.both_radio.setChecked(True)  # 기본 선택

        layout.setContentsMargins(20,5,15,10)
        layout.addWidget(QLabel(self.lang_texts["Custom_QDialog_label_content"]["PrintOptionsDialog_selectcontent"]))
        layout.addWidget(self.word_radio)
        layout.addWidget(self.meaning_radio)
        layout.addWidget(self.both_radio)

        # 폰트 크기 선택
        layout.addWidget(QLabel(self.lang_texts["Custom_QDialog_label_content"]["PrintOptionsDialog_fontsize"]))
        self.font_size_spinbox = QSpinBox()
        self.font_size_spinbox.setRange(8, 48)  # 폰트 크기 범위 설정
        self.font_size_spinbox.setValue(12)  # 기본값 설정
        layout.addWidget(self.font_size_spinbox)

        # 확인 버튼
        self.confirm_button = ThemedButton(self.lang_texts["Custom_QDialog_buttons"]["text_ok"])
        self.confirm_button.clicked.connect(self.accept)  # 확인을 누르면 창을 닫음
        self.parent.apply_theme_toButtons(self.parent.current_theme, self.confirm_button)
        self.parent.apply_hover_events(self.confirm_button, self.parent.animated_hover_start, self.parent.animated_hover_end)
        layout.addWidget(self.confirm_button)

        self.setLayout(layout)

    def get_options(self):
        """선택된 옵션을 반환"""
        return {
            'print_option': 'word' if self.word_radio.isChecked() else
                            'meaning' if self.meaning_radio.isChecked() else 'both',
            'font_size': self.font_size_spinbox.value()
        }
    
class SoundPlayer:
    def __init__(self):
        pygame.mixer.init()
        self.streak_count = 0  # 🎯 연속 정답 개수 (1~10)
        self.max_streak = 10   # 최대 콤보 단계

        # ✅ resource_path를 통해 전체 경로 미리 만들어둠
        self.sound_files = {
            "correct": [self.resource_path(f"sounds/correct{i}.mp3") for i in range(1, 11)],
            "incorrect": self.resource_path("sounds/incorrect.mp3")
        }

    def resource_path(self, relative_path):
        """ 실행 파일 내부 또는 개발 환경 모두에서 사용 가능한 경로 생성기 """
        if getattr(sys, 'frozen', False):  # PyInstaller로 빌드된 경우
            base_path = sys._MEIPASS       # 임시 디렉토리 (_MEIPASS)
        else:
            base_path = os.path.dirname(__file__)  # 개발 중일 때 현재 파일 위치
        return os.path.join(base_path, relative_path)

    def play_sound(self, file_path):
        """ 🎶 MP3 사운드 파일 재생 """
        if os.path.exists(file_path):
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.set_volume(0.3)  # ✅ 여기서 볼륨 설정
            pygame.mixer.music.play()
        else:
            print(f"⚠️ 파일 없음: {file_path}")  # 파일이 없을 경우 오류 방지

    def play_correct_async(self):
        """ ✅ 정답 시 연속 카운트 증가 & 효과음 실행 """
        self.streak_count = min(self.streak_count + 1, self.max_streak)  # 10 이상 증가 방지
        sound_file = self.sound_files["correct"][self.streak_count - 1]
        threading.Thread(target=self.play_sound, args=(sound_file,), daemon=True).start()

    def play_wrong_async(self):
        """ ❌ 오답 시 효과음 실행 & 콤보 리셋 """
        self.streak_count = 0
        threading.Thread(target=self.play_sound, args=(self.sound_files["incorrect"],), daemon=True).start()
        # print("❌ 오답! 연속 카운트 리셋!")

class MyApp(QMainWindow, Ui_MainWindow): #본 프로그램 시작
    update_signal = pyqtSignal(str)
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.graphicEnv = None
        
        # ✅ OpenGL 컨텍스트 강제 활성화
        self.context = OpenGLContextLoader(self)

        self.item_selection_connected = False  # itemSelectionChanged 시그널 연결 상태 플래그
        self.cell_changed_connected = False  # cellChanged 시그널 연결 상태 플래그
        self.current_file = "" #불러온 파일 이름 저장
        self.txtWordInput.setReadOnly(True)
        self.txtWordInput.status = "no file"
        self.txtMeaningInput.status = "no file"
        self.btnEdit.status = "saved"
        self.btnAutoPlay.userData = "stop"
        self.set_text_widget_editable(False)
        self.set_table_editable(False)
        self.txtAutoAudioDuration.setText("0")
        self.progressBar.setValue(0)
        self.pitch_speed_preset_keys = [
            "lowest_slow", "lowest_normal", "lowest_fast", "low_slow", "low_normal", "low_fast", "slow", "normal", "fast", 
            "high_slow", "high_normal", "high_fast", "random_preset", "everytime_random_preset", "random_pitch", "everytime_random_pitch",
            "random_speed", "everytime_random_speed", "random_pitch_speed", "everytime_random_pitch_speed", "user", 
            ]
        self.TestType_keys = ["Descending", "Ascending", "Random"]
        self.PlayType_keys = ["Descending", "Ascending", "Random"]
        self.cbbTheme_keys = ["Default", "Dark", "Emerald", "Pink", "Evening_Sky", "Campfire_Glow", "Magma", "Ice", "Space", "Forest",
                              "Rainy_Day", "Desert", "Choco", "Navy_Admiral", "Royal_Scenery", "Clerical_Robe", "Ancient_Egypt", "Gemstone", "Go_Stones"]
        self.current_theme = ""
        self.cbbLanguages.addItems(["한국어", "English", "Español", "Ελληνικά"])

        try:
            with open("settings.json", "r", encoding="utf-8") as f:
                settings = json.load(f)
            user_language = settings.get("user_language", "한국어")
        except:
            user_language = "한국어"

        self.cbbLanguages.setCurrentText(user_language)
        self.current_language = user_language

        # 1. 시스템 폰트 경로 및 언어 기반 표시 이름 가져오기
        self.font_display_pairs = self.get_fonts_with_localized_names(self.current_language)  # → [(굴림, Gulim), ...]

        # 2. 콤보박스 목록 구성 (표시이름, 실제이름)
        self.populate_font_list(self.cbbFontSetting, self.font_display_pairs)
        self.populate_font_list(self.cbbFontSetting_tolearn, self.font_display_pairs)

        # 3. 표시이름 → 실제 family name 매핑 딕셔너리 생성
        self.font_map = {display: real for display, real in self.font_display_pairs}

        self.preview_cache = FontPixmapCache(max_size=100)

        self.font_delegate = FontPreviewDelegate(
            preview_map=self.preview_cache.get,
            render_func=self.render_pixmap,
            theme=self.current_theme,
            parent=self.cbbFontSetting
        )
        self.font_delegate_learn = FontPreviewDelegate(
            preview_map=self.preview_cache.get,
            render_func=self.render_pixmap,
            theme=self.current_theme,
            parent=self.cbbFontSetting
        )

        self.cbbFontSetting.setItemDelegate(self.font_delegate)
        self.cbbFontSetting_tolearn.setItemDelegate(self.font_delegate)

        self.cbbFontSetting.currentIndexChanged.connect(self.apply_font)
        self.cbbFontSetting_tolearn.currentIndexChanged.connect(self.apply_font_totarget)

        self.cbbLanguages.currentIndexChanged.connect(lambda: self.apply_language(self.cbbLanguages.currentText()))

        self.word_font_size = 0
        self.meaning_font_size = 0
        self.table_font_size = 0
        self.apply_language(self.cbbLanguages.currentText())

        self.cbbTestType.clear()
        for key in self.TestType_keys:
            translated_text = LANGUAGES[self.current_language]["cbbTestType_list"][key]
            self.cbbTestType.addItem(translated_text, userData=key)
        self.populate_rate_filter()
        self.cbbPlayType.clear()
        for key in self.PlayType_keys:
            translated_text = LANGUAGES[self.current_language]["cbbPlayType_list"][key]
            self.cbbPlayType.addItem(translated_text, userData=key)
        self.cbbPitchPreset.clear()
        for key in self.pitch_speed_preset_keys:
            translated_text = LANGUAGES[self.current_language]["cbbPitchPreset_list"][key]
            self.cbbPitchPreset.addItem(translated_text, userData=key)
        self.cbbPitchPreset.currentIndexChanged.connect(self.on_preset_changed)
        # 프리셋 리스트 정의 (피치와 속도를 함께 저장)
        self.randomePresetsList = {
            "lowest_slow": ("25", "150"),  # 피치 90%, 속도 80%
            "lowest_normal": ("25", "185"), # 피치 90%, 속도 100%
            "lowest_fast": ("25", "350"), # 피치 90%, 속도 120%
            "low_slow": ("45", "110"),    # 피치 80%, 속도 80%
            "low_normal": ("45", "150"),   # 피치 80%, 속도 100%
            "low_fast": ("45", "250"),   # 피치 80%, 속도 120%
            "slow": ("55", "80"),       # 피치 100%, 속도 80%
            "normal": ("55", "100"),      # 피치 100%, 속도 100%
            "fast": ("55", "200"),      # 피치 100%, 속도 120%
            "high_slow": ("60", "80"),   # 피치 120%, 속도 80%
            "high_normal": ("60", "100"),  # 피치 120%, 속도 100%
            "high_fast": ("60", "160")   # 피치 120%, 속도 120%
        }
        #self.widgets_forEvent_override = self.findChildren((QPushButton, QComboBox))
        self.widgets_forEvent_override = [self.btnDeleteAudios, self.btnRecord, self.btnMakeAudios, self.btnOpenThisWordsMP3, self.btnAutoPlay, self.cbbPlayType, self.cbbPitchPreset, self.btnPractice,
                                          self.btnEdit, self.btnTextTestMtoW, self.btnTextTestWtoM, self.btnAudioTestMtoW, self.btnAudioTestWtoM, self.btnAudioTestDictation, self.cbbTestType,
                                          self.cbbLangToLearn, self.cbbBaseLang, self.btn_browser, self.btnDeleteScores, self.btnAlignCellsWidth, self.btnAutoInputNumbers, self.cbbWordFile,
                                          self.btnWordFileOpen, self.btnRefreshWordList, self.btnDeleteWordFile, self.cbbRateFilter, self.cbbTheme, self.btnPrintWords, self.title_bar.minimize_button,
                                          self.title_bar.maximize_button, self.title_bar.close_button, self.cbbTheme, self.cbbLanguages, self.btnMergeFiles, self.btnDivideFile, self.cbbLanguages, self.cbbFontSetting, 
                                          self.cbbFontSetting_tolearn, self.btnDeleteNowAudio]
        self.cbbTheme.clear()
        for key in self.cbbTheme_keys:
            translated_text = LANGUAGES[self.current_language]["cbbTheme_list"][key]
            self.cbbTheme.addItem(translated_text, userData=key)
        self.theme_changed_byuser = False
        self.cbbTheme.currentIndexChanged.connect(lambda: self.Theme_Changed(self.cbbTheme.currentData()))
        # 슬라이드바 초기 설정
        self.slbVolume.setRange(0, 500)
        self.slbVolume.setValue(100)  # 기본값 100 (1배)
        self.slbVolume.valueChanged.connect(self.update_volume)
        self.slbPitchControler.setRange(25, 120)
        self.slbPitchControler.setValue(55)  # 기본값 100 (1배)
        self.slbPitchControler.valueChanged.connect(self.update_pitch)
        self.slbSpeedControler.setRange(10, 300)
        self.slbSpeedControler.setValue(100)  # 기본값 100 (1배)
        self.slbSpeedControler.valueChanged.connect(self.update_speed)
        self.volumeFactor = ""
        self.pitchFactor = ""
        self.speedFactor = ""
        self.txtVolume.textChanged.connect(lambda: self.validate_numeric_input(self.txtVolume))
        self.txtPitchControler.textChanged.connect(lambda: self.validate_numeric_input(self.txtPitchControler))
        self.txtSpeedControler.textChanged.connect(lambda: self.validate_numeric_input(self.txtSpeedControler))
        self.txtAutoAudioDuration.textChanged.connect(lambda: self.validate_numeric_input(self.txtAutoAudioDuration, max_length=4))
        self.txtVolume.textChanged.connect(lambda: self.update_slider_from_textbox(self.txtVolume, self.slbVolume))
        self.txtPitchControler.textChanged.connect(lambda: self.update_slider_from_textbox(self.txtPitchControler, self.slbPitchControler))
        self.txtSpeedControler.textChanged.connect(lambda: self.update_slider_from_textbox(self.txtSpeedControler, self.slbSpeedControler))

        self.confirmedAllWord = False
        self.is_practice = False
        self.is_editing = False  # 편집 모드 여부를 나타내는 플래그
        self.is_loading = False  # 데이터 로드 중 상태를 나타내는 플래그
        self.is_testing = False      # 테스트 상태 플래그
        self.toplay_in_test = False #시험 중 오디오 재생 여부
        self.clicked_test_button_name = ""
        self.practice_mode = None
        self.simulate_backspace_effect(self.txtMeaningInput)
        self.simulate_backspace_effect(self.txtWordInput)
        
        self.word_meaning_list = []  # 단어와 뜻 페어를 담을 리스트
        self.current_word = ""       # 현재 표시된 단어
        self.current_meaning = ""    # 현재 단어의 뜻
        self.current_number = 0
        
        self.numbered_word_meaning_list = []
        self.wrong_answer = []
        self.correct_times_before = []
        self.correct_times = []
        self.recent_time = []
        self.fastest_time = []
        self.corrects = []
        self.incorrect_answers = {}
        self.word_answer_pairs = []
        
        """📌 프로그램 실행 시 recent_list.json 확인 및 불러오기"""
        self.recent_list_path = os.path.join(os.getcwd(), "recent_list.json")  # ✅ 현재 디렉토리에 recent_list.json 위치
        self.recent_file_list = []  # ✅ 최근 연 파일 목록 저장
        
        self.load_recent_files()  # ✅ 최근 파일 목록 불러오기
        
        self.total_words_count = 0
        self.current_words_count = 0
        self.answer_words_count = 0

        self.time_elapsed = QTime(0, 0, 0, 1)
        self.starting_time = QTime(0,0,0,0)
        self.word_time_pairs = []
        self.time_result = []
        self.btnDeleteScores.clicked.connect(self.delete_scores_and_save)
        self.is_auto_playing = False  # 자동재생 중인지 상태를 추적하는 변수 초기화
        
        # 프로그램 실행 시 설정 파일에서 마지막에 불러온 파일 읽기
        settings = self.load_settings()

        # 콤보박스 이벤트 연결 (목록화 이후에 연결)
        self.selected_file = LANGUAGES[self.current_language]["cbbWordFile_list"]["no_file_click_edit"]
            
        # 초기에는 표를 수정 불가능하게 설정
        self.set_table_editable(False)

        # 언어 목록 초기화 및 설정 파일에서 언어 설정 로드
        self.populate_language_comboboxes()
        self.load_language_settings(settings)

        # 버튼 클릭 시 파일 목록 갱신 함수 연결
        if getattr(sys, 'frozen', False):
            # ✅ PyInstaller로 패키징된 경우 실행 파일 위치 사용
            self.its_placement  = os.path.dirname(os.path.abspath(sys.executable))
        else:
            # ✅ 일반 Python 실행 시 스크립트 위치 사용
            self.its_placement  = os.path.dirname(os.path.abspath(__file__))
            
        # ✅ recent_list.json 파일 확인 및 불러오기
        if os.path.exists(self.recent_list_path):
            try:
                with open(self.recent_list_path, "r", encoding="utf-8") as f:
                    self.recent_file_list = json.load(f)
            except json.JSONDecodeError:
                #print("🚨 recent_list.json 파일이 손상되었습니다. 초기화합니다.")
                text = LANGUAGES[self.current_language]["cbbWordFile_list"]["no_recent_file"]
                self.recent_file_list = [text]
        else:
            text = LANGUAGES[self.current_language]["cbbWordFile_list"]["no_recent_file"]
            self.recent_file_list = [text]

        self.current_folder = self.its_placement
        
        self.cbbWordFile.currentIndexChanged.connect(self.on_combobox_changed)
        self.btnRefreshWordList.clicked.connect(self.refresh_file_list_bybutton)
        self.is_opened_byuser = False
        
        csv_files = [f for f in os.listdir(self.its_placement) if f.endswith(".csv")]
        # ✅ 파일 경로 목록 생성
        file_paths = [os.path.join(self.its_placement, f) for f in csv_files]

        if file_paths:  # ✅ CSV 파일이 없을 경우 `min()` 실행 방지

            # ✅ 각 파일의 수정된 날짜 및 생성된 날짜 가져오기
            file_mod_times = {f: os.path.getmtime(f) for f in file_paths}  # 수정된 날짜
            file_create_times = {f: os.path.getctime(f) for f in file_paths}  # 생성된 날짜

            # ✅ 오늘 날짜 확인
            today = datetime.today().date()  # 🔥 `.date()` 추가 (시간까지 비교 안 하도록)
            modified_dates = {f: datetime.fromtimestamp(file_mod_times[f]).date() for f in file_paths}

            # ✅ 수정된 날짜가 가장 오래된 파일 찾기
            oldest_modified_file = min(file_paths, key=lambda f: file_mod_times[f])

            # ✅ 모든 파일이 오늘 수정된 경우
            if all(modified_dates[f] == today for f in file_paths):
                #print("📌 모든 파일이 오늘 수정됨 → 생성 날짜 기준으로 선택")
                oldest_file = min(file_paths, key=lambda f: file_create_times[f])  # 생성된 날짜 기준 선택
            else:
                #print("📌 수정된 날짜 기준으로 파일 선택")
                oldest_file = oldest_modified_file  # 수정 날짜가 가장 오래된 파일 선택

            # ✅ 선택한 파일을 콤보박스에서 강조 & 자동 로드
            self.cbbWordFile.setCurrentText(os.path.basename(oldest_file))
            self.selected_file = self.get_relative_path(oldest_file)
            #print(f"refresh_file_list selected_file: {self.selected_file}")

        # 테이블 셀 선택 변경 이벤트 연결
        self.tbWordList.itemSelectionChanged.connect(self.on_cell_selection_changed)
        self.tbWordList.cellDoubleClicked.connect(self.on_cell_selection_changed)
        
        # 테이블 셀 편집 완료 이벤트 연결
        self.tbWordList.cellChanged.connect(self.on_cell_edit_finished)
        self.item_selection_connected = True  # itemSelectionChanged 시그널 연결 상태 플래그
        self.cell_changed_connected = True  # cellChanged 시그널 연결 상태 플래그
        
        # 편집 버튼 클릭 이벤트 연결
        self.btnEdit.clicked.connect(self.toggle_edit_mode)
        self.btnPractice.clicked.connect(self.toggle_practice_mode)
        self.btnTextTestWtoM.clicked.connect(self.toggle_test_mode)
        self.btnTextTestMtoW.clicked.connect(self.toggle_test_mode)
        self.btnAudioTestWtoM.clicked.connect(self.toggle_test_mode)
        self.btnAudioTestMtoW.clicked.connect(self.toggle_test_mode)
        self.btnAudioTestDictation.clicked.connect(self.toggle_test_mode)
        
        self.btnAlignCellsWidth.clicked.connect(self.align_cells_width)
        self.btnAutoInputNumbers.clicked.connect(self.auto_input_numbers)
        self.btnDeleteWordFile.clicked.connect(self.delete_current_file)
        self.btnMakeAudios.clicked.connect(self.create_audio_files_for_table)
        self.btnMergeFiles.clicked.connect(self.file_merging)
        self.btnDivideFile.clicked.connect(self.file_to_divide)
        
        self.lbWordsCounter.lower()
        self.lbTimer.lower()
        self.lbWordsCounter.setVisible(False)
        self.lbTimer.setVisible(False)
        self.lbThreeCount.lower()
        self.tbWordList.cellChanged.connect(self.on_cell_changed)
        self.setup_checkboxes()
        self.cbbRateFilter.currentIndexChanged.connect(self.on_rate_filter_changed)
        self.chbAllWords.setChecked(True)  # 기본적으로 AllWords 체크박스를 켬
        self.on_rate_filter_changed()
        self.setup_table()
        # 버튼과 함수 연결
        self.btnDeleteAudios.clicked.connect(self.delete_temp_files)
        self.btnDeleteNowAudio.clicked.connect(self.delete_temp_a_file)
        self.btnAutoPlay.clicked.connect(self.toggle_auto_play)
        self.btnWordFileOpen.clicked.connect(self.open_file_dialog)
        self.btnOpenThisWordsMP3.clicked.connect(self.open_mp3_file_to_audio_editor)
        
        self.btnRecord.clicked.connect(self.toggle_recording)
        self.recorder = Recorder(main_window=self)
        self.recording = False
        
        self.sound_player = SoundPlayer()
        
        # 버튼에 연결
        self.btnPrintWords.clicked.connect(self.show_print_options_dialog)
        self.txtMeaningInput.installEventFilter(self)
        self.btn_browser.clicked.connect(self.search_selected_word)

        # 이벤트 필터 추가 (마우스 휠 감지)
        self.txtWordInput.installEventFilter(self)
        self.txtMeaningInput.installEventFilter(self)
        self.tbWordList.installEventFilter(self)

        try: # 테스트 타입 이전 설정 불러오기
            saved_test_type = settings.get("test_type", "Descending")  # 기본값을 '내림차순'으로 설정
            index = self.cbbTestType.findData(saved_test_type)
        
            if index != -1:
                self.cbbTestType.setCurrentIndex(index)  # 설정값이 있으면 해당 인덱스 설정
            else:
                self.cbbTestType.setCurrentIndex(self.cbbTestType.findData("Descending"))  # 없으면 기본값 설정

        except (FileNotFoundError, json.JSONDecodeError):
            # 파일이 없거나 JSON 파싱 오류일 경우 기본값을 사용
            self.cbbTestType.setCurrentIndex(self.cbbTestType.findData("Descending"))
            #print("settings.json 파일이 없거나 잘못된 형식입니다. 기본값으로 설정합니다.")
        try: #자동재생 타입 이전 설정 불러오기
            saved_play_type = settings.get("play_type", "Descending")  # 기본값을 '내림차순'으로 설정
            index = self.cbbPlayType.findData(saved_play_type)
        
            if index != -1:
                self.cbbPlayType.setCurrentIndex(index)  # 설정값이 있으면 해당 인덱스 설정
            else:
                self.cbbPlayType.setCurrentIndex(self.cbbPlayType.findData("Descending"))  # 없으면 기본값 설정

        except (FileNotFoundError, json.JSONDecodeError):
            # 파일이 없거나 JSON 파싱 오류일 경우 기본값을 사용
            self.cbbPlayType.setCurrentIndex(self.cbbPlayType.findData("Descending"))

        try:
            with open("settings.json", "r", encoding="utf-8") as f:
                settings = json.load(f)

            saved_preset = settings.get("pitch", "")
            index = self.cbbPitchPreset.findData(saved_preset)
            if index != -1:
                self.cbbPitchPreset.setCurrentIndex(index)
            else:
                raise ValueError("저장된 pitch 값이 리스트에 없음")

        except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
            logging.warning(f"[⚠️ 설정 로딩 오류] {e}")
    
            # 기본값으로 'normal' 키값을 기반으로 설정
            default_key = "normal"
            fallback_index = self.cbbPitchPreset.findData(default_key)
            if fallback_index != -1:
                self.cbbPitchPreset.setCurrentIndex(fallback_index)

            # 언어별 오류 메시지 출력
            translated_text = LANGUAGES[self.current_language]
            if isinstance(e, FileNotFoundError):
                print(translated_text.get("jsonerror_nofile"))
            else:
                print(translated_text.get("jsonerror_valueerror"))
        
        try:
            with open("settings.json", "r", encoding="utf-8") as f:
                settings = json.load(f)
            
            self.word_font_size = settings.get("word_font_size", 24)
            self.meaning_font_size = settings.get("meaning_font_size", 24)
            self.table_font_size = settings.get("table_font_size", 12)

            # 텍스트 위젯 크기 적용
            self.txtWordInput.setFixedHeight(settings.get("txtWordInput_height", self.txtWordInput.height()))
            self.txtMeaningInput.setFixedHeight(settings.get("txtMeaningInput_height", self.txtMeaningInput.height()))

            # 그리드 레이아웃 패딩 적용
            grid_padding = settings.get("gridLayout_padding", (0, 0, 0, 0))
            self.layout().setContentsMargins(*grid_padding)

            # ✅ 🎵 pitch & volume 적용
            volume_value = settings.get("volume", "50")  # 🔊 volume 기본값 설정
            self.txtVolume.setText(volume_value)  # ✅ volume 적용
            
            user_language = settings.get("user_language", "한국어")
            self.cbbLanguages.setCurrentText(user_language)
            
        except FileNotFoundError:
            logging.warning(LANGUAGES[self.current_language]["jsonerror_nofile"])
            print(LANGUAGES[self.current_language]["jsonerror_nofile"])
        except json.JSONDecodeError:
            logging.warning(LANGUAGES[self.current_language]["jsonerror_valueerror"])
            print(LANGUAGES[self.current_language]["jsonerror_valueerror"])
            
        if settings and "theme" in settings:
            theme_name = settings["theme"]  # JSON에서 저장된 테마 값 불러오기
            if theme_name in [self.cbbTheme.itemData(i) for i in range(self.cbbTheme.count())]:  # 🎯 존재하는 테마인지 확인
                index = self.cbbTheme.findData(theme_name)
                self.cbbTheme.setCurrentIndex(index)
                self.Theme_Changed(theme_name)
            else:
                index = self.cbbTheme.findData("Default")
                self.cbbTheme.setCurrentIndex(index)
                self.Theme_Changed("Default")
        else:
            index = self.cbbTheme.findData("Default")
            self.cbbTheme.setCurrentIndex(index)
            self.Theme_Changed("Default")

        """settings.json에서 폰트 설정을 불러와 콤보박스에 적용"""
        try:
            with open("settings.json", "r", encoding="utf-8") as f:
                settings = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            settings = {}

        font_name = settings.get("font_setting", self.font().family())

        index = self.cbbFontSetting.findText(font_name)
        if index >= 0:
            self.cbbFontSetting.setCurrentIndex(index)
        else:
            # fallback: 시스템 기본 폰트
            default_font = self.font().family()
            default_index = self.cbbFontSetting.findText(default_font)
            if default_index >= 0:
                self.cbbFontSetting.setCurrentIndex(default_index)

        font_name_tolearn = settings.get("font_setting_tolearn", self.font().family())

        index = self.cbbFontSetting_tolearn.findText(font_name_tolearn)
        if index >= 0:
            self.cbbFontSetting_tolearn.setCurrentIndex(index)
        else:
            # fallback: 시스템 기본 폰트
            default_font = self.font().family()
            default_index = self.cbbFontSetting_tolearn.findText(default_font)
            if default_index >= 0:
                self.cbbFontSetting_tolearn.setCurrentIndex(default_index)
        self.apply_font_totarget()

        # 글씨 크기 적용
        font = QFont(self.txtWordInput.font())
        self.adjust_text_widget_height(self.txtWordInput, font)
        font = QFont(self.txtMeaningInput.font())
        self.adjust_text_widget_height(self.txtMeaningInput, font)
            
        self.is_initializing = True
        self.refresh_file_list()
        self.update_volume()
        self.update_pitch()
        self.update_speed()
        self.align_cells_width()
        self.apply_hover_events_Allwidgets()
        self.apply_hover_events(self.title_bar.minimize_button, self.animated_hover_start, self.animated_hover_end)
        self.apply_hover_events(self.title_bar.maximize_button, self.animated_hover_start, self.animated_hover_end)
        self.apply_hover_events(self.title_bar.close_button, self.animated_hover_start, self.animated_hover_end)
        self.theme_hover_refresher()
        self.increase_font_size(self.txtWordInput)
        self.increase_font_size(self.txtMeaningInput)
        self.increase_font_size(self.tbWordList)
        self.decrease_font_size(self.txtWordInput)
        self.decrease_font_size(self.txtMeaningInput)
        self.decrease_font_size(self.tbWordList)
        
#--------------------------------------------------------------------------------        
#------------------------변수설정 및 프로그램 초기화 끝--------------------------
#--------------------------------------------------------------------------------

    def get_fonts_with_localized_names(self, language):
        font_families = QFontDatabase().families()
        font_folder = Path("C:/Windows/Fonts")
        fonts = []

        for fam in font_families:
            path = self.find_font_file(fam, font_folder)  # ← QFont → .ttf/.ttc 파일 경로 찾아주는 함수 필요
            display_name = self.get_localized_font_name(str(path), language) if path else None
            display_name = display_name or fam
            if not display_name:
                # 강제 fallback: 실제 QFont 생성 후 표시이름 추출
                display_name = QFont(fam).family()
            fonts.append((display_name, fam))  # (표시용, 실제용)
        return fonts

    def find_font_file(self, font_family: str, font_folder: str = "C:/Windows/Fonts") -> str | None:
        """윈도우 레지스트리에서 폰트 패밀리 이름에 해당하는 실제 파일명을 찾아 경로를 반환"""
        try:
            # 윈도우 레지스트리 접근
            reg_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path) as key:
                for i in range(winreg.QueryInfoKey(key)[1]):
                    name, value, _ = winreg.EnumValue(key, i)
                    if font_family.lower() in name.lower():  # 대소문자 무시 포함 검색
                        file_path = os.path.join(font_folder, value)
                        if os.path.exists(file_path):
                            return file_path
        except Exception as e:
            print(f"🔍 폰트 경로 찾기 실패: {font_family} → {e}")
        return None

    def get_localized_font_name(self, font_path: str, language: str) -> str | None:
        lang_id_map = {
            "한국어": 0x0412,
            "English": 0x0409,
            "日本語": 0x0411,
            "Ελληνικά": 0x0408,
            "Español": 0x0C0A
        }
        lang_id = lang_id_map.get(language, 0x0409)

        if not font_path.lower().endswith((".ttf", ".otf", ".ttc")):
            return None

        try:
            font_path = Path(font_path)
            if font_path.suffix.lower() == ".ttc":
                collection = TTCollection(str(font_path))
                for font in collection.fonts:
                    name_table = font['name']
                    for record in name_table.names:
                        if record.nameID in (1, 4) and record.langID == lang_id:
                            return record.toUnicode()

            else:  # .ttf or .otf
                font = TTFont(str(font_path))
                name_table = font['name']
                for record in name_table.names:
                    if record.nameID in (1, 4) and record.langID == lang_id:
                        return record.toUnicode()

        except Exception as e:
            # 선택적으로 출력
            if font_path.name.lower().endswith(".fon"):
                return None  # 비트맵 폰트는 무시
            print(f"⚠️ Failed to parse {font_path.name}: {e} (ignored)")
            return None

    def render_pixmap(self, font_display_name: str, height: int = 22, theme: str = "light") -> QPixmap:
        actual_family = self.font_map.get(font_display_name, font_display_name)  # 표시→실제
        font = QFont(actual_family)
        font.setPointSize(height - 6)

        # 테마 색상 가져오기
        if theme is None:
            theme = self.current_theme  # ← 현재 테마를 기본으로 사용
        color = QColor(THEME_COLORS[theme]["main_text"])

        metrics = QFontMetrics(font)
        width = metrics.width(actual_family) + 12
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setFont(font)
        painter.setPen(color)
        painter.drawText(pixmap.rect(), Qt.AlignVCenter | Qt.AlignLeft, actual_family)
        painter.end()

        return pixmap

    def get_font_pixmap(self, font_name, height=12, MAX_CACHE = 100):
        if font_name in self.font_previews:
            return self.font_previews[font_name]

        if len(self.font_previews) > MAX_CACHE:
            self.font_previews.clear()

        font = QFont(font_name)
        font.setPointSize(height)
    
        metrics = QFontMetrics(font)
        pixmap = QPixmap(metrics.width(font_name) + 10, height + 6)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setFont(font)
        painter.setPen(Qt.black)
        painter.drawText(pixmap.rect(), Qt.AlignVCenter | Qt.AlignLeft, font_name)
        painter.end()

        self.font_previews[font_name] = pixmap
        return pixmap

    def get_fonts_from_system_folder(self):
        font_extensions = ['.ttf', '.otf', '.ttc']
        font_names = []
        seen_families = set()

        system = sys_platform.system()
        font_dirs = []

        if system == "Windows":
            font_dirs = [r"C:\Windows\Fonts"]
        elif system == "Darwin":
            font_dirs = ["/System/Library/Fonts", "/Library/Fonts", str(Path.home() / "Library/Fonts")]
        elif system == "Linux":
            font_dirs = ["/usr/share/fonts", "/usr/local/share/fonts", str(Path.home() / ".fonts")]

        for folder in font_dirs:
            if not os.path.exists(folder):
                continue

            for root, _, files in os.walk(folder):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in font_extensions):
                        full_path = os.path.join(root, file)
                        font_id = QFontDatabase.addApplicationFont(full_path)
                        if font_id != -1:
                            families = QFontDatabase.applicationFontFamilies(font_id)
                            for fam in families:
                                if fam not in seen_families:
                                    seen_families.add(fam)
                                    font_names.append(fam)

        return sorted(font_names)

    def populate_font_list(self, combo: QComboBox, font_pairs: list[tuple[str, str]]):
        combo.clear()
        for display_name, family_name in font_pairs:
            combo.addItem(display_name, userData=family_name)

    def lazy_apply_fonts(self, combo: QComboBox):
        # 현재 인덱스를 기준으로 앞뒤로 몇 개만 적용
        view = combo.view()
        current_index = combo.currentIndex()
        visible = combo.maxVisibleItems()
        start = max(0, current_index - visible)
        end = min(combo.count(), current_index + visible + 2)

        for i in range(start, end):
            if combo.itemData(i, Qt.FontRole) is None:
                combo.setItemData(i, QFont(combo.itemText(i)), Qt.FontRole)

        combo.view().update()

    def bind_font_lazy_scroll(self, combo: QComboBox):
        view = combo.view()
        scrollbar = combo.view().verticalScrollBar()

        try:
            scrollbar.valueChanged.disconnect()
        except:
            pass  # 연결된 게 없으면 무시
    
        def apply_visible_fonts_on_scroll(value):
            # 현재 첫 번째 보여지는 인덱스 계산
            first_visible_row = value
            max_items = combo.maxVisibleItems()
            last_row = min(combo.count(), first_visible_row + max_items + 2)

            for i in range(first_visible_row, last_row):
                if combo.itemData(i, Qt.FontRole) is None:
                    combo.setItemData(i, QFont(combo.itemText(i)), Qt.FontRole)

        scrollbar.valueChanged.connect(lambda value: combo.view().viewport().update())
        combo.view().update()

    def apply_font(self):
        self.disconnect_events()

        font_name = self.cbbFontSetting.currentText()
        selected_index = self.cbbFontSetting.currentIndex()
        actual_font_family = self.cbbFontSetting.itemData(selected_index)  # ⬅️ userData 사용
        base_font = QApplication.font()

        # 전역 폰트 설정 (스타일 유지, 폰트만 변경)
        custom_font = QFont(actual_font_family)
        custom_font.setPointSize(base_font.pointSize())
        custom_font.setWeight(base_font.weight())
        custom_font.setStyle(base_font.style())

        QApplication.setFont(custom_font)

        # 모든 위젯 순회하며 강제 폰트 적용
        for widget in QApplication.allWidgets():
            current_size = widget.font().pointSize()
            if current_size <= 0:
                current_size = base_font.pointSize()  # 기본값 보정

            new_font = QFont(font_name)
            new_font.setPointSize(current_size)
            widget.setFont(new_font)

            # QPushButton은 스타일시트에 font-family 적용 필요
            if isinstance(widget, QPushButton):
                current_style = widget.styleSheet().rstrip(";")
                widget.setStyleSheet(f"{current_style}; font-family: '{font_name}';")

        font_name = self.cbbFontSetting_tolearn.currentText()

        for row in range(self.tbWordList.rowCount()):
            item = self.tbWordList.item(row, 1)
            if item:
                old_font = item.font()
                new_font = QFont(font_name)
                new_font.setPointSize(old_font.pointSize())
                new_font.setWeight(old_font.weight())
                new_font.setStyle(old_font.style())
                item.setFont(new_font)

                # ✅ 색상 유지 (필요시)
                item.setForeground(item.foreground())
        old_font = self.cbbFontSetting_tolearn.font()
        new_font = QFont(font_name)
        new_font.setPointSize(old_font.pointSize())
        new_font.setWeight(old_font.weight())
        new_font.setStyle(old_font.style())
        self.cbbFontSetting_tolearn.setFont(new_font)
        self.apply_font_totxts()
        
        self.connect_events()

    def apply_font_totarget(self):
        self.disconnect_events()
        
        new_family = self.cbbFontSetting_tolearn.currentText()

        # ✅ 테이블 1번 컬럼만 처리
        for row in range(self.tbWordList.rowCount()):
            item = self.tbWordList.item(row, 1)
            if item:
                old_font = item.font()
                new_font = QFont(new_family)
                new_font.setPointSize(self.table_font_size)
                item.setFont(new_font)

                # ✅ 기존 글씨 색상 유지
                item.setForeground(item.foreground())
        old_font = self.cbbFontSetting_tolearn.font()
        new_font = QFont(new_family)
        new_font.setPointSize(old_font.pointSize())
        new_font.setWeight(old_font.weight())
        new_font.setStyle(old_font.style())
        self.apply_font_totxts()
        self.cbbFontSetting_tolearn.setFont(new_font)
        self.align_cells_width()
        
        self.connect_events()
        QApplication.processEvents()  # ✅ 렌더 이벤트 정리

    def apply_font_totxts(self):
        self.disconnect_events()
        
        word_text = self.txtWordInput.toPlainText().strip()
        meaning_text = self.txtMeaningInput.toPlainText().strip()

        base_font_family = self.cbbFontSetting.currentData()
        learn_font_family = self.cbbFontSetting_tolearn.currentData()

        base_word_font = QFont(self.txtWordInput.font())
        base_meaning_font = QFont(self.txtMeaningInput.font())

        word_match = None
        meaning_match = None

        for row in range(self.tbWordList.rowCount()):
            word_item = self.tbWordList.item(row, 1)  # 1번: 학습언어
            meaning_item = self.tbWordList.item(row, 2)  # 2번: 모국어

            word_val = word_item.text().strip() if word_item else ""
            meaning_val = meaning_item.text().strip() if meaning_item else ""

            # ⚠️ 반대로 적용: 1번 컬럼 → learn, 2번 컬럼 → base
            if word_text == word_val:
                word_match = "learn"
            elif word_text == meaning_val:
                word_match = "base"

            if meaning_text == word_val:
                meaning_match = "learn"
            elif meaning_text == meaning_val:
                meaning_match = "base"

            if word_match and meaning_match:
                break

        def copy_with_new_family(original_font: QFont, new_family: str):
            font = QFont(original_font)
            font.setFamily(new_family)
            return font

        final_word_font = copy_with_new_family(
            base_word_font,
            learn_font_family if word_match == "learn" else base_font_family
        )
        final_meaning_font = copy_with_new_family(
            base_meaning_font,
            learn_font_family if meaning_match == "learn" else base_font_family
        )

        self.txtWordInput.setFont(final_word_font)
        self.txtMeaningInput.setFont(final_meaning_font)
        
        self.connect_events()

    def apply_language(self, lang_code):
        self.current_language = lang_code
        texts = LANGUAGES.get(lang_code, LANGUAGES["한국어"])  # 기본은 한글
        
        self.label.setText(texts["label"])
        self.label_2.setText(texts["label_2"])
        self.btnDeleteAudios.setToolTip(texts["btnDeleteAudios_t"])
        self.btnDeleteAudios.setText(texts["btnDeleteAudios"])
        self.btnDeleteNowAudio.setToolTip(texts["btnDeleteNowAudio_t"])
        self.btnDeleteNowAudio.setText(texts["btnDeleteNowAudio"])
        self.btnRecord.setToolTip(texts["btnRecord_t"])
        self.btnRecord.setText(texts["btnRecord"])
        self.btnMakeAudios.setToolTip(texts["btnMakeAudios_t"])
        self.btnMakeAudios.setText(texts["btnMakeAudios"])
        self.btnOpenThisWordsMP3.setText(texts["btnOpenThisWordsMP3"])
        self.btnOpenThisWordsMP3.setToolTip(texts["btnOpenThisWordsMP3_t"])
        if self.btnAutoPlay.userData == "stop":
            self.btnAutoPlay.setToolTip(texts["btnAutoPlay_t"])
            self.btnAutoPlay.setText(texts["btnAutoPlay"])
        else:
            self.btnAutoPlay.setToolTip(texts["btnAutoPlay_stop_t"])
            self.btnAutoPlay.setText(texts["btnAutoPlay_stop"])
        self.cbbPlayType.setToolTip(texts["cbbPlayType"])
        self.chbToReadMeaning.setToolTip(texts["chbToReadMeaning_t"])
        self.chbToReadMeaning.setText(texts["chbToReadMeaning"])
        self.label_13.setText(texts["label_13"])
        self.txtAutoAudioDuration.setToolTip(texts["txtAutoAudioDuration"])
        self.label_14.setText(texts["label_14"])
        self.label_3.setText(texts["label_3"])
        self.txtPitchControler.setToolTip(texts["txtPitchControler"])
        self.label_4.setText(texts["label_4"])
        self.txtSpeedControler.setToolTip(texts["txtSpeedControler"])
        self.cbbPitchPreset.setToolTip(texts["cbbPitchPreset"])
        self.cbbLangToLearn.setToolTip(texts["cbbLangToLearn"])
        self.cbbLanguages.setToolTip(texts["cbbLanguages"])
        self.btnTextTestWtoM.setToolTip(texts["btnTextTestWtoM_t"])
        self.btnTextTestWtoM.setText(texts["btnTextTestWtoM"])
        self.label_5.setText(texts["label_5"])
        self.label_7.setText(texts["label_7"])
        self.btnAudioTestWtoM.setToolTip(texts["btnAudioTestWtoM_t"])
        self.btnAudioTestWtoM.setText(texts["btnAudioTestWtoM"])
        self.label_6.setText(texts["label_6"])
        self.cbbTestType.setToolTip(texts["cbbTestType"])
        self.btnAudioTestMtoW.setToolTip(texts["btnAudioTestMtoW_t"])
        self.btnAudioTestMtoW.setText(texts["btnAudioTestMtoW"])
        self.cbbBaseLang.setToolTip(texts["cbbBaseLang"])
        self.btnPractice.setToolTip(texts["btnPractice_t"])
        self.btnPractice.setText(texts["btnPractice"])
        self.btnAudioTestDictation.setToolTip(texts["btnAudioTestDictation_t"])
        self.btnAudioTestDictation.setText(texts["btnAudioTestDictation"])
        self.btnTextTestMtoW.setToolTip(texts["btnTextTestMtoW_t"])
        self.btnTextTestMtoW.setText(texts["btnTextTestMtoW"])
        self.btn_browser.setToolTip(texts["btn_browser_t"])
        self.btn_browser.setText(texts["btn_browser"])
        self.btnDeleteScores.setToolTip(texts["btnDeleteScores_t"])
        self.btnDeleteScores.setText(texts["btnDeleteScores"])
        self.btnAlignCellsWidth.setToolTip(texts["btnAlignCellsWidth_t"])
        self.btnAlignCellsWidth.setText(texts["btnAlignCellsWidth"])
        self.btnAutoInputNumbers.setToolTip(texts["btnAutoInputNumbers_t"])
        self.btnAutoInputNumbers.setText(texts["btnAutoInputNumbers"])
        self.label_8.setText(texts["label_8"])
        self.cbbWordFile.setToolTip(texts["cbbWordFile"])
        self.btnWordFileOpen.setText(texts["btnWordFileOpen"])
        self.btnWordFileOpen.setToolTip(texts["btnWordFileOpen_t"])
        self.btnRefreshWordList.setToolTip(texts["btnRefreshWordList_t"])
        self.btnRefreshWordList.setText(texts["btnRefreshWordList"])
        self.btnDeleteWordFile.setToolTip(texts["btnDeleteWordFile_t"])
        self.btnDeleteWordFile.setText(texts["btnDeleteWordFile"])
        self.btnMergeFiles.setToolTip(texts["btnMergeFiles_t"])
        self.btnMergeFiles.setText(texts["btnMergeFiles"])
        self.btnDivideFile.setToolTip(texts["btnDivideFile_t"])
        self.btnDivideFile.setText(texts["btnDivideFile"])
        self.label_9.setText(texts["label_9"])
        self.chbAllWords.setToolTip(texts["chbAllWords_t"])
        self.chbAllWords.setText(texts["chbAllWords"])
        self.chbOnlyIncorrects.setToolTip(texts["chbOnlyIncorrects_t"])
        self.chbOnlyIncorrects.setText(texts["chbOnlyIncorrects"])
        self.chbOnlyLowRates.setToolTip(texts["chbOnlyLowRates_t"])
        self.chbOnlyLowRates.setText(texts["chbOnlyLowRates"])
        self.label_10.setText(texts["label_10"])
        item = self.tbWordList.horizontalHeaderItem(0)
        item.setText(texts["tbWordList0"])
        item = self.tbWordList.horizontalHeaderItem(1)
        item.setText(texts["tbWordList1"])
        item = self.tbWordList.horizontalHeaderItem(2)
        item.setText(texts["tbWordList2"])
        item = self.tbWordList.horizontalHeaderItem(3)
        item.setText(texts["tbWordList3"])
        item = self.tbWordList.horizontalHeaderItem(4)
        item.setText(texts["tbWordList4"])
        item = self.tbWordList.horizontalHeaderItem(5)
        item.setText(texts["tbWordList5"])
        item = self.tbWordList.horizontalHeaderItem(6)
        item.setText(texts["tbWordList6"])
        item = self.tbWordList.horizontalHeaderItem(7)
        item.setText(texts["tbWordList7"])
        item = self.tbWordList.horizontalHeaderItem(8)
        item.setText(texts["tbWordList8"])
        item = self.tbWordList.horizontalHeaderItem(9)
        item.setText(texts["tbWordList9"])
        self.lbWordsCounter.setText(texts["lbWordsCounter"])
        self.lbTimer.setText(texts["lbTimer"])
        self.lbThreeCount.setText(texts["lbThreeCount"])
        self.label_11.setText(texts["label_11"])
        self.label_cbbLanguages.setText(texts["label_cbbLanguages"])
        self.label_12.setText(texts["label_12"])
        self.label_cbbFontSetting.setText(texts["label_cbbFontSetting"])
        self.label_cbbFontSetting_tolearn.setText(texts["label_cbbFontSetting_tolearn"])
        self.txtVolume.setToolTip(texts["txtVolume"])
        
        invalid_codes = {
            None,
            "no_sub_folder",
            "no_file_click_edit",
            "no_recent_file",
            "go_to_top",
            "current_folder",
            "files_in_current_folder",
            "recent_file",
            "oldest_tested",
            "no_oldest_tested",
        }

        # 🔁 self.current_file → 코드값으로 변환 시도
        selected_code = self.get_code_from_translated_value(self.current_file)

        # ✅ 1단계: 코드값일 경우 → 무시
        if selected_code in invalid_codes:
            self.lbLastTest.setText(texts["lbLastTest"])

        # ✅ 2단계: 코드화 실패 → 파일 경로로 간주
        else:
            # 여기선 selected_code는 None, self.current_file은 파일 경로일 가능성
            self.update_last_test_label(self.current_file)
            
        self.cbbTheme.setToolTip(texts["cbbTheme"])
        self.btnPrintWords.setText(texts["btnPrintWords"])
        self.btnPrintWords.setToolTip(texts["btnPrintWords_t"])
        if self.btnEdit.status == "saved":
            self.btnEdit.setToolTip(texts["btnEdit_t"])
            self.btnEdit.setText(texts["btnEdit"])
        else:
            self.btnEdit.setToolTip(texts["btnEdit2_t"])
            self.btnEdit.setText(texts["btnEdit2"])
            
        current_language = self.cbbLanguages.currentText()
        temp_item = self.cbbPitchPreset.currentData()
        self.cbbPitchPreset.clear()
        for key in self.pitch_speed_preset_keys:
            translated_text = LANGUAGES[current_language]["cbbPitchPreset_list"][key]
            self.cbbPitchPreset.addItem(translated_text, userData=key)
        index = self.cbbPitchPreset.findData(temp_item)
        if index != -1:
            self.cbbPitchPreset.setCurrentIndex(index)
            
        temp_item = self.cbbTestType.currentData()
        self.cbbTestType.clear()
        for key in self.TestType_keys:
            translated_text = LANGUAGES[current_language]["cbbTestType_list"][key]
            self.cbbTestType.addItem(translated_text, userData=key)
        index = self.cbbTestType.findData(temp_item)
        if index != -1:
            self.cbbTestType.setCurrentIndex(index)
            
        temp_item = self.cbbPlayType.currentData()
        self.cbbPlayType.clear()
        for key in self.PlayType_keys:
            translated_text = LANGUAGES[current_language]["cbbPlayType_list"][key]
            self.cbbPlayType.addItem(translated_text, userData=key)
        index = self.cbbPlayType.findData(temp_item)
        if index != -1:
            self.cbbPlayType.setCurrentIndex(index)
            
        self.cbbTheme.blockSignals(True)  # 🔇 시그널 차단
        temp_item = self.cbbTheme.currentData()
        self.cbbTheme.clear()
        for key in self.cbbTheme_keys:
            translated_text = LANGUAGES[current_language]["cbbTheme_list"][key]
            self.cbbTheme.addItem(translated_text, userData=key)
        # 🔁 원래 선택되어 있던 항목 복구
        index = self.cbbTheme.findData(temp_item)
        if index != -1:
            self.cbbTheme.setCurrentIndex(index)
        self.cbbTheme.blockSignals(False)  # ✅ 다시 시그널 활성화
        base_font_name = self.cbbFontSetting.currentData()
        if self.txtWordInput.status == "no file":
            translated_text = LANGUAGES.get(self.current_language, LANGUAGES["한국어"])
            self.txtWordInput.setPlainText(translated_text["wordfileloaded_nofile1"])
            self.txtMeaningInput.setPlainText(translated_text["wordfileloaded_nofile2"])
        elif self.txtWordInput.status == "file is loaded": 
            translated_text = LANGUAGES.get(self.current_language, LANGUAGES["한국어"])
            self.txtWordInput.setPlainText(translated_text["wordfileloaded_success1"])
            self.txtMeaningInput.setPlainText(translated_text["wordfileloaded_success2"])
        elif self.txtWordInput.status == "practicing done":
            translated_text = LANGUAGES.get(self.current_language, LANGUAGES["한국어"])
            self.txtWordInput.setPlainText(translated_text["practicing_done1"])
            self.txtMeaningInput.setPlainText(translated_text["practicing_done2"])
        elif self.txtWordInput.status == "is editing":
            translated_text = LANGUAGES.get(self.current_language, LANGUAGES["한국어"])
            self.txtWordInput.setPlainText(translated_text["is_editing1"])
            self.txtMeaningInput.setPlainText(translated_text["is_editing2"])
        elif self.txtWordInput.status == "tested well":
            translated_text = LANGUAGES.get(self.current_language, LANGUAGES["한국어"])
            self.txtWordInput.setPlainText(translated_text["test_contition_error1"])
            self.txtMeaningInput.setPlainText(translated_text["tested_well2"])
        self.txtmeaninginput_style_reset(self.current_theme)
        if base_font_name:
            font = QFont(base_font_name)
            font.setPointSize(self.word_font_size)  # 현재 설정된 크기 유지
            self.txtWordInput.setFont(font)
            self.txtMeaningInput.setFont(font)
            
        for i in range(self.cbbWordFile.count()):
            key = self.cbbWordFile.itemData(i)
            translated = LANGUAGES[self.current_language]["cbbWordFile_list"].get(key, None)
            if translated:
                self.cbbWordFile.setItemText(i, translated)
        
        self.disconnect_events()
        for row in range(self.tbWordList.rowCount()):
            for col in [6, 7, 8]:
                item = self.tbWordList.item(row, col)
                if item:
                    code_value = item.data(QtCore.Qt.UserRole)  # ✅ 항상 내부 코드값 기준
                    #print(f"코드값 {code_value}")
                    display_value = self.translate_cell_value(code_value)
                    item.setText(display_value)
        self.connect_events()

        # 🌐 1. 폰트 이름을 새 언어 기준으로 다시 가져오기
        self.font_display_pairs = self.get_fonts_with_localized_names(lang_code)

        # 🗺️ 2. 표시이름 → 실제 family name 매핑 다시 생성
        self.font_map = {display: real for display, real in self.font_display_pairs}

        # 🧠 3. 기존 선택 폰트 기억해두기
        prev_font_cbb1 = self.cbbFontSetting.currentData()
        prev_font_cbb2 = self.cbbFontSetting_tolearn.currentData()

        # 🎯 4. 콤보박스 다시 구성
        self.populate_font_list(self.cbbFontSetting, self.font_display_pairs)
        self.populate_font_list(self.cbbFontSetting_tolearn, self.font_display_pairs)

        # 🔁 5. 이전 선택값 복원
        if prev_font_cbb1:
            index = self.cbbFontSetting.findData(prev_font_cbb1)
            if index >= 0:
                self.cbbFontSetting.setCurrentIndex(index)

        if prev_font_cbb2:
            index = self.cbbFontSetting_tolearn.findData(prev_font_cbb2)
            if index >= 0:
                self.cbbFontSetting_tolearn.setCurrentIndex(index)

        # 🎨 6. Delegate의 테마 반영 (선택적으로 호출)
        self.font_delegate.theme = self.current_theme
        self.font_delegate_learn.theme = self.current_theme
        self.font_delegate.invalidate_cache()
        self.font_delegate_learn.invalidate_cache()

        self.cbbFontSetting.view().viewport().update()
        self.cbbFontSetting_tolearn.view().viewport().update()
    
    def get_code_from_translated_value(self, translated_text):
        if not translated_text:
            return None  # ✅ None이나 빈 문자열 방지

        for lang_data in LANGUAGES.values():
            file_list = lang_data.get("cbbWordFile_list", {})
            for k, v in file_list.items():
                if translated_text == v:
                    return k
        return None

    def resource_path(self, relative_path):
        """ 실행 파일 내부 또는 개발 환경 모두에서 사용 가능한 경로 생성기 """
        if getattr(sys, 'frozen', False):  # PyInstaller로 빌드된 경우
            base_path = sys._MEIPASS       # 임시 디렉토리 (_MEIPASS)
        else:
            base_path = os.path.dirname(__file__)  # 개발 중일 때 현재 파일 위치
        return os.path.join(base_path, relative_path)

    def search_selected_word(self):
        translated = LANGUAGES[self.current_language]
        current_row = self.tbWordList.currentRow()  # 현재 선택된 행
        if current_row != -1:  # 선택된 행이 있을 경우
            word_item = self.tbWordList.item(current_row, 1)  # 단어 열 (예: 1번 컬럼)
            if word_item:
                word = word_item.text().strip()  # 단어 텍스트 가져오기
                if word:
                    self.search_google(word)
                else:
                    self.show_custom_message(translated["Custom_QDialog_label_title"]["text_warning"], translated["Custom_QDialog_label_content"]["search_selected_word_no_word"])
        else:
            self.show_custom_message(translated["Custom_QDialog_label_title"]["text_warning"], translated["Custom_QDialog_label_content"]["search_selected_word_choose_word"])
            
    def search_google(self, query):
        base_url = "https://www.google.com/search?q="
        encoded_query = urllib.parse.quote(query)  # ✅ URL 인코딩
        search_url = base_url + encoded_query
        webbrowser.open(search_url)

    def theme_changed_byuser_change(self):
        self.theme_changed_byuser = True

    def apply_hover_events_Allwidgets(self):
        self.apply_hover_events(self.btnDeleteAudios, self.animated_hover_start, self.animated_hover_end)
        self.apply_hover_events(self.btnRecord, self.animated_hover_start, self.animated_hover_end)
        self.apply_hover_events(self.btnMakeAudios, self.animated_hover_start, self.animated_hover_end)
        self.apply_hover_events(self.btnOpenThisWordsMP3, self.animated_hover_start, self.animated_hover_end)
        self.apply_hover_events(self.btnAutoPlay, self.animated_hover_start, self.animated_hover_end)
        self.apply_hover_events(self.cbbPlayType, self.animated_hover_start, self.animated_hover_end)
        self.apply_hover_events(self.cbbPitchPreset, self.animated_hover_start, self.animated_hover_end)
        self.apply_hover_events(self.btnPractice, self.animated_hover_start, self.animated_hover_end)
        self.apply_hover_events(self.btnEdit, self.animated_hover_start, self.animated_hover_end)
        self.apply_hover_events(self.btnTextTestMtoW, self.animated_hover_start, self.animated_hover_end)
        self.apply_hover_events(self.btnTextTestWtoM, self.animated_hover_start, self.animated_hover_end)
        self.apply_hover_events(self.btnAudioTestMtoW, self.animated_hover_start, self.animated_hover_end)
        self.apply_hover_events(self.btnAudioTestWtoM, self.animated_hover_start, self.animated_hover_end)
        self.apply_hover_events(self.btnAudioTestDictation, self.animated_hover_start, self.animated_hover_end)
        self.apply_hover_events(self.cbbTestType, self.animated_hover_start, self.animated_hover_end)
        self.apply_hover_events(self.cbbLangToLearn, self.animated_hover_start, self.animated_hover_end)
        self.apply_hover_events(self.cbbBaseLang, self.animated_hover_start, self.animated_hover_end)
        self.apply_hover_events(self.btn_browser, self.animated_hover_start, self.animated_hover_end)
        self.apply_hover_events(self.btnDeleteScores, self.animated_hover_start, self.animated_hover_end)
        self.apply_hover_events(self.btnAlignCellsWidth, self.animated_hover_start, self.animated_hover_end)
        self.apply_hover_events(self.btnAutoInputNumbers, self.animated_hover_start, self.animated_hover_end)
        self.apply_hover_events(self.cbbWordFile, self.animated_hover_start, self.animated_hover_end)
        self.apply_hover_events(self.btnWordFileOpen, self.animated_hover_start, self.animated_hover_end)
        self.apply_hover_events(self.btnRefreshWordList, self.animated_hover_start, self.animated_hover_end)
        self.apply_hover_events(self.btnDeleteWordFile, self.animated_hover_start, self.animated_hover_end)
        self.apply_hover_events(self.cbbRateFilter, self.animated_hover_start, self.animated_hover_end)
        self.apply_hover_events(self.cbbTheme, self.animated_hover_start, self.animated_hover_end)
        self.apply_hover_events(self.btnPrintWords, self.animated_hover_start, self.animated_hover_end)
        self.apply_hover_events(self.btnMergeFiles, self.animated_hover_start, self.animated_hover_end)
        self.apply_hover_events(self.btnDivideFile, self.animated_hover_start, self.animated_hover_end)
        self.apply_hover_events(self.cbbLanguages, self.animated_hover_start, self.animated_hover_end)
        self.apply_hover_events(self.cbbFontSetting, self.animated_hover_start, self.animated_hover_end)
        self.apply_hover_events(self.cbbFontSetting_tolearn, self.animated_hover_start, self.animated_hover_end)
        self.apply_hover_events(self.btnDeleteNowAudio, self.animated_hover_start, self.animated_hover_end)
        
    def theme_hover_refresher(self):
        self.theme_changed_byuser = True
        # 예시: 모든 위젯에 리셋 애니메이션 적용
        for widget in self.widgets_forEvent_override:
            self.animated_hover_end(widget)  # ✅ 강제로 현재 테마색으로 갱신
        self.theme_changed_byuser = False  # ✅ 리셋

    def apply_hover_events(self, widget, on_hover, on_leave):
        """🎨 위젯에 Hover 필터 적용"""
        # 애니메이션 기본 배경색 설정
        theme = THEME_COLORS.get(self.current_theme, THEME_COLORS["basic"])
        end_color = theme['button_bg']

        # 필터 객체 생성 (on_hover, on_leave 넘겨줌)
        hover_filter = HoverEventFilter(on_hover, on_leave)

        # 위젯에 이벤트 필터 설치
        widget.installEventFilter(hover_filter)
        
        widget._hover_filter = hover_filter  # ✅ 나중에 제거할 수 있게 보관

        # 애니메이션 설정
        widget.animation_thread = AnimationThread(widget, end_color)
        widget.animation_thread.update_signal.connect(
            lambda color: self.update_widget_style(widget, color)
        )
        widget.animation_thread.start()

        # 위젯 객체가 소멸되면 필터도 유지하려면 참조 저장 (안 그러면 GC로 사라질 수 있음)
        if not hasattr(self, "_hover_filters"):
            self._hover_filters = []
        self._hover_filters.append(hover_filter)

    def animated_hover_start(self, widget):
        """ 🔥 마우스 오버 시 배경색 애니메이션 시작 (활성 상태 또는 테마 강제 변경 시만) """
        if not self.theme_changed_byuser and not widget.isEnabled():
            return  # ⛔ 비활성 위젯은 무시 (단, 테마 변경 시에는 강제로 적용)

        if hasattr(widget, "animation_thread") and widget.animation_thread.isRunning():
            widget.animation_thread.stop()

        theme = THEME_COLORS.get(self.current_theme, THEME_COLORS["basic"])
        end_color = theme['button_hover_bg']

        widget.animation_thread = AnimationThread(widget, end_color)
        widget.animation_thread.update_signal.connect(
            lambda color: self.update_widget_style(widget, color)
        )
        widget.animation_thread.start()
    
    def animated_hover_end(self, widget):
        """ 🔥 마우스 리브 시 기본색 복귀 애니메이션 (활성 상태 또는 테마 변경 시만) """
        if not self.theme_changed_byuser and not widget.isEnabled():
            return  # ⛔ 비활성 위젯은 무시

        # ✅ 상태에 따라 end_color 설정
        theme = THEME_COLORS.get(self.current_theme, THEME_COLORS["basic"])
        end_color = (
            theme['button_disible_bg'] if not widget.isEnabled()
            else theme['button_bg']
        )

        # ✅ 기존 애니메이션 중단
        if hasattr(widget, "animation_thread") and widget.animation_thread.isRunning():
            widget.animation_thread.stop()

        # ✅ 새 애니메이션 시작
        widget.animation_thread = AnimationThread(widget, end_color)
        widget.animation_thread.update_signal.connect(
            lambda color: self.update_widget_style(widget, color)
        )
        widget.animation_thread.start()
    
    def update_widget_style(self, widget, new_bg_color):
        """ ✅ 기존 스타일을 유지하면서 `background-color`만 업데이트 """
        existing_style = widget.styleSheet()  # 🔥 기존 스타일 가져오기
        updated_style = re.sub(r"background-color:\s*#[0-9A-Fa-f]{6};", f"background-color: {new_bg_color};", existing_style)

        if not re.search(r"background-color:\s*#[0-9A-Fa-f]{6};", existing_style):
            # ✅ 만약 기존에 `background-color`가 없었다면 추가
            updated_style += f" background-color: {new_bg_color};"

        widget.setStyleSheet(updated_style)  # 🔥 스타일 업데이트
    
    def Theme_Changed(self, theme):
        if theme == "Default":
            self.current_theme = "basic"
        elif theme == "Dark":
            self.current_theme = "dark"
        elif theme == "Emerald":
            self.current_theme = "cyan"
        elif theme == "Pink":
            self.current_theme = "pink"
        elif theme == "Evening_Sky":
            self.current_theme = "blue"
        elif theme == "Campfire_Glow":
            self.current_theme = "fire"
        elif theme == "Magma":
            self.current_theme = "magma"
        elif theme == "Ice":
            self.current_theme = "ice"
        elif theme == "Space":
            self.current_theme = "space"
        elif theme == "Forest":
            self.current_theme = "forest"
        elif theme == "Rainy_Day":
            self.current_theme = "rainy"
        elif theme == "Desert":
            self.current_theme = "desert"
        elif theme == "Choco":
            self.current_theme = "choco"
        elif theme == "Navy_Admiral":
            self.current_theme = "admiral"
        elif theme == "Royal_Scenery":
            self.current_theme = "royal"
        elif theme == "Clerical_Robe":
            self.current_theme = "priest"
        elif theme == "Ancient_Egypt":
            self.current_theme = "egyptian"
        elif theme == "Gemstone":
            self.current_theme = "gems"
        elif theme == "Go_Stones":
            self.current_theme = "baduk_stone"
        else:
            self.current_theme = "basic"
            
        self.apply_theme(self.current_theme)
        self.theme_hover_refresher()
    
    def apply_theme_toButtons(self, theme_name, target_widget=None):
        theme = THEME_COLORS.get(theme_name, "basic")
        font_family = QApplication.font().family()
        if target_widget is None:
            target_widget = self
        target_widget.setStyleSheet(f"""
            QPushButton {{
                font-family: {font_family};
                background-color: {theme['button_bg']};
                color: {theme['button_text']};
                border: 0px solid #4F4F4F;
                border-radius: 4px;
                font-size: 12px;
                            padding-left: 15px; /* 왼쪽에만 15px 패딩 */
                            padding-right: 15px; /* 오른쪽에만 10px 패딩 */
                            padding-top: 7px;    /* 위쪽에만 5px 패딩 */
                            padding-bottom: 7px; /* 아래쪽에만 5px 패딩 */
            }}

            QPushButton:hover {{
                color: {theme['button_hover_text']};
                background-color: {theme['button_hover_bg']};
            }}
                
            QPushButton:disabled {{
                color: {theme['button_disible_text']};
                background-color: {theme['button_disible_bg']};
            }}

        """)

    def apply_theme(self, theme_name, target_widget=None):
        self.disconnect_events()
        theme = THEME_COLORS.get(theme_name, "basic")
        
        if target_widget is None:
            target_widget = self
            
        self.increase_font_size(self.tbWordList)
        self.decrease_font_size(self.tbWordList)
            
        """CSS 스타일 시트를 적용하여 테마 변경"""
        target_widget.setStyleSheet(f"""
            QMainWindow {{
                background-color: {theme["gradient_bg"]};
                color: {theme['main_text']};
            }}
               
            QToolTip {{
                color: {theme['main_text']};
                background-color: {theme['main_bg']};
                border: 0px solid white;
                border-radius: 4px;
            }}
    
            QLabel {{
                background-color: transparent; 
                color: {theme['label_text']};
            }}
            
            QProgressBar {{
                border: 0px solid #555;
                border-radius: 4px;
                background-color: {theme['button_bg']};
                text-align: center;  /* 가운데 정렬 */
                color: {theme['button_text']};
            }}
            
            QProgressBar::chunk {{
                background-color: {theme['button_disible_bg']}; /* 오렌지 색 */
                border-radius: 4px;
            }}

            QDialog {{
                background-color: {theme["gradient_bg"]};
                color: {theme['main_text']};
            }}
            
            QLineEdit {{
                background-color: {theme['textedit_bg']};
                color: {theme['textedit_text']};
                border-radius: 4px; /* 모서리 둥글게 */           
                border: 0px solid #545454;            
            }}
                               
            QRadioButton {{
                color: {theme['label_text']};
            }}
                               
            QPlainTextEdit {{
                background-color: {theme['textedit_bg']};
                color: {theme['textedit_text']};
                border-radius: 8px; /* 모서리 둥글게 */           
                border: 0px solid #545454;            
            }}  
                               
            QTableWidget {{
                background-color: {theme['main_bg']};
                color: {theme['main_text']};
                border: 0px solid #4F4F4F; 
                border-radius: 8px; /* 모서리 둥글게 */           
            }}
                               
            /* QTableWidget의 세로 스크롤바 스타일 */
            QTableWidget QScrollBar:vertical {{
                background-color: {theme['main_text']};
                border-radius: 8px; /* 모서리 둥글게 */
                border: 0px solid #545454;            
                width: 12px;  /* 스크롤바 너비 */
            }}

            QTableWidget QScrollBar::handle:vertical {{
                background-color: {theme['scroll']};
                min-height: 20px;  /* 스크롤 핸들의 최소 높이 */
                border: none; /* 기존 테두리 제거 */
                border-radius: 6px;  /* 스크롤 핸들의 모서리 반경 */
            }}

            QTableWidget QScrollBar::add-line:vertical,
            QTableWidget QScrollBar::sub-line:vertical {{
                background: none;
                height: 0px;
            }}

            /* QTableWidget의 가로 스크롤바 스타일 */
            QTableWidget QScrollBar:horizontal {{
                background-color: {theme['main_text']};
                border: 0px solid #333333;       /* 헤더 테두리 */
                border-radius: 8px; /* 모서리 둥글게 */           
                height: 12px;
            }}

            QTableWidget QScrollBar::handle:horizontal {{
                background-color: {theme['scroll']};
                min-width: 20px;
                border: none; /* 기존 테두리 제거 */
                border-radius: 6px;
            }}

            QTableWidget QScrollBar::add-line:horizontal,
            QTableWidget QScrollBar::sub-line:horizontal {{
                background: none;
                border: none; /* 기존 테두리 제거 */
                border-radius: 8px; /* 모서리 둥글게 */           
                width: 0px;
            }} 
                               
            QHeaderView::section {{
                background-color: {theme['table_headerview_bg']};       /* 헤더 배경색 */
                color: {theme['table_headerview_text']};
                border: 0px solid #333333;       /* 헤더 테두리 */
                border-radius: 8px; /* 모서리 둥글게 */           
            }}
                               
            QHeaderView::section:horizontal {{
                background-color: {theme['table_headerview_bg']};       /* 헤더 배경색 */
                color: {theme['table_headerview_text']};
                border: 0px solid #333333;       /* 헤더 테두리 */
                border-radius: 8px; /* 모서리 둥글게 */           
            }}

            QHeaderView::section:vertical {{
                background-color: {theme['table_headerview_bg']};       /* 헤더 배경색 */
                color: {theme['table_headerview_text']};
                border: 0px solid #333333;       /* 헤더 테두리 */
                border-radius: 8px; /* 모서리 둥글게 */           
            }}
                
            /* 헤더 남은 여백 색상 및 셀 테두리 */
            QHeaderView {{
                background-color: {theme['table_headerview_bg']};       /* 헤더 배경색 */
                color: {theme['table_headerview_text']};
                border: 0px solid #323232;
                border-radius: 8px; /* 모서리 둥글게 */           
            }}
                               
            QTableCornerButton::section {{
                background-color: {theme['table_headerview_bg']};       /* 헤더 배경색 */
                border: 0px solid #323232;
                border-radius: 8px; /* 모서리 둥글게 */           
            }}
            
            /* QCheckBox의 글자색 */
            QCheckBox {{
                color: {theme['label_text']};
            }}
                               
            QComboBox QAbstractItemView {{
                background-color: {theme['main_bg']};        /* 드롭다운 목록 배경 */
                selection-background-color: {theme['drop_down_select_bg']};
                selection-color: {theme['drop_down_select_text']};
                color: {theme['main_text']};
                            border: 0px solid #1F1F1F;        /* 드롭다운 외곽선 */
                            border-radius: 4px; /* 모서리 둥글게 */           
                            font-family: Arial;               /* 드롭다운 항목 폰트 종류 */
                            font-size: 12px;                  /* 드롭다운 항목 폰트 크기 */
            }}
                              
            /* QComboBox 드롭다운 리스트의 세로 스크롤바 스타일 */
            QComboBox QAbstractItemView QScrollBar:vertical {{
                background-color: {theme['main_text']};
                            width: 12px;  /* 스크롤바 너비 */
            }}

            QComboBox QAbstractItemView QScrollBar::handle:vertical {{
                background-color: {theme['scroll']};
                            min-height: 20px;  /* 스크롤 핸들의 최소 높이 */
                            border-radius: 6px;  /* 스크롤 핸들의 모서리 반경 */
            }}

            QComboBox QAbstractItemView QScrollBar::add-line:vertical,
            QComboBox QAbstractItemView QScrollBar::sub-line:vertical {{
                background: none;
                height: 0px;
            }}
            
            QComboBox::drop-down {{
                            background: none; /* 배경 제거 */
                            border: none; /* 테두리 제거 */
                            width: 0px; /* 화살표 영역 크기 0으로 설정 */
            }}
            QComboBox::down-arrow {{
                            image: none;  /* 화살표 아이콘 삭제 */
            }}
            
            QSlider::groove:horizontal {{
                border: 1px solid #444;
                background: {theme['button_bg']};  /* 슬라이드 바(트랙) 색상 */
                            height: 8px;  /* 바의 높이 */
                            border-radius: 4px;  /* 모서리 둥글게 */
            }}

            QSlider::handle:horizontal {{
                background: {theme['button_hover_text']};  /* 핸들 색상 (오렌지) */
                border: 2px solid #666;
                            width: 14px;  /* 핸들 크기 */
                            margin: -4px 0;  /* 핸들 위치 조정 */
                            border-radius: 8px;  /* 핸들 둥글게 */
            }}

            QSlider::sub-page:horizontal {{
                background: {theme['button_hover_text']};  /* 슬라이드 이동한 부분 색상 (파란색) */
                border-radius: 4px;
            }}

            QSlider::add-page:horizontal {{
                background: {theme['button_disible_bg']};  /* 슬라이드 이동하지 않은 부분 색상 */
                border-radius: 4px;
            }}
            
            QListWidget {{
                background-color: {theme['button_disible_bg']};  /* 배경색 */
                color: {theme['main_text']};             /* 글자색 */
                            border: 0px solid #555555;  /* 테두리 */
                            border-radius: 5px;         /* 모서리 둥글게 */
                            padding: 5px;               /* 내부 여백 */
            }}

            QListWidget::item {{
                            padding: 8px;               /* 아이템 내부 여백 */
                            border-bottom: 1px solid #444444; /* 아이템 구분선 */
            }}

            QListWidget::item:selected {{
                background-color: {theme['drop_down_select_bg']};  /* 선택된 아이템 배경색 */
                color: {theme['drop_down_select_text']};             /* 선택된 아이템 글자색 */
                border-radius: 5px;
            }}

            QListWidget::item:hover {{
                background-color: {theme['button_hover_bg']};  /* 마우스 오버 시 배경색 */
                color: {theme['button_hover_text']};
            }}

            QListWidget::item:disabled {{
                color: {theme['button_disible_bg']}; /* 비활성화된 항목 */
            }}

            QListWidget::item:focus {{
                background-color: {theme['button_hover_bg']}; /* 포커스된 아이템 */
                color: {theme['button_hover_text']};
            }}            
            QListWidget QScrollBar:vertical {{
                border: none;
                background-color: {theme['scroll']};
                            width: 12px; /* 스크롤바 너비 */
                            margin: 2px 0px 2px 0px; /* 위아래 여백 */
            }}

            QListWidget QScrollBar::handle:vertical {{
                background-color: {theme['button_text']};
                min-height: 20px;
                border-radius: 6px;
            }}

            QListWidget QScrollBar::handle:vertical:hover {{
                background-color: {theme['main_text']};
            }}

            QListWidget QScrollBar::add-line:vertical,
            QListWidget QScrollBar::sub-line:vertical {{
                background-color: none;
                border: none;
            }}

            QListWidget QScrollBar::add-page:vertical,
            QListWidget QScrollBar::sub-page:vertical {{
                background-color: none;
            }}
            QListWidget QScrollBar:horizontal {{
                border: none;
                background-color: {theme['scroll']};
                height: 12px; /* 스크롤바 높이 */
                margin: 0px 2px 0px 2px;
            }}

            QListWidget QScrollBar::handle:horizontal {{
                background-color: {theme['button_text']};
                min-width: 20px;
                border-radius: 6px;
            }}

            QListWidget QScrollBar::handle:horizontal:hover {{
                background-color: {theme['main_text']};
            }}

            QListWidget QScrollBar::add-line:horizontal,
            QListWidget QScrollBar::sub-line:horizontal {{
                background-color: none;
                border: none;
            }}

            QListWidget QScrollBar::add-page:horizontal,
            QListWidget QScrollBar::sub-page:horizontal {{
                background-color: none;
            }}
            QPushButton {{
                font-family: "Dotum";               
                background-color: {theme['button_bg']};
                color: {theme['button_text']};
                border: 0px solid #4F4F4F;
                border-radius: 4px;
                font-size: 12px;
                            padding-left: 5px; /* 왼쪽에만 15px 패딩 */
                            padding-right: 5px; /* 오른쪽에만 10px 패딩 */
                            padding-top: 3px;    /* 위쪽에만 5px 패딩 */
                            padding-bottom: 3px; /* 아래쪽에만 5px 패딩 */
            }}

            QPushButton:hover {{
                color: {theme['button_hover_text']};
                background-color: {theme['button_hover_bg']};
            }}
                
            QPushButton:disabled {{
                color: {theme['button_disible_text']};
                background-color: {theme['button_disible_bg']};
            }}
            QComboBox {{
                background-color: {theme['button_bg']};
                color: {theme['button_text']};
                border: 0px inset #434343;
                border-radius: 4px; /* 모서리 둥글게 */           
            }}

            QComboBox:hover {{
                border: 0px inset #545454;
                color: {theme['button_hover_text']};
                background-color: {theme['button_hover_bg']};
            }}
                               
            QComboBox:disabled {{
                border: 0px inset #545454;
                color: {theme['button_disible_text']};
                background-color: {theme['button_disible_bg']};
            }}
            
            """)
        
        self.title_bar.title.setStyleSheet(f"""
            QWidget {{
                background-color: {theme["main_bg"]};
                color: {theme['main_text']};
            }}
            QLabel {{
                background-color: {theme['main_bg']}; 
                color: {theme['label_text']};
                border-radius: 4px;
            }}
            """)
        
        self.title_bar.setStyleSheet(f"""
            QWidget {{
                background-color: {theme["main_bg"]};
                color: {theme['main_text']};
            }}
            QLabel {{
                background-color: {theme['main_bg']}; 
                color: {theme['label_text']};
            }}
            QPushButton {{
                font-family: "Dotum";               
                background-color: {theme['button_bg']};
                color: {theme['button_text']};
                border: 0px solid #4F4F4F;
                border-radius: 4px;
                font-size: 12px;
                padding-left: 5px; /* 왼쪽에만 15px 패딩 */
                padding-right: 5px; /* 오른쪽에만 10px 패딩 */
                padding-top: 3px;    /* 위쪽에만 5px 패딩 */
                padding-bottom: 3px; /* 아래쪽에만 5px 패딩 */
            }}

            QPushButton:hover {{
                color: {theme['button_hover_text']};
                background-color: {theme['button_hover_bg']};
            }}
                
            QPushButton:disabled {{
                color: {theme['button_disible_text']};
                background-color: {theme['button_disible_bg']};
            }}
            """)

        # ✅ 캐시를 비우고
        self.font_delegate.invalidate_cache()
        self.font_delegate_learn.invalidate_cache()

        # ✅ 테마도 갱신
        self.font_delegate.theme = theme_name
        self.font_delegate_learn.theme = theme_name

        # ✅ 콤보박스 갱신
        self.cbbFontSetting.view().viewport().update()
        self.cbbFontSetting_tolearn.view().viewport().update()

        self.animated_hover_end(self.title_bar.minimize_button)
        self.animated_hover_end(self.title_bar.maximize_button)
        self.animated_hover_end(self.title_bar.close_button)
        self.apply_theme_to_cbbWordFile()
        
        self.update_cell_background()
        self.update_last_test_colors()
        self.connect_events()
        self.load_font_settings()
        self.txtmeaninginput_style_reset(self.current_theme)
        
        
    def apply_theme_to_cbbWordFile(self):
        theme = THEME_COLORS.get(self.current_theme, THEME_COLORS["basic"])
        model = self.cbbWordFile.model()
        for row in range(model.rowCount()):
            item = model.item(row)
            
            user_data = item.data(Qt.UserRole)
            if user_data in ["go_to_top", "current_folder", "files_in_current_folder", "recent_file", "oldest_tested"]:
                # ✅ 테마에 따른 색상 스타일 적용
                font = item.font()
                font.setBold(True)
                font.setPointSize(14)  # 테마에서 크기 지정

                item.setFont(font)
                item.setTextAlignment(Qt.AlignCenter)
                item.setForeground(QColor(theme["main_text"]))
                item.setBackground(QColor(theme["main_bg"]))

        
    def load_font_settings(self):
        """글씨 크기 설정을 settings.json에서 불러와 적용하는 함수"""
        try:
            # settings.json 불러오기
            with open("settings.json", "r", encoding="utf-8") as f:
                settings = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # 설정 파일이 없거나 잘못된 경우 기본 설정 적용
            settings = {}

        # 기본 폰트 크기
        default_word_font_size = self.txtWordInput.font().pointSize() or 24
        default_meaning_font_size = self.txtMeaningInput.font().pointSize() or 24
        default_table_font_size = self.tbWordList.font().pointSize() or 12

        # 저장된 값이 있으면 적용, 없으면 기본값 적용
        self.word_font_size = settings.get("word_font_size", default_word_font_size)
        self.meaning_font_size = settings.get("meaning_font_size", default_meaning_font_size)
        self.table_font_size = settings.get("table_font_size", default_table_font_size)
        
        # 폰트 크기 UI에 적용
        word_font = self.txtWordInput.font()
        word_font.setPointSize(self.word_font_size)
        self.txtWordInput.setFont(word_font)

        meaning_font = self.txtMeaningInput.font()
        meaning_font.setPointSize(self.meaning_font_size)
        self.txtMeaningInput.setFont(meaning_font)

        table_font = self.tbWordList.font()
        table_font.setPointSize(self.table_font_size)
        self.tbWordList.setFont(table_font)
        
    ###############################################################################
    #--------------------------------인쇄 관련 기능-------------------------------#
    ###############################################################################
    def show_print_options_dialog(self):
        """인쇄 옵션 설정을 위한 대화창 표시"""
        dialog = PrintOptionsDialog(parent=self, theme=self.current_theme, lang=self.current_language)
        self.popupWidget_on_Center(dialog)
        # ✅ 부모 창의 현재 위치 & 크기 가져오기
        if dialog.exec_() == QDialog.Accepted:
            options = dialog.get_options()
            self.print_selected_columns(options)
            
    def popupWidget_on_Center(self, widget):
        parent_rect = self.geometry()
        parent_center_x = parent_rect.x() + parent_rect.width() // 2
        parent_center_y = parent_rect.y() + parent_rect.height() // 2

        # ✅ 다이얼로그 크기 고려하여 정확한 중앙 위치 계산
        dialog_x = parent_center_x - (widget.width() // 2)
        dialog_y = parent_center_y - (widget.height() // 2)

        widget.move(dialog_x, dialog_y)

    def print_selected_columns(self, options):
        """📄 선택된 옵션에 따라 단어와 뜻을 좌우로 인쇄"""
        document = QTextDocument()
        cursor = QTextCursor(document)
        font_size = options['font_size']

        # 📐 테이블 서식 설정 (좌우 2열, 가로 너비 100%)
        table_format = QTextTableFormat()
        table_format.setAlignment(Qt.AlignLeft)
        table_format.setCellPadding(5)
        table_format.setCellSpacing(0)
        table_format.setBorder(0)
        table_format.setColumnWidthConstraints([
            QTextLength(QTextLength.PercentageLength, 50),
            QTextLength(QTextLength.PercentageLength, 50)
        ])

        # ✍️ 글자 스타일 설정
        text_format = QTextCharFormat()
        text_format.setFont(QFont("Arial", font_size))

        # ✏️ 테이블 삽입 (조건에 따라 열 개수 다르게)
        if options['print_option'] == 'both':
            table = cursor.insertTable(self.tbWordList.rowCount(), 2, table_format)
        else:
            table = cursor.insertTable(self.tbWordList.rowCount(), 1, table_format)

        self.disconnect_events()
        # 🧾 테이블에 데이터 채우기
        for row in range(self.tbWordList.rowCount()):
            word_item = self.tbWordList.item(row, 1)
            meaning_item = self.tbWordList.item(row, 2)

            if options['print_option'] == 'word' and word_item:
                cursor.setCharFormat(text_format)
                cursor.insertText(word_item.text())
                cursor.movePosition(QTextCursor.NextCell)

            elif options['print_option'] == 'meaning' and meaning_item:
                cursor.setCharFormat(text_format)
                cursor.insertText(meaning_item.text())
                cursor.movePosition(QTextCursor.NextCell)

            elif options['print_option'] == 'both' and word_item and meaning_item:
                cursor.setCharFormat(text_format)
                cursor.insertText(word_item.text())
                cursor.movePosition(QTextCursor.NextCell)

                cursor.setCharFormat(text_format)
                cursor.insertText(meaning_item.text())
                cursor.movePosition(QTextCursor.NextCell)

        self.connect_events()
        # 🖨️ 프린터 설정 및 인쇄
        printer = QPrinter()
        dialog = QPrintDialog(printer)
        if dialog.exec_() == QPrintDialog.Accepted:
            document.print_(printer)
        
    ###############################################################################
    #--------------------------------인쇄 관련 기능-------------------------------#
    ###############################################################################
    
    ###############################################################################
    #--------------------------------녹음 관련 기능-------------------------------#
    ###############################################################################

    def show_overlay(self):
        """ 🔴 녹음 중 화면 오버레이 표시 """
        translated = LANGUAGES[self.current_language]
        font_family = QApplication.font().family()
        self.overlay = QWidget(self)
        self.overlay.setGeometry(0, 0, self.width(), self.height())
        self.overlay.setStyleSheet("background-color: rgba(0, 0, 0, 200);")
        self.overlay.show()

        # 🔴 녹음 중 표시
        self.overlay_label = QLabel(translated["Custom_QDialog_label_content"]["show_overlay_recording"], self.overlay)
        self.overlay_label.setStyleSheet(f"color: red; font-size: 24px; font-weight: bold; font-family: {font_family};")
        self.overlay_label.setAlignment(Qt.AlignCenter)
        self.overlay_label.setGeometry(0, self.height() // 2 - 25, self.width(), 50)
        self.overlay_label.raise_()  # ✅ 글씨를 위로 올림
        self.overlay_label.show()  # ✅ QLabel 강제 표시

        # ESC 안내 문구
        self.esc_label = QLabel(translated["Custom_QDialog_label_content"]["show_overlay_press_ESC"], self.overlay)
        self.esc_label.setStyleSheet(f"color: white; font-size: 18px; font-family: {font_family};")
        self.esc_label.setAlignment(Qt.AlignCenter)
        self.esc_label.setGeometry(0, self.height() - 80, self.width(), 30)
        self.esc_label.raise_()  # ✅ 글씨를 위로 올림
        self.esc_label.show()  # ✅ QLabel 강제 표시
        
    def hide_overlay(self):
        """ 🎯 녹음 종료 후 화면을 가리는 오버레이 제거 """
        if hasattr(self, "overlay") and self.overlay:  # ✅ overlay가 존재하는 경우에만 제거
            self.overlay.deleteLater()  # ✅ Qt 메모리 관리 방식으로 위젯 삭제
            self.overlay = None  # ✅ 변수 초기화
            #print("🛑 녹음 오버레이 제거 완료")
        
    def show_device_selection_dialog(self):
        """녹음 장치 선택을 위한 대화창을 표시하고 장치를 선택합니다."""
        translated = LANGUAGES[self.current_language]
        dialog = ThemedDialog(translated["Custom_QDialog_label_title"]["text_show_device_selection_dialog"], self, self.current_theme)
        
        # 장치 목록을 QListWidget으로 표시
        device_list_widget = QListWidget(dialog)
        devices = self.recorder.get_device_list()
        for name, device_id in devices:
            device_list_widget.addItem(f"{name} (ID: {device_id})")
        device_list_widget.setStyleSheet(self.styleSheet())    

        # 선택 및 취소 버튼
        select_button = ThemedButton(translated["Custom_QDialog_buttons"]["text_select"], dialog, self.current_theme)
        select_button.clicked.connect(lambda: self.select_device(device_list_widget, dialog))
        cancel_button = ThemedButton(translated["Custom_QDialog_buttons"]["text_cancel"], dialog, self.current_theme)
        cancel_button.clicked.connect(lambda: (dialog.reject(), setattr(self.recorder, "recording", False)))
        self.apply_hover_events(select_button, self.animated_hover_start, self.animated_hover_end)
        self.apply_hover_events(cancel_button, self.animated_hover_start, self.animated_hover_end)

        # 레이아웃 구성
        dialog.content_layout.addWidget(device_list_widget)
        dialog.content_layout.addWidget(select_button)
        dialog.content_layout.addWidget(cancel_button)
        
        dialog.exec_()
        
    def toggle_recording(self):
        """녹음 시작/중지를 토글합니다."""
        if self.recorder.recording:
            # 녹음 중지 및 데이터 가져오기
            recorded_data = self.recorder.stop_recording()
            self.recorder.recording = False

            # 편집/저장 선택 팝업 띄우기
            self.show_edit_or_save_dialog(recorded_data)
        else:
            # 장치 선택 대화창 표시
            self.show_device_selection_dialog()
            if not hasattr(self, 'selected_device'):
                return
        
            # 선택된 장치로 녹음 시작
            self.recorder.start_recording(self.selected_device)
            self.recorder.recording = True
        
    def select_device(self, device_list_widget, dialog):
        """장치를 선택하고 대화창을 닫습니다."""
        translated = LANGUAGES[self.current_language]
        selected_item = device_list_widget.currentItem()
        if selected_item:
            self.selected_device = int(selected_item.text().split("ID: ")[-1].strip(")"))
            self.show_overlay()
            dialog.accept()  # 대화창을 닫음
        else:
            warn_dialog = ThemedDialog(title=translated["Custom_QDialog_label_title"]["text_select_device"], parent=self, theme=self.current_theme)
            warn_label = QLabel(translated["Custom_QDialog_label_content"]["select_device_choose_device"], warn_dialog)
            warn_label.setAlignment(Qt.AlignCenter)
        
            # 버튼 추가
            btn_ok = QPushButton(translated["Custom_QDialog_buttons"]["text_ok"], warn_dialog)
            btn_ok.clicked.connect(warn_dialog.accept)

            # 레이아웃 설정
            warn_dialog.content_layout.addWidget(warn_label)
            warn_dialog.content_layout.addWidget(btn_ok, alignment=Qt.AlignCenter)

            # 테마 적용 및 실행
            self.apply_theme(self.current_theme, warn_dialog)
            self.apply_theme_toButtons(self.current_theme, btn_ok)
            self.apply_hover_events(btn_ok, self.animated_hover_start, self.animated_hover_end)

            warn_dialog.exec_()
            return
    
    def show_edit_or_save_dialog(self, recorded_data):
        """녹음 후 편집/저장을 선택하는 테마 다이얼로그를 띄웁니다."""
        translated = LANGUAGES[self.current_language]
        if not recorded_data:
            return

        # 🎯 ThemedDialog 사용하여 다이얼로그 생성
        dialog = ThemedDialog(title=translated["Custom_QDialog_label_title"]["text_recording_complete"], parent=self, theme=self.current_theme)

        # 🔥 QLabel 추가 (타이틀바 아래에 텍스트 배치)
        text_label = QLabel(translated["Custom_QDialog_label_content"]["show_edit_or_save_dialog_recording_done"], dialog)
        text_label.setAlignment(Qt.AlignCenter)
        dialog.content_layout.addWidget(text_label)

        # ✅ 버튼 추가 (편집 / 저장 / 취소)
        btn_edit = QPushButton(translated["Custom_QDialog_buttons"]["text_edit"], dialog)
        btn_edit.setToolTip(translated["Custom_QDialog_buttons"]["text_edit_t"])
        btn_edit.clicked.connect(lambda: dialog.done(1))  # ✅ accept() 대신 특정 값 반환
        btn_edit.clicked.connect(self.hide_overlay)

        btn_save = QPushButton(translated["Custom_QDialog_buttons"]["text_save"], dialog)
        btn_save.setToolTip(translated["Custom_QDialog_buttons"]["text_save_t"])
        btn_save.clicked.connect(lambda: dialog.done(2))
        btn_save.clicked.connect(self.hide_overlay)

        btn_cancel = QPushButton(translated["Custom_QDialog_buttons"]["text_cancel"], dialog)
        btn_cancel.setToolTip(translated["Custom_QDialog_buttons"]["text_cancel_t"])
        btn_cancel.clicked.connect(lambda: dialog.done(0))

        # ✅ 버튼을 다이얼로그에 추가
        dialog.content_layout.addWidget(btn_edit)
        dialog.content_layout.addWidget(btn_save)
        dialog.content_layout.addWidget(btn_cancel)

        # ✅ 테마 적용 및 애니메이션 설정
        self.apply_theme(self.current_theme, dialog)
        self.apply_theme_toButtons(self.current_theme, btn_edit)
        self.apply_theme_toButtons(self.current_theme, btn_save)
        self.apply_theme_toButtons(self.current_theme, btn_cancel)
        self.apply_hover_events(btn_edit, self.animated_hover_start, self.animated_hover_end)
        self.apply_hover_events(btn_save, self.animated_hover_start, self.animated_hover_end)
        self.apply_hover_events(btn_cancel, self.animated_hover_start, self.animated_hover_end)

        # ✅ 다이얼로그 실행 및 선택값 반환
        result = dialog.exec_()

        # ✅ 사용자의 선택에 따라 동작 수행
        if result == 1:
            self.open_audio_editor(recorded_data)  # 🎬 편집창 열기
        elif result == 2:
            self.recorder.open_save_dialog(recorded_data)  # 💾 저장창 열기
        else:
            dialog.close()
            self.hide_overlay()
           
    def open_audio_editor(self, recorded_data):
        """📌 녹음 데이터를 AudioEditor로 전달하여 편집 창 열기 (파일 vs. AudioSegment 자동 판별)"""

        # ✅ recorded_data가 파일 경로인지, AudioSegment인지 판별
        if isinstance(recorded_data, str):  # ✅ 문자열이면 파일 경로
            #print(f"📌 MP3 파일 경로 감지: {recorded_data}")
            try:
                recorded_data = AudioSegment.from_file(recorded_data, format="mp3")  # ✅ MP3 → AudioSegment 변환
            except Exception as e:
                #print(f"🚨 MP3 파일 로드 실패: {e}")
                return  # ✅ 파일 로드 실패 시 종료
    
        elif not isinstance(recorded_data, AudioSegment):  # ✅ 올바른 타입이 아닐 경우
            print("🚨 지원되지 않는 데이터 유형입니다.")
            return  

        self.recorded_data = recorded_data  # ✅ 변환된 데이터를 저장
        #print(f"📌 오디오 데이터 준비 완료, 그래픽 환경: {self.graphicEnv}")
        
        # ✅ 그래픽 환경에 따라 편집기 선택
        #self.graphicEnv = "Not openGL" #파이그래프 시험용, 강제로 파이그래프 실행
        try:
            if self.graphicEnv == "openGL":
                editor = AudioEditor_openGL(parent=self, data=self.recorded_data, theme_name=self.current_theme, lang=self.current_language)
                editor.update_signal.connect(self.apply_hover_events)
                editor.exec_()
            elif self.graphicEnv == "Not openGL":
                editor = AudioEditor_PyQtGraph(parent=self, data=self.recorded_data, theme_name=self.current_theme, lang=self.current_language)
                editor.update_signal.connect(self.apply_hover_events)
                editor.exec_()
            else:
                print("🚨 그래픽 환경이 설정되지 않았습니다.")
        except Exception as e:
            print(f"🚨 AudioEditor 초기화 중 오류 발생: {e}")
        
    def open_mp3_file_to_audio_editor(self):
        """📌 MP3 파일을 오디오 편집기로 열기 (사용자가 셀을 선택하지 않았을 경우 경고창 표시)"""
        translated = LANGUAGES[self.current_language]
        current_row = self.tbWordList.currentRow()
        current_column = self.tbWordList.currentColumn()

        # ✅ 🔥 사용자가 아무 셀도 선택하지 않은 경우
        if current_row == -1:
            """📌 테마가 적용된 경고 메시지 박스 띄우기 (ThemedButton 활용)"""
            self.show_custom_message(translated["Custom_QDialog_label_title"]["text_warning"], translated["Custom_QDialog_label_content"]["search_selected_word_choose_word"])
            return  # 🚨 함수 종료

        if current_column != 2:
            word_item = self.tbWordList.item(current_row, 1)
            language = self.cbbLangToLearn.currentData()
        else:
            word_item = self.tbWordList.item(current_row, 2)
            language = self.cbbBaseLang.currentData()

        sanitized_text = self.sanitize_filename(word_item.text())
        mp3_file = os.path.join(MP3_FOLDER, f"{sanitized_text}_{language}.mp3")

        if not os.path.exists(mp3_file):
            self.create_audio_file(word_item, language, mp3_file)
        else:
            self.open_audio_editor(mp3_file)
        
    ###############################################################################
    #--------------------------------녹음 관련 기능-------------------------------#
    ###############################################################################
    
    ###############################################################################
    #--------------------------------자동 재생 관련 기능--------------------------#
    ###############################################################################
    
    def on_preset_changed(self):
        selected_preset = self.cbbPitchPreset.currentData()

        if selected_preset == "lowest_slow":
            self.txtPitchControler.setText("25")  # 느린 피치 (예: 80%)
            self.txtSpeedControler.setText("150")  # 빠른 속도 (예: 120%)
        elif selected_preset == "lowest_normal":
            self.txtPitchControler.setText("25")  # 기본 피치 (100%)
            self.txtSpeedControler.setText("185")  # 기본 속도 (100%)
        elif selected_preset == "lowest_fast":
            self.txtPitchControler.setText("25")  # 높은 피치 (120%)
            self.txtSpeedControler.setText("350")   # 느린 속도 (80%)
        elif selected_preset == "low_slow":
            self.txtPitchControler.setText("45")  # 기본 피치 (100%)
            self.txtSpeedControler.setText("110")  # 기본 속도 (100%)
        elif selected_preset == "low_normal":
            self.txtPitchControler.setText("45")  # 높은 피치 (120%)
            self.txtSpeedControler.setText("150")   # 느린 속도 (80%)
        elif selected_preset == "low_fast":
            self.txtPitchControler.setText("45")  # 기본 피치 (100%)
            self.txtSpeedControler.setText("250")  # 기본 속도 (100%)
        elif selected_preset == "slow":
            self.txtPitchControler.setText("55")  # 높은 피치 (120%)
            self.txtSpeedControler.setText("80")   # 느린 속도 (80%)
        elif selected_preset == "normal":
            self.txtPitchControler.setText("55")  # 기본 피치 (100%)
            self.txtSpeedControler.setText("100")  # 기본 속도 (100%)
        elif selected_preset == "fast":
            self.txtPitchControler.setText("55")  # 높은 피치 (120%)
            self.txtSpeedControler.setText("200")   # 느린 속도 (80%)
        elif selected_preset == "high_slow":
            self.txtPitchControler.setText("60")  # 기본 피치 (100%)
            self.txtSpeedControler.setText("80")  # 기본 속도 (100%)
        elif selected_preset == "high_normal":
            self.txtPitchControler.setText("60")  # 높은 피치 (120%)
            self.txtSpeedControler.setText("100")   # 느린 속도 (80%)
        elif selected_preset == "high_fast":
            self.txtPitchControler.setText("60")  # 기본 피치 (100%)
            self.txtSpeedControler.setText("160")  # 기본 속도 (100%)
        elif selected_preset == "random_preset":
            # 프리셋 중 랜덤으로 하나 선택
            selected_preset = random.choice(list(self.randomePresetsList.keys()))

            # 선택된 프리셋에 따라 피치와 속도 설정
            pitch, speed = self.randomePresetsList[selected_preset]

            # 피치와 속도를 적용
            self.txtPitchControler.setText(pitch)
            self.txtSpeedControler.setText(speed)
        elif selected_preset == "everytime_random_preset":
            # 프리셋 중 랜덤으로 하나 선택
            selected_preset = random.choice(list(self.randomePresetsList.keys()))

            # 선택된 프리셋에 따라 피치와 속도 설정
            pitch, speed = self.randomePresetsList[selected_preset]

            # 피치와 속도를 적용
            self.txtPitchControler.setText(pitch)
            self.txtSpeedControler.setText(speed)
        elif selected_preset == "random_pitch":
            random_pitch = random.randint(25, 120)
            self.txtPitchControler.setText(str(random_pitch))  # 기본 피치 (100%)
        elif selected_preset == "everytime_random_pitch":
            random_pitch = random.randint(25, 120)
            self.txtPitchControler.setText(str(random_pitch))  # 기본 피치 (100%)
        elif selected_preset == "random_speed":
            random_seped = random.randint(80, 500)
            self.txtSpeedControler.setText(str(random_seped))  # 기본 피치 (100%)
        elif selected_preset == "everytime_random_speed":
            random_seped = random.randint(80, 500)
            self.txtSpeedControler.setText(str(random_seped))  # 기본 피치 (100%)
        elif selected_preset == "random_pitch_speed":
            random_pitch = random.randint(25, 120)
            random_seped = random.randint(80, 500)
            self.txtPitchControler.setText(str(random_pitch))  # 기본 피치 (100%)
            self.txtSpeedControler.setText(str(random_seped))  # 기본 피치 (100%)
        elif selected_preset == "everytime_random_pitch_speed":
            random_pitch = random.randint(25, 120)
            random_seped = random.randint(80, 500)
            self.txtPitchControler.setText(str(random_pitch))  # 기본 피치 (100%)
            self.txtSpeedControler.setText(str(random_seped))  # 기본 피치 (100%)
        elif selected_preset == "user":
            # 사용자 지정일 경우 기존 값 그대로 유지 (사용자가 직접 입력)
            pass
    
    def toggle_auto_play(self):
        """자동재생 토글 함수"""
        texts = LANGUAGES.get(self.current_language, LANGUAGES["한국어"])  # 기본은 한글
        if self.is_auto_playing:
            self.btnAutoPlay.setToolTip(texts["btnAutoPlay_t"])
            self.btnAutoPlay.setText(texts["btnAutoPlay"])
            self.btnAutoPlay.userData = "stop"
            self.stop_auto_play()  # 자동재생을 중단
        else:
            self.btnAutoPlay.setToolTip(texts["btnAutoPlay_stop_t"])
            self.btnAutoPlay.setText(texts["btnAutoPlay_stop"])
            self.btnAutoPlay.userData = "play"
            self.start_auto_play()  # 자동재생을 시작
        
    def start_auto_play(self):
        """자동재생을 시작하는 함수 (동적 간격 적용)"""
        translated = LANGUAGES[self.current_language]
        self.is_auto_playing = True  # 상태를 False로 설정
        self.auto_play_timer = QTimer(self)
        self.auto_play_timer.timeout.connect(self.play_next_audio)

        # 재생 대상 필터링
        self.filtered_word_rows = self.get_filtered_rows()
        #print(f"선출된 단어: {self.filtered_word_rows}")

        if not self.filtered_word_rows:
            self.show_custom_message(translated["Custom_QDialog_label_title"]["text_aleart"], translated["Custom_QDialog_label_content"]["start_auto_play_not_condition"])
            self.toggle_auto_play()
            return

        # 첫 번째 단어 선택
        first_row = self.filtered_word_rows[0]
        self.tbWordList.setCurrentCell(first_row, 1)

        # 첫 번째 음성 파일 재생 시간 확인 및 타이머 설정
        word_item = self.tbWordList.item(first_row, 1)
        lang_code = self.cbbLangToLearn.currentData()
        user_delay_ms = self.get_user_defined_delay()
        if word_item:
            word_text = word_item.text()
            duration_ms = self.get_audio_duration(word_text, lang_code)  # 밀리초 단위 길이 반환

            # 타이머 시작 (재생 시간에 약간의 여유 추가)
            self.auto_play_timer.start(duration_ms + user_delay_ms)  # 0.5초 여유 추가
            
    def get_user_defined_delay(self):
        """
        사용자가 지정한 추가 지연 시간(ms)을 반환합니다.
        """
        try:
            user_input = self.txtAutoAudioDuration.text()  # QLineEdit에서 입력된 값 가져오기
            delay_seconds = float(user_input)  # 입력값을 초로 변환
            delay_ms = int(delay_seconds * 1000)  # 밀리초로 변환
            return max(0, delay_ms)  # 음수 값은 0으로 반환
        except ValueError:
            # 잘못된 입력값일 경우 기본 500ms 반환
            return 500
    
    def get_audio_duration(self, word_text,lang_code):
        """단어와 언어 코드를 이용해 mp3 파일의 길이를 밀리초 단위로 반환"""
        mp3_file = f"mp3/{word_text}_{lang_code}.mp3"  # mp3 파일 경로 생성
        try:
            audio = AudioSegment.from_file(mp3_file)
            duration_ms = len(audio)  # 재생 시간(밀리초)
            return duration_ms
        except Exception as e:
            #print(f"오디오 파일 로드 중 오류 발생: {e}")
            return 3000  # 기본 3초 반환
    
    def get_filtered_rows(self):
        """조건에 맞는 행 인덱스를 필터링하는 함수"""
        translated = LANGUAGES[self.current_language]
        selected_rows = []

        # 모든 단어 재생 체크박스가 활성화되어 있으면 모든 행 반환
        if self.chbAllWords.isChecked():
            return list(range(self.tbWordList.rowCount()))  # 0부터 rowCount-1까지 모든 행 인덱스를 반환

        selected_rate = int(self.cbbRateFilter.currentText().replace('%', ''))

        self.disconnect_events()
        for row in range(self.tbWordList.rowCount()):
            result_item = self.tbWordList.item(row, 8)  # 8번 컬럼 (정답/오답)
            rate_item = self.tbWordList.item(row, 5)  # 5번 컬럼 (정답률)

            is_incorrect = self.chbOnlyIncorrects.isChecked() and result_item and result_item.text() == translated["Custom_QDialog_label_content"]["show_feedback_var_incor"]
            is_low_rate = self.chbOnlyLowRates.isChecked() and rate_item and rate_item.text().replace('%', '').isdigit() and int(rate_item.text().replace('%', '')) <= selected_rate

            # 오답 또는 정답률 기준 충족 시 추가
            if is_incorrect or is_low_rate:
                selected_rows.append(row)
        self.connect_events()
        return selected_rows

    def stop_auto_play(self):
        """자동재생을 멈추는 함수"""
        if hasattr(self, 'auto_play_timer'):
            self.is_auto_playing = False  # 상태를 False로 전환
            self.auto_play_timer.stop()

    def play_next_audio(self):
        """📌 cbbPlayType 설정과 필터링 조건에 따라 다음 셀로 이동하면서 음성을 재생"""
        if not self.filtered_word_rows:
            return  # 필터링된 단어가 없으면 종료

        current_row = self.tbWordList.currentRow()
        current_column = self.tbWordList.currentColumn()
        user_delay_ms = self.get_user_defined_delay()

        # 콤보박스에서 재생 타입 선택
        play_type = self.cbbPlayType.currentData()

        # ✅ 체크박스 상태에 따라 이동 순서 변경
        if self.chbToReadMeaning.isChecked():
            # 🔄 뜻 → 단어 → 다음 행 뜻
            if current_column == 2:  # 뜻을 읽고 나면 단어로 이동
                word_item = self.tbWordList.item(current_row, 1)
                lang_code = self.cbbLangToLearn.currentData()
                word_text = word_item.text()
                duration_ms = self.get_audio_duration(word_text, lang_code)  # 단어 길이
                self.auto_play_timer.stop()  
                self.tbWordList.setCurrentCell(current_row, 1)  # ✅ 단어로 이동
                self.auto_play_timer.start(duration_ms + user_delay_ms)  
                return  
        else:
            # ✅ 단어 → 다음 행 단어
            if current_column == 1 and self.chbToReadMeaning.isChecked():
                word_item = self.tbWordList.item(current_row, 2)
                lang_code = self.cbbBaseLang.currentData()
                word_text = word_item.text()
                duration_ms = self.get_audio_duration(word_text, lang_code)  # 뜻 길이
                self.auto_play_timer.stop()  
                self.tbWordList.setCurrentCell(current_row, 2)  # ✅ 뜻으로 이동
                self.auto_play_timer.start(duration_ms + user_delay_ms)  
                return

        # ✅ 다음 행 결정
        if play_type == "Descending":
            next_index = (self.filtered_word_rows.index(current_row) + 1) % len(self.filtered_word_rows)
        elif play_type == "Ascending":
            next_index = (self.filtered_word_rows.index(current_row) - 1) % len(self.filtered_word_rows)
        elif play_type == "Random":
            next_index = random.randint(0, len(self.filtered_word_rows) - 1)
        else:
            next_index = (self.filtered_word_rows.index(current_row) + 1) % len(self.filtered_word_rows)

        next_row = self.filtered_word_rows[next_index]

        # ✅ 체크박스가 체크된 경우 뜻 → 단어 순서로 이동
        if self.chbToReadMeaning.isChecked():
            word_item = self.tbWordList.item(next_row, 2)  # 다음 행 뜻 읽기
            lang_code = self.cbbBaseLang.currentData()
        else:
            word_item = self.tbWordList.item(next_row, 1)  # 다음 행 단어 읽기
            lang_code = self.cbbLangToLearn.currentData()

        word_text = word_item.text()
        duration_ms = self.get_audio_duration(word_text, lang_code)  

        self.auto_play_timer.stop()  
        self.tbWordList.setCurrentCell(next_row, 2 if self.chbToReadMeaning.isChecked() else 1)  
        self.auto_play_timer.start(duration_ms + user_delay_ms)  
    
    def get_audio_metadata(self, file_path):
        command = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_streams',
            '-select_streams', 'a',
            file_path
        ]

        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
        metadata = json.loads(result.stdout)

        if 'streams' in metadata:
            audio_streams = metadata['streams']
            if audio_streams:
                # 일반적으로 첫 번째 오디오 스트림을 사용합니다.
                stream = audio_streams[0]
                sample_rate = stream.get('sample_rate')
                channels = stream.get('channels')
                bit_rate = stream.get('bit_rate')
                #print(f"get_audio_metadata - 샘플레이트: {sample_rate}, 채널: {channels}, 비트레이트: {bit_rate}")
                return {
                    'sample_rate': sample_rate,
                    'channels': channels,
                    'bit_rate': bit_rate
                }

        return None

    ###############################################################################
    #--------------------------------자동 재생 관련 기능--------------------------#
    ###############################################################################

    ###############################################################################
    #-------------------------------정렬 관련 기능--------------------------------#
    ###############################################################################

    def setup_table(self):
        """테이블 설정 및 헤더 클릭 이벤트 연결"""
        # 테이블 헤더를 가져옴
        header = self.tbWordList.horizontalHeader()

        # 헤더 클릭 이벤트를 handle_header_click 함수와 연결
        header.sectionClicked.connect(self.handle_header_click)

        # 기본 정렬 방향 설정 (오름차순)
        self.is_descending = False
    
    def handle_header_click(self, column_index):
        """헤더 클릭 시 정렬 처리"""
        self.disconnect_events()
    
        rows = []
        for row in range(self.tbWordList.rowCount()):
            row_data = []
            for col in range(self.tbWordList.columnCount()):
                item = self.tbWordList.item(row, col)
                row_data.append(item.text() if item else "")
            rows.append(row_data)

        def safe_int(val):
            try:
                return int(val.strip().lstrip('\ufeff'))
            except:
                return float('inf')  # 빈값은 맨 뒤로

        # 0번 컬럼은 숫자 정렬
        if column_index == 0:
            rows.sort(
                key=lambda x: safe_int(x[column_index]),
                reverse=self.is_descending
            )

        # 정답 횟수 (4번 컬럼): "정답/총횟수" 형태로 계산
        elif column_index == 4:
            def sort_by_correct_ratio(data):
                try:
                    correct, total = map(int, data.split("/"))
                    return (total - correct, total)  # 정답 차이와 시험 횟수로 정렬
                except ValueError:
                    return (float('inf'), float('inf'))  # 정렬 불가한 값은 끝으로 보냄
            rows.sort(key=lambda x: sort_by_correct_ratio(x[column_index]), reverse=self.is_descending)

        # 정답률 (5번 컬럼): "%"를 떼고 숫자로 처리
        elif column_index == 5:
            rows.sort(key=lambda x: int(x[column_index].replace("%", "")) if x[column_index] else 0, reverse=self.is_descending)

        # 시간 (6번, 7번 컬럼): "hh시간 mm분 ss.sss초"를 초 단위로 변환
        elif column_index in [6, 7]:
            def time_to_seconds(data):
                hour_txt = LANGUAGES[self.current_language]["Custom_QDialog_label_content"]["handle_header_click_h"]
                minute_txt = LANGUAGES[self.current_language]["Custom_QDialog_label_content"]["handle_header_click_m"] 
                second_txt = LANGUAGES[self.current_language]["Custom_QDialog_label_content"]["handle_header_click_s"] 
                try:
                    # "hh시간 mm분 ss.sss초" 형식에서 숫자만 추출
                    pattern = rf'(\d+){hour_txt}\s*(\d+){minute_txt}\s*([\d.]+){second_txt}'
                    match = re.match(pattern, data)
                    if match:
                        hours = int(match.group(1))
                        minutes = int(match.group(2))
                        seconds = float(match.group(3))
                        return hours * 3600 + minutes * 60 + seconds
                    else:
                        return float('inf')  # 잘못된 형식은 끝으로 보냄
                except ValueError:
                    return float('inf')  # 잘못된 형식은 끝으로 보냄
            rows.sort(key=lambda x: time_to_seconds(x[column_index]), reverse=self.is_descending)
    
        # 그 외: 문자 정렬
        else:
            rows.sort(key=lambda x: x[column_index], reverse=self.is_descending)

        # 정렬 후 데이터 테이블에 반영
        self.tbWordList.setRowCount(0)  # 기존 데이터 삭제
        for row_data in rows:
            row_number = self.tbWordList.rowCount()
            self.tbWordList.insertRow(row_number)
            for column_number, data in enumerate(row_data):
                item = QTableWidgetItem(data)
                self.tbWordList.setItem(row_number, column_number, item)

        # 정렬 방향 전환
        self.apply_font_totarget()
        self.apply_font()
        self.is_descending = not self.is_descending
        self.update_cell_background()
        self.update_last_test_colors()
        self.on_rate_filter_changed()
        self.align_cells_width()
        self.connect_events()
    
    ###############################################################################
    #-------------------------------정렬 관련 기능--------------------------------#
    ###############################################################################

    ###############################################################################
    #-------------------------------mp3 파일 삭제 및 제어 기능--------------------#
    ###############################################################################

    # 텍스트박스 값이 변경되면 슬라이드바 업데이트
    def update_slider_from_volume(self):
        volume_value = int(self.txtVolume.text()) * 100  # 정수로 변환 후 슬라이드바에 적용
        self.slbVolume.setValue(volume_value)

    def update_slider_from_pitch(self):
        pitch_value = int(self.txtPitchControler.text()) * 100
        self.slbPitchControler.setValue(pitch_value)

    def update_slider_from_speed(self):
        speed_value = int(self.txtSpeedControler.text()) * 100
        self.slbSpeedControler.setValue(speed_value)

    def delete_temp_a_file(self):
        translated = LANGUAGES[self.current_language]
        temp_folder = os.path.join(os.getcwd(), 'mp3')
        selected_word = self.txtWordInput.toPlainText().strip()
        lang_code = self.cbbLangToLearn.currentData()

        if not selected_word or not lang_code:
            self.show_custom_message(
                translated["Custom_QDialog_label_title"]["text_warning"],
                translated["Custom_QDialog_label_content"]["delete_temp_no_selection"]
            )
            return

        target_filename = f"{selected_word}_{lang_code}.mp3"
        file_path = os.path.join(temp_folder, target_filename)

        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                self.show_custom_message(
                    translated["Custom_QDialog_label_title"]["text_complete"],
                    translated["Custom_QDialog_label_content"]["delete_temp_files_delete_succesed"]
                )
            except Exception as e:
                self.show_custom_message(
                    translated["Custom_QDialog_label_title"]["text_error"],
                    f"{translated['Custom_QDialog_label_content']['delete_temp_files_delete_error']} {e}"
                )
        else:
            self.show_custom_message(
                translated["Custom_QDialog_label_title"]["text_warning"],
                translated["Custom_QDialog_label_content"]["delete_temp_file_not_found"]
            )

    def delete_temp_files(self):
        translated = LANGUAGES[self.current_language]
        temp_folder = os.path.join(os.getcwd(), 'mp3')  # 프로그램의 현재 위치에서 temp 폴더 경로 생성
    
        if os.path.exists(temp_folder):
            try:
                # temp 폴더 안의 모든 파일을 삭제
                for file_name in os.listdir(temp_folder):
                    file_path = os.path.join(temp_folder, file_name)
                
                    if os.path.isfile(file_path):
                        os.remove(file_path)  # 파일 삭제
            
                # 성공 메시지 박스
                self.show_custom_message(translated["Custom_QDialog_label_title"]["text_complete"], translated["Custom_QDialog_label_content"]["delete_temp_files_delete_succesed"])

            except Exception as e:
                # 오류 메시지 박스
                self.show_custom_message(translated["Custom_QDialog_label_title"]["text_error"], f"{translated['Custom_QDialog_label_content']['delete_temp_files_delete_error']} {e}")
        else:
            # temp 폴더가 존재하지 않는 경우 메시지 박스
            self.show_custom_message(translated["Custom_QDialog_label_title"]["text_warning"], translated["Custom_QDialog_label_content"]["delete_temp_no_folder"])
        
    def play_text_as_audio(self, text, language):
        # 텍스트를 음성으로 변환하여 재생
        if not text.strip():  # 빈 문자열인 경우 처리하지 않음
            return

        sanitized_text = self.sanitize_filename(text)
        mp3_file = os.path.join(MP3_FOLDER, f"{sanitized_text}_{language}.mp3")
        
        if not os.path.exists(mp3_file):
            self.create_audio_file(text, language, mp3_file)
        self.play_audio(mp3_file, self.volumeFactor, self.pitchFactor, self.speedFactor)
        
    def create_audio_file(self, text, language, mp3_file):
        """파일이 없으면 음성 파일을 생성, 파일이 있으면 생성하지 않음"""
        if os.path.exists(mp3_file):
            print(f"{mp3_file} 파일이 이미 존재합니다. 파일을 생성하지 않습니다.")
        else:
            # 파일이 없을 경우에만 음성 파일을 생성
            tts = gTTS(text=text, lang=language)
            os.makedirs(MP3_FOLDER, exist_ok=True)
            tts.save(mp3_file)
            #print(f"{mp3_file} 파일을 생성했습니다.")
        
    def play_audio(self, mp3_file, volume_factor=1.0, pitch_factor=1.0, speed_factor=1.0):
        """
        MP3 파일을 받아서 볼륨, 피치, 속도를 적용해 실시간으로 재생하는 함수.
        """
        metadata = self.get_audio_metadata(mp3_file)
        
        # 샘플레이트, 채널, 비트레이트를 가져옴
        sample_rate = metadata.get('sample_rate', 44100)  # 기본값 44100 Hz
        channels = metadata.get('channels', 1)          # 기본 채널 수
        bit_rate = metadata.get('bit_rate', 128000)       # 기본 비트레이트 128 kbps
        
        current_pitch = self.cbbPitchPreset.currentData()
        
        # 프리셋 및 랜덤 속성 설정 (기존 코드 유지)
        if current_pitch == "everytime_random_preset":
            selected_preset = random.choice(list(self.randomePresetsList.keys()))
            pitch, speed = self.randomePresetsList[selected_preset]
            pitch_factor = pitch / 100
            speed_factor = speed / 100
            self.txtPitchControler.setText(str(pitch))
            self.txtSpeedControler.setText(str(speed))
        elif current_pitch == "everytime_random_pitch":
            random_pitch = random.randint(25, 120)
            self.txtPitchControler.setText(str(random_pitch))
            pitch_factor = random_pitch / 100
        elif current_pitch == "everytime_random_speed":
            random_speed = random.randint(80, 500)
            self.txtSpeedControler.setText(str(random_speed))
            speed_factor = random_speed / 100
        elif current_pitch == "everytime_random_pitch_speed":
            random_pitch = random.randint(25, 120)
            random_speed = random.randint(80, 500)
            self.txtPitchControler.setText(str(random_pitch))
            self.txtSpeedControler.setText(str(random_speed))
            pitch_factor = random_pitch / 100
            speed_factor = random_speed / 100

        speed_factor = self.build_atempo_filters(speed_factor)

        if isinstance(speed_factor, list):
            atempo_filters = ",".join([f"atempo={val}" for val in speed_factor])
        else:
            atempo_filters = f"atempo={speed_factor}"

        filter_chain = f"asetrate={float(sample_rate)*1.8375}*{pitch_factor}, {atempo_filters}"

        #print(f"play_audio - 샘플레이트: {float(sample_rate)*1.8375}, 채널: {channels}, 비트레이트: {bit_rate}")

        # ffmpeg 명령을 사용하여 볼륨, 피치, 속도를 조절하고 PCM 데이터로 출력
        command = [
            "ffmpeg",
            "-i", mp3_file,
            "-filter:a", f"volume={volume_factor},{filter_chain}",
            "-f", "s16le",
            "-acodec", "pcm_s16le",  # PCM 데이터로 변환
            "-ac", f"{max(1, channels)}",    # 채널 설정
            "-ar", str(sample_rate),  # 샘플레이트 설정
            "-b:a", str(bit_rate),    # 비트레이트 설정
            "-y", "pipe:1"           # 파이프를 통해 출력
        ]

        # FFmpeg 프로세스를 실행하여 변환된 오디오 데이터를 파이프로 받아옴
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
        audio_data, _ = proc.communicate()

        # NumPy 배열로 변환하여 sounddevice로 재생
        audio_array = np.frombuffer(audio_data, dtype=np.int16)
        sd.play(audio_array, samplerate=float(sample_rate))

    def build_atempo_filters(self, rate):
        filters = []
        while rate < 0.5 and len(filters) < 5:  # 최대 5개까지만 반복
            filters.append("0.5")
            rate *= 2
        filters.append(f"{rate:.6f}")
        return filters

    def create_audio_files_for_table(self):
        """🎵 백그라운드에서 MP3 파일 생성하는 스레드 실행"""
        self.disable_buttons()
        self.progressBar.setValue(0)

        # ✅ 백그라운드 스레드 실행
        self.audio_thread = AudioGenerationThread(
            self, self.tbWordList, self.create_audio_file,
            self.sanitize_filename, MP3_FOLDER,
            self.cbbLangToLearn, self.cbbBaseLang
        )
    
        # ✅ 진행률 업데이트
        self.audio_thread.progress_signal.connect(self.progressBar.setValue)

        # ✅ 작업 완료 시 메시지 박스 표시
        self.audio_thread.finished_signal.connect(self.show_completion_message)

        self.audio_thread.start()
        
    def show_completion_message(self):
        """🎯 모든 MP3 파일 생성 완료 후 메시지 출력"""
        translated = LANGUAGES[self.current_language]
        self.progressBar.setValue(100)
        self.show_custom_message(translated["Custom_QDialog_label_title"]["text_complete"], translated["Custom_QDialog_label_content"]["show_completion_message"])
        self.progressBar.setValue(0)
        self.enable_buttons()
    
    def update_volume(self):
        """슬라이드바 값에 따라 볼륨을 업데이트하는 함수"""
        volume_value = self.slbVolume.value()  # 슬라이드바 값(0~500)을 0.0~5.0으로 변환
        volume_display = f"{volume_value:.0f}"
    
        # 텍스트 박스에 볼륨 값 표시
        self.txtVolume.setText(volume_display)
    
        # 볼륨 값을 숫자로 저장 (FFmpeg에 사용할 값)
        self.volumeFactor = volume_value * 0.01  # 볼륨 배율은 float로 처리해야 함

    def update_pitch(self):
        """슬라이드바 값에 따라 볼륨을 업데이트하는 함수"""
        pitch_value = self.slbPitchControler.value()  # 슬라이드바 값(0~500)을 0.0~5.0으로 변환
        pitch_display = f"{pitch_value:.0f}"
    
        # 텍스트 박스에 볼륨 값 표시
        self.txtPitchControler.setText(pitch_display)
    
        # 볼륨 값을 숫자로 저장 (FFmpeg에 사용할 값)
        self.pitchFactor = pitch_value / 100  # 볼륨 배율은 float로 처리해야 함

    def update_speed(self):
        """슬라이드바 값에 따라 볼륨을 업데이트하는 함수"""
        speed_value = self.slbSpeedControler.value()  # 슬라이드바 값(0~500)을 0.0~5.0으로 변환
        speed_display = f"{speed_value:.0f}"
    
        # 텍스트 박스에 볼륨 값 표시
        self.txtSpeedControler.setText(speed_display)
    
        # 볼륨 값을 숫자로 저장 (FFmpeg에 사용할 값)
        self.speedFactor = speed_value / 100 # 볼륨 배율은 float로 처리해야 함
        
    # QTextEdit의 경우, 숫자가 아닌 입력을 실시간으로 감지하여 처리하는 방식
    def validate_numeric_input(self, text_edit, max_length=6):
        """입력된 텍스트가 숫자 또는 소숫점 형태이고 최대 글자 수를 넘지 않도록 확인하는 함수"""
        text = text_edit.text()

        # 소숫점 숫자 형식 확인: 숫자만 입력되거나, '123.45' 같은 소숫점 형식인지 확인
        if not re.fullmatch(r'\d*\.?\d*', text):  # 정규식: 숫자 0개 이상 + '.' 0~1개 + 숫자 0개 이상
            text_edit.blockSignals(True)
            text_edit.setText('')  # 잘못된 입력일 경우 초기화
            text_edit.blockSignals(False)
        elif len(text) > max_length:
            text_edit.blockSignals(True)
            text_edit.setText(text[:max_length])
            text_edit.setCursorPosition(len(text[:max_length]))
            text_edit.blockSignals(False)
        
    def update_slider_from_textbox(self, text_edit, slider):
        """QLineEdit의 값이 변경될 때 슬라이드바에 적용"""
        text = text_edit.text().strip()  # QLineEdit의 텍스트를 가져옴
    
        # 입력 값이 숫자인지 확인하고 숫자인 경우 슬라이드바에 값 적용
        if text.isdigit():
            value = int(text)
            # 슬라이드바 범위 내에서만 값을 적용
            if slider.minimum() <= value <= slider.maximum():
                slider.setValue(value)
            else:
                # 값이 범위를 벗어나면 슬라이드바의 최대값 또는 최소값으로 설정
                slider.setValue(slider.maximum() if value > slider.maximum() else slider.minimum())
            
    ###############################################################################
    #-------------------------------mp3 파일 재생 및 제어 기능--------------------#
    ###############################################################################


    ###############################################################################
    #-------------------------------정렬 관련 기능--------------------------------#
    ###############################################################################
        
    def on_rate_filter_changed(self):
        self.disconnect_events()
        # 콤보박스에서 선택된 값을 가져옴 (숫자만 추출)
        selected_rate_text = self.cbbRateFilter.currentText().replace('%', '').strip()

        if selected_rate_text:  # 선택된 값이 공백이 아닌 경우에만 처리
            selected_rate = int(selected_rate_text)
        else:
            selected_rate = 100  # 값이 없을 경우 기본값으로 100%를 사용 (필요에 맞게 수정 가능)

        # 정답률이 있는 5번 컬럼의 값을 체크
        for row in range(self.tbWordList.rowCount()):
            correct_rate_item = self.tbWordList.item(row, 5)  # 정답률 컬럼은 5번

            if correct_rate_item:
                correct_rate_text = correct_rate_item.text().replace('%', '').strip()
                if correct_rate_text:  # 정답률이 빈 문자열이 아닌 경우에만 처리
                    correct_rate = int(correct_rate_text)

                    # 정답률이 선택된 값보다 낮으면 배경을 빨갛게
                    if correct_rate <= selected_rate:
                        correct_rate_item.setBackground(QtGui.QColor(255, 0, 0))  # 빨간색 배경
                    else:
                        correct_rate_item.setData(Qt.BackgroundRole, None)  # 기본 테마 색상으로 복구
                else:
                    correct_rate_item.setData(Qt.BackgroundRole, None)  # 기본 테마 색상으로 복구
        self.connect_events()
        
    def rate_filter_updater(self):
        """📌 정답률 필터를 업데이트하고 기본값을 설정"""
        self.disconnect_events()
        rate_values = set()
    
        # ✅ 5번 컬럼(정답률) 데이터를 가져와 중복 제거 및 정렬
        for row in range(self.tbWordList.rowCount()):
            item = self.tbWordList.item(row, 5)
            if item and item.text():
                rate_values.add(item.text().strip())
    
        # ✅ 100%는 항상 포함
        rate_values.add("100%")
    
        # ✅ 유효한 값만 필터링 (숫자 + % 기호 포함 여부 확인)
        filtered_rates = {rate for rate in rate_values if rate[:-1].isdigit()}

        # ✅ 모든 값이 공백이거나 0%일 경우, 기본값 설정
        if not filtered_rates or filtered_rates == {"0%"}:
            sorted_rates = ["0%", "100%"]
        else:
            sorted_rates = sorted(filtered_rates, key=lambda x: int(x.replace('%', '')))

        # ✅ 콤보박스 업데이트
        self.cbbRateFilter.clear()
        self.cbbRateFilter.addItems(sorted_rates)

        # ✅ 기본 선택값 설정 (target_rate: 60%)
        target_rate = 60
        lower_rates = [int(rate.replace('%', '')) for rate in sorted_rates if int(rate.replace('%', '')) < target_rate]

        if lower_rates:
            best_match = max(lower_rates)  # ✅ 60% 이하 중 가장 큰 값 선택
        else:
            best_match = int(sorted_rates[0].replace('%', ''))  # ✅ 없으면 가장 낮은 값 선택

        self.cbbRateFilter.setCurrentText(f"{best_match}%")  # ✅ 콤보박스 값 자동 설정
        #print(f"✅ 선택된 정답률 필터: {best_match}%")  # 디버깅 출력
        self.connect_events()

    def new_time_record_check(self):
        """📌 최근소요시간(6번 컬럼)과 최단소요시간(7번 컬럼)을 비교 후 배경색 변경"""
        translated = LANGUAGES[self.current_language]
        
        self.disconnect_events()
        for row in range(self.tbWordList.rowCount()):
            recent_time_item = self.tbWordList.item(row, 6)  # ✅ 최근소요시간 셀
            best_time_item = self.tbWordList.item(row, 7)  # ✅ 최단소요시간 셀

            # ✅ 최근소요시간이 없거나 "기록 없음"이면 원래 배경색 유지
            if not recent_time_item or not best_time_item:
                continue  # 다음 행으로 넘어감
        
            recent_time = recent_time_item.text().strip()
            best_time = best_time_item.text().strip()

            if recent_time == "" or recent_time == translated["Custom_QDialog_label_content"]["new_time_record_check_no_record"]:
                recent_time_item.setData(Qt.BackgroundRole, None)  # 배경 초기화
                recent_time_item.setData(Qt.ForegroundRole, None)  # 글자색도 초기화
            elif recent_time == best_time:
                recent_time_item.setBackground(QColor(144, 238, 144))  # 연한 라임색
                recent_time_item.setForeground(QColor(0, 0, 0))        # ✅ 검정 글씨
            else:
                recent_time_item.setData(Qt.BackgroundRole, None)
                recent_time_item.setData(Qt.ForegroundRole, None)
        self.connect_events()
        
    def populate_rate_filter(self):
        """정답률 필터 콤보박스에 1~100% 값을 추가하고, settings.json에 저장된 값을 불러옴"""
        # 콤보박스에 1~100% 추가
        self.cbbRateFilter.clear()
        for i in range(1, 101):
            self.cbbRateFilter.addItem(f"{i}%")

        # settings.json에서 저장된 설정을 불러옴
        settings = self.load_settings()
    
        # 만약 정답률 필터 설정이 있다면, 해당 값으로 콤보박스를 설정
        saved_rate_filter = settings.get("rate_filter", None)
        if saved_rate_filter is not None:
            index = self.cbbRateFilter.findText(saved_rate_filter)
            if index != -1:
                self.cbbRateFilter.setCurrentIndex(index)
        else:
            self.rate_filter_updater()
            
    def setup_checkboxes(self):
        # 체크박스 상태 변경 시 호출될 메서드 연결
        self.chbAllWords.stateChanged.connect(self.handle_all_words_checked)
        self.chbOnlyIncorrects.stateChanged.connect(self.handle_incorrects_or_lowrates_checked)
        self.chbOnlyLowRates.stateChanged.connect(self.handle_incorrects_or_lowrates_checked)

    def handle_all_words_checked(self):
        if self.chbAllWords.isChecked():
            # AllWords가 체크되면 나머지 두 체크박스를 해제
            self.chbOnlyIncorrects.setChecked(False)
            self.chbOnlyLowRates.setChecked(False)

    def handle_incorrects_or_lowrates_checked(self):
        if self.chbOnlyIncorrects.isChecked() or self.chbOnlyLowRates.isChecked():
            # OnlyIncorrects 또는 OnlyLowRates가 체크되면 AllWords를 해제
            self.chbAllWords.setChecked(False)
        else:
            # 둘 다 체크 해제되면 AllWords를 체크
            self.chbAllWords.setChecked(True)
        
    def auto_input_numbers(self):
        """0번 컬럼(번호 컬럼)에 순차적으로 번호를 자동 입력"""
        self.disconnect_events()
        for row in range(self.tbWordList.rowCount()):
            # 1부터 시작하는 번호를 입력
            self.tbWordList.setItem(row, 0, QtWidgets.QTableWidgetItem(str(row + 1)))
        self.align_cells_width()
        self.save_changes_to_file(self.current_file)
        self.connect_events()

    def align_cells_width(self):
        """테이블의 각 열 너비를 내용에 맞춰 자동으로 조정"""
        self.disconnect_events()
        self.tbWordList.resizeColumnsToContents()
        self.tbWordList.resizeRowsToContents()  # 먼저 기본 크기로 조정
        for row in range(self.tbWordList.rowCount()):
            self.tbWordList.setRowHeight(row, self.tbWordList.rowHeight(row) + 8)
        self.connect_events()
    
    def delete_scores_and_save(self):
        """번호, 단어, 뜻을 제외한 모든 칸의 데이터를 삭제하고 파일을 저장"""

        # 이벤트 연결 해제 (필요한 경우)
        self.disconnect_events()

        try:
            # 테이블의 모든 행을 순회
            for row in range(self.tbWordList.rowCount()):
                for col in range(3, self.tbWordList.columnCount()):  # 3번 열부터 나머지 열을 빈 값으로 설정
                    self.tbWordList.setItem(row, col, QtWidgets.QTableWidgetItem(""))

            # 파일로 저장 (파일 이름은 self.current_file로 저장된 이름 사용)
            if hasattr(self, 'current_file') and self.current_file:
                self.save_changes_to_file(self.current_file)
            else:
                print("저장할 파일이 없습니다.")

        finally:
            # 작업 완료 후 이벤트 다시 연결
            self.connect_events()
        
    def on_cell_changed(self, row, column):
        """셀 값이 변경될 때 호출되는 함수"""
        if column == 4:
            self.calculate_correct_rate(row)
        
    def calcualte_time_differnce(self):    
        """두 QTime 객체를 밀리초로 환산 후 뺄셈하고, 다시 QTime으로 변환"""
        
        time1 = self.current_time
        time2 = self.starting_time
        #print(f"현재시간: {time1}", f"시작시간: {time2}")
    
        # 각 부분의 차이를 계산
        hours_diff = time1.hour() - time2.hour()
        minutes_diff = time1.minute() - time2.minute()
        seconds_diff = time1.second() - time2.second()
        msecs_diff = time1.msec() - time2.msec()

        # 밀리초가 음수일 경우 초에서 1을 빼고 밀리초를 1000 더해줌
        if msecs_diff < 0:
            seconds_diff -= 1
            msecs_diff += 1000

        # 초가 음수일 경우 분에서 1을 빼고 초를 60 더해줌
        if seconds_diff < 0:
            minutes_diff -= 1
            seconds_diff += 60

        # 분이 음수일 경우 시간에서 1을 빼고 분을 60 더해줌
        if minutes_diff < 0:
            hours_diff -= 1
            minutes_diff += 60

        # 음수 시간은 0으로 처리
        if hours_diff < 0:
            hours_diff = 0
            
        result = QTime(hours_diff, minutes_diff, seconds_diff, msecs_diff)
        #print(f"계산된 시간: {result}")
        
        if self.practice_mode == 0 or self.practice_mode == 2 or self.practice_mode == 4:
            self.update_best_time(self.current_number, self.current_word,result)
        else:
            self.update_best_time(self.current_number, self.current_meaning,result)
        self.update_starting_time_record()

    def update_best_time(self, number, word, new_time):
        """최단 소요 시간을 갱신하고 이를 표시하는 함수"""
        for idx, (num, stored_word, recent_time, best_time) in enumerate(self.word_time_pairs):
            if num == number and stored_word == word:
                # 최근 소요 시간은 항상 갱신
                self.word_time_pairs[idx] = (number, stored_word, new_time, best_time)  # 최근 기록 갱신

                # 새로운 시간이 더 짧으면 최단 기록을 갱신
                if best_time.msecsSinceStartOfDay() == 0 or new_time.msecsSinceStartOfDay() < best_time.msecsSinceStartOfDay():
                    self.word_time_pairs[idx] = (number, stored_word, new_time, new_time)  # 최단 기록 갱신

    def update_best_time_forError(self, number, word):#지울 가능성 있음
        """최단 소요 시간을 갱신하고 이를 표시하는 함수"""
        for idx, (num, stored_word, recent_time, best_time) in enumerate(self.word_time_pairs):
            if num == number and stored_word == word:
                self.word_time_pairs[idx] = (number, stored_word, recent_time, best_time)  # 최근 기록 갱신

    def save_previous_records(self):
        """이전 기록을 저장하는 함수, 단어와 기록을 페어로 리스트에 저장"""
        #print("이전 시간 저장됨")
        translated = LANGUAGES[self.current_language]
        self.word_time_pairs = []  # 단어와 시간을 페어로 저장할 리스트
        
        self.disconnect_events()
        for row in range(self.tbWordList.rowCount()):
            # 1번 인덱스에서 단어 가져오기
            number = int(self.tbWordList.item(row, 0).text())  # 단어 컬럼
            word_item = self.tbWordList.item(row, 1)  # 단어 컬럼
            word = word_item.text() if word_item else ""

            # 7번 인덱스: 최단 기록, 6번 인덱스: 최근 기록
            best_time_item = self.tbWordList.item(row, 7)  # 최단 소요 시간
            recent_time_item = self.tbWordList.item(row, 6)  # 최근 소요 시간

            # 공란이거나 '기록 없음'일 경우에 기본값(00:00:00.000) 설정, 그 외에는 파싱
            if best_time_item and best_time_item.text().strip() and best_time_item.text().strip() != translated["Custom_QDialog_label_content"]["new_time_record_check_no_record"]:
                # 값이 있으면 파싱
                best_time = self.parse_time(best_time_item.text())
            else:
                # 공란 또는 '기록 없음'이면 기본값 설정
                best_time = QTime(0, 0, 0, 0)

            if recent_time_item and recent_time_item.text().strip() and recent_time_item.text().strip() != translated["Custom_QDialog_label_content"]["new_time_record_check_no_record"]:
                # 값이 있으면 파싱
                recent_time = self.parse_time(recent_time_item.text())
            else:
                # 공란 또는 '기록 없음'이면 기본값 설정
                recent_time = QTime(0, 0, 0, 0)
    
            # 리스트에 (단어, 최단기록), (단어, 최근기록)을 저장
            self.word_time_pairs.append((number, word, recent_time, best_time))  # 단어와 시간을 함께 저장
        self.connect_events()
        

    def parse_time(self, time_str):
        """hh시간mm분ss.sss초 형식을 QTime으로 변환하는 파싱 함수"""
        translated = LANGUAGES[self.current_language]
        hour_text = translated["Custom_QDialog_label_content"]["handle_header_click_h"]
        min_text = translated["Custom_QDialog_label_content"]["handle_header_click_m"]
        sec_text = translated["Custom_QDialog_label_content"]["handle_header_click_s"]
        try:
            # 시간 문자열을 파싱 (예: 00:00:05.123)
            hours, minutes, seconds = 0, 0, 0.0
            if hour_text in time_str:
                parts = time_str.split(hour_text)
                hours = int(parts[0])
                time_str = parts[1].strip()
            if min_text in time_str:
                parts = time_str.split(min_text)
                minutes = int(parts[0])
                time_str = parts[1].strip()
            if sec_text in time_str:
                parts = time_str.split(sec_text)
                seconds = float(parts[0].replace(",", ".").strip())  # 초 단위를 float으로 변환

            # QTime 생성 (시간, 분, 초)
            return QTime(hours, minutes, int(seconds), int((seconds * 1000) % 1000))
        except Exception as e:
            #(f"Error parsing time: {e}")
            return QTime(0, 0, 0, 0)  # 오류가 발생하면 기본 값 반환

    def qtime_to_string(self, qtime):
        """QTime을 hh시간 mm분 ss.sss초 형식으로 변환, 00:00:00.000일 경우 '기록 없음' 반환"""
        # QTime이 00:00:00.000일 경우 '기록 없음'을 반환
        translated = LANGUAGES[self.current_language]
        if qtime == QTime(0, 0, 0, 0):
            return translated["Custom_QDialog_label_content"]["new_time_record_check_no_record"]

        # 시간, 분, 초 가져오기
        hours = qtime.hour()
        minutes = qtime.minute()
        seconds = qtime.second()
        milliseconds = qtime.msec()  # 밀리초

        # 초와 밀리초를 합쳐서 소수점 이하 포함한 형식으로 만듦
        seconds_with_milliseconds = f"{seconds}.{milliseconds:03d}"

        # 문자열로 변환
        hour_text = translated["Custom_QDialog_label_content"]["handle_header_click_h"]
        min_text = translated["Custom_QDialog_label_content"]["handle_header_click_m"]
        sec_text = translated["Custom_QDialog_label_content"]["handle_header_click_s"]
        time_str = f"{hours:02d}{hour_text} {minutes:02d}{min_text} {seconds_with_milliseconds}{sec_text}"

        return time_str

    def update_starting_time_record(self):
        """현재 타이머 시간을 QTime 형식으로 저장"""
        self.starting_time = self.time_elapsed

    def save_answer_counts_data(self):
        """표에서 정답 횟수 데이터를 파싱하여 저장하는 함수"""
        self.word_answer_pairs = []  # 단어, 맞춘 횟수, 총 횟수를 저장할 리스트
        self.disconnect_events()
        for row in range(self.tbWordList.rowCount()):
            # 1번 인덱스에서 단어 가져오기
            number  = int(self.tbWordList.item(row, 0).text())
            word_item = self.tbWordList.item(row, 1)  # 단어 컬럼
            word = word_item.text() if word_item else ""

            # 4번 인덱스에서 정답 횟수 가져오기
            answer_count_item = self.tbWordList.item(row, 4)  # 정답 횟수 컬럼
            if answer_count_item and answer_count_item.text().strip():
                # n/n 형식으로 되어 있는 데이터를 파싱
                answer_data = answer_count_item.text().split('/')
                if len(answer_data) == 2:
                    temp_answer_number = int(answer_data[0].strip())  # 맞춘 횟수
                    temp_total_number = int(answer_data[1].strip())   # 총 시험 횟수
                else:
                    # 잘못된 형식이면 기본값으로 설정
                    temp_answer_number = 0
                    temp_total_number = 0
            else:
                # 데이터가 없을 경우 기본값 0으로 설정
                temp_answer_number = 0
                temp_total_number = 0

            # 데이터를 리스트에 저장 (단어, 맞춘 횟수, 총 횟수)
            self.word_answer_pairs.append((number, word, temp_answer_number, temp_total_number))
    
        #print(f"정답 횟수 데이터 저장 완료: {self.word_answer_pairs}")
        self.connect_events()

    def update_answer_count(self, number, word, is_correct):
        """정답 횟수와 총 시험 횟수를 갱신하는 함수"""
        #print(f"업뎃앤서카운트 인자: {word, is_correct}")
        for idx, (num, stored_word, correct_count, total_count) in enumerate(self.word_answer_pairs):
            #print(f"저장된 단어: {stored_word}", f"입력한 단어: {word}")
            if num == number and stored_word == word:
                #print("시험횟수 증가")
                # 총 시험 횟수는 무조건 증가
                total_count += 1

                # 정답일 경우 정답 횟수도 증가
                if is_correct:
                    #print("맞은횟수 증가")
                    correct_count += 1

                # 리스트 갱신
                self.word_answer_pairs[idx] = (number, stored_word, correct_count, total_count)
            #print(f"갱신된 정답횟수: {self.word_answer_pairs}")
        
    def calculate_correct_rate(self, row):
        """정답률을 계산하여 %로 표시하는 함수 (소수점 없이 정수로 표시)"""
    
        # 4번 컬럼에서 정답 횟수 데이터를 가져오기 (n/n 형식)
        correct_count_item = self.tbWordList.item(row, 4)
        #print(f"4번 컬럼 셀의 내용{correct_count_item.text()}")
    
        if correct_count_item:
            correct_data = correct_count_item.text()
        
            # 정답 횟수 데이터를 n/n 형식으로 파싱
            if '/' in correct_data:
                correct_count_str, total_count_str = correct_data.split('/')
                correct_count = int(correct_count_str.strip())
                #print(f"맞춘횟수: {correct_count}")
                total_count = int(total_count_str.strip())
                #print(f"시험횟수: {total_count}")
            
                if total_count > 0:  # 0으로 나누는 오류 방지
                    # 정답률 계산 (소수점 없이 정수로 처리)
                    correct_rate = int((correct_count / total_count) * 100)
                    correct_rate_str = f"{correct_rate}%"  # 정수로 % 표시
                
                    # 5번 컬럼에 정답률을 표시
                    self.tbWordList.setItem(row, 5, QtWidgets.QTableWidgetItem(correct_rate_str))
                else:
                    # 총 시험 횟수가 0이면 정답률을 0%로 표시
                    #print("총 시험 횟수가 0이면 정답률을 0%로 표시")
                    self.tbWordList.setItem(row, 5, QtWidgets.QTableWidgetItem("0%"))
            else:
                # 형식이 잘못된 경우도 0%로 처리
                #print("형식이 잘못된 경우도 0%로 처리")
                self.tbWordList.setItem(row, 5, QtWidgets.QTableWidgetItem("0%"))

    def record_incorrect_answer(self, number, word, is_correct):
        """정답 여부에 따라 오답 데이터를 단어별로 저장"""

        # 사용자 입력값 정리
        user_input = self.txtMeaningInput.toPlainText().strip()

        # 오답 비교용 딕셔너리 초기화
        if word not in self.incorrect_answers:
            self.incorrect_answers[word] = []

        # 저장할 값 준비
        answer_to_store = "" if is_correct else user_input
        self.incorrect_answers[word].append((number, answer_to_store, word))

        #print(f"최종내용: {self.incorrect_answers[word]}")
        
    def get_current_question_number(self):
        """현재 표시된 문제(self.current_word)에 해당하는 테이블의 번호를 가져옴"""
        # 현재 표시 중인 단어를 기반으로 테이블에서 검색
        self.disconnect_events()
        for row in range(self.tbWordList.rowCount()):
            word_item = self.tbWordList.item(row, 1)  # 1번 컬럼은 단어
            if word_item or word_item.text() == self.current_word:
                number_item = self.tbWordList.item(row, 0)  # 0번 컬럼에서 번호 가져오기
                if number_item:
                    return int(number_item.text())  # 번호를 int로 반환
        self.connect_events()
        return -1  # 문제가 없으면 -1 반환 (에러 처리)

    def record_answer(self, number, word, is_correct):
        if word:
            self.corrects.append((number, word, is_correct))
        
    def toggle_test_mode(self):
        """시험 모드 전환 전 3초 카운트다운 후 시작"""
        
        self.disconnect_events()
        translated_text = LANGUAGES.get(self.current_language, LANGUAGES["한국어"])
        base_font_name = self.cbbFontSetting.currentData()
        if not self.number_checker_before_test():  # ✅ `False` 반환 시 실행 중단
            return  # 🚨 번호가 없거나 오류 발생 시 실행 중단

        if not self.is_testing:
            self.sound_player.streak_count = 0
            self.word_answer_pairs = []
            self.word_time_pairs = []
            self.corrects = []
            clicked_button = self.sender()
            self.clicked_test_button_name = clicked_button.objectName()
            test_mode = ""
            if "Text" in self.clicked_test_button_name:
                self.toplay_in_test = False
            elif "Audio" in self.clicked_test_button_name:
                self.toplay_in_test = True
                self.txtWordInput.setVisible(False)
            else :
                self.toplay_in_test = True
                self.txtWordInput.setVisible(False)
            if not self.chbAllWords.isChecked():    
                # 모드에 따라 단어-뜻 또는 뜻-단어 리스트 생성
                if "WtoM" in self.clicked_test_button_name :
                    test_mode = "word_to_meaning"
                if "MtoW" in self.clicked_test_button_name :
                    test_mode = "meaning_to_word"
                if "Dictation" in self.clicked_test_button_name :
                    test_mode = "dictation"
                filtered_pairs = self.create_word_meaning_list(test_mode)
            
                # 필터링된 단어가 없는 경우
                #print(f"필터된 단어::: {filtered_pairs}")
                if not filtered_pairs: #시험 조건이 맞지 않으므로
                    QApplication.beep()
                    msg_box = ThemedDialog(title=translated_text["Custom_QDialog_label_title"]["text_aleart"], parent=self, theme=self.current_theme)
                    label = QLabel(translated_text["Custom_QDialog_label_content"]["toggle_test_mode_no_condition"], msg_box)
                    msg_box.content_layout.setContentsMargins(15,5,15,5)
                    msg_box.content_layout.addWidget(label)
                    
                    yes_button = ThemedButton(translated_text["Custom_QDialog_buttons"]["text_test_all_word"], self, self.current_theme)
                    yes_button.setProperty("result", 1)
                    yes_button.clicked.connect(lambda: msg_box.done(yes_button.property("result")))
                    no_button = ThemedButton(translated_text["Custom_QDialog_buttons"]["text_cancel"], self, self.current_theme)
                    no_button.setProperty("result", 2)
                    no_button.clicked.connect(lambda: msg_box.done(no_button.property("result")))
                    self.apply_hover_events(yes_button, self.animated_hover_start, self.animated_hover_end)
                    self.apply_hover_events(no_button, self.animated_hover_start, self.animated_hover_end)
                    msg_box.button_layout.setContentsMargins(15,5,15,5)
                    msg_box.button_layout.addWidget(yes_button)
                    msg_box.button_layout.addWidget(no_button)
                    
                    result = msg_box.exec_()

                    if result == 1: #전체 시험을 할 것인가?
                        self.confirmedAllWord = True
                    else: #시험 자체를 취소할 것인가
                        self.confirmedAllWord = False
                        self.txtWordInput.setVisible(True)
                        # 시험 종료
                        return

            self.is_testing = True
            self.disable_buttons()
            self.tbWordList.setVisible(False)
            self.txtMeaningInput.setPlainText("")
            self.txtWordInput.clear()
            """시험 모드 전환 전 3초 카운트다운 후 시작"""
            self.countdown = 3  # 카운트다운 변수 설정
            self.show_feedback(str(self.countdown))
            self.countdown -= 1  # 1초 감소
            self.countimer = QTimer(self)
            mp3 = self.resource_path("sounds/wait.mp3")
            threading.Thread(target=lambda: (pygame.mixer.music.load(mp3), pygame.mixer.music.play()), daemon=True).start()
            self.countimer.timeout.connect(self.update_countdown_with_animation)
            self.countimer.start(1000)  # 1초마다 카운트다운
        else:
            
            self.disconnect_events()
            if self.current_words_count > 0 :
                QApplication.beep()
                msg_box = ThemedDialog(translated_text["Custom_QDialog_buttons"]["text_cancel"], self, self.current_theme)
                label = QLabel(translated_text["Custom_QDialog_label_content"]["toggle_test_mode_surt_to_end"], msg_box)
                msg_box.content_layout.setContentsMargins(15,5,15,5)
                msg_box.content_layout.addWidget(label)
                
                # Yes, No 버튼 추가
                yes_button = QPushButton(translated_text["Custom_QDialog_buttons"]["text_test_done"])
                yes_button.setProperty("result", 1)  # ✅ 반환 값 지정
                yes_button.clicked.connect(lambda: msg_box.done(yes_button.property("result")))
                no_button = QPushButton(translated_text["Custom_QDialog_buttons"]["text_test_keep_going"])
                no_button.setProperty("result", 2)  # ✅ 반환 값 지정
                no_button.clicked.connect(lambda: msg_box.done(no_button.property("result")))
                self.apply_theme_toButtons(self.current_theme, yes_button)
                self.apply_theme_toButtons(self.current_theme, no_button)
                self.apply_hover_events(yes_button, self.animated_hover_start, self.animated_hover_end)
                self.apply_hover_events(no_button, self.animated_hover_start, self.animated_hover_end)
                msg_box.button_layout.addWidget(yes_button)
                msg_box.button_layout.addWidget(no_button)
                
                # 메시지 박스 실행 후 결과 확인
                result = msg_box.exec_()

                # Yes를 선택했을 경우 시험 종료
                if result == 1:
                    self.is_testing = False
                    self.enable_buttons()
                    self.tbWordList.setVisible(True)
                    self.lbWordsCounter.setVisible(False)
                    self.lbTimer.setVisible(False)
                    self.txtWordInput.status = "test condition error"
                    self.txtMeaningInput.status = "test condition error"
                    self.txtWordInput.setPlainText(translated_text["test_contition_error1"])
                    self.txtMeaningInput.setPlainText(translated_text["test_contition_error2"])
                    if base_font_name:
                        font = QFont(base_font_name)
                        font.setPointSize(self.word_font_size)  # 현재 설정된 크기 유지
                        self.txtWordInput.setFont(font)
                        self.txtMeaningInput.setFont(font)
                    self.word_meaning_list = []  # 단어와 뜻 페어를 담을 리스트
                    self.current_word = ""       # 현재 표시된 단어
                    self.current_meaning = ""    # 현재 단어의 뜻
                    self.current_number = 0
        
                    self.numbered_word_meaning_list = []
                    self.wrong_answer = []
                    self.correct_times_before = []
                    self.correct_times = []
                    self.recent_time = []
                    self.fastest_time = []
                    self.corrects = []
                    self.incorrect_answers = {}
                    self.word_answer_pairs = []
        
                    self.total_words_count = 0
                    self.current_words_count = 0
                    self.answer_words_count = 0

                    self.time_elapsed = QTime(0, 0, 0, 1)
                    self.starting_time = QTime(0,0,0,0)
                    self.word_time_pairs = []
                    self.time_result = []
                else:
                    # No를 선택했을 경우 메시지 박스만 닫힘 (기본 동작)
                    pass
            else:
                self.is_testing = False
                self.enable_buttons()
                self.tbWordList.setVisible(True)
                self.lbWordsCounter.setVisible(False)
                self.lbTimer.setVisible(False)
                translated_text = LANGUAGES.get(self.current_language, LANGUAGES["한국어"])
                self.txtWordInput.status = "tested well"
                self.txtMeaningInput.status = "tested well"
                self.txtWordInput.setPlainText(translated_text["test_contition_error1"])
                self.txtMeaningInput.setPlainText(translated_text["tested_well2"])
                if base_font_name:
                    font = QFont(base_font_name)
                    font.setPointSize(self.word_font_size)  # 현재 설정된 크기 유지
                    self.txtWordInput.setFont(font)
                    self.txtMeaningInput.setFont(font)
                self.display_result()
                self.word_meaning_list = []  # 단어와 뜻 페어를 담을 리스트
                self.current_word = ""       # 현재 표시된 단어
                self.current_meaning = ""    # 현재 단어의 뜻
                self.current_number = 0      # 현재 단어의 번호
        
                self.numbered_word_meaning_list = []
                self.wrong_answer = []
                self.correct_times_before = []
                self.correct_times = []
                self.recent_time = []
                self.fastest_time = []
                self.corrects = []
                self.incorrect_answers = {}
                self.word_answer_pairs = []
        
                self.total_words_count = 0
                self.current_words_count = 0
                self.answer_words_count = 0

                self.time_elapsed = QTime(0, 0, 0, 1)
                self.starting_time = QTime(0,0,0,0)
                self.word_time_pairs = []
                self.time_result = []
                
        self.connect_events()
        
        self.txtmeaninginput_style_reset(self.current_theme)

    def update_cell_background(self):
        transalted = LANGUAGES[self.current_language]
        self.disconnect_events()
        """셀의 내용이 '오답'이면 배경을 빨갛게, 정답률 기준 미달이면 배경을 빨갛게, 그 이외에는 하얗게 변경"""
        for row in range(self.tbWordList.rowCount()):
            result_item = self.tbWordList.item(row, 8)  # 8번 컬럼(결과 컬럼)에서 확인

            # '오답'에 대한 처리
            if result_item:
                #print(result_item.text())
                if result_item.text() == transalted["Custom_QDialog_label_content"]["show_feedback_var_incor"]:
                    # 셀 배경을 빨간색으로 설정
                    result_item.setBackground(QBrush(QColor(255, 0, 0)))  # 빨간색
                else:
                    # 셀 배경을 흰색으로 설정
                    result_item.setData(Qt.BackgroundRole, None)  # 기본 테마 색상으로 복구
        self.connect_events()
                    
    def update_last_test_colors(self):
        """정답률과 마지막 시험일시를 기준으로 복습 신호를 업데이트"""
        
        self.disconnect_events()
        current_date = datetime.now()

        for row in range(self.tbWordList.rowCount()):
            # '마지막시험일시' 컬럼 (예: 9번 컬럼) 가져오기
            last_test_item = self.tbWordList.item(row, 9)
            correct_rate_item = self.tbWordList.item(row, 5)  # '정답률' 컬럼

            if not last_test_item or not correct_rate_item:
                continue  # 데이터가 없으면 건너뜀

            try:
                last_test_date = datetime.strptime(last_test_item.text(), "%Y-%m-%d %H:%M:%S")
                days_elapsed = (current_date - last_test_date).days  # 경과 일 수 계산
                correct_rate = int(correct_rate_item.text().replace("%", ""))  # 정답률

                # 색상 설정 초기화
                color = QColor()
                text_color = QColor()  

                # 시험본날~3일차 (정답률이 낮은 것에 대해서만 재시험 추천)
                if days_elapsed <= 3:
                    if 100 >= correct_rate >= 80:
                        color.setRgb(0, 255, 0)  # 녹색 (추천 안 함)
                        text_color.setRgb(0, 0, 0)  # 검정
                    elif 79 >= correct_rate >= 60:
                        color.setRgb(144, 238, 144)  # 라임색 (재시험 약함)
                        text_color.setRgb(0, 0, 0)  # 검정
                    elif 59 >= correct_rate >= 40:
                        color.setRgb(255, 255, 0)  # 노란색 (재시험 강함)
                        text_color.setRgb(0, 0, 0)  # 검정
                    else:
                        color.setRgb(255, 0, 0)  # 빨간색 (강력 추천)
                        text_color.setRgb(255, 255, 255)  # 흰색

                # 4일차~7일차 (재시험 추천 범위를 약간 강화)
                elif 4 <= days_elapsed <= 7:
                    if 100 >= correct_rate >= 70:
                        color.setRgb(144, 238, 144)  # 라임색 (재시험 약함)
                        text_color.setRgb(0, 0, 0)  # 검정
                    elif 69 >= correct_rate >= 50:
                        color.setRgb(144, 238, 144)  # 라임색 (재시험 약함)
                        text_color.setRgb(0, 0, 0)  # 검정
                    elif 49 >= correct_rate >= 30:
                        color.setRgb(255, 255, 0)  # 노란색 (재시험 강함)
                        text_color.setRgb(0, 0, 0)  # 검정
                    else:
                        color.setRgb(255, 0, 0)  # 빨간색 (강력 추천)
                        text_color.setRgb(255, 255, 255)  # 흰색

                # 1주차~2주차 (재시험 추천 범위를 강화, 정답률 100%여도 약한 추천)
                elif 8 <= days_elapsed <= 14:
                    if 100 >= correct_rate >= 70:
                        color.setRgb(144, 238, 144)  # 라임색 (재시험 약함)
                        text_color.setRgb(0, 0, 0)  # 검정
                    elif 69 >= correct_rate >= 50:
                        color.setRgb(255, 255, 0)  # 노란색 (재시험 강함)
                        text_color.setRgb(0, 0, 0)  # 검정
                    else:
                        color.setRgb(255, 0, 0)  # 빨간색 (강력 추천)
                        text_color.setRgb(255, 255, 255)  # 흰색

                # 2주차~1달차 (대부분 단어에 대해 재시험 추천)
                elif 15 <= days_elapsed <= 30:
                    if 100 >= correct_rate >= 70:
                        color.setRgb(255, 255, 0)  # 노란색 (재시험 강함)
                        text_color.setRgb(0, 0, 0)  # 검정
                    else:
                        color.setRgb(255, 0, 0)  # 빨간색 (강력 추천)
                        text_color.setRgb(255, 255, 255)  # 흰색

                # 1달 이상 (무조건 전부 재시험)
                elif 30 <= days_elapsed:
                    color.setRgb(255, 0, 0)  # 빨간색 (강력 추천)
                    text_color.setRgb(255, 255, 255)  # 흰색
                    
                # '마지막시험일시' 셀의 배경색을 변경
                last_test_item.setBackground(QBrush(color))
                last_test_item.setForeground(QBrush(text_color))

            except ValueError:
                # 날짜 변환에 실패할 경우 로그 출력
                continue

        #print("복습 추천 색상 업데이트 완료!")
        
        self.connect_events()
    
    def display_result(self):
        transalted = LANGUAGES[self.current_language]
        """시험이 끝나면 정답과 오답을 번호에 맞춰 표시하고 시간을 업데이트"""
        # 이벤트 제거
        self.disconnect_events()

        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # 현재 시간
        #print(self.word_time_pairs)
        #print(self.word_answer_pairs)
        #print(self.incorrect_answers)
        #print(self.corrects)

        for row in range(self.tbWordList.rowCount()):
            number_item = self.tbWordList.item(row, 0)  # 0번 컬럼 (번호 컬럼)
            word_item = self.tbWordList.item(row, 1)  # 1번 컬럼 (단어 컬럼)

            number = int(number_item.text())
            current_word = word_item.text()

            # 이벤트 제거 후 데이터 업데이트
              # 이벤트 신호 일시 중단

            # 시간 정보 업데이트 (6번: 최근 소요 시간, 7번: 최단 소요 시간)
            for pair in self.word_time_pairs:
                if pair[0] == number:
                    if pair[1] == current_word:
                        #print(f"비교페어번호: {pair[0]}, 포문번호:{number}")
                        code_recent = self.qtime_to_code_string(pair[2])
                        translated_recent = self.translate_time_value(code_recent)
                        recent_item = QTableWidgetItem(translated_recent)
                        recent_item.setData(QtCore.Qt.UserRole, code_recent)
                        self.tbWordList.setItem(row, 6, recent_item)

                        code_best = self.qtime_to_code_string(pair[3])
                        translated_best = self.translate_time_value(code_best)
                        best_item = QTableWidgetItem(translated_best)
                        best_item.setData(QtCore.Qt.UserRole, code_best)
                        self.tbWordList.setItem(row, 7, best_item)

            # 정답 횟수와 총 시험 횟수 업데이트 (4번 컬럼)
            for pair in self.word_answer_pairs:
                if pair[0] == number:
                    if pair[1] == current_word:
                        correct_count_str = f"{pair[2]}/{pair[3]}"
                        self.tbWordList.setItem(row, 4, QtWidgets.QTableWidgetItem(correct_count_str))

            # 오답 비교 업데이트 (3번 컬럼)
            for word, attempts in self.incorrect_answers.items():
                for stored_number, incorrect_answer, stored_word in attempts:
                    for row in range(self.tbWordList.rowCount()):
                        number_item = self.tbWordList.item(row, 0)
                        word_item = self.tbWordList.item(row, 1)

                        if not number_item or not word_item:
                            continue

                        number = int(number_item.text())
                        current_word = word_item.text()

                        if number == stored_number and current_word == stored_word:
                            self.tbWordList.setItem(row, 3, QtWidgets.QTableWidgetItem(incorrect_answer))
                            break

            # 오답 여부 업데이트 (8번 컬럼)
            for row in range(self.tbWordList.rowCount()):
                number_item = self.tbWordList.item(row, 0)
                word_item = self.tbWordList.item(row, 1)

                if not number_item or not word_item:
                    continue

                row_number = int(number_item.text())
                row_word = word_item.text()

                for number, word, is_correct in self.corrects:
                    if row_number == number and row_word == word:
                        translated = LANGUAGES[self.current_language]["table_values"].get(is_correct, str(is_correct))

                        item = QTableWidgetItem(translated)
                        item.setData(QtCore.Qt.UserRole, is_correct)
                        self.tbWordList.setItem(row, 8, item)

                        # 마지막 시험 일시 업데이트 (9번 컬럼)
                        self.tbWordList.setItem(row, 9, QTableWidgetItem(current_datetime))

                        # 정답률 계산
                        self.calculate_correct_rate(row)
                        break  # 이 row에 표시 완료했으면 다음 row로

        # 시험에 걸린 총 시간을 출력  
        total_elapsed_time = self.get_total_elapsed_time()
        result_message = f"{transalted['Custom_QDialog_label_content']['display_result_correct_num']} {self.answer_words_count}/{self.total_words_count}\n{transalted['Custom_QDialog_label_content']['display_result_total_time']} {total_elapsed_time}"
        self.show_custom_message(transalted["Custom_QDialog_label_title"]["text_result"], result_message)

        # 파일 저장 및 초기화
        self.current_file = self.cbbWordFile.currentText()
        self.save_changes_to_file(self.current_file)
        self.set_table_editable(False)
        self.set_text_widget_editable(False)
        self.confirmedAllWord = False
        
        # 테이블 스타일 및 정렬 업데이트
        self.update_cell_background()
        self.apply_font_totarget()
        self.update_last_test_colors()
        self.align_cells_width()
        self.on_rate_filter_changed()
        self.rate_filter_updater()
        self.new_time_record_check()
        if self.is_descending:
            self.is_descending = not self.is_descending
        else:
            pass
        self.handle_header_click(8)
        self.update_last_test_label(self.current_file)
        self.connect_events()
        
    def qtime_to_code_string(self, qtime_obj):
        if not isinstance(qtime_obj, QtCore.QTime):
            return str(qtime_obj)

        h = qtime_obj.hour()
        m = qtime_obj.minute()
        s = qtime_obj.second()
        ms = qtime_obj.msec()
        return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"  # 예: 00:01:23.456

    def update_countdown_with_animation(self):
        transalted = LANGUAGES[self.current_language]
        """카운트다운을 1초마다 애니메이션으로 업데이트"""
        if self.countdown > 0:
            self.show_feedback(str(self.countdown))  # 카운트다운 숫자 표시 및 애니메이션
            self.countdown -= 1  # 1초 감소
            mp3 = self.resource_path("sounds/wait.mp3")
            threading.Thread(target=lambda: (pygame.mixer.music.load(mp3), pygame.mixer.music.play()), daemon=True).start()
        else:
            self.countimer.stop()  # 카운트다운 타이머 종료
            self.show_feedback(transalted["Custom_QDialog_label_content"]["next_question_forTest_start"])  # "시작!" 메시지 표시 및 애니메이션
            mp3 = self.resource_path("sounds/go.mp3")
            threading.Thread(target=lambda: (pygame.mixer.music.load(mp3), pygame.mixer.music.play()), daemon=True).start()
            self.lbWordsCounter.setText(f"{transalted['Custom_QDialog_label_content']['next_question_forTest_remain']} {self.current_words_count}/{self.total_words_count}")
            self.start_test_mode(self.clicked_test_button_name)  # 바로 시작
        
    def start_test_mode(self, choice):
        self.reset_text_format_except_font(self.txtMeaningInput)
        base_font_name = self.cbbFontSetting.currentData()
        learning_font_name = self.cbbFontSetting_tolearn.currentData()
        """시험 모드 시작: toggle_test_mode 함수에서 호출"""
        self.init_stopwatch()  # 초시계 초기화 및 시작
        self.start_stopwatch()  # 초시계 시작
        self.update_starting_time_record()
        
        """연습 모드를 선택하는 함수. 선택지에 따라 단어-뜻 또는 뜻-단어 리스트를 생성"""
        button_object = self.findChild(QtWidgets.QPushButton, self.clicked_test_button_name)
        if button_object:  # 버튼 객체가 존재하면
            button_object.setEnabled(True)  # 해당 버튼을 활성화  
        self.set_text_widget_editable(True)
        self.lbWordsCounter.setVisible(True)
        self.lbTimer.setVisible(True)
        #print(f"선택된 버튼{choice}")
        if "btnTextTestWtoM" in choice :
            # 단어-뜻 페어로 리스트 생성
            self.create_word_meaning_list(mode="word_to_meaning")
            self.practice_mode = 0
            self.changed_font_of_txtwidgets(base_font_name, learning_font_name)
            
        elif "btnTextTestMtoW" in choice :
            # 단어-뜻 페어로 리스트 생성
            self.create_word_meaning_list(mode="meaning_to_word")
            self.practice_mode = 1
            self.changed_font_of_txtwidgets(learning_font_name, base_font_name)
            
        elif "btnAudioTestWtoM" in choice:
            # 뜻-단어 페어로 리스트 생성
            self.create_word_meaning_list(mode="word_to_meaning")
            self.practice_mode = 2
            self.changed_font_of_txtwidgets(base_font_name, learning_font_name)
            
        elif "btnAudioTestMtoW" in choice:
            # 뜻-단어 페어로 리스트 생성
            self.create_word_meaning_list(mode="meaning_to_word")
            self.practice_mode = 3
            self.changed_font_of_txtwidgets(learning_font_name, base_font_name)
            
        elif "Dictation" in choice:
            self.create_word_meaning_list(mode="dictation")
            self.practice_mode = 4
            self.changed_font_of_txtwidgets(learning_font_name, learning_font_name)
            
        self.save_previous_records()
        self.save_answer_counts_data()
        self.start_test_forTest()

    def changed_font_of_txtwidgets(self, base_font_name, learning_font_name):
        if base_font_name:
            font = QFont(base_font_name)
            font.setPointSize(self.word_font_size)  # 현재 설정된 크기 유지
            self.txtMeaningInput.setFont(font)
        if learning_font_name:
            font = QFont(learning_font_name)
            font.setPointSize(self.word_font_size)  # 현재 설정된 크기 유지
            self.txtWordInput.setFont(font) 
            
    def correct_beep(self):
        self.sound_player.play_correct_async()
    
    def incorrect_beep(self):
        self.sound_player.play_wrong_async()

    def show_feedback(self, correct):
        """정답과 오답을 lbWordsCounter 라벨에 표시하고 애니메이션을 적용"""
        translated = LANGUAGES[self.current_language]
        self.lbThreeCount.raise_()
        
        if hasattr(self, 'timer') and self.timer.isActive():
            self.timer.stop()
        
        # 텍스트와 색상 설정: 정답일 경우 "정답!"(초록색), 오답일 경우 "오답..."(빨간색)
        if isinstance(correct, bool):  # correct가 True 또는 False일 때
            #print(f"정답여부: {correct}")
            if correct:
                self.lbThreeCount.setText(translated["Custom_QDialog_label_content"]["show_feedback_label_cor"])
                self.correct_beep()
                self.text_color = "rgba(7, 166, 98"  # 초록색
                self.current_stopwatch()
                if self.practice_mode in (0, 2, 4, 6):
                    self.record_answer(self.current_number, self.current_word, "correct")
                    self.update_answer_count(self.current_number, self.current_word, True)
                    self.record_incorrect_answer(self.current_number, self.current_word, True)
                else:
                    self.record_answer(self.current_number, self.current_meaning, "correct")
                    self.update_answer_count(self.current_number, self.current_meaning, True)
                    self.record_incorrect_answer(self.current_number, self.current_meaning, True)
                self.calcualte_time_differnce()
            else:
                self.lbThreeCount.setText(translated["Custom_QDialog_label_content"]["show_feedback_label_incor"])
                self.incorrect_beep()
                self.text_color = "rgba(183, 33, 36"  # 빨간색
                if self.practice_mode in (0, 2, 4, 6):
                    self.record_answer(self.current_number, self.current_word, "wrong")
                    self.update_answer_count(self.current_number, self.current_word, False)
                    self.record_incorrect_answer(self.current_number, self.current_word, False)
                    self.update_best_time_forError(self.current_number, self.current_word)
                else:
                    self.record_answer(self.current_number, self.current_meaning, "wrong")
                    self.update_answer_count(self.current_number, self.current_meaning, False)
                    self.record_incorrect_answer(self.current_number, self.current_meaning, False)
                    self.update_best_time_forError(self.current_number, self.current_meaning)
                self.update_starting_time_record()
        elif isinstance(correct, str):  # correct가 문자열일 때
            # 팔레트에서 텍스트 색상 가져오기
            palette = self.txtWordInput.palette()
            default_text_color = palette.color(QtGui.QPalette.Text)  # 기본 텍스트 색상
    
            # QColor를 rgba 문자열로 변환
            r = default_text_color.red()
            g = default_text_color.green()
            b = default_text_color.blue()
            self.text_color = f"rgba({r}, {g}, {b}"
            
            self.lbThreeCount.setText(correct)  # 문자열 출력
    
            self.update_starting_time_record()
        else:  # 숫자나 다른 형식일 경우
            self.lbThreeCount.setText(translated["Custom_QDialog_label_content"]["show_feedback_label_none"])
            self.text_color = "rgba(128, 128, 128"  # 회색
            self.update_starting_time_record()
    
        # 초기 상태 설정
        self.lbThreeCount.setStyleSheet(f"color: {self.text_color}, 255); font-size: 1px;")
    
        # 애니메이션 변수 설정
        self.current_font_size = 1  # 초기 글씨 크기
        self.current_opacity = 255   # 초기 투명도 (완전히 불투명)
        self.animation_steps = 50   # 애니메이션을 100단계로 나누어 진행 (부드럽게)
        self.step_duration = 15      # 각 단계는 30ms 간격으로 업데이트 (총 3000ms)

        # 타이머 설정 (애니메이션 30ms 간격으로 업데이트)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate_feedback)
        self.timer.start(self.step_duration)  # 30ms마다 애니메이션 업데이트

    def animate_feedback(self):
        """글씨 크기와 투명도를 변화시켜 애니메이션 효과 적용"""
    
        # 글씨 크기 점진적으로 증가 (최대 40px)
        if self.current_font_size < 100:
            self.current_font_size += (100 - 1) / self.animation_steps  # 작은 단위로 변화

        # 투명도 점진적으로 감소 (0 이상으로 유지)
        if self.current_opacity > 0:
            self.current_opacity -= 120 / self.animation_steps  # 투명도도 작은 단위로 변화
            self.current_opacity = max(0, self.current_opacity)
        else:
            self.current_opacity = 0  # 투명도가 0 이하로 내려가지 않도록 제한

        # 글씨 크기와 투명도 적용
        self.lbThreeCount.setStyleSheet(
            f"color: {self.text_color}, {int(self.current_opacity)}); font-size: {int(self.current_font_size)}px;"
        )

        # 애니메이션 종료 조건: 글씨 크기가 40px에 도달하고, 투명도가 0이 되었을 때
        if self.current_font_size >= 100 and self.current_opacity <= 0:
            self.timer.stop()  # 애니메이션 중단
            self.lbThreeCount.lower()
            self.lbThreeCount.clear()  # 애니메이션 후 텍스트를 비움
            self.text_color = "rgba(128, 128, 128"  # 회색
       
    def init_stopwatch(self):
        """초시계 초기 설정"""
        self.time_elapsed = QTime(0, 0, 0, 1)  # 시간 초기화 (00:00:00.000)
        self.stopwatch = QTimer(self)
        self.stopwatch.timeout.connect(self.update_timer)  # 타이머가 끝날 때마다 update_timer 호출
        self.lbTimer.setText(self.time_elapsed.toString("hh:mm:ss.zzz"))  # 초기 시간 표시

    def start_stopwatch(self):
        """초시계 시작"""
        self.start_time = QTime.currentTime()  # 시작 시간 기록
        self.stopwatch.start(1)  # 1ms마다 업데이트
        
    def current_stopwatch(self):
        self.current_time = self.time_elapsed

    def update_timer(self):
        """초시계 업데이트 (1ms마다 호출됨)"""
        elapsed = self.start_time.msecsTo(QTime.currentTime())  # 시작 시간부터 경과 시간 계산
        self.time_elapsed = QTime(0, 0, 0, 0).addMSecs(elapsed)  # 경과 시간으로 QTime 업데이트
        self.lbTimer.setText(self.time_elapsed.toString("hh:mm:ss.zzz"))  # 라벨에 시간 표시

    def stop_stopwatch(self):
        """초시계 일시정지"""
        self.stopwatch.stop()

    def reset_stopwatch(self):
        """초시계 리셋"""
        self.stopwatch.stop()
        self.time_elapsed = QTime(0, 0, 0, 0)  # 시간 초기화
        self.lbTimer.setText(self.time_elapsed.toString("hh:mm:ss.zzz"))  # 라벨에 초기 시간 표시
        
    def get_total_elapsed_time(self):
        """시험이 끝났을 때 총 시간을 추출"""
        return self.time_elapsed.toString("hh:mm:ss.zzz")  # 총 시간을 문자열로 반환

    def start_test_forPractice(self):
        """테스트를 시작하는 함수. 옵션에 따라 리스트를 정렬"""
        #print(f"문제 들어옴?: {self.word_meaning_list}")
        self.txtWordInput.status = "is testing"
        self.txtMeaningInput.status = "is testing"
        self.txtMeaningInput.setFocus()
        self.txtMeaningInput.setPlainText("")
        self.next_question_forPractice()  # 첫 번째 문제를 표시
        
    def next_question_forPractice(self):
        """리스트에서 다음 단어를 가져와 txtWordInput에 표시"""
        base_font_name = self.cbbFontSetting.currentData()
        learn_font_name = self.cbbFontSetting_tolearn.currentData()
        if self.word_meaning_list:
            # 리스트에서 첫 번째 단어와 뜻을 가져옴
            if self.practice_mode == 5:
                self.current_number, self.current_word, self.current_meaning = self.word_meaning_list.pop(0)
                language = self.cbbLangToLearn.currentData()
                if base_font_name:
                    font = QFont(base_font_name)
                    font.setPointSize(self.word_font_size)  # 현재 설정된 크기 유지
                    self.txtMeaningInput.setFont(font)
                if learn_font_name:
                    font = QFont(learn_font_name)
                    font.setPointSize(self.meaning_font_size)
                    self.txtWordInput.setFont(font)
            elif self.practice_mode == 6:
                self.current_number, self.current_word, self.current_meaning = self.word_meaning_list.pop(0)
                language = self.cbbBaseLang.currentData()
                if base_font_name:
                    font = QFont(base_font_name)
                    font.setPointSize(self.word_font_size)  # 현재 설정된 크기 유지
                    self.txtWordInput.setFont(font)
                if learn_font_name:
                    font = QFont(learn_font_name)
                    font.setPointSize(self.meaning_font_size)
                    self.txtMeaningInput.setFont(font)
            else:
                self.current_number, self.current_word, self.current_meaning = self.word_meaning_list.pop(0)
                language = self.cbbLangToLearn.currentData()
                if base_font_name:
                    font = QFont(learn_font_name)
                    font.setPointSize(self.word_font_size)  # 현재 설정된 크기 유지
                    self.txtWordInput.setFont(font)
                if learn_font_name:
                    font = QFont(learn_font_name)
                    font.setPointSize(self.meaning_font_size)
                    self.txtMeaningInput.setFont(font)
            self.txtWordInput.setPlainText(self.current_word)

            self.highlight_current_word_in_table()
            text = self.current_word
            if self.toplay_in_test:
                self.play_text_as_audio(text, language)
        else:
            self.toggle_practice_mode()
            
    def highlight_current_word_in_table(self):
        """📌 현재 단어에 해당하는 행을 찾아 배경색을 빨간색으로 변경"""
        self.disconnect_events()
        
        target_row = None  # 📌 스크롤을 이동할 목표 행
        
        for row in range(self.tbWordList.rowCount()):
            word_item_0 = self.tbWordList.item(row, 0)  # ✅ 1번 컬럼 (단어)
            word_item_1 = self.tbWordList.item(row, 1)  # ✅ 1번 컬럼 (단어)
            word_item_2 = self.tbWordList.item(row, 2)  # ✅ 2번 컬럼 (뜻)
            if ((word_item_1.text() == self.current_word) or \
            (word_item_2.text() == self.current_word)) and \
            (int(word_item_0.text()) == self.current_number):
                # ✅ 해당 단어가 있는 행의 배경색을 빨간색으로 설정
                self.tbWordList.item(row, 0).setData(Qt.BackgroundRole, QtGui.QBrush(QtGui.QColor(255, 100, 100)))  # 빨간색
                self.tbWordList.item(row, 1).setData(Qt.BackgroundRole, QtGui.QBrush(QtGui.QColor(255, 100, 100)))  # 빨간색
                self.tbWordList.item(row, 2).setData(Qt.BackgroundRole, QtGui.QBrush(QtGui.QColor(255, 100, 100)))  # 빨간색
                target_row = row  # 📌 스크롤 이동을 위해 저장
            else:
                # ✅ 나머지 행들은 원래 색으로 복원
                if word_item_0:
                    word_item_0.setData(Qt.BackgroundRole, None)
                if word_item_1:
                    word_item_1.setData(Qt.BackgroundRole, None)
                if word_item_2:
                    word_item_2.setData(Qt.BackgroundRole, None)
                    
        # ✅ 해당 단어가 있는 경우 스크롤 이동 실행
        if target_row is not None:
            self.tbWordList.scrollToItem(self.tbWordList.item(target_row, 1), QtWidgets.QAbstractItemView.PositionAtCenter)
            
        self.connect_events()
                
    def start_test_forTest(self):
        """테스트를 시작하는 함수. 옵션에 따라 리스트를 정렬"""
        self.txtWordInput.status = "is testing"
        self.txtMeaningInput.status = "is testing"
        self.txtMeaningInput.setFocus()
        self.next_question_forTest()  # 첫 번째 문제를 표시

    def next_question_forTest(self):
        """리스트에서 다음 단어를 가져와 txtWordInput에 표시"""
        #print(f"만들어진 단어내용: {self.word_meaning_list}")
        if self.word_meaning_list:
            # 리스트에서 첫 번째 단어와 뜻을 가져옴
            self.current_number, self.current_word, self.current_meaning = self.word_meaning_list.pop(0)
            self.txtWordInput.setPlainText(self.current_word)
            if self.practice_mode == 0 or self.practice_mode == 2 or self.practice_mode == 4:
                language = self.cbbLangToLearn.currentData()
            else :
                language = self.cbbBaseLang.currentData()
            text = self.current_word
            if self.toplay_in_test:
                self.play_text_as_audio(text, language)
        else:
            self.toggle_test_mode()
        self.lbWordsCounter.setText(f"{LANGUAGES[self.current_language]['Custom_QDialog_label_content']['next_question_forTest_remain']} {self.current_words_count}/{self.total_words_count}")
                
    def check_answer(self):
        """사용자가 입력한 답을 확인하는 함수"""
        user_input = self.txtMeaningInput.toPlainText().strip()
        if user_input == self.current_meaning:
            self.show_feedback(True)
            self.show_error_onColumn3_8("", self.current_meaning, self.current_word, self.current_number, True)
        else:
            self.show_feedback(False)
            self.show_error_onColumn3_8(user_input, self.current_meaning, self.current_word, self.current_number, False)

        self.txtMeaningInput.setPlainText("")
        self.next_question_forPractice()  # 다음 문제로 이동

    def show_error_onColumn3_8(self, error_text, word, meaning, number, error):
          # 이벤트 신호 일시 중단
        translated = LANGUAGES[self.current_language]
        self.disconnect_events()
        for row in range(self.tbWordList.rowCount()):
            number_item = self.tbWordList.item(row, 0)
            word_item = self.tbWordList.item(row, 1)
            meaning_item = self.tbWordList.item(row, 2)

            if not number_item or not word_item or not meaning_item:
                continue

            try:
                row_number = int(number_item.text())
            except ValueError:
                continue  # 숫자 변환 실패 시 건너뜀

            if (
                row_number == number and
                word_item.text() == word and
                meaning_item.text() == meaning
            ) or (
                row_number == number and
                meaning_item.text() == word and
                word_item.text() == meaning
            ) or (
                row_number == number and
                word_item.text() == word and
                word_item.text() == meaning
            ) :
                self.tbWordList.setItem(row, 3, QTableWidgetItem(error_text))

                if error:
                    text = translated["Custom_QDialog_label_content"]["show_feedback_var_cor"]
                    self.tbWordList.setItem(row, 8, QTableWidgetItem(text))
                else:
                    text = translated["Custom_QDialog_label_content"]["show_feedback_var_incor"]
                    self.tbWordList.setItem(row, 8, QTableWidgetItem(text))
                break  # ✅ 일치하는 항목 찾았으면 중단
        self.connect_events()
          # 이벤트 신호 일시 중단

    def check_answer_forTest(self):
        """사용자가 입력한 답을 확인하는 함수"""
        user_input = self.txtMeaningInput.toPlainText().strip()
        if user_input == self.current_meaning:
            self.show_feedback(True)
            self.answer_words_count += 1
            self.current_words_count -= 1
            self.lbWordsCounter.setText(f"{LANGUAGES[self.current_language]['Custom_QDialog_label_content']['next_question_forTest_remain']} {self.current_words_count}/{self.total_words_count}")
        else:
            self.show_feedback(False)
            self.current_words_count -= 1
            self.lbWordsCounter.setText(f"{LANGUAGES[self.current_language]['Custom_QDialog_label_content']['next_question_forTest_remain']} {self.current_words_count}/{self.total_words_count}")
            
        self.next_question_forTest()  # 다음 문제로 이동

    def sanitize_filename(self, text):
        # 파일 이름에 사용할 수 없는 문자를 '_'로 대체하는 함수
        return re.sub(r'[\\/*?:"<>|]', "_", text)
    
    def connect_events(self):
        """이벤트를 연결하는 함수"""
        if not self.item_selection_connected:
            self.tbWordList.itemSelectionChanged.connect(self.on_cell_selection_changed)
            self.item_selection_connected = True
        if not self.cell_changed_connected:
            self.tbWordList.cellChanged.connect(self.on_cell_edit_finished)
            self.cell_changed_connected = True
        self.tbWordList.blockSignals(False)
        
            
    def disconnect_events(self):
        """이벤트를 해제하는 함수"""
        self.tbWordList.blockSignals(True)
        if self.item_selection_connected:
            self.tbWordList.itemSelectionChanged.disconnect()
            self.item_selection_connected = False
        if self.cell_changed_connected:
            self.tbWordList.cellChanged.disconnect()
            self.cell_changed_connected = False

    #-----------------------------------------------------------키 이벤트------------------------------------------------------#
    
    def keyPressEvent(self, event):
        focused_widget = self.focusWidget()
        
        # 포커스가 self.txtMeaningInput일 때 처리
        if focused_widget == self.txtMeaningInput:
            if event.key() == QtCore.Qt.Key_Return or event.key() == QtCore.Qt.Key_Enter:
                return
            elif event.key() == QtCore.Qt.Key_F5:
                if self.is_testing and self.practice_mode in (2, 3, 4):
                    self.lbThreeCount.raise_()
        
                    if hasattr(self, 'timer') and self.timer.isActive():
                        self.timer.stop()

                    self.text_color = "rgba(183, 33, 36"  # 빨간색
                    self.lbThreeCount.setText(LANGUAGES[self.current_language]["Custom_QDialog_label_content"]["keyPressEvent_label"])
                    self.sound_player.streak_count = 0
                    if self.practice_mode == 2 or self.practice_mode == 4:
                        lang_code = self.cbbLangToLearn.currentData()
                        self.update_answer_count(self.current_number, self.current_word, False)
                        self.play_text_as_audio(self.current_word, lang_code)
                    else:
                        lang_code = self.cbbBaseLang.currentData()
                        self.update_answer_count(self.current_number, self.current_meaning, False)
                        self.play_text_as_audio(self.current_word, lang_code)
                        
                    # 초기 상태 설정
                    self.lbThreeCount.setStyleSheet(f"color: {self.text_color}, 255); font-size: 1px;")
    
                    # 애니메이션 변수 설정
                    self.current_font_size = 1  # 초기 글씨 크기
                    self.current_opacity = 255   # 초기 투명도 (완전히 불투명)
                    self.animation_steps = 50   # 애니메이션을 100단계로 나누어 진행 (부드럽게)
                    self.step_duration = 15      # 각 단계는 30ms 간격으로 업데이트 (총 3000ms)

                    # 타이머 설정 (애니메이션 30ms 간격으로 업데이트)
                    self.timer = QTimer(self)
                    self.timer.timeout.connect(self.animate_feedback)
                    self.timer.start(self.step_duration)  # 30ms마다 애니메이션 업데이트
                    
                elif self.is_practice:
                    if self.is_practice and self.practice_mode in (5, 6):
                        if self.practice_mode == 5:
                            lang_code = self.cbbLangToLearn.currentData()
                            self.play_text_as_audio(self.current_word, lang_code)
                        elif self.practice_mode == 6:
                            lang_code = self.cbbBaseLang.currentData()
                            self.play_text_as_audio(self.current_word, lang_code)
                        elif self.practice_mode == 7:
                            lang_code = self.cbbLangToLearn.currentData()
                            self.play_text_as_audio(self.current_word, lang_code)
            return
    
        current_row = self.tbWordList.currentRow()
        current_column = self.tbWordList.currentColumn()
        total_rows = self.tbWordList.rowCount() - 1

        """F5 키 누름 이벤트"""
        #print("keyPressEvent 호출됨")  # 키 이벤트 진입 확인
        if event.key() == Qt.Key_F5: 
            selected_item = self.tbWordList.currentItem()
            if selected_item:
                #print(f"선택된 셀의 단어: {selected_item.text()}")
                language = self.cbbLangToLearn.currentData()
                row = self.tbWordList.currentRow()
                column = self.tbWordList.currentColumn()
                item = self.tbWordList.item(row, column)
                if item and item.text().strip():  # 빈 문자열이 아닌 경우에만 처리
                    if column == 2:  # 뜻 열 편집 완료
                        item = self.tbWordList.item(row, 2)
                        text = item.text()
                        language = self.cbbBaseLang.currentData()
                    elif column == 3:  # 뜻 열 편집 완료
                        if self.practice_mode == 0 or self.practice_mode == 2 or self.practice_mode == 4:
                            item = self.tbWordList.item(row, 1)
                            text = item.text()
                            language = self.cbbLangToLearn.currentData()
                        else:
                            item = self.tbWordList.item(row, 2)
                            text = item.text()
                            language = self.cbbBaseLang.currentData()
                    else:  # 단어 열 또는 다른 셀 편집 완료
                        item = self.tbWordList.item(row, 1)
                        text = item.text()
                        language = self.cbbLangToLearn.currentData()
                else:
                    item = self.tbWordList.item(row, 1)
                    text = item.text()
                    language = self.cbbLangToLearn.currentData()
                    
                self.play_text_as_audio(text, language)

            event.accept()  # 이벤트가 다른 곳으로 전파되지 않도록 처리
        else:
            super(MyApp, self).keyPressEvent(event)
        
    # 엑셀처럼 Enter와 Shift+Enter를 처리하는 메서드
        if event.key() == QtCore.Qt.Key_Return or event.key() == QtCore.Qt.Key_Enter:
            if event.modifiers() == QtCore.Qt.ShiftModifier:
                # Shift+Enter 처리 - 위쪽 셀로 이동
                next_row = total_rows if current_row == 0 else current_row - 1
            else:
                # Enter 처리 - 아래쪽 셀로 이동
                next_row = 0 if current_row == total_rows else current_row + 1
            self.tbWordList.setCurrentCell(next_row, current_column)
            event.accept()
        else:
            super(MyApp, self).keyPressEvent(event)
            
        if self.is_editing:
            # ✅ Ctrl 키 조합
            if event.modifiers() == QtCore.Qt.ControlModifier:
                if event.key() == QtCore.Qt.Key_Backspace:
                    self.delete_selected_rows()
                elif event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
                    self.add_new_row(current_row, total_rows)
                elif event.key() == QtCore.Qt.Key_V:
                    self.paste_csv()
            # ✅ Delete 키 단독
            elif event.key() == QtCore.Qt.Key_Delete:
                self.delete_selected_rows()
            else:
                super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)
        
        """ 🎯 ESC 키 입력 시 녹음 종료 """
        if event.key() == Qt.Key_Escape:
            #print("🔴 ESC 입력 감지 → 녹음 종료")
            if self.recorder.recording:  # ✅ 녹음 중인 경우에만 toggle_recording() 호출
                self.toggle_recording()  
                    
    #-----------------------------------------------------------키 이벤트------------------------------------------------------#
                    
    def paste_csv(self):
        clipboard = QtWidgets.QApplication.clipboard()
        text = clipboard.text().lstrip('\ufeff').strip()  # ✅ BOM 제거 + 공백 제거

        if not text:
            return  # 클립보드가 비어있으면 아무것도 안 함

        rows = [row for row in text.split('\n') if row.strip()]  # ✅ 빈 줄 제거
        data = [row.split('|') for row in rows]

        selected = self.tbWordList.selectedIndexes()

        # ✅ 선택된 셀이 없으면 마지막 행, 첫 열부터 시작
        if selected:
            start_row = selected[0].row()
            start_col = selected[0].column()
        else:
            start_row = self.tbWordList.rowCount()
            start_col = 0

        # ✅ 필요한 만큼 행을 추가
        needed_rows = start_row + len(data)
        if needed_rows > self.tbWordList.rowCount():
            self.tbWordList.setRowCount(needed_rows)

        # ✅ 이벤트 차단 (blockSignals 대신 disconnect_events)
        self.disconnect_events()
        for i, row_data in enumerate(data):
            for j, cell in enumerate(row_data):
                if start_col + j < self.tbWordList.columnCount():
                    self.tbWordList.setItem(start_row + i, start_col + j, QTableWidgetItem(cell))
        self.align_cells_width()
        self.apply_font()
        self.apply_font_totarget()
        self.connect_events()

    def delete_selected_rows(self):
        selected_indexes = self.tbWordList.selectedIndexes()
        if not selected_indexes:
            return

        # ✅ 선택된 행 번호들 구하고 중복 제거
        rows = sorted(set(index.row() for index in selected_indexes), reverse=True)

        # ✅ 이벤트 차단
        self.disconnect_events()
        for row in rows:
            self.tbWordList.removeRow(row)
        self.connect_events()
    
    def add_new_row(self, current_row, total_rows):
        # 현재 선택된 행이 없는 경우 마지막 행을 기준으로 설정
        if current_row == -1:
            total_rows = total_rows - 1

        # 새로운 행을 current_row 아래에 추가
        if current_row == total_rows - 1:
            self.tbWordList.insertRow(total_rows)  # 마지막에 새로운 행 추가
            current_row = total_rows
        elif current_row == -1 and total_rows == -2:
            # 첫 번째 행을 추가
            self.tbWordList.insertRow(0)
            current_row = 0
        else:
            # 선택된 행의 바로 아래에 새 행 추가
            self.tbWordList.insertRow(current_row + 1)
            current_row += 1
        
        # 새로 추가된 행의 첫 번째 셀에 빈 항목 추가
        new_item = QTableWidgetItem("")
        self.tbWordList.setItem(current_row, 0, new_item)

        # 포커스 및 선택 상태 설정
        self.tbWordList.setCurrentCell(current_row, 0)
        self.tbWordList.clearSelection()
        self.tbWordList.selectRow(current_row)

        # 테이블 강제 갱신
        self.tbWordList.viewport().update()

        # 디버깅: 새 행 추가 후 현재 선택된 행 확인
        
    def number_checker_before_test(self):
        """📌 테이블의 0번 컬럼(번호)이 올바르게 입력되었는지 확인"""
        translated = LANGUAGES[self.current_language]
        self.disconnect_events()
        for row in range(self.tbWordList.rowCount()):
            number_item = self.tbWordList.item(row, 0)  # ✅ 0번 컬럼 (번호)
            word_item = self.tbWordList.item(row, 1)
            meaning_item = self.tbWordList.item(row, 2)

            text = number_item.text().strip() if number_item else ""
            valid = False
            #print(f"[검사중] row={row}, 입력값='{text}'")

            try:
                value = int(text)
                if value <= 0:
                    error_message = translated["Custom_QDialog_label_content"]["number_checker_before_test_error1"]
                else:
                    valid = True
            except (ValueError, AttributeError):
                error_message = translated["Custom_QDialog_label_content"]["number_checker_before_test_error2"]

            if not valid:
                self.show_custom_message(translated["Custom_QDialog_label_title"]["text_error"], error_message)
                return False
                
            if not word_item or not word_item.text().strip() or not meaning_item or not meaning_item.text().strip() :  # ✅ 빈 값 체크
                self.show_custom_message(translated["Custom_QDialog_label_title"]["text_error"], translated["Custom_QDialog_label_content"]["number_checker_before_test_label"])
                return False  # ✅ 숫자로 변환 실패 시도 `False` 반환
        self.connect_events()
        return True  # ✅ 모든 번호가 정상적으로 입력되었을 경우 True 반환
    
    def toggle_practice_mode(self):
        """연습 모드를 선택하는 함수. 선택지에 따라 단어-뜻 또는 뜻-단어 리스트를 생성"""
        translated = LANGUAGES[self.current_language]
        result = self.number_checker_before_test()
        #print(f"[디버그] number_checker_before_test() 결과: {result}")

        if not result:
            return

        filtered_pairs = self.create_word_meaning_list(mode="word_to_meaning")
        if not filtered_pairs and not self.is_practice:
            self.no_exam_practice_mode()
            return
        
        # 선택지 다이얼로그 생성
        self.sound_player.streak_count = 0
        if not self.is_practice:
            self.reset_text_format_except_font(self.txtMeaningInput)
            self.is_practice = True
            self.practice_mode = 5
            self.toplay_in_test = True
            self.disable_buttons()
            self.btnPractice.setEnabled(True)
            self.set_text_widget_editable(True)
            self.tbWordList.clearSelection()
            choice = self.show_practice_choice_dialog()
            self.disconnect_events()
            for row in range(self.tbWordList.rowCount()):
                empty_item = QTableWidgetItem("")  # 공백 아이템 생성
                self.tbWordList.setItem(row, 3, empty_item)
            #print(f"선택된 모드: {choice}")
            if choice == translated["Custom_QDialog_label_content"]["toggle_practice_mode_wtom"]:
                # 단어-뜻 페어로 리스트 생성
                filtered_pairs = self.create_word_meaning_list(mode="word_to_meaning")
                self.start_test_forPractice()
            elif choice == translated["Custom_QDialog_label_content"]["toggle_practice_mode_mtow"]:
                # 뜻-단어 페어로 리스트 생성
                filtered_pairs = self.create_word_meaning_list(mode="meaning_to_word")
                self.start_test_forPractice()
            elif choice == translated["Custom_QDialog_label_content"]["toggle_practice_mode_dict"]:
                # 뜻-단어 페어로 리스트 생성
                filtered_pairs = self.create_word_meaning_list(mode="dictation")
                self.start_test_forPractice()
            else:
                filtered_pairs = []
                self.cancel_practice_mode()
                self.connect_events()
                return
        else:
            self.cancel_practice_mode()
            self.connect_events()
            return
            
    def no_exam_practice_mode(self):
        translated = LANGUAGES[self.current_language]
        self.show_custom_message(translated["Custom_QDialog_label_title"]["text_error"], translated["Custom_QDialog_label_content"]["toggle_practice_mode_no_word"])
        self.cancel_practice_mode()

    def cancel_practice_mode(self):
        translated_text = LANGUAGES.get(self.current_language, LANGUAGES["한국어"])
        base_font_name = self.cbbFontSetting.currentData()
        self.txtWordInput.status = "practicing done"
        self.txtMeaningInput.status = "practicing done"
        self.txtWordInput.setPlainText(translated_text["practicing_done1"])
        self.txtMeaningInput.setPlainText(translated_text["practicing_done2"])
        if base_font_name:
            font = QFont(base_font_name)
            font.setPointSize(self.word_font_size)  # 현재 설정된 크기 유지
            self.txtWordInput.setFont(font)
            self.txtMeaningInput.setFont(font)
        self.sound_player.streak_count = 0
        self.current_word = ""
        self.current_meaning = ""
        self.current_number = 0
        self.highlight_current_word_in_table()
        self.is_practice = False
        self.enable_buttons()
        self.btnPractice.setEnabled(True)
        self.set_text_widget_editable(False)
        self.update_cell_background()
        if self.is_descending:
            self.is_descending = not self.is_descending
        else:
            pass
        self.handle_header_click(8)
        
        self.connect_events()
        
    def show_practice_choice_dialog(self):
        """사용자에게 선택지를 제시하는 다이얼로그"""
        translated = LANGUAGES[self.current_language]
        choice_dialog = ThemedDialog(title=translated["Custom_QDialog_label_title"]["text_select_practice_mode"], parent=self, theme=self.current_theme)
        
        label = QLabel(translated["Custom_QDialog_label_content"]["show_practice_choice_dialog_select_mode"], choice_dialog)
        label.setContentsMargins(QMargins(45,2,2,2))
        choice_dialog.content_layout.addWidget(label)
        
        # ✅ 버튼 직접 생성
        btn1 = QPushButton(translated["Custom_QDialog_label_content"]["toggle_practice_mode_wtom"])
        btn1.setProperty("result", 1)  # ✅ 반환 값 지정
        btn1.clicked.connect(lambda: choice_dialog.done(btn1.property("result")))
        btn2 = QPushButton(translated["Custom_QDialog_label_content"]["toggle_practice_mode_mtow"])
        btn2.setProperty("result", 2)  # ✅ 반환 값 지정
        btn2.clicked.connect(lambda: choice_dialog.done(btn2.property("result")))
        btn3 = QPushButton(translated["Custom_QDialog_label_content"]["toggle_practice_mode_dict"])
        btn3.setProperty("result", 3)  # ✅ 반환 값 지정
        btn3.clicked.connect(lambda: choice_dialog.done(btn3.property("result")))
        btn_close = QPushButton(translated["Custom_QDialog_buttons"]["text_cancel"])  # 🔥 X 버튼 역할
        btn_close.clicked.connect(lambda: (choice_dialog.done(0), choice_dialog.close()))  # ✅ 다이얼로그 종료 & 함수 즉시 종료
        
        choice_dialog.button_layout.addWidget(btn1)
        choice_dialog.button_layout.addWidget(btn2)
        choice_dialog.button_layout.addWidget(btn3)
        # ✅ X 버튼(닫기 버튼)을 활성화하려면 `QMessageBox.RejectRole` 버튼을 추가해야 함
        choice_dialog.button_layout.addWidget(btn_close)
        
        self.apply_theme_toButtons(self.current_theme, btn1)
        self.apply_theme_toButtons(self.current_theme, btn2)
        self.apply_theme_toButtons(self.current_theme, btn3)
        self.apply_theme_toButtons(self.current_theme, btn_close)
        self.apply_hover_events(btn1, self.animated_hover_start, self.animated_hover_end)
        self.apply_hover_events(btn2, self.animated_hover_start, self.animated_hover_end)
        self.apply_hover_events(btn3, self.animated_hover_start, self.animated_hover_end)
        self.apply_hover_events(btn_close, self.animated_hover_start, self.animated_hover_end)

        result = choice_dialog.exec_()
        
        if result == 1:
            self.practice_mode = 5    
            return translated["Custom_QDialog_label_content"]["toggle_practice_mode_wtom"]
        elif result == 2:
            self.practice_mode = 6    
            return translated["Custom_QDialog_label_content"]["toggle_practice_mode_mtow"]
        elif result == 3:
            self.practice_mode = 7    
            return translated["Custom_QDialog_label_content"]["toggle_practice_mode_dict"]
        else:
            return

    def create_word_meaning_list(self, mode="word_to_meaning"):
        """단어와 뜻 리스트를 생성하는 함수. 번호를 포함한 리스트를 전역 변수에 저장"""
        #print(f"시험모드{mode}")
        # 먼저 tbWordList의 모든 번호, 단어, 뜻을 가져옴
        
        self.disconnect_events()
        translated = LANGUAGES[self.current_language]
        word_meaning_pairs = []
        for row in range(self.tbWordList.rowCount()):
            number_item = self.tbWordList.item(row, 0)  # 0번 컬럼 (번호)
            word_item = self.tbWordList.item(row, 1)    # 1번 컬럼 (단어)
            meaning_item = self.tbWordList.item(row, 2) # 2번 컬럼 (뜻)
        
            if number_item and word_item and meaning_item:
                number = int(number_item.text())  # 번호를 int로 변환
                word = word_item.text()
                meaning = meaning_item.text()

                # 모드에 따라 단어-뜻 또는 뜻-단어 리스트 생성
                if mode == "word_to_meaning":
                    word_meaning_pairs.append((number, word, meaning))  # 번호와 함께 저장 (단어 -> 뜻)
                elif mode == "meaning_to_word":
                    word_meaning_pairs.append((number, meaning, word))  # 번호와 함께 저장 (뜻 -> 단어)
                elif mode == "dictation":
                    word_meaning_pairs.append((number, word, word))  # 번호와 함께 저장 (단어 -> 뜻)

        # 필터링 조건 적용
        filtered_pairs = []
        #print(self.confirmedAllWord)

        # 모든 단어 선택 시
        if self.chbAllWords.isChecked() or self.confirmedAllWord:
            filtered_pairs = word_meaning_pairs

        # 오답만 필터링
        elif self.chbOnlyIncorrects.isChecked() and not self.chbOnlyLowRates.isChecked() and not self.confirmedAllWord and not self.chbAllWords.isChecked():
            for row in range(self.tbWordList.rowCount()):
                result_item = self.tbWordList.item(row, 8)  # 8번 컬럼 (정답/오답)
                if result_item and result_item.text() == translated["Custom_QDialog_label_content"]["show_feedback_var_incor"]:
                    filtered_pairs.append(word_meaning_pairs[row])

        # 정답률 기준만 필터링
        elif self.chbOnlyLowRates.isChecked() and not self.chbOnlyIncorrects.isChecked() and not self.confirmedAllWord and not self.chbAllWords.isChecked():
            selected_rate = int(self.cbbRateFilter.currentText().replace('%', ''))
            for row in range(self.tbWordList.rowCount()):
                rate_item = self.tbWordList.item(row, 5)  # 5번 컬럼 (정답률)
                if rate_item and rate_item.text().replace('%', '').isdigit():
                    rate = int(rate_item.text().replace('%', ''))
                    if rate <= selected_rate:
                        #print(f"선택된 정답률: {selected_rate}")
                        #print(f"선택된 문제: {word_meaning_pairs[row]}")
                        filtered_pairs.append(word_meaning_pairs[row])

        # 오답만 + 정답률 기준 필터링
        elif self.chbOnlyIncorrects.isChecked() and self.chbOnlyLowRates.isChecked() and not self.confirmedAllWord and not self.chbAllWords.isChecked():
            selected_rate = int(self.cbbRateFilter.currentText().replace('%', ''))
            for row in range(self.tbWordList.rowCount()):
                result_item = self.tbWordList.item(row, 8)  # 8번 컬럼 (정답/오답)
                rate_item = self.tbWordList.item(row, 5)  # 5번 컬럼 (정답률)
                if (result_item and result_item.text() == translated["Custom_QDialog_label_content"]["show_feedback_var_incor"]) or (rate_item and rate_item.text().replace('%', '').isdigit()):
                    rate = int(rate_item.text().replace('%', ''))
                    result = result_item.text()
                    if rate <= selected_rate or result == translated["Custom_QDialog_label_content"]["show_feedback_var_incor"]:
                        #print(f"선택된 정답률: {selected_rate}")
                        #print(f"선택된 문제: {word_meaning_pairs[row]}")
                        filtered_pairs.append(word_meaning_pairs[row])

        # 전역 변수에 번호가 포함된 리스트 저장
        self.numbered_word_meaning_list = filtered_pairs

        # 정렬 방식에 따라 처리
        selected_test_type = self.cbbTestType.currentText()
        if selected_test_type == translated["Custom_QDialog_label_content"]["start_test_forTest_des"]:
            filtered_pairs.sort(key=lambda x: x[0], reverse=True)  # 0번 컬럼 (번호) 기준 내림차순 정렬
        elif selected_test_type == translated["Custom_QDialog_label_content"]["start_test_forTest_as"]:
            filtered_pairs.sort(key=lambda x: x[0])  # 0번 컬럼 (번호) 기준 오름차순 정렬
        elif selected_test_type == translated["Custom_QDialog_label_content"]["start_test_forTest_rd"]:
            random.shuffle(filtered_pairs)  # 무작위 섞기

        # 최종적으로 정렬된 리스트에서 번호를 제외한 단어-뜻 페어 저장
        self.word_meaning_list = [(item[0], item[1], item[2]) for item in filtered_pairs]
        #print(f"만들어진 내용{self.word_meaning_list}")
    
        self.total_words_count = len(self.word_meaning_list)
        self.current_words_count = len(self.word_meaning_list)
        self.answer_words_count = 0
        self.connect_events()
        return filtered_pairs 
    
    def toggle_edit_mode(self):
        translated = LANGUAGES[self.current_language]
        self.disconnect_events()
        if self.is_editing:
            if self.check_for_empty_cells():
                self.show_custom_message(translated["Custom_QDialog_label_title"]["text_warning"], translated["Custom_QDialog_label_content"]["toggle_edit_mode_label"])
            else:
                self.show_save_options()
        else:
            self.enter_edit_mode()
            
    def check_for_empty_cells(self):
        self.disconnect_events()
        for row in range(self.tbWordList.rowCount()):
            for column in range(3):  # 0, 1, 2 열만 체크
                item = self.tbWordList.item(row, column)
                if item is None or item.text().strip() == "":
                    return True
        self.connect_events()
        return False
            
    #-------------------------------------------------------파일 처리 관련 함수 ------------------------------------------------#
    
    def load_csv(self, file_name):
        """CSV 파일을 로드하고 테이블에 데이터를 표시하는 함수"""
        translated = LANGUAGES[self.current_language]
        self.disconnect_events()
        self.is_loading = True  # 데이터 로드 중임을 표시
        #print(f"load_csv 현재 파일은?: {file_name}")
        self.current_folder = os.path.dirname(file_name)
        #print(f"load_csv 현재 폴더는?: {self.current_folder}")
        self.current_file = self.get_relative_path(file_name)
        #print(f"load_csv 현재 파일은?: {self.current_file}")
        self.save_recent_files(self.current_file)
        self.load_recent_files()

        try:
            with open(file_name, newline='', encoding='utf-8-sig') as csvfile:
                csvreader = csv.reader(csvfile, delimiter='|')
                self.tbWordList.setRowCount(0)
                for row_data in csvreader:
                    row_number = self.tbWordList.rowCount()
                    self.tbWordList.insertRow(row_number)
                    for column_number in range(len(row_data)):
                        data = row_data[column_number]
    
                        if column_number in [6, 7, 8]:
                            code_value = self.normalize_cell_value(data)  # 한국어든 영어든 → 코드값으로
                            display_value = self.translate_cell_value(code_value)  # 코드값 → 현재 언어로 번역
                            item = QTableWidgetItem(display_value)
                            item.setData(QtCore.Qt.UserRole, code_value)  # 코드값 저장
                            #print(f"[변환] col={column_number}, 원본={data}, 코드={code_value}, 표시={display_value}")
                        else:
                            # 나머지 열은 있는 그대로 표시
                            item = QTableWidgetItem(data)

                        item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)
                        self.tbWordList.setItem(row_number, column_number, item)
    
                    # 각 행이 추가된 후 정답률 계산
                    self.calculate_correct_rate(row_number)
                self.display_success_message()
        
        except Exception as e:
            self.display_no_file_message()
            if not self.is_initializing:
                self.show_custom_message(translated["Custom_QDialog_label_title"]["text_error"], f"{translated['Custom_QDialog_label_content']['load_csv_label']} {e}")
        finally:
            self.is_loading = False  # 데이터 로드 완료

        self.current_file = self.cbbWordFile.currentText()
        self.rate_filter_updater()
        self.on_rate_filter_changed()
        self.new_time_record_check()
        self.update_cell_background()
        self.update_last_test_colors()
        self.update_last_test_label(file_name)
        self.set_table_editable(False)
        self.align_cells_width()
        self.apply_font_totarget()
        self.connect_events()
        self.txtmeaninginput_style_reset(self.current_theme)
    
    def open_file_dialog(self):
        """📂 사용자가 CSV 파일을 선택할 때"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "단어 파일 선택", self.current_folder, "CSV 파일 (*.csv);;모든 파일 (*)"
        )
    
        #print(f"📌 파일 경로(open_file_dialog): {file_path}")  # ✅ 디버깅용 출력

        # ✅ 사용자가 취소 버튼을 눌렀을 경우 → 함수 종료
        if not file_path:  
            return  # ✅ 아무 작업도 하지 않고 함수 종료

        # ✅ 사용자가 파일을 선택한 경우
        self.current_folder = os.path.dirname(file_path)
        self.selected_file = os.path.relpath(file_path, self.its_placement)
        #print(f"open_file_dialog self.current_folder: {self.current_folder}")
        #print(f"open_file_dialog self.selected_file: {self.selected_file}")

        # ✅ 블록 시그널 비활성화 후, 사용자가 선택한 파일과 일치하는 아이템 선택
        self.cbbWordFile.blockSignals(False)  
        self.cbbWordFile.setCurrentText(self.selected_file)  # 🔥 사용자가 선택한 파일을 목록에서 강조
        self.load_csv(file_path)  # ✅ 선택한 파일 로드
        self.save_recent_files(self.selected_file)
        
        self.is_opened_byuser = False
        self.refresh_file_list()  # ✅ 사용자가 직접 파일 선택
    
    def show_save_options(self):
        translated = LANGUAGES[self.current_language]
        self.disconnect_events()
        """저장 옵션 다이얼로그를 표시하고 파일 이름을 기반으로 처리"""
        dialog = ThemedDialog(title="저장 옵션", parent=self, theme=self.current_theme)

        # 콤보박스에서 선택된 파일 이름을 사용
        file_name = self.cbbWordFile.currentText()

        label = QLabel(translated["Custom_QDialog_label_content"]["show_save_options_label"], dialog)
        label.setContentsMargins(QMargins(45,2,2,2))
        self.apply_theme(self.current_theme, label)
        dialog.content_layout.addWidget(label)

        btn_save_exit = QPushButton(translated["Custom_QDialog_buttons"]["text_edit_justexit"], dialog)
        btn_save_exit.clicked.connect(lambda: self.save_and_exit(dialog, save=False))
        self.apply_theme_toButtons(self.current_theme, btn_save_exit)
        dialog.button_layout.addWidget(btn_save_exit)

        btn_overwrite = QPushButton(translated["Custom_QDialog_buttons"]["text_edit_override"], dialog)
        btn_overwrite.clicked.connect(lambda: self.save_and_exit(dialog, save=True))
        self.apply_theme_toButtons(self.current_theme, btn_overwrite)
        dialog.button_layout.addWidget(btn_overwrite)

        btn_save_as = QPushButton(translated["Custom_QDialog_buttons"]["text_edit_save_othername"], dialog)
        btn_save_as.clicked.connect(lambda: self.save_as_new_file(dialog))
        self.apply_theme_toButtons(self.current_theme, btn_save_as)
        dialog.button_layout.addWidget(btn_save_as)

        btn_continue_edit = QPushButton(translated["Custom_QDialog_buttons"]["text_edit_keep_editing"], dialog)
        btn_continue_edit.clicked.connect(lambda: (self.disconnect_events(), dialog.close()))
        self.apply_theme_toButtons(self.current_theme, btn_continue_edit)
        dialog.button_layout.addWidget(btn_continue_edit)

        file_name = self.cbbWordFile.currentText()

        # ✅ 파일 존재 + 확장자가 csv 인지 확인
        if os.path.isfile(file_name) and file_name.lower().endswith('.csv'):
            btn_overwrite.setEnabled(True)   # 활성화
            self.apply_hover_events(btn_overwrite, self.animated_hover_start, self.animated_hover_end)
        else:
            btn_overwrite.setEnabled(False)  # 비활성화
    
        self.apply_hover_events(btn_save_exit, self.animated_hover_start, self.animated_hover_end)
        self.apply_hover_events(btn_save_as, self.animated_hover_start, self.animated_hover_end)
        self.apply_hover_events(btn_continue_edit, self.animated_hover_start, self.animated_hover_end)

        dialog.exec_()
        
    def save_and_exit(self, dialog, save):
        """저장하고 종료하는 함수"""
        if save and self.current_file:  # self.current_file에는 파일 이름이 문자열로 저장되어 있어야 함
            # 파일 이름이 올바른지 확인 후 저장
            self.save_changes_to_file(self.current_file)
        self.exit_edit_mode()
        dialog.accept()
        
        self.disconnect_events()  # ✅ 이벤트 해제
        if not save:
            self.tbWordList.setRowCount(0)  # ✅ 모든 행 삭제
        self.refresh_file_list()
        self.connect_events()
        
    def get_latest_csv_file(self, folder_path='.'):
        """폴더 및 모든 하위 폴더 내에서 가장 최근에 수정된 CSV 파일 반환"""
        csv_files = []

        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith('.csv'):
                    full_path = os.path.join(root, file)
                    if os.path.isfile(full_path):  # ✅ 경로가 유효한지 추가로 체크!
                        csv_files.append(full_path)

        if not csv_files:
            return None

        latest_file = max(csv_files, key=os.path.getmtime)
        return latest_file

    def set_current_file(self, file_name):
        """현재 파일을 설정하고 테이블에 로드 (가장 최근 파일 등)"""
        # 콤보박스에서 선택된 파일 표시
        self.load_csv(file_name)
        self.selected_file = self.get_relative_path(file_name)
        index = self.cbbWordFile.findText(os.path.basename(self.selected_file))
        if index != -1:
            self.cbbWordFile.setCurrentIndex(index)
        self.connect_events()

    def save_as_new_file(self, dialog):
        """다른 이름으로 저장하는 함수"""
        self.disconnect_events()
        file_dialog = QtWidgets.QFileDialog()
        new_file_path, _ = file_dialog.getSaveFileName(self, LANGUAGES[self.current_language]["Custom_QDialog_label_content"]["save_as_new_file_dialog_title"], "", "CSV Files (*.csv)")

        if not new_file_path:  
            return  # ✅ 취소하면 함수 종료 (다이얼로그만 닫힘)

        # ✅ 새로운 파일로 저장
        self.save_changes_to_file(new_file_path)

        # ✅ 폴더 내에서 가장 최근에 수정된 파일을 불러옴
        latest_file = self.get_latest_csv_file(self.its_placement)

        if latest_file:
            self.set_current_file(latest_file)  # 가장 최근 파일을 현재 파일로 설정하고 로드
            #print(f"최근 수정된 파일: {latest_file}")

            # ✅ 다이얼로그 닫기
        self.refresh_file_list()
        self.cbbWordFile.setCurrentText(self.current_file)
        self.display_success_message()
        self.exit_edit_mode()    
        dialog.accept()

    def save_changes_to_file(self, file_name):
        """파일 이름을 사용하여 데이터를 저장"""
        self.disconnect_events()
        #print(f"save_changes_to_file file_name{file_name}")
        if isinstance(file_name, str):  # 파일 이름이 문자열인지 확인
            file_path = os.path.join(self.its_placement, file_name)  # ✅ 전체 경로 생성
            #print(f"save_changes_to_file file_path{file_path}")
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f, delimiter='|')
                for row in range(self.tbWordList.rowCount()):
                    row_data = []
                    for col in range(self.tbWordList.columnCount()):
                        item = self.tbWordList.item(row, col)
    
                        if item:
                            if col in [6, 7, 8]:  # ✅ 코드값으로 저장해야 할 컬럼
                                value = item.data(QtCore.Qt.UserRole)
                                if value is None:
                                    value = self.normalize_cell_value(item.text())
                            else:  # ✅ 일반 컬럼은 텍스트 그대로 저장
                                value = item.text()
                        else:
                            value = ""
    
                        row_data.append(value)
                    writer.writerow(row_data)
        else:
            print(f"잘못된 파일 이름: {file_path}")
        self.connect_events()
    
    def delete_current_file(self):
        """현재 불러와진 파일을 삭제하고 파일 목록을 새로 고침"""
        translated = LANGUAGES[self.current_language]
        if hasattr(self, 'current_file') and self.current_file:
            QApplication.beep()
            msg_box = ThemedDialog(translated["Custom_QDialog_label_title"]["text_delete_file"], self, self.current_theme)
            label = QLabel(f"{self.current_file} {translated['Custom_QDialog_label_content']['delete_current_file_sure_to_delete']}", msg_box)
            msg_box.content_layout.setContentsMargins(15, 5, 15, 5)
            msg_box.content_layout.addWidget(label)

            yes_button = QPushButton(translated["Custom_QDialog_buttons"]["text_delete"])
            yes_button.setProperty("result", 1)  # ✅ 반환 값 지정
            yes_button.clicked.connect(msg_box.accept)  # ✅ 클릭하면 다이얼로그 닫힘
            no_button = QPushButton(translated["Custom_QDialog_buttons"]["text_cancel"])
            no_button.setProperty("result", 2)  # ✅ 반환 값 지정
            no_button.clicked.connect(msg_box.close)  # ✅ 클릭하면 다이얼로그 닫힘
            self.apply_theme_toButtons(self.current_theme, yes_button)
            self.apply_theme_toButtons(self.current_theme, no_button)
            self.apply_hover_events(yes_button, self.animated_hover_start, self.animated_hover_end)
            self.apply_hover_events(no_button, self.animated_hover_start, self.animated_hover_end)
            msg_box.button_layout.addWidget(yes_button)
            msg_box.button_layout.addWidget(no_button)

                    # ✅ 다이얼로그 실행 후 결과 반환
            result = msg_box.exec_() #if문 있으면 써야
            
            if result == 1:
                try:
                    # 파일 삭제
                    os.remove(self.current_file)
                    self.delete_recent_files(self.current_file)
                    self.show_custom_message(translated["Custom_QDialog_label_title"]["text_complete"], f"{self.current_file} {translated['Custom_QDialog_label_title']['text_delete_complete']}")
                                    # 파일 목록 새로 고침
                    self.is_opened_byuser = False
                    self.tbWordList.setRowCount(0)
                    self.refresh_file_list()

                                    # 현재 파일 정보 초기화
                    self.current_file = None
                except Exception as e:
                    self.show_custom_message(translated["Custom_QDialog_label_title"]["text_error"], f"{translated['Custom_QDialog_label_content']['delete_current_file_delete_error']} {e}")
            else:
                self.show_custom_message(translated["Custom_QDialog_label_title"]["text_cancel"], translated["Custom_QDialog_label_content"]["delete_current_file_delete_cancel"])
        else:
            self.show_custom_message(translated["Custom_QDialog_label_title"]["text_error"], translated["Custom_QDialog_label_content"]["delete_current_file_no_file"])

        self.refresh_file_list_bybutton()
        
    def refresh_file_list_bybutton(self):
        self.is_opened_byuser = True
        self.refresh_file_list()

    def refresh_file_list(self):
        """📂 CSV 파일 목록을 정렬하여 콤보박스에 추가"""
        
        if not self.current_folder:
            return
        
        # ✅ 블록 시그널 작동
        self.cbbWordFile.blockSignals(True)
        self.current_file = self.selected_file
        self.load_recent_files()
        
        # ✅ 폴더 내 CSV 파일 가져오기
        csv_files = [f for f in os.listdir(self.current_folder) if f.endswith(".csv")]
        csv_folders = []
        for root, dirs, files in os.walk(self.current_folder):  # 🔥 하위 폴더까지 탐색
            if any(f.endswith(".csv") for f in files):  # ✅ 해당 폴더에 CSV 파일이 있으면 추가
                csv_folders.append(root)
        #print(f"refresh_file_list current_folder: {self.current_folder}")
        #print(f"refresh_file_list csv_folders: {csv_folders}")
        
        self.cbbWordFile.clear()
        
        """📌 recent_list.json 파일의 상태에 따라 cbbWordFile 업데이트"""
        self.cbbWordFile.addItem(LANGUAGES[self.current_language]["cbbWordFile_list"]["go_to_top"], userData="go_to_top")  # ✅ 또 다른 구분선 추가 가능
        self.cbbWordFile.addItem(LANGUAGES[self.current_language]["cbbWordFile_list"]["current_folder"], userData="current_folder")  # ✅ 또 다른 구분선 추가 가능
        if csv_folders:  # ✅ 폴더가 있을 경우
            folder_paths = [os.path.relpath(os.path.join(self.current_folder, f), start=os.getcwd()) for f in csv_folders]
            self.cbbWordFile.addItems(folder_paths)
        else:
            self.cbbWordFile.addItem(LANGUAGES[self.current_language]["cbbWordFile_list"]["no_sub_folder"], userData="no_sub_folder")
            
        self.cbbWordFile.addItem(LANGUAGES[self.current_language]["cbbWordFile_list"]["files_in_current_folder"], userData="files_in_current_folder")  # ✅ 또 다른 구분선 추가 가능
        if csv_files:  # ✅ CSV 파일이 없을 경우
            self.display_success_message()
            file_paths = [os.path.relpath(os.path.join(self.current_folder, f), start=os.getcwd()) for f in csv_files]
            self.cbbWordFile.addItems(file_paths)
        else:
            self.display_no_file_message()
            self.cbbWordFile.addItem(LANGUAGES[self.current_language]["cbbWordFile_list"]["no_file_click_edit"], userData="no_file_click_edit")
            index = self.cbbWordFile.findData("no_file_click_edit")
            self.cbbWordFile.setCurrentIndex(index)
            
        if self.is_opened_byuser:
        
            # ✅ 파일 경로 목록 생성
            file_paths = [os.path.join(self.current_folder, f) for f in csv_files]
            #print(f"csv파일 유무: {file_paths}")

            if not file_paths:  # ✅ CSV 파일이 없을 경우 `min()` 실행 방지
                print("🚨 CSV 파일이 없음 → min() 실행 방지")
                self.cbbWordFile.addItem(LANGUAGES[self.current_language]["cbbWordFile_list"]["recent_file"], userData="recent_file")  # ✅ 구분선 추가
                if not self.recent_file_list or self.recent_file_list == [LANGUAGES[self.current_language]["cbbWordFile_list"]["no_recent_file"]]:            
                    self.cbbWordFile.addItem(LANGUAGES[self.current_language]["cbbWordFile_list"]["no_recent_file"], userData="no_recent_file")
                    
                for i in range(self.cbbWordFile.count()):
                    key = self.cbbWordFile.itemData(i)
                    translated = LANGUAGES[self.current_language]["cbbWordFile_list"].get(key, None)
                    if translated:
                        self.cbbWordFile.setItemText(i, translated)

                            #print("json 없거나 json 안에 아무것도 없음")
                else:
                    self.cbbWordFile.addItems(self.recent_file_list)

                return  

            # ✅ 각 파일의 수정된 날짜 및 생성된 날짜 가져오기
            file_mod_times = {f: os.path.getmtime(f) for f in file_paths}  # 수정된 날짜
            file_create_times = {f: os.path.getctime(f) for f in file_paths}  # 생성된 날짜

            # ✅ 오늘 날짜 확인
            today = datetime.today().date()  # 🔥 `.date()` 추가 (시간까지 비교 안 하도록)
            modified_dates = {f: datetime.fromtimestamp(file_mod_times[f]).date() for f in file_paths}

            # ✅ 수정된 날짜가 가장 오래된 파일 찾기
            oldest_modified_file = min(file_paths, key=lambda f: file_mod_times[f])

            # ✅ 모든 파일이 오늘 수정된 경우
            if all(modified_dates[f] == today for f in file_paths):
                #print("📌 모든 파일이 오늘 수정됨 → 생성 날짜 기준으로 선택")
                oldest_file = min(file_paths, key=lambda f: file_create_times[f])  # 생성된 날짜 기준 선택
            else:
                #print("📌 수정된 날짜 기준으로 파일 선택")
                oldest_file = oldest_modified_file  # 수정 날짜가 가장 오래된 파일 선택

            # ✅ 선택한 파일을 콤보박스에서 강조 & 자동 로드
            self.cbbWordFile.setCurrentText(os.path.basename(oldest_file))
            self.load_csv(oldest_file)  # ✅ `load_csv()` 호출
            self.selected_file = self.get_relative_path(oldest_file)
            self.load_recent_files()
            #print(f"refresh_file_list selected_file: {self.selected_file}")
    
        self.cbbWordFile.addItem("★★★★최근 연 파일★★★★", userData="recent_file")  # ✅ 구분선 추가
        if not self.recent_file_list or self.recent_file_list == [LANGUAGES[self.current_language]["cbbWordFile_list"]["no_recent_file"]]:            
            self.cbbWordFile.addItem(LANGUAGES[self.current_language]["cbbWordFile_list"]["no_recent_file"], userData="no_recent_file")
            #print("json 없거나 json 안에 아무것도 없음")
        else:
            self.cbbWordFile.addItems(self.recent_file_list)
                
        #print(f"✅ 최근 파일 목록 추가됨: {self.recent_file_list}")

        self.cbbWordFile.setCurrentText(self.selected_file)
        for i in range(self.cbbWordFile.count()):
            key = self.cbbWordFile.itemData(i)
            translated = LANGUAGES[self.current_language]["cbbWordFile_list"].get(key, None)
            if translated:
                self.cbbWordFile.setItemText(i, translated)
        
        csv_files = []

        # 하위 폴더 포함 .csv 파일 전체 탐색
        for folder, _, files in os.walk(self.its_placement):
            for filename in files:
                if filename.endswith('.csv'):
                    full_path = os.path.join(folder, filename)
                    try:
                        modified_time = os.path.getmtime(full_path)
                        csv_files.append((modified_time, full_path))
                    except Exception as e:
                        print(f"[경고] 파일 접근 실패: {full_path} - {e}")

        # 수정 시각이 오래된 순으로 정렬
        csv_files.sort(key=lambda x: x[0])

        # 📥 리스트박스에 추가
        self.cbbWordFile.addItem(LANGUAGES[self.current_language]["cbbWordFile_list"]["oldest_tested"], userData="oldest_tested")
        
        if not csv_files:
            # 📭 파일이 하나도 없을 때
            self.cbbWordFile.addItem(LANGUAGES[self.current_language]["cbbWordFile_list"]["no_oldest_tested"], userData="no_oldest_tested")
        else:
            # 🔟 상위 10개만 선택
            oldest_files = csv_files[:10]
            if not oldest_files:
                self.cbbWordFile.addItem(LANGUAGES[self.current_language]["cbbWordFile_list"]["no_oldest_tested"], userData="no_oldest_tested")
            else:
                for _, path in oldest_files:
                    display_path = os.path.relpath(path, self.its_placement)
                    self.cbbWordFile.addItem(display_path)

        if self.is_initializing:
            self.load_csv(self.current_file)
            self.is_initializing = False
        self.apply_theme_to_cbbWordFile()
        self.is_opened_byuser = False
        self.cbbWordFile.blockSignals(False)
                
    def get_relative_path(self, absolute_path):
        """📌 절대경로를 프로그램 실행 위치(self.its_placement)에서의 상대경로로 변환"""
        return os.path.relpath(absolute_path, start=self.its_placement)

    def load_recent_files(self):
        """📌 recent_list.json이 존재하면 불러오고, 없으면 기본 메시지 추가"""
        translated = LANGUAGES[self.current_language]["cbbWordFile_list"]["no_recent_file"]
        if os.path.exists(self.recent_list_path):  # ✅ 파일 존재 여부 확인
            try:
                with open(self.recent_list_path, "r", encoding="utf-8") as f:
                    self.recent_file_list = json.load(f)  # ✅ 파일 로드
            except json.JSONDecodeError:
                #print("🚨 recent_list.json 파일이 손상되었습니다. 초기화합니다.")
                self.recent_file_list = [f"{translated}"]
            except Exception as e:
                #print(f"🚨 최근 파일 목록을 불러오는 중 오류 발생: {e}")
                self.recent_file_list = [f"{translated}"]
            else:
                if not self.recent_file_list:  # ✅ 파일이 비어 있으면 기본 메시지 추가
                    self.recent_file_list = [f"{translated}"]

        #print(f"📌 불러온 최근 파일 목록: {self.recent_file_list}")
        
    def is_internal_ui_text(self, text):
        # 모든 언어의 표시 텍스트 → 코드로 역변환
        for lang in LANGUAGES.values():
            for code, ui_text in lang.get("cbbWordFile_list", {}).items():
                if text == ui_text:
                    return True
        return False

    def save_recent_files(self, file_path):
        """📌 새로운 파일 경로를 recent_list.json에 추가하고, 최근 10개까지만 유지"""
        if not isinstance(file_path, str):
            print("🚫 최근 파일 저장 실패: 문자열 아님 →", file_path)
            return
        
        if os.path.isdir(file_path):
            print("🚫 폴더는 최근 파일로 저장하지 않음:", file_path)
            return

        if self.is_internal_ui_text(file_path):
            print("🚫 UI 텍스트이므로 최근 파일에서 제외 →", file_path)
            return
    
        # ✅ recent_file_list에서 유효하지 않은 파일 제거 (remove() 사용)
        self.recent_file_list = [
            f for f in self.recent_file_list
            if f.strip() not in {".", "", "./"} and os.path.isfile(f)
        ]
        self.recent_file_list = [
            f for f in self.recent_file_list
            if isinstance(f, str) and (os.path.exists(f) or "/" in f or "\\" in f) and not self.is_internal_ui_text(f)
        ]

        #print(f"✅ 저장 전 파일 목록: {self.recent_file_list}")  # ✅ 저장된 목록 출력
        
        # ✅ 파일이 이미 목록에 있으면 제거 후 맨 앞에 추가 (중복 방지)
        if file_path in self.recent_file_list:
            self.recent_file_list.remove(file_path)
            

        self.recent_file_list.insert(0, file_path)  # ✅ 최신 파일을 맨 앞에 추가

        # ✅ 최대 10개까지만 저장 (FIFO 방식)
        if len(self.recent_file_list) > 10:
            self.recent_file_list.pop()  # ✅ 가장 오래된 파일 제거

        # ✅ JSON 파일에 저장
        try:
            with open(self.recent_list_path, "w", encoding="utf-8") as f:
                json.dump(self.recent_file_list, f, indent=4, ensure_ascii=False)
            #print(f"✅ 최근 파일 목록이 저장되었습니다: {self.recent_file_list}")  # ✅ 저장된 목록 출력
        except Exception as e:
            print(f"🚨 최근 파일 목록 저장 중 오류 발생: {e}")
            
    def delete_recent_files(self, file_path):
        """📌 사용자가 유효하지 않은 파일 경로 클릭 시 최근 목록에서 삭제"""
        # ✅ recent_file_list에서 유효하지 않은 파일 제거 (remove() 사용)
        self.recent_file_list = [f for f in self.recent_file_list if f not in file_path]
        try:
            with open(self.recent_list_path, "w", encoding="utf-8") as f:
                json.dump(self.recent_file_list, f, indent=4, ensure_ascii=False)
            #print(f"✅ 최근 파일 목록이 저장되었습니다: {self.recent_file_list}")  # ✅ 저장된 목록 출력
        except Exception as e:
            print(f"🚨 최근 파일 목록 저장 중 오류 발생: {e}")

    def file_merging(self):
        translated = LANGUAGES[self.current_language]["file_merging"]
        msg_box = ThemedDialog(translated["title"], self, self.current_theme)
        msg_box.selected_result = None  # ✅ 커스텀 속성으로 누른 버튼 추적

        # 버튼 생성 및 연결
        def make_action_button(text, callback):
            btn = QPushButton(text)
            btn.clicked.connect(callback)
            self.apply_theme_toButtons(self.current_theme, btn)
            self.apply_hover_events(btn, self.animated_hover_start, self.animated_hover_end)
            return btn

        def on_file_open():
            file_paths, _ = QFileDialog.getOpenFileNames(
                msg_box,
                translated["dialog_open_title"],
                "",
                "CSV Files (*.csv);;All Files (*)"
            )
            for path in file_paths:
                if path and not any(path == files_list_box.item(i).text() for i in range(files_list_box.count())):
                    files_list_box.addItem(path)

        def on_file_remove():
            for item in files_list_box.selectedItems():
                files_list_box.takeItem(files_list_box.row(item))

        def on_file_merge():
            if files_list_box.count() == 0:
                self.show_custom_message(translated["error"], translated["no_file_to_merge"])
                return

            save_path, _ = QFileDialog.getSaveFileName(
                msg_box,
                translated["dialog_save_title"],
                "merged.csv",
                "CSV Files (*.csv);;All Files (*)"
            )

            if not save_path:
                return

            # ✅ 병합 대상에 저장 경로가 포함돼 있다면 경고 후 중단
            selected_paths = [files_list_box.item(i).text() for i in range(files_list_box.count())]

            if os.path.abspath(save_path) in map(os.path.abspath, selected_paths):
                QApplication.beep()
                YorN_box = ThemedDialog(title=translated["warning"], parent=self, theme=self.current_theme)
                label = QLabel(translated["overwrite_warning"], YorN_box)
                YorN_box.content_layout.setContentsMargins(15,5,15,5)
                YorN_box.content_layout.addWidget(label)
                    
                yes_button = ThemedButton(translated["yes"], self, self.current_theme)
                yes_button.setProperty("result", 1)
                yes_button.clicked.connect(lambda: YorN_box.done(yes_button.property("result")))
                no_button = ThemedButton(translated["no"], self, self.current_theme)
                no_button.setProperty("result", 2)
                no_button.clicked.connect(lambda: YorN_box.done(no_button.property("result")))
                self.apply_hover_events(yes_button, self.animated_hover_start, self.animated_hover_end)
                self.apply_hover_events(no_button, self.animated_hover_start, self.animated_hover_end)
                YorN_box.button_layout.setContentsMargins(15,5,15,5)
                YorN_box.button_layout.addWidget(yes_button)
                YorN_box.button_layout.addWidget(no_button)
                    
                result = YorN_box.exec_()

                if result == 1:
                    try:
                        merge_files(save_path, files_list_box)  # ✅ 병합 실행
                        self.show_custom_message(translated["completed"], translated["merging_completed"])
                    except Exception as e:
                        self.show_custom_message(translated["error"], f"{translated['merging_error']}\n{e}")
                else:
                    return
            else:
                try:
                    merge_files(save_path, files_list_box)  # ✅ 병합 실행
                    self.show_custom_message(translated["completed"], translated["merging_completed"])
                except Exception as e:
                    self.show_custom_message(translated["error"], f"{translated['merging_error']}\n{e}")

        def merge_files(save_path, files_list_box):
            file_contents = []
            for i in range(files_list_box.count()):
                path = files_list_box.item(i).text()
                with open(path, "r", encoding="utf-8") as infile:
                    content = infile.read().rstrip()
                    file_contents.append(content)

            with open(save_path, "w", encoding="utf-8") as outfile:
                for content in file_contents:
                    outfile.write(content + "\n")

        def on_close():
            msg_box.reject()  # 또는 accept()

        files_list_box = QListWidget(msg_box)
        msg_box.content_layout.setContentsMargins(15, 5, 15, 5)
        msg_box.content_layout.addWidget(files_list_box)

        msg_box.button_layout.addWidget(make_action_button(translated["btn_file_open"], on_file_open))
        msg_box.button_layout.addWidget(make_action_button(translated["btn_except_file"], on_file_remove))
        msg_box.button_layout.addWidget(make_action_button(translated["btn_files_to_merge"], on_file_merge))
        msg_box.button_layout.addWidget(make_action_button(translated["btn_exit"], on_close))

        msg_box.exec_()

    def file_to_divide(self):
        translated = LANGUAGES[self.current_language]["file_divide"]
        selected_rows = set(index.row() for index in self.tbWordList.selectedIndexes())
        if not selected_rows:
            self.show_custom_message(translated["file_not_selected_title"], translated["file_not_selected"])
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, translated["file_saving"], "selected_words.csv", "CSV Files (*.csv);;All Files (*)"
        )
        if not file_path:
            return

        with open(file_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter="|")
            for row in sorted(selected_rows):
                row_data = [
                    self.tbWordList.item(row, col).text() if self.tbWordList.item(row, col) else ""
                    for col in range(self.tbWordList.columnCount())
                ]
                writer.writerow(row_data)

        self.show_custom_message(translated["file_saved_title"], translated["file_saved"])
        self.refresh_file_list_bybutton()

    def show_custom_message(self, title, message):
        translated = LANGUAGES[self.current_language]["Custom_QDialog_buttons"]
        QApplication.beep()
        dialog = ThemedDialog(title, self, self.current_theme)

        label = QLabel(message)
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        dialog.content_layout.setContentsMargins(15, 5, 15, 5)
        dialog.content_layout.addWidget(label)

        btn_ok = QPushButton(translated["text_ok"])
        btn_ok.clicked.connect(dialog.accept)
        self.apply_theme_toButtons(self.current_theme, btn_ok)
        self.apply_hover_events(btn_ok, self.animated_hover_start, self.animated_hover_end)

        dialog.button_layout.addWidget(btn_ok)

        dialog.exec_()

    #-------------------------------------------------------파일 처리 관련 함수 끝 ------------------------------------------------#

    def disable_buttons(self):
        self.btnPractice.setEnabled(False)
        self.btnEdit.setEnabled(False)
        self.btnTextTestWtoM.setEnabled(False)
        self.btnTextTestMtoW.setEnabled(False)
        self.btnAudioTestWtoM.setEnabled(False)
        self.btnAudioTestMtoW.setEnabled(False)
        self.btnAudioTestDictation.setEnabled(False)
        self.btnAutoInputNumbers.setEnabled(False)
        self.cbbWordFile.setEnabled(False)
        self.btnRefreshWordList.setEnabled(False)
        self.btnDeleteWordFile.setEnabled(False)
        self.btnDeleteScores.setEnabled(False)
        self.btnDeleteAudios.setEnabled(False)
        self.btnDeleteNowAudio.setEnabled(False)
        self.btnRecord.setEnabled(False)
        self.btnMakeAudios.setEnabled(False)
        self.btnAutoPlay.setEnabled(False)
        self.btnPrintWords.setEnabled(False)
        self.tbWordList.setEnabled(False)
        self.btnAlignCellsWidth.setEnabled(False)
        self.btnWordFileOpen.setEnabled(False)
        self.btn_browser.setEnabled(False)
        self.cbbTestType.setEnabled(False)
        self.cbbRateFilter.setEnabled(False)
        self.cbbBaseLang.setEnabled(False)
        self.cbbLangToLearn.setEnabled(False)
        self.btnOpenThisWordsMP3.setEnabled(False)
        self.cbbPlayType.setEnabled(False)
        self.btnMergeFiles.setEnabled(False)
        self.btnDivideFile.setEnabled(False)
        self.theme_hover_refresher()

    def enable_buttons(self):
        self.btnPractice.setEnabled(True)
        self.btnEdit.setEnabled(True)
        self.btnTextTestWtoM.setEnabled(True)
        self.btnTextTestMtoW.setEnabled(True)
        self.btnAudioTestWtoM.setEnabled(True)
        self.btnAudioTestMtoW.setEnabled(True)
        self.btnAudioTestDictation.setEnabled(True)
        self.btnAutoInputNumbers.setEnabled(True)
        self.cbbWordFile.setEnabled(True)
        self.btnRefreshWordList.setEnabled(True)
        self.btnDeleteWordFile.setEnabled(True)
        self.btnDeleteScores.setEnabled(True)
        self.btnDeleteAudios.setEnabled(True)
        self.btnDeleteNowAudio.setEnabled(True)
        self.btnRecord.setEnabled(True)
        self.btnMakeAudios.setEnabled(True)
        self.btnAutoPlay.setEnabled(True)
        self.btnPrintWords.setEnabled(True)
        self.tbWordList.setEnabled(True)
        self.txtWordInput.setVisible(True)
        self.txtMeaningInput.setVisible(True)
        self.btnAlignCellsWidth.setEnabled(True)
        self.btnWordFileOpen.setEnabled(True)
        self.btn_browser.setEnabled(True)
        self.cbbTestType.setEnabled(True)
        self.cbbRateFilter.setEnabled(True)
        self.cbbBaseLang.setEnabled(True)
        self.cbbLangToLearn.setEnabled(True)
        self.cbbPlayType.setEnabled(True)
        self.btnMergeFiles.setEnabled(True)
        self.btnDivideFile.setEnabled(True)
        self.btnOpenThisWordsMP3.setEnabled(True)
        self.theme_hover_refresher()

    #--------------------------------------------------편집모드 관련 함수들----------------------------------------------------------------#

    def exit_edit_mode(self):
        self.disconnect_events()
        translated_text = LANGUAGES.get(self.current_language, LANGUAGES["한국어"])
        self.txtWordInput.status = "edited"
        self.txtMeaningInput.status = "edited"

        # 모든 열 표시
        for col in range(3, self.tbWordList.columnCount()):
            self.tbWordList.setColumnHidden(col, False)

        # 편집 버튼을 다시 "편집"으로 변경
        self.btnEdit.status = "saved"    
        self.btnEdit.setText(translated_text["btnEdit"])
        self.btnEdit.setToolTip(translated_text["btnEdit_t"])

        # 다른 버튼 활성화
        self.enable_buttons()
        
        # 표를 다시 편집 불가능하게 설정
        self.set_table_editable(False)

        # 편집 모드 비활성화
        self.is_editing = False
        
    def enter_edit_mode(self):
        self.disconnect_events()
        translated_text = LANGUAGES.get(self.current_language, LANGUAGES["한국어"])
        self.txtWordInput.status = "is editing"
        self.txtMeaningInput.status = "is editing"
        self.txtWordInput.setPlainText(translated_text["is_editing1"])
        self.txtMeaningInput.setPlainText(translated_text["is_editing2"])
        
        # 0, 1, 2열을 제외한 나머지 숨기기
        for col in range(3, self.tbWordList.columnCount()):
            self.tbWordList.setColumnHidden(col, True)

        # 편집 버튼을 "저장"으로 변경
        self.btnEdit.status = "editing"    
        self.btnEdit.setText(translated_text["btnEdit2"])
        self.btnEdit.setToolTip(translated_text["btnEdit2_t"])

        # 다른 버튼 비활성화
        self.disable_buttons()
        self.btnEdit.setEnabled(True)
        self.tbWordList.setEnabled(True)
        self.btnAutoInputNumbers.setEnabled(True)

        # 표를 편집 가능하게 설정
        self.set_table_editable(True)

        # 편집 모드 활성화
        self.is_editing = True
        
        # 테이블에 포커스를 줌
        self.tbWordList.setFocus()  
        
        # 첫 번째 셀을 선택 상태로 만듦
        try:
            if self.tbWordList.item(0, 0):  # 첫 번째 셀이 존재하는지 확인
                self.tbWordList.setCurrentCell(0, 0)  # 첫 번째 셀에 포커스를 줌
                self.tbWordList.item(0, 0).setSelected(True)  # 첫 번째 셀을 선택 상태로 만듦
        except AttributeError:
            # 셀이 None이면 발생하는 에러를 건너뛰고 코드가 계속 실행되도록 함
            pass

        # 필요한 경우 다시 연결
        #self.connect_events()
            
    def save_changes(self):
        # 비어있는 행이 있는지 확인
        translated_text = LANGUAGES.get(self.current_language, LANGUAGES["한국어"])
        if self.has_empty_rows():
            self.show_custom_message(translated_text["Custom_QDialog_label_title"]["text_warning"], translated_text["Custom_QDialog_label_content"]["save_changes_label"])
            return

        # 편집 모드 종료 처리
        self.exit_edit_mode()

    def has_empty_rows(self):
        self.disconnect_events()
        for row in range(self.tbWordList.rowCount()):
            if not self.tbWordList.item(row, 0) or not self.tbWordList.item(row, 1) or not self.tbWordList.item(row, 2):
                return True
        self.connect_events()
        return False
    
    def set_text_widget_editable(self, editable):
        """텍스트 위젯의 수정 가능 여부 설정"""
        if editable:
            # 편집 가능 상태: 입력 및 선택 가능
            self.txtMeaningInput.setReadOnly(False)
        else:
            self.txtMeaningInput.setReadOnly(True)  # 편집 불가능

    def set_table_editable(self, editable):
        """표의 모든 셀의 수정 가능 여부를 설정하는 함수"""
        self.disconnect_events()
        if editable:
            self.tbWordList.setEditTriggers(QtWidgets.QAbstractItemView.AllEditTriggers)
        else:
            self.tbWordList.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

        for row in range(self.tbWordList.rowCount()):
            for column in range(self.tbWordList.columnCount()):
                item = self.tbWordList.item(row, column)
                if item is None:
                    item = QTableWidgetItem("")
                    self.tbWordList.setItem(row, column, item)
                if editable:
                    item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable)
                else:
                    item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        self.connect_events()
        self.tbWordList.viewport().update()

    def on_combobox_changed(self):
        """📌 콤보박스에서 선택된 파일을 올바른 경로로 로드 (상대경로 유지)"""
        data = self.cbbWordFile.currentData()
        translated = LANGUAGES[self.current_language]
        if data is not None:
            self.selected_file = data
        else:
            self.selected_file = self.cbbWordFile.currentText()  # 또는 적절한 기본값
            #print(f"on_combobox_changed: {self.selected_file}")
        
        invalid_files = {
            None,
            "no_sub_folder",
            "no_file_click_edit",
            "no_recent_file",
            "go_to_top",
            "current_folder",
            "files_in_current_folder",
            "recent_file",
            "oldest_tested",
            "no_oldest_tested",
        }
        if self.selected_file == "go_to_top":
            self.current_folder = self.its_placement
            self.tbWordList.setRowCount(0)
            self.is_opened_byuser = False
            self.refresh_file_list()
            self.update_last_test_label(self.current_file)
        elif self.selected_file in invalid_files:
            self.selected_file = ""
            return
        elif self.selected_file.endswith(".csv"): # ✅ 선택된 파일이 상대경로인지 확인 후 절대경로로 변환
            file_path = os.path.abspath(os.path.join(self.selected_file))
            
            if not os.path.exists(file_path):  # 🚨 파일이 존재하지 않으면 경고
                            #print(f"🚨 파일이 존재하지 않음: {file_path}")
                self.show_custom_message(translated["Custom_QDialog_label_title"]["text_error"], f"{translated['Custom_QDialog_label_content']['on_combobox_changed_error']} {file_path}")

                self.delete_recent_files(file_path)
                temp = self.current_file
                self.refresh_file_list()
                self.cbbWordFile.setCurrentText(temp)  # 🔥 사용자가 선택한 파일을 목록에서 강조
                return

            #print(f"✅ 콤보박스 선택: {self.selected_file} (경로: {file_path})")  # 디버깅 출력

            # 📌 테이블 업데이트
              # 신호 차단 (불필요한 이벤트 방지)
            self.load_csv(file_path)  # ✅ 올바른 파일 경로 전달
              # 신호 다시 연결
            self.tbWordList.viewport().update()  # 테이블의 뷰를 강제로 새로고침
            self.align_cells_width()
            self.is_opened_byuser = False
            self.refresh_file_list()
            self.connect_events()
        else: #선택된 것이 폴더라면
            self.current_folder = os.path.join(self.its_placement, self.selected_file) 
            #print(f"on_combobox_changed: current_folder: {self.current_folder}")
            self.refresh_file_list_bybutton()
        
    def load_settings(self):
        """설정 파일 읽기 함수"""
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding='utf-8') as f:
                    settings = json.load(f)
                    # 콤보박스 설정 불러오기 (있으면 불러오고, 없으면 기본값으로 설정)
                    return settings
            except (json.JSONDecodeError, ValueError):
                #print("설정 파일이 손상되었거나 잘못된 형식입니다. 기본 설정을 사용합니다.")
                return {}  # JSON 형식이 잘못되었을 경우 기본값을 반환
        return {}  # 설정 파일이 없을 경우 기본값 반환

    def save_settings(self, settings):
        # 설정 파일 저장
        current_settings = self.load_settings()

        # 콤보박스의 현재 값을 설정에 추가
        current_settings.update(settings)

        with open(SETTINGS_FILE, "w", encoding='utf-8') as f:
            json.dump(current_settings, f, ensure_ascii=False, indent=4)
        
    def populate_language_comboboxes(self):
        languages = tts_langs()
        self.cbbLangToLearn.clear()
        self.cbbBaseLang.clear()

        for lang_code, lang_name in languages.items():
            self.cbbLangToLearn.addItem(lang_name, lang_code)
            self.cbbBaseLang.addItem(lang_name, lang_code)

    def load_language_settings(self, settings):
        # 설정 파일에서 언어 설정 로드
        learn_language = settings.get("learn_language", DEFAULT_LEARN_LANGUAGE)
        base_language = settings.get("base_language", DEFAULT_BASE_LANGUAGE)

        learn_index = self.cbbLangToLearn.findData(learn_language)
        base_index = self.cbbBaseLang.findData(base_language)

        if learn_index != -1:
            self.cbbLangToLearn.setCurrentIndex(learn_index)
        else:
            self.cbbLangToLearn.setCurrentIndex(self.cbbLangToLearn.findData(DEFAULT_LEARN_LANGUAGE))

        if base_index != -1:
            self.cbbBaseLang.setCurrentIndex(base_index)
        else:
            self.cbbBaseLang.setCurrentIndex(self.cbbBaseLang.findData(DEFAULT_BASE_LANGUAGE))

    #--------------------------------------------------편집모드 관련 함수들----------------------------------------------------------------#

    @pyqtSlot(int, int)
    def on_cell_edit_finished(self, row, column):
        self.apply_font()
        self.apply_font_totarget()
        if self.is_loading:
            return

        if self.is_editing:
            return
        
        # 셀 편집이 완료되었을 때 호출되는 슬롯
        item = self.tbWordList.item(row, column)
        if item and item.text().strip():  # 빈 문자열이 아닌 경우에만 처리
            text = item.text()
            if column == 2:  # 뜻 열 편집 완료
                language = self.cbbBaseLang.currentData()
            else:  # 단어 열 또는 다른 셀 편집 완료
                language = self.cbbLangToLearn.currentData()
            self.play_text_as_audio(text, language)
            
    def txtmeaninginput_style_reset(self, theme_name):
        """🎨 테마 변경 시 txtMeaningInput 내부 텍스트 색상 전체를 현재 테마 색으로 일괄 적용"""
        theme = THEME_COLORS.get(theme_name, THEME_COLORS["basic"])
        new_text_color = QtGui.QColor(theme['textedit_text'])

        doc = self.txtMeaningInput.document()
        cursor = QtGui.QTextCursor(doc)
        cursor.beginEditBlock()

        block = doc.begin()
        block_end = doc.end()

        while block != block_end:
            it = block.begin()
            while not it.atEnd():
                fragment = it.fragment()
                if fragment.isValid():
                    # ✅ fragment 범위에 대응하는 커서 만들기
                    frag_cursor = QtGui.QTextCursor(doc)
                    frag_cursor.setPosition(fragment.position())
                    frag_cursor.setPosition(fragment.position() + fragment.length(), QtGui.QTextCursor.KeepAnchor)

                    fmt = fragment.charFormat()
                    fmt.setForeground(new_text_color)
                    frag_cursor.setCharFormat(fmt)
                it += 1
            block = block.next()

        cursor.endEditBlock()
    
    @pyqtSlot()
    def on_cell_selection_changed(self):
        if self.is_loading:
            return

        if self.is_editing:
            return
        #print("on_cell_selection_changed 호출됨")
        #print(self.practice_mode)
        selected_items = self.tbWordList.selectedItems()

        if selected_items:
            # 📌 글씨체 적용
            base_font_name = self.cbbFontSetting.currentData()
            learn_font_name = self.cbbFontSetting_tolearn.currentData()

            selected_item = selected_items[0]
            row = selected_item.row()
            column = selected_item.column()
            if column == 2:  # 뜻 열 선택
                word_item = self.tbWordList.item(row, 1)  # 단어 열(1번 열)을 참조
                meaning_item = self.tbWordList.item(row, 2)  # 뜻 열(2번 열)을 참조

                if word_item and meaning_item:
                    word = word_item.text()
                    meaning = meaning_item.text()

                    self.txtWordInput.setPlainText(meaning)  # 뜻을 Word 텍스트 위젯에 표시
                    self.txtMeaningInput.setPlainText(word)  # 단어를 Meaning 텍스트 위젯에 표시

                    if base_font_name:
                        font = QFont(base_font_name)
                        font.setPointSize(self.word_font_size)  # 현재 설정된 크기 유지
                        self.txtWordInput.setFont(font)

                    if learn_font_name:
                        font = QFont(learn_font_name)
                        font.setPointSize(self.meaning_font_size)
                        self.txtMeaningInput.setFont(font)

                    language = self.cbbBaseLang.currentData()
                    self.play_text_as_audio(meaning, language)
                    self.txtmeaninginput_style_reset(self.current_theme)

            elif column == 3:  # 오답비교 열 선택
                self.processorforColumn3(self.tbWordList, row)            
            else:  # 나머지 셀 선택
                word_item = self.tbWordList.item(row, 1)  # 단어 열(1번 열)을 참조
                meaning_item = self.tbWordList.item(row, 2)  # 뜻 열(2번 열)을 참조

                if word_item and meaning_item:
                    word = word_item.text()
                    meaning = meaning_item.text()

                    self.txtWordInput.setPlainText(word)  # 단어를 Word 텍스트 위젯에 표시
                    self.txtMeaningInput.setPlainText(meaning)  # 뜻을 Meaning 텍스트 위젯에 표시

                    if base_font_name:
                        font = QFont(base_font_name)
                        font.setPointSize(self.word_font_size)  # 현재 설정된 크기 유지
                        self.txtMeaningInput.setFont(font)

                    if learn_font_name:
                        font = QFont(learn_font_name)
                        font.setPointSize(self.meaning_font_size)
                        self.txtWordInput.setFont(font)

                    language = self.cbbLangToLearn.currentData()
                    self.play_text_as_audio(word, language)
                    self.txtmeaninginput_style_reset(self.current_theme)
                    
    #-------------------------기타 기능--------------------------------#
    def processorforColumn3(self, obj, row):
        obj.blockSignals(True)
        self.disconnect_events()
        base_font_name = self.cbbFontSetting.currentData() #기본폰트
        learn_font_name = self.cbbFontSetting_tolearn.currentData() #배울언어 폰트
        word_item = self.tbWordList.item(row, 1) #단어
        meaning_item = self.tbWordList.item(row, 2) #뜻
        error_item = self.tbWordList.item(row, 3) #오답 
        word = word_item.text() #단어 텍스트화
        meaning = meaning_item.text() 
        error = error_item.text()
        caller = inspect.stack()[1].function

        if error_item and error_item.text().strip(): # 3번 컬럼에 텍스트(오답)이 있다면
            if self.practice_mode == 0: #방금 본 시험이 단어>뜻 시험이었다면 (텍스트)

                self.condition_cell_click_when_column3(meaning, error, base_font_name, base_font_name)
                language = self.cbbLangToLearn.currentData()
                self.highlight_differences(meaning, error)
                # 이벤트 처리 순서 조정
                if isinstance(obj, QtWidgets.QTableWidget):
                    if caller == "on_cell_selection_changed":
                        self.play_text_as_audio(word, language)

            elif self.practice_mode == 1: #방금 본 시험이 뜻>단어 시험이었다면 (텍스트)

                self.condition_cell_click_when_column3(word, error, learn_font_name, learn_font_name)
                language = self.cbbLangToLearn.currentData()
                self.highlight_differences(word, error)
                # 이벤트 처리 순서 조정
                if isinstance(obj, QtWidgets.QTableWidget):
                    if caller == "on_cell_selection_changed":
                        self.play_text_as_audio(word, language)

            elif self.practice_mode == 2: #방금 본 시험이 단어>뜻 시험이었다면 (오디오)

                self.condition_cell_click_when_column3(meaning, error, base_font_name, base_font_name)
                language = self.cbbLangToLearn.currentData()
                self.highlight_differences(meaning, error)
                # 이벤트 처리 순서 조정
                if isinstance(obj, QtWidgets.QTableWidget):
                    if caller == "on_cell_selection_changed":
                        self.play_text_as_audio(word, language)

            elif self.practice_mode == 3: #방금 본 시험이 뜻>단어 시험이었다면 (오디오)

                self.condition_cell_click_when_column3(word, error, learn_font_name, learn_font_name)
                language = self.cbbBaseLang.currentData()
                self.highlight_differences(word, error)
                # 이벤트 처리 순서 조정
                if isinstance(obj, QtWidgets.QTableWidget):
                    if caller == "on_cell_selection_changed":
                        self.play_text_as_audio(meaning, language)

            elif self.practice_mode == 4: #방금 본 시험이 받아쓰기 시험이었다면 (오디오)

                self.condition_cell_click_when_column3(word, error, learn_font_name, learn_font_name)
                language = self.cbbLangToLearn.currentData()
                self.highlight_differences(word, error)
                # 이벤트 처리 순서 조정
                if isinstance(obj, QtWidgets.QTableWidget):
                    self.highlight_differences(word, error)
                    if caller == "on_cell_selection_changed":
                        self.play_text_as_audio(word, language)

            elif self.practice_mode == 5: #방금 연습이 단어>뜻 시험이었다면 (텍스트)

                self.condition_cell_click_when_column3(meaning, error, base_font_name, base_font_name)
                language = self.cbbLangToLearn.currentData()
                self.highlight_differences(meaning, error)
                # 이벤트 처리 순서 조정
                if isinstance(obj, QtWidgets.QTableWidget):
                    if caller == "on_cell_selection_changed":
                        self.play_text_as_audio(word, language)

            elif self.practice_mode == 6: #방금 연습이 뜻>단어 시험이었다면 (텍스트)

                self.condition_cell_click_when_column3(word, error, learn_font_name, learn_font_name)
                language = self.cbbLangToLearn.currentData()
                self.highlight_differences(word, error)
                # 이벤트 처리 순서 조정
                if isinstance(obj, QtWidgets.QTableWidget):
                    if caller == "on_cell_selection_changed":
                        self.play_text_as_audio(word, language)

            else:#방금 본 시험이 받아쓰기 또는 프로그램 처음 켰을 시 None
                self.condition_cell_click_when_column3(word, error, learn_font_name, learn_font_name)
                language = self.cbbLangToLearn.currentData()
                self.highlight_differences(word, error)
                # 이벤트 처리 순서 조정
                if isinstance(obj, QtWidgets.QTableWidget):
                    if caller == "on_cell_selection_changed":
                        self.play_text_as_audio(word, language)

        else: #오답을 가져오는데 없다면 평범한 셀클릭 작동
            self.normal_cell_click_when_column3(word, meaning, row, learn_font_name, base_font_name, obj)

        obj.blockSignals(False)
        self.connect_events()

    def condition_cell_click_when_column3(self, word, meaning, base_font_name, learn_font_name):
        self.txtWordInput.setPlainText(word)
        self.txtMeaningInput.setPlainText(meaning)

        if base_font_name:
            font = QFont(base_font_name)
            font.setPointSize(self.word_font_size)  # 현재 설정된 크기 유지
            self.txtWordInput.setFont(font)

        if learn_font_name:
            font = QFont(learn_font_name)
            font.setPointSize(self.meaning_font_size)
            self.txtMeaningInput.setFont(font)

    def normal_cell_click_when_column3(self, word_item, meaning_item, row, base_font_name, learn_font_name, obj):
        word_item = self.tbWordList.item(row, 1)  # 단어 열(1번 열)을 참조
        meaning_item = self.tbWordList.item(row, 2)  # 뜻 열(2번 열)을 참조
                        
        word = word_item.text()
        meaning = meaning_item.text()

        self.txtWordInput.setPlainText(word)  # 뜻을 Word 텍스트 위젯에 표시
        self.txtMeaningInput.setPlainText(meaning)  # 단어를 Meaning 텍스트 위젯에 표시

        if base_font_name:
            font = QFont(base_font_name)
            font.setPointSize(self.word_font_size)  # 현재 설정된 크기 유지
            self.txtWordInput.setFont(font)

        if learn_font_name:
            font = QFont(learn_font_name)
            font.setPointSize(self.meaning_font_size)
            self.txtMeaningInput.setFont(font)

        language = self.cbbLangToLearn.currentData()
                
        # 이벤트 처리 순서 조정
        if isinstance(obj, QtWidgets.QTableWidget):
            self.disconnect_events()
            self.play_text_as_audio(word, language)
            self.connect_events()
        else:
            return
                    
    def update_last_test_label(self, file_name):
        """파일의 최초 생성 날짜와 마지막 수정 날짜를 가져와서 lbLastTest 라벨에 표시"""
        translated = LANGUAGES[self.current_language]
        locale_code = language_locale_map.get(self.current_language, "en")  # 기본값 영어
        if os.path.exists(file_name):
            # 📌 파일의 마지막 수정 시간 가져오기
            last_modified_timestamp = os.path.getmtime(file_name)
            last_modified_date = datetime.fromtimestamp(last_modified_timestamp).date()

            # 📌 파일의 최초 생성 시간 가져오기
            created_timestamp = os.path.getctime(file_name)  # ✅ 최초 생성 날짜 추가
            created_date = datetime.fromtimestamp(created_timestamp).date()

            # 📌 오늘 날짜와 비교하여 차이 계산
            today = datetime.now().date()
            days_passed = (today - last_modified_date).days

            # 📌 날짜 형식 변환 (YYYY년 MM월 DD일)
            created_date_str = self.format_created_date(created_date, translated)

            # 📌 라벨 업데이트
            self.lbLastTest.setText(f"{translated['Custom_QDialog_label_content']['update_last_test_label_resisted_file']} {created_date_str} {translated['Custom_QDialog_label_content']['update_last_test_label_last_test']} {days_passed}{translated['Custom_QDialog_label_content']['update_last_test_label_d_passed']}")
        else:
            self.lbLastTest.setText(translated["Custom_QDialog_label_content"]["update_last_test_label_no_file"])
            
    def format_created_date(self, date_obj, lang_texts):
        # LANGUAGES[언어]["Custom_QDialog_label_content"]가 들어온 상태
        y_label = lang_texts["Custom_QDialog_label_content"].get("update_last_test_label_y", "Y")
        m_label = lang_texts["Custom_QDialog_label_content"].get("update_last_test_label_m", "M")
        d_label = lang_texts["Custom_QDialog_label_content"].get("update_last_test_label_d", "D")

        return f"{date_obj.year}{y_label} {date_obj.month}{m_label} {date_obj.day}{d_label}"

    #-------------------------기타 기능--------------------------------#
    def eventFilter(self, obj, event):
        """
        QPlainTextEdit에서 휠 이벤트로 글씨 크기 조절 및 Enter 키 이벤트 처리.
        """
        #print(f"EventFilter: Object={obj.objectName()} (Type={type(obj).__name__}), Event={event.type()}")
        # 디버깅 출력으로 대상 확인
        # 마우스 휠 이벤트: Ctrl+휠로 글씨 크기 조절
        if event.type() == QtCore.QEvent.Wheel and event.modifiers() == QtCore.Qt.ControlModifier:
            
            self.disconnect_events()
            # 글씨 크기 조절
            if event.angleDelta().y() > 0:  # 휠 업 (위로 스크롤)
                self.increase_font_size(obj)
            else:  # 휠 다운 (아래로 스크롤)
                self.decrease_font_size(obj)

            # 초기화 (글씨 크기 유지)
            self.reset_text_format_except_font(obj)

            # 컬럼 3번의 색 변경 처리
            current_column = self.tbWordList.currentColumn()
            row = self.tbWordList.currentRow()
            if current_column == 3:
                self.processorforColumn3(obj, row)

            # 강제 업데이트 적용
            #print(f"강제 업데이트 실행: {obj.objectName()}")
            obj.viewport().update()
            self.connect_events()
            
            return True

        # 키 이벤트: Enter 키 처리
        if event.type() == QtCore.QEvent.KeyPress and obj == self.txtMeaningInput:
            if event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
                # 엔터키 입력 처리
                if self.is_practice:
                    self.check_answer()
                    self.reset_text_format_except_theme(obj)
                    event.accept()  # 이벤트 처리 후 다른 곳으로 전달되지 않도록 처리
                elif self.is_testing:
                    self.check_answer_forTest()
                    self.reset_text_format_except_theme(obj)
                else:
                    return False  # 기본 이벤트 차단
            elif event.key() == Qt.Key_Control:
                self.force_ime_refresh(obj)
            self.handle_cut_action()
            obj.viewport().update()
            
        # 다른 이벤트는 기본 처리
        #print(f"Event detected: {event.type()}, Object: {obj.objectName()}")        
        return super().eventFilter(obj, event)
    
    def increase_font_size(self, obj):
        """글씨 크기 증가"""
        #print(f"increase_font_size 호출됨 - 대상: {obj.objectName()}")
        if obj == self.txtWordInput:
            self.word_font_size = min(self.word_font_size + 2, 80)  # 최대 글씨 크기 제한
            font = self.txtWordInput.font()
            font.setPointSize(self.word_font_size)
            self.txtWordInput.setFont(font)
            self.txtWordInput.viewport().update()  # UI 즉시 업데이트
            font = QFont(self.txtWordInput.font())
            self.adjust_text_widget_height(self.txtWordInput, font)
            self.update_layout()

        elif obj == self.txtMeaningInput:
            self.meaning_font_size = min(self.meaning_font_size + 2, 80)
            font = self.txtMeaningInput.font()
            font.setPointSize(self.meaning_font_size)
            self.txtMeaningInput.setFont(font)
            self.txtMeaningInput.viewport().update()  # UI 즉시 업데이트
            font = QFont(self.txtMeaningInput.font())
            self.adjust_text_widget_height(self.txtMeaningInput, font)
            self.update_layout()

        elif obj == self.tbWordList:
            
            self.disconnect_events()

            self.table_font_size = min(self.table_font_size + 1, 40)

            font = self.tbWordList.font()
            font.setPointSize(self.table_font_size)
            self.tbWordList.setFont(font)

            header_font = QFont()
            header_font.setPointSize(self.table_font_size)  # ← 또는 원하는 크기

            style = f"QHeaderView::section {{ font-size: {self.table_font_size}pt; }}"
            self.tbWordList.setStyleSheet(style)

            for row in range(self.tbWordList.rowCount()):
                item = self.tbWordList.item(row, 1)
                if item:
                    font = item.font()
                    font.setPointSize(self.table_font_size)
                    item.setFont(font)
            self.connect_events()
            self.align_cells_width()  # 테이블 폭 재조정

    def decrease_font_size(self, obj):
        """글씨 크기 감소"""
        #print(f"decrease_font_size 호출됨 - 대상: {obj.objectName()}")
        if obj == self.txtWordInput:
            self.word_font_size = max(self.word_font_size - 2, 8)  # 최소 글씨 크기 제한
            font = self.txtWordInput.font()
            font.setPointSize(self.word_font_size)
            self.txtWordInput.setFont(font)
            self.txtWordInput.viewport().update()  # UI 즉시 업데이트
            font = QFont(self.txtWordInput.font())
            self.adjust_text_widget_height(self.txtWordInput, font)
            self.update_layout()

        elif obj == self.txtMeaningInput:
            self.meaning_font_size = max(self.meaning_font_size - 2, 8)
            font = self.txtMeaningInput.font()
            font.setPointSize(self.meaning_font_size)
            self.txtMeaningInput.setFont(font)
            self.txtMeaningInput.viewport().update()  # UI 즉시 업데이트
            font = QFont(self.txtMeaningInput.font())
            self.adjust_text_widget_height(self.txtMeaningInput, font)
            self.update_layout()

        elif obj == self.tbWordList:
            
            self.disconnect_events()

            self.table_font_size = max(self.table_font_size - 1, 8)

            font = self.tbWordList.font()
            font.setPointSize(self.table_font_size)
            self.tbWordList.setFont(font)

            header_font = QFont()
            header_font.setPointSize(self.table_font_size)

            style = f"QHeaderView::section {{ font-size: {self.table_font_size}pt; }}"
            self.tbWordList.setStyleSheet(style)

            for row in range(self.tbWordList.rowCount()):
                item = self.tbWordList.item(row, 1)
                if item:
                    font = item.font()
                    font.setPointSize(self.table_font_size)
                    item.setFont(font)
            self.connect_events()
            self.align_cells_width()  # 테이블 폭 재조정

    def adjust_text_widget_height(self, widget, font: QFont, lines: int = 1):
        metrics = QFontMetrics(font)
        line_height = metrics.lineSpacing()  # ascent + descent + leading 포함
        total_height = line_height * lines + 10  # 여유 패딩
        widget.setFixedHeight(total_height)
    
    def save_font_settings(self):
        """글씨 크기 설정을 settings.json에 저장하는 함수"""
        settings = self.load_settings()  # 기존 설정을 불러옴

        # settings.json에 저장
        with open("settings.json", "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
        
    def display_success_message(self):
        # 파일이 성공적으로 불러와졌을 때 안내 메시지 표시
        translated_text = LANGUAGES.get(self.current_language, LANGUAGES["한국어"])
        base_font_name = self.cbbFontSetting.currentData()
        self.txtWordInput.status = "file is loaded"
        self.txtMeaningInput.status = "file is loaded"
        self.txtWordInput.setPlainText(translated_text["wordfileloaded_success1"])
        self.txtMeaningInput.setPlainText(translated_text["wordfileloaded_success2"])
        if base_font_name:
            font = QFont(base_font_name)
            font.setPointSize(self.word_font_size)  # 현재 설정된 크기 유지
            self.txtWordInput.setFont(font)
            self.txtMeaningInput.setFont(font)
        self.enable_buttons()

    def display_no_file_message(self):
        # 파일이 없을 때 안내 메시지 표시
        translated_text = LANGUAGES.get(self.current_language, LANGUAGES["한국어"])
        base_font_name = self.cbbFontSetting.currentData()
        self.txtWordInput.status = "no file"
        self.txtMeaningInput.status = "no file"
        self.txtWordInput.setPlainText(translated_text["wordfileloaded_nofile1"])
        self.txtMeaningInput.setPlainText(translated_text["wordfileloaded_nofile2"])
        if base_font_name:
            font = QFont(base_font_name)
            font.setPointSize(self.word_font_size)  # 현재 설정된 크기 유지
            self.txtWordInput.setFont(font)
            self.txtMeaningInput.setFont(font)
        self.disable_buttons()
        self.btnEdit.setEnabled(True)
        self.cbbWordFile.setEnabled(True)
        self.cbbWordFile.blockSignals(False)
        self.cbbLangToLearn.setEnabled(True)
        self.cbbBaseLang.setEnabled(True)
        self.btnWordFileOpen.setEnabled(True)
        self.btnMergeFiles.setEnabled(True)
        self.btnRefreshWordList.setEnabled(True)
        self.theme_changed_byuser = True

        # 예시: 모든 위젯에 리셋 애니메이션 적용
        for widget in self.widgets_forEvent_override:
            self.animated_hover_end(widget)  # ✅ 강제로 현재 테마색으로 갱신

        self.theme_changed_byuser = False  # ✅ 리셋
        
    def closeEvent(self, event):
        """프로그램 종료 시 호출되는 함수"""
        # 프로그램 종료 전 모든 설정 저장
        settings = {
            "show_all_words": self.chbAllWords.isChecked(),
            "only_incorrects": self.chbOnlyIncorrects.isChecked(),
            "only_low_rates": self.chbOnlyLowRates.isChecked(),
            "rate_filter": self.cbbRateFilter.currentText(),
            "test_type": self.cbbTestType.currentData(),
            "play_type": self.cbbPlayType.currentData(),
            "learn_language": self.cbbLangToLearn.currentData(),
            "base_language": self.cbbBaseLang.currentData(),
            "pitch": self.cbbPitchPreset.currentData(),
            "volume": self.txtVolume.text(),
            "theme": self.cbbTheme.currentData(),
            "word_font_size": self.word_font_size,
            "meaning_font_size": self.meaning_font_size,
            "table_font_size": self.table_font_size,
            "txtWordInput_height": self.txtWordInput.height(),
            "txtMeaningInput_height": self.txtMeaningInput.height(),
            "user_language": self.cbbLanguages.currentText(),
            "font_setting": self.cbbFontSetting.currentText(),
            "font_setting_tolearn": self.cbbFontSetting_tolearn.currentText(),
            "gridLayout_padding": (
                self.layout().contentsMargins().left(),
                self.layout().contentsMargins().top(),
                self.layout().contentsMargins().right(),
                self.layout().contentsMargins().bottom()
            ),
            # 필요한 다른 설정도 추가
        }

        self.save_settings(settings)

        # 종료 이벤트를 허용하여 창이 닫히도록 설정
        event.accept()
    
    def highlight_differences(self, correct_answer, user_answer):
        """
        정답과 사용자의 입력을 비교하여 다른 부분을 빨간색으로 표시.
        사용자 입력이 짧을 경우 하이픈으로 채우고, 초과된 입력은 빨간색으로 표시.
        """
        self.txtMeaningInput.clear()
        self.txtMeaningInput.setPlainText(user_answer)

        cursor = self.txtMeaningInput.textCursor()

        # 테마에서 기본 텍스트 색상 가져오기
        palette = self.txtMeaningInput.palette()
        default_text_color = palette.color(QtGui.QPalette.Text)

        # 기본 형식과 오답 형식 정의
        format_default = QTextCharFormat()
        format_default.setForeground(default_text_color)

        format_incorrect = QTextCharFormat()
        format_incorrect.setForeground(QtGui.QColor("red"))

        cursor.beginEditBlock()

        # 사용자 입력과 정답을 비교
        for i in range(max(len(correct_answer), len(user_answer))):
            if i < len(user_answer):
                char = user_answer[i]
                cursor.setPosition(i)
                cursor.movePosition(QtGui.QTextCursor.NextCharacter, QtGui.QTextCursor.KeepAnchor)
                if i < len(correct_answer) and char == correct_answer[i]:
                    cursor.setCharFormat(format_default)  # 정답인 부분
                else:
                    cursor.setCharFormat(format_incorrect)  # 오답인 부분
            elif i < len(correct_answer):
                # 사용자 입력이 짧은 경우 남은 정답에 하이픈 추가
                cursor.setPosition(i)
                cursor.insertText("-", format_incorrect)
            else:
                # 사용자 입력이 긴 경우 초과된 문자 빨간색 처리
                char = user_answer[i]
                cursor.setPosition(i)
                cursor.insertText(char, format_incorrect)

        cursor.endEditBlock()

    def reset_text_format_except_font(self, obj):
        """글씨 크기를 제외한 스타일 초기화"""
        #print("reset_text_format_except_font 호출")
        # 테마의 기본 텍스트 색상 가져오기
        palette = obj.palette()
        default_text_color = palette.color(QtGui.QPalette.Text)
        if isinstance(obj, QtWidgets.QPlainTextEdit):
            # QPlainTextEdit일 경우 스타일 초기화
            cursor = obj.textCursor()
            cursor.select(QtGui.QTextCursor.Document)
            
            # 기본 형식으로 초기화
            default_format = QtGui.QTextCharFormat()
            default_format.setForeground(default_text_color)  # 텍스트 색상 초기화
            cursor.setCharFormat(default_format)
            
            # 글씨 크기 유지
            font = obj.font()
            font.setPointSize(self.meaning_font_size if obj == self.txtMeaningInput else self.word_font_size)
            obj.setFont(font)
            
        elif isinstance(obj, QtWidgets.QTableWidget):
            # QTableWidget일 경우 스타일 초기화
            obj.blockSignals(True)
            self.disconnect_events()
            for row in range(obj.rowCount()):
                for col in range(obj.columnCount()):
                    item = obj.item(row, col)
                    if item:
                        # 기본 텍스트 색상으로 초기화
                        item.setForeground(default_text_color)
        else:
            print(f"reset_text_format_except_font: 처리할 수 없는 객체 유형 {type(obj)}")

        self.update_cell_background()
        self.update_last_test_colors()
        self.align_cells_width()
        self.on_rate_filter_changed()
        self.new_time_record_check()

    # 글씨 크기에 기반한 텍스트 위젯의 높이 계산
    def calculate_widget_height(self, font_size, line_spacing_factor=1.2, min_visible_lines=1, padding_factor=0.5):
        """
        텍스트 위젯의 높이를 계산하는 함수.
        - font_size: 글씨 크기
        - line_spacing_factor: 줄 간격 비율
        - min_visible_lines: 최소 보이는 줄 수
        - padding_factor: 글씨 크기에 비례한 추가 여백 비율
        """
        # 줄 간격 계산
        line_spacing = font_size * line_spacing_factor

        # 글씨 크기에 비례한 추가 여백 계산
        extra_padding = font_size * padding_factor

        # 텍스트 위젯 높이 계산
        widget_height = (line_spacing * min_visible_lines) + extra_padding

        # 최소/최대 높이 제약 추가
        return max(int(widget_height), int(font_size * 1.2))  # 최소 높이 보장

    def update_layout(self):
        """레이아웃을 강제로 업데이트"""
        self.gridLayout_4.update()
        self.centralwidget.adjustSize()
        self.centralwidget.updateGeometry()
        
    def handle_cut_action(self):
        """Ctrl+X (잘라내기) 후 커서 및 그래픽 상태를 복구"""
        # 포커스 강제 설정 (포커스가 없더라도 실행되도록)
        if not self.txtMeaningInput.toPlainText().strip():
            #print("입력이 비어 있습니다.")

            # 커서 상태 복구
            cursor = self.txtMeaningInput.textCursor()
            cursor.movePosition(QtGui.QTextCursor.Start)
            self.txtMeaningInput.setTextCursor(cursor)

            # 텍스트 위젯 업데이트
            self.txtMeaningInput.updateGeometry()
            self.txtMeaningInput.viewport().update()
            # 빈 경우 기본 텍스트로 복구 (원하는 메시지를 설정 가능)
            
            self.txtMeaningInput.setPlainText("")  # 빈 상태 유지
            self.reset_text_format_except_theme(self.txtMeaningInput)
            self.txtMeaningInput.setFocus()
            self.simulate_backspace_effect(self.txtMeaningInput)
        
    def reset_text_format_except_theme(self, widget):
        """
        텍스트 위젯의 설정을 초기화하되 테마는 유지.
        """
        if isinstance(widget, QtWidgets.QPlainTextEdit):
            # 텍스트 삭제 및 커서 초기화
            widget.clear()
            cursor = widget.textCursor()
            cursor.select(QtGui.QTextCursor.Document)
        
            # 테마에 따라 기본 스타일 설정
            palette = self.txtMeaningInput.palette()
            theme_color = palette.color(QtGui.QPalette.Text)
            default_format = QtGui.QTextCharFormat()
            default_format.setForeground(QtGui.QBrush(theme_color))
            cursor.setCharFormat(default_format)
        
            # 커서 상태 재설정
            widget.setTextCursor(cursor)
            
    def simulate_backspace_effect(self, widget):
        """
        텍스트 위젯에서 백스페이스를 누른 것과 동일한 효과를 강제로 적용.
        """
        # 텍스트를 임시로 추가
        #print(f"시험모드: {self.is_testing}, 연습모드: {self.is_practice}, 시험타입: {self.practice_mode}")
        translated_text = LANGUAGES.get(self.current_language, LANGUAGES["한국어"])
        if not self.is_testing and not self.is_practice:
            if not self.is_testing and self.practice_mode in (None, 0, 1, 2, 3, 4):
                widget.insertPlainText(translated_text["tested_well2"])
            elif not self.is_practice and self.practice_mode in (5, 6):
                widget.insertPlainText(translated_text["practicing_done2"])
        else:
            widget.insertPlainText(" ")

        # 커서를 뒤로 이동 (공백 위치로 이동)
        cursor = widget.textCursor()
        cursor.movePosition(cursor.End)
        widget.setTextCursor(cursor)

        # 백스페이스 입력 이벤트 처리
        backspace_event = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_Backspace, Qt.NoModifier)
        widget.keyPressEvent(backspace_event)
        
        widget.update()  # 위젯 전체를 강제로 업데이트
        widget.repaint()  # 즉각적인 다시 그리기 요청
        cursor = widget.textCursor()
        cursor.setPosition(0)  # 커서를 첫 번째 위치로 이동
        widget.setTextCursor(cursor)
        
        doc = self.txtMeaningInput.document()
        doc.setDocumentMargin(1)  # 문서 마진 초기화
        doc.adjustSize()  # 레이아웃 강제 조정
        doc = self.txtWordInput.document()
        doc.setDocumentMargin(1)  # 문서 마진 초기화
        doc.adjustSize()  # 레이아웃 강제 조정

    def force_ime_refresh(self, widget):
        """
        IME 상태를 강제로 갱신하여 텍스트 렌더링 문제를 해결.
        """
        widget.setAttribute(Qt.WA_InputMethodEnabled, False)
        widget.setAttribute(Qt.WA_InputMethodEnabled, True)
        widget.update()  # 위젯 다시 그리기 요청
        
    def normalize_cell_value(self, value):
        reverse_ko = {
                    "정답": "correct",
                    "오답": "wrong",
                    "기록 없음": "no_record"
        }
        reverse_en = {
            "correct": "correct",
            "wrong": "wrong",
            "no record": "no_record"
        }
        #print(f"normalize_cell_value value {value}")

        # 시간 포맷 처리
        # ✅ 한국어 시간 → 코드값
        match_ko = re.match(r"(\d+)시간\s*(\d+)분\s*([\d.]+)초", value)
        if match_ko:
            h, m, s = match_ko.groups()
            return f"{int(h):02d}:{int(m):02d}:{float(s):06.3f}"

        # ✅ 영어 시간 → 그대로 (검증만)
        match_en = re.match(r"(\d+):(\d+):([\d.]+)", value)
        if match_en:
            return value

        match2 = re.match(r"(\d+):(\d+):([\d.]+)", value)
        if match2:
            # 이미 코드값 형태면 그대로 사용
            return value

        # 텍스트 → 코드 변환
        if value in reverse_ko:
            return reverse_ko[value]
        elif value in reverse_en:
            return reverse_en[value]

        return value  # 못 알아본 건 그대로 둠
    
    def translate_cell_value(self, code_value):
        # 🔹 공백 문자열이면 그대로 반환
        if code_value == "":
            return ""

        table_values = LANGUAGES.get(self.current_language, LANGUAGES["한국어"]).get("table_values", {})

        if code_value in table_values:
            return table_values[code_value]

        # 🔐 문자열 타입이고 시간 형식이면 번역
        if isinstance(code_value, str) and re.match(r"^\d+:\d+:[\d.]+$", code_value):
            return self.translate_time_value(code_value)

        return str(code_value)  # 예외 대비 안전하게 문자열 반환

    def translate_time_value(self, code_time_str):
        trs_time = LANGUAGES[self.current_language]
        trs_h = trs_time["Custom_QDialog_label_content"]["handle_header_click_h"]
        trs_m = trs_time["Custom_QDialog_label_content"]["handle_header_click_m"]
        trs_s = trs_time["Custom_QDialog_label_content"]["handle_header_click_s"]
        match = re.match(r"(\d+):(\d+):([\d.]+)", code_time_str)
        if match:
            h, m, s = match.groups()
            h, m, s = int(h), int(m), float(s)
            sec_int = int(s)
            sec_frac = f"{s:.3f}".split(".")[1]

            return f"{h:02d}{trs_h} {m:02d}{trs_m} {sec_int}.{sec_frac}{trs_s}"
        return code_time_str  # 코드 포맷이 아니면 그대로

try:
    if __name__ == '__main__':
        logging.debug("프로그램 시작")
        app = QApplication(sys.argv)
        app.setStyle("windowvista")
        window = MyApp()
        window.show()
        sys.exit(app.exec_())
        
except Exception as e:
    print(f"오류 발생: {e}")
    import traceback
    traceback.print_exc()
    
input("Press Enter to exit...")