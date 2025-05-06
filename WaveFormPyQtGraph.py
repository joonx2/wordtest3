# graphics_widget.py
import pyqtgraph as pg
from PyQt5.QtWidgets import QWidget, QVBoxLayout
import numpy as np
from pydub import AudioSegment
from PyQt5.QtGui import QLinearGradient, QPen, QColor, QGradient, QCursor
from PyQt5.QtCore import Qt

class GraphWidget(QWidget):
    def __init__(self, audio_data, parent=None):
        """
        :param audio_data: pydub.AudioSegment 객체 (오디오 파일의 세그먼트)
        """
        super(GraphWidget, self).__init__(parent)
        self.audio_data = audio_data  # AudioSegment 객체
        self.sample = self.audiosegment_to_numpy(self.audio_data)
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout(self)
        
        # PyQtGraph PlotWidget 생성
        self.plot_widget = pg.PlotWidget()
        layout.addWidget(self.plot_widget)
        
        # 배경을 검은색('k')으로 설정
        self.plot_widget.setBackground('k')
        
        # PlotWidget 인스턴스에서 PlotItem을 가져와서 축의 색상을 흰색('w')으로 설정
        plot_item = self.plot_widget.getPlotItem()
        plot_item.getAxis('left').setPen('w')
        plot_item.getAxis('bottom').setPen('w')
        
        # 축 숨기기
        plot_item.hideAxis('left')
        plot_item.hideAxis('bottom')
        
        # 자동 리셋 버튼("A" 버튼) 숨기기
        plot_item.hideButtons()
        
        # 마우스 인터랙션 비활성화 (팬/줌)
        plot_item.vb.setMouseEnabled(x=False, y=False)
        
        # 오디오 파형을 그립니다.
        
        self.plot_waveform()
        
        # 파형 위에 인터랙션 가능한 핸들 추가
        self.add_handles()
        
    def plot_waveform(self):
        if self.sample is None:
            return

        # 1. 데이터가 정수형(int16 등)인 경우, 부동 소수점 값으로 변환하고 정규화합니다.
        if np.issubdtype(self.sample.dtype, np.integer):
            max_val = np.iinfo(self.sample.dtype).max
            y = self.sample.astype(np.float32) / max_val
        else:
            y = self.sample
            
        # 1.5. 소리 없는 영역 (silence) 판별 및 진폭 축소:
        # 동적 범위(최대값 - 최소값)를 계산하여, 매우 낮은 경우(예: 0.05 미만) 진폭을 축소합니다.
        dynamic_range = np.max(y) - np.min(y)
        silence_threshold = 0.001  # 임계치 (현재 측정값이 0.000244 정도니까, 0.001로 잡으면 무음으로 간주됨)
        if dynamic_range < silence_threshold:
            y = np.zeros_like(y)  # 완전히 평평하게 만듭니다.
    
        # 2. x축 데이터 생성: 각 샘플의 인덱스로 사용
        x = np.arange(len(y))

        # 3. 데이터 포인트 수가 많으면 다운샘플링하여 성능 최적화 (선택 사항)
        max_points = 5000
        if len(x) > max_points:
            factor = len(x) // max_points
            x = x[::factor]
            y = y[::factor]

        # 4. 어두운 보라색 단색 펜을 생성 (그라데이션 대신)
        pen = pg.mkPen("#4B0082", width=2)
        self.plot_widget.plot(x, y, pen=pen)

        # 5. 파형을 그립니다.
        self.plot_widget.plot(x, y, pen=pen)

        # 5. 뷰 범위를 수동으로 설정하여 데이터가 플롯의 끝까지 표시되도록 합니다.
        plot_item = self.plot_widget.getPlotItem()
        plot_item.vb.setRange(xRange=(x[0], x[-1]),
                              yRange=(float(np.min(y)), float(np.max(y))),
                              padding=0)
        # 뷰의 x축 한계를 데이터 범위로 제한하여 엔드 핸들이 오른쪽 끝에 붙도록 함
        plot_item.vb.setLimits(xMin=x[0], xMax=x[-1])
    
        # downsampling된 x 범위를 저장 (핸들 위치 결정에 사용)
        self.x_range = (x[0], x[-1])
    
    def audiosegment_to_numpy(self, audio_seg: AudioSegment) -> np.ndarray:
        """
        AudioSegment 객체를 NumPy 배열로 변환합니다.
        만약 스테레오 오디오라면, 두 채널의 값을 평균하여 모노로 변환합니다.
        """
        if audio_seg is None:
            return None

        # AudioSegment의 샘플 데이터를 가져옵니다.
        samples = audio_seg.get_array_of_samples()
        samples_np = np.array(samples)

        # 채널 수가 2 이상이면 (예: 스테레오) 데이터를 재구조화하여 모노로 변환
        if audio_seg.channels > 1:
            # 샘플 배열을 (샘플 개수, 채널 수) 형태로 재구조화
            samples_np = samples_np.reshape((-1, audio_seg.channels))
            # 모노 플롯을 위해 각 샘플의 채널 평균을 계산합니다.
            samples_np = samples_np.mean(axis=1)
    
        return samples_np
    
    def add_handles(self):
        """ 파형 위에 인터랙션 가능한 핸들 3개(스타트, 미드, 엔드)를 추가합니다. """
        # x_range가 저장되어 있으면 이를 사용하여 초기 위치를 결정합니다.
        if hasattr(self, "x_range"):
            x0, x1 = self.x_range
        else:
            x0, x1 = 0, 0
            
        mid = x0

        # 핸들은 InfiniteLine 객체를 사용하며, angle=90 (수직선)로 설정합니다.
        # 색상은 각각 RGB 값을 사용하여 (예: 스타트: 빨강, 미드: 녹색, 엔드: 파랑) 지정합니다.
        # 사용자 정의 핸들(HandleLine) 객체 생성 (각 핸들은 movable=True로 드래그 가능)
        start_handle = HandleLine(pos=x0, angle=90, movable=True,
                                  pen=pg.mkPen((255, 0, 0), width=4))
        mid_handle   = HandleLine(pos=mid, angle=90, movable=True,
                                  pen=pg.mkPen((0, 255, 0), width=4))
        end_handle   = HandleLine(pos=x1, angle=90, movable=True,
                                  pen=pg.mkPen((0, 0, 255), width=4))
    
        # 각 핸들의 이동 범위를 설정하여 화면(데이터) 범위 밖으로 나가지 않도록 합니다.
        start_handle.setBounds((x0, x1))
        mid_handle.setBounds((x0, x1))
        end_handle.setBounds((x0, x1))

        # 핸들을 플롯에 추가합니다.
        self.plot_widget.addItem(start_handle)
        self.plot_widget.addItem(mid_handle)
        self.plot_widget.addItem(end_handle)

        # 필요하다면 이후에 핸들의 위치에 접근할 수 있도록 저장합니다.
        self.start_handle = start_handle
        self.mid_handle = mid_handle
        self.end_handle = end_handle
        
