from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QHBoxLayout
from PyQt5.QtCore import Qt, QPoint

class CustomTitleBar(QWidget):
    """ 🔹 기본 타이틀바를 제거하고 새롭게 만드는 커스텀 타이틀바 """

    def __init__(self, parent, show_maximize=True):
        super().__init__(parent)
        self.setFixedHeight(30)  # 타이틀바 높이 설정
        self.parent = parent
        self.dragging = False
        self.old_pos = QPoint()

        # 🔹 레이아웃 설정
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 0, 0, 0)
        layout.setSpacing(5)

        # 🔹 프로그램 타이틀 (왼쪽)
        self.title_label = QLabel(self.parent.windowTitle(), self)
        self.title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(self.title_label)

        # 🔹 창 컨트롤 버튼 (오른쪽)
        layout.addStretch(1)  # 빈 공간 추가

        if show_maximize:
            self.btn_maximize = QPushButton("🗖", self)
            self.btn_maximize.setFixedSize(30, 30)
            self.btn_maximize.clicked.connect(self.toggle_maximize_restore)
            layout.addWidget(self.btn_maximize)

        self.btn_minimize = QPushButton("🗕", self)
        self.btn_minimize.setFixedSize(30, 30)
        self.btn_minimize.clicked.connect(parent.showMinimized)
        layout.addWidget(self.btn_minimize)

        self.btn_close = QPushButton("✖", self)
        self.btn_close.setFixedSize(30, 30)
        self.btn_close.clicked.connect(parent.close)
        layout.addWidget(self.btn_close)

        self.setLayout(layout)

    def toggle_maximize_restore(self):
        """ 🔄 창 최대화 및 복구 토글 """
        if self.parent.isMaximized():
            self.parent.showNormal()
        else:
            self.parent.showMaximized()

    def mousePressEvent(self, event):
        """ 🎯 창을 드래그할 수 있도록 설정 """
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.old_pos = event.globalPos()

    def mouseMoveEvent(self, event):
        """ 🎯 창 이동 기능 구현 """
        if self.dragging:
            delta = event.globalPos() - self.old_pos
            self.parent.move(self.parent.pos() + delta)
            self.old_pos = event.globalPos()

    def mouseReleaseEvent(self, event):
        """ 🎯 드래그 해제 """
        self.dragging = False
