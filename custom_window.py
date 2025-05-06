from PyQt5.QtWidgets import QDialog, QVBoxLayout
from PyQt5.QtCore import Qt
from custom_titlebar import CustomTitleBar

def apply_custom_titlebar(window):
    """ 📌 기존 창 (QDialog, QMessageBox 등)에 커스텀 타이틀바 적용 """
    window.setWindowFlags(Qt.FramelessWindowHint)  # ✅ 기본 타이틀바 제거
    window.setAttribute(Qt.WA_TranslucentBackground)  # ✅ 둥근 모서리 지원

    layout = QVBoxLayout(window)
    layout.setContentsMargins(0, 0, 0, 0)

    # ✅ 커스텀 타이틀바 추가
    title_bar = CustomTitleBar(window, show_maximize=False)
    layout.addWidget(title_bar)

    content_widget = QDialog(window)
    layout.addWidget(content_widget)

    window.setLayout(layout)