class HandleLine(pg.InfiniteLine):
    def __init__(self, pos, angle, movable, pen):
        super().__init__(pos=pos, angle=angle, movable=movable, pen=pen)
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.ArrowCursor)
        self._dragging = False  # 드래그 상태를 추적하는 플래그

    def hoverEnterEvent(self, ev):
        # 드래그 중이 아니라면 열린 손 모양(OpenHandCursor)으로 변경
        if not self._dragging:
            self.setCursor(Qt.OpenHandCursor)
        ev.accept()

    def hoverLeaveEvent(self, ev):
        # 드래그 중이 아니라면 기본 화살표로 복원
        if not self._dragging:
            self.setCursor(Qt.ArrowCursor)
        ev.accept()

    def mousePressEvent(self, ev):
        # 클릭 시 (마우스 누름) 바로 주먹 모양(ClosedHandCursor)으로 변경
        self._dragging = True
        self.setCursor(Qt.ClosedHandCursor)
        ev.accept()
        # 부모 클래스의 마우스 프레스 이벤트도 호출
        super().mousePressEvent(ev)

    def mouseReleaseEvent(self, ev):
        # 클릭(또는 드래그) 종료 시
        self._dragging = False
        # 마우스가 여전히 핸들 위에 있으면 열린 손 모양, 아니면 기본 화살표로 복원
        if self.isUnderMouse():
            self.setCursor(Qt.OpenHandCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
        ev.accept()
        super().mouseReleaseEvent(ev)

    def mouseDragEvent(self, ev):
        # 드래그 시작 시 주먹 모양으로 변경 (이미 mousePressEvent에서 설정됨)
        if ev.isStart():
            self._dragging = True
            self.setCursor(Qt.ClosedHandCursor)
        super().mouseDragEvent(ev)
        if ev.isFinish():
            self._dragging = False
            # 드래그 종료 후 핸들 위에 있으면 열린 손 모양, 아니면 기본 화살표로 복원
            if self.isUnderMouse():
                self.setCursor(Qt.OpenHandCursor)
            else:
                self.setCursor(Qt.ArrowCursor)
                