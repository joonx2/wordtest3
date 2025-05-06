from PyQt5.QtWidgets import QApplication, QOpenGLWidget
from PyQt5.QtGui import QOpenGLContext, QSurfaceFormat, QCursor
from PyQt5.QtCore import (QTimer, QThread, pyqtSignal, Qt, QEvent)
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np
from pydub import AudioSegment
from pydub.playback import play
import time
import pyaudio
import sounddevice as sd

class WaveformGLWidget(QOpenGLWidget):
    def __init__(self, audio_data, parent=None):
        super().__init__(parent)
        self.audio_data = np.array(audio_data.get_array_of_samples())  # NumPy 배열로 변환
        #print(f"Audio data length (NumPy): {len(self.audio_data)}")
        self.sample_rate = audio_data.frame_rate  # 샘플 레이트 저장
        self.parent = parent
        #print(f"부모객체: {self.parent}")
        
        self.start_time = -1.0
        self.mid_time = -1.0
        self.end_time = 1.0
        
        # 작은 진폭 제거
        self.audio_data = np.where(abs(self.audio_data) > 1e-4, self.audio_data, 0)
        
        if np.all(self.audio_data == 0):
            #print("Detected silent audio. Generating flat waveform.")
            self.audio_data = np.zeros(1000)  # 임의로 길이 1000짜리 무음 생성

        # 최대 진폭 계산
        self.max_amplitude = max(abs(self.audio_data)) or 1
        #print(f"Initial max amplitude: {self.max_amplitude}")
    
        # 임계값 설정
        THRESHOLD = 5000  # 소리가 입력되었을 때의 정상적인 최대 진폭
        if self.max_amplitude < THRESHOLD:
            #print(f"Max amplitude ({self.max_amplitude}) is below threshold. Adjusting to {THRESHOLD}.")
            self.max_amplitude = THRESHOLD

        #print(f"Final max amplitude: {self.max_amplitude}")
        self.setMinimumSize(800, 200)  # 위젯 최소 크기 설정
        self.shader_program_invert = None
        self.shader_program_waveform = None
        self.texture = None  # 텍스처 초기화
        self.render_done = None
        self.player_thread = None  # 오디오 재생 스레드
        self.is_playing = False  # 재생 여부
        
        self.dragging_handle = None # 'start', 'mid', 'end' 중 하나
        self.handle_radius = 0.02  # 클릭할 수 있는 범위
        
        self.setMouseTracking(True)  # 🎯 마우스 이동 감지 (클릭 없이도 감지)
        self.installEventFilter(self)  # 🎯 이벤트 필터 추가
        self.current_cursor = Qt.ArrowCursor  # ⭐ 현재 커서 상태 저장!

    def initializeGL(self):
        """QOpenGLWidget이 활성화될 때 OpenGL 초기화"""
        from OpenGL.GL import glGetString, GL_VERSION, GL_RENDERER, GL_VENDOR
        glClearColor(0.0, 0.0, 0.0, 1.0)
        #print("WaveformGLWidget OpenGL 초기화 성공")
        #print(f"OpenGL Version: {glGetString(GL_VERSION).decode()}")
        #print(f"Renderer: {glGetString(GL_RENDERER).decode()}")
        #print(f"Vendor: {glGetString(GL_VENDOR).decode()}")
        
        glClearColor(0.0, 0.0, 0.0, 1.0)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)

        self.vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        
        self.texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.texture)
    
        self.vertex_data = np.array([
            (i / self.sample_rate, sample / self.max_amplitude)
            for i, sample in enumerate(self.audio_data)
        ], dtype=np.float32)
        
        audio_duration = len(self.audio_data) / self.sample_rate

        # X 좌표를 정규화 (녹음 길이만큼 확장)
        self.vertex_data[:, 0] = (self.vertex_data[:, 0] / audio_duration) * 2.0 - 1.0

        # X 좌표를 약간 왼쪽으로 이동하여 빈 공간 보정
        #x_offset = -audio_duration * 0.11  # 필요에 따라 0.05~0.15 조정 가능
        #self.vertex_data[:, 0] += x_offset

        glBufferData(GL_ARRAY_BUFFER, self.vertex_data.nbytes, self.vertex_data, GL_STATIC_DRAW)

        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 0, None)

        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)
        
        self.makeCurrent()  # 컨텍스트 활성화
        
        # 셰이더 초기화
        vertex_shader_code = """
        #version 330 core
        layout(location = 0) in vec2 position;  // 오디오 데이터 좌표
        out vec2 debug_position;  // 디버깅용 변수
        out float intensity;  // 진폭 값

        void main() {
            gl_Position = vec4(position, 0.0, 1.0);
            debug_position = position;  // X 좌표를 그대로 전달
            intensity = abs(position.y);  // Y 좌표(진폭) 기반으로 강도 계산
        }
        """
        fragment_shader_code = """
        #version 330 core
        in vec2 debug_position;  // 버텍스 셰이더에서 전달받은 좌표
        in float intensity;  // 버텍스 셰이더에서 전달받은 진폭 값
        out vec4 fragColor;

        void main() {
            // 🎨 광선 효과: 중앙 (y=0)은 붉고, 위/아래로 갈수록 파랗게 변화
            float centerEffect = abs(debug_position.y) * 1.7;  // 중앙(y=0)일수록 낮고, 위/아래일수록 높음 (0~2 범위)
    
            float r = 0.8 - 0.5 * centerEffect;  // 중앙은 강한 빨강, 위/아래로 갈수록 감소
            float g = 0.05 + 0.05 * (1.0 - intensity);  // 초록색 감소 (약한 변화)
            float b = 0.7 + 0.5 * centerEffect;  // 중앙은 약한 파랑, 위/아래로 갈수록 강한 파랑
    
            fragColor = vec4(r, g, b, 1.0);
        }
        """
        
        vertex_shader_invertrect_code = """
        #version 330 core
        layout(location = 0) in vec2 position;
        out float intensity;  // Fragment Shader로 전달

        void main() {
            gl_Position = vec4(position, 0.0, 1.0);
            intensity = abs(position.y);  // y 좌표 기반으로 강도 계산
        }

        """
        fragment_shader_invertrect_code = """
        #version 330 core
        in float intensity;  // Vertex Shader로부터 전달받은 강도
        out vec4 fragColor;

        void main() {
            // 진폭에 따른 그라데이션 (어두운 파랑 ~ 보라색)
            fragColor = vec4(0.2 * intensity, 0.0, 0.5 + 0.5 * intensity, 1.0);
        }

        """
        # 셰이더 컴파일 및 프로그램 생성
        vertex_shader = self.compile_shader(vertex_shader_code, GL_VERTEX_SHADER)
        fragment_shader = self.compile_shader(fragment_shader_code, GL_FRAGMENT_SHADER)
        
        vertex_shader_invertrect = self.compile_shader(vertex_shader_invertrect_code, GL_VERTEX_SHADER)
        fragment_shader_invertrect = self.compile_shader(fragment_shader_invertrect_code, GL_FRAGMENT_SHADER)

        # 파형 렌더링용 셰이더 프로그램
        self.shader_program_waveform = glCreateProgram()
        glAttachShader(self.shader_program_waveform, vertex_shader)
        glAttachShader(self.shader_program_waveform, fragment_shader)
        glLinkProgram(self.shader_program_waveform)

        # 반전 영역 렌더링용 셰이더 프로그램
        self.shader_program_invert = glCreateProgram()
        glAttachShader(self.shader_program_invert, vertex_shader_invertrect)
        glAttachShader(self.shader_program_invert, fragment_shader_invertrect)
        glLinkProgram(self.shader_program_invert)
        
          # 컴파일된 셰이더 삭제
        glDeleteShader(vertex_shader)
        glDeleteShader(fragment_shader)
        glDeleteShader(vertex_shader_invertrect)
        glDeleteShader(fragment_shader_invertrect)
        
    def resizeGL(self, w, h):
        """OpenGL 화면 크기 변경"""
        self.makeCurrent()  # 컨텍스트 활성화
        
        glViewport(0, 0, w, h)  # OpenGL 뷰포트 크기 설정
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        
        # 🔥 X축: 전체 오디오 길이 (초), Y축: -1.0 ~ 1.0 (정규화된 진폭)
        audio_duration = len(self.audio_data) / self.sample_rate
        bottom, top = -1.0, 1.0
        x_min, x_max = -1, 1
        gluOrtho2D(x_min, x_max, bottom, top)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        
        #print(f"🚀 First X value: {self.vertex_data[0, 0]}, Last X value: {self.vertex_data[-1, 0]}")
        #print(f"🚀 Expected X range: 0.0 ~ {audio_duration}")

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT)  # 화면 초기화
        glLineWidth(1.0)
        glBindVertexArray(self.vao)  # 🔥 VAO 바인딩 (이거 필수!)
        
        # 파형 그리기
        glViewport(0, 0, self.width(), self.height())
        glUseProgram(self.shader_program_waveform)
        glDrawArrays(GL_LINE_STRIP, 0, len(self.audio_data))
        glBindVertexArray(0)
        glUseProgram(0)
    
        # 🎨 선택 영역 1 (왼쪽, 시작 ~ 스타트핸들)
        glColor4f(0.0, 0.0, 0.0, 0.5)  # 검정색 반투명
        glBegin(GL_QUADS)
        glVertex2f(-1.0, -1.0)  # 화면의 가장 왼쪽
        glVertex2f(-1.0, 1.0)
        glVertex2f(self.start_time, 1.0)
        glVertex2f(self.start_time, -1.0)
        glEnd()

        # 🎨 선택 영역 2 (오른쪽, 엔드핸들 ~ 끝)
        glColor4f(0.0, 0.0, 0.0, 0.5)  # 검정색 반투명
        glBegin(GL_QUADS)
        glVertex2f(self.end_time, -1.0)
        glVertex2f(self.end_time, 1.0)
        glVertex2f(1.0, 1.0)  # 화면의 가장 오른쪽
        glVertex2f(1.0, -1.0)
        glEnd()

        # 3. 핸들 그리기 (선)
        glLineWidth(3.0)  # 선 두께 설정

        # 스타트핸들 (빨간색 선)
        glColor3f(1.0, 0.0, 0.0)
        glBegin(GL_LINES)
        glVertex2f(self.start_time, -1.0)
        glVertex2f(self.start_time, 1.0)
        glEnd()

        # 미드핸들 (초록색 선)
        glColor3f(0.0, 1.0, 0.0)
        glBegin(GL_LINES)
        #print(self.mid_time, f"마우스 드래깅중?: {self.dragging_handle}")
        glVertex2f(self.mid_time, -1.0)
        glVertex2f(self.mid_time, 1.0)
        glEnd()

        # 엔드핸들 (파란색 선)
        glColor3f(0.0, 0.0, 1.0)
        glBegin(GL_LINES)
        glVertex2f(self.end_time, -1.0)
        glVertex2f(self.end_time, 1.0)
        glEnd()
    
    def compile_shader(self, source, shader_type):
        shader = glCreateShader(shader_type)
        glShaderSource(shader, source)
        glCompileShader(shader)
        if not glGetShaderiv(shader, GL_COMPILE_STATUS):
            raise RuntimeError(glGetShaderInfoLog(shader).decode())
        return shader

    def render_to_texture(self):
        """현재 화면 내용을 텍스처로 캡처"""
        width, height = self.width(), self.height()
        self.texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.texture)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, width, height, 0, GL_RGB, GL_UNSIGNED_BYTE, None)
        glCopyTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, 0, 0, width, height, 0)
        glBindTexture(GL_TEXTURE_2D, 0)
        
    def on_audio_finished(self):
        """ 오디오가 끝나면 상태 초기화 """
        self.is_playing = False
        self.audio_thread = None
        
    def time_to_opengl_x(self, time_value):
        """ 초 단위 시간을 OpenGL 좌표로 변환 """
        return 1.0 - (time_value / self.end_time) * 2.0
    
    def mousePressEvent(self, event):
        """ 🎯 마우스 클릭 이벤트 (핸들 감지) """
        x_norm = self.normalize_x(event.x())

        # 🚀 핸들 클릭 감지
        if abs(x_norm - self.start_time) < self.handle_radius:
            self.dragging_handle = "start"
            self.parent.stop_audio(True)
            #print("✅ Start 핸들 클릭됨!")
        elif abs(x_norm - self.mid_time) < self.handle_radius:
            self.dragging_handle = "mid"
            self.parent.stop_audio(True)
            #print("✅ Mid 핸들 클릭됨!")
        elif abs(x_norm - self.end_time) < self.handle_radius:
            self.dragging_handle = "end"
            self.parent.stop_audio(True)
            #print("✅ End 핸들 클릭됨!")

        if self.dragging_handle:
            self.setCursor(Qt.ClosedHandCursor)  # 움켜쥔 손 모양
            #print(f"🎯 드래그 시작: {self.dragging_handle} 핸들")
            
    def mouseMoveEvent(self, event):
        """ 🎯 마우스 이동 이벤트 (핸들 드래그 & 커서 변경) """
        if self.dragging_handle:
            x_norm = self.normalize_x(event.x())  # X 좌표 변환
            self.updateHandlePosition(self.dragging_handle, x_norm)
            self.setCursor(Qt.ClosedHandCursor)  # ✋ 움켜쥔 손 모양
        else:
            # 🎯 드래그가 아니더라도 마우스 움직일 때 커서 변경
            self.updateCursor(event.x())

        self.update()
    
    def mouseReleaseEvent(self, event):
        """ 🎯 마우스 버튼 떼기 (드래그 해제) """
        if self.dragging_handle:
            #print(f"🛑 드래그 종료: {self.dragging_handle} 핸들")
            self.dragging_handle = None  # 핸들 해제
            self.setCursor(Qt.ArrowCursor)  # 기본 커서 복구
        self.update()
    
    def updateHandlePosition(self, handle, x_norm):
        """ 🎯 핸들 위치 업데이트 & OpenGL 다시 그리기 """
        MIN_GAP = 0.00  # ⭐ 최소 간격 (초)
    
        if handle == "start":
            self.start_time = max(-1.0, min(x_norm, self.end_time - MIN_GAP))  # 🚀 스타트핸들 → 엔드핸들 왼쪽
            self.mid_time = max(self.start_time + MIN_GAP, min(self.mid_time, self.end_time - MIN_GAP))  # ⭐ 미드핸들도 함께 이동!

        elif handle == "mid":
            self.mid_time = max(self.start_time + MIN_GAP, min(x_norm, self.end_time - MIN_GAP))  # 🚀 스타트핸들 & 엔드핸들 사이

        elif handle == "end":
            self.end_time = max(self.start_time + MIN_GAP, min(x_norm, 1.0))  # 🚀 엔드핸들 → 스타트핸들 오른쪽
            if self.end_time <= self.mid_time:
                self.mid_time = self.start_time
        
        self.update()  # OpenGL 다시 그리기
        self.parent.update_labels()
        
    def updateCursor(self, pixel_x):
        """ 🎯 마우스 위치에 따라 커서 변경 (손바닥 or 기본) """
        HANDLE_THRESHOLD = 0.1  # 🔥 감지 범위
        time_x = self.pixelToTime(pixel_x)  # X 좌표를 시간으로 변환

        new_cursor = Qt.ArrowCursor  # 기본 커서
        
        start_time = self.convertOpenGLToTime(self.start_time)
        mid_time = self.convertOpenGLToTime(self.mid_time)
        end_time = self.convertOpenGLToTime(self.end_time)

        # 🔥 핸들 감지 (마우스 버튼이 눌리지 않은 상태에서도 감지)
        if abs(time_x - start_time) < HANDLE_THRESHOLD:
            new_cursor = Qt.OpenHandCursor  # 스타트 핸들
        elif abs(time_x - end_time) < HANDLE_THRESHOLD:
            new_cursor = Qt.OpenHandCursor  # 엔드 핸들
        elif abs(time_x - mid_time) < HANDLE_THRESHOLD:
            new_cursor = Qt.OpenHandCursor  # ⭐ 미드핸들은 다른 모양

        if new_cursor != self.current_cursor:
            self.setCursor(new_cursor)
            self.current_cursor = new_cursor
            self.update() 
        
    def normalize_x(self, x):
        """ 🎯 픽셀 좌표를 OpenGL 정규화 좌표(-1 ~ 1)로 변환 """
        return (x / self.width()) * 2.0 - 1.0
    
    def convertOpenGLToTime(self, gl_x):
        """ 🔄 OpenGL 좌표 (-1 ~ 1) → 오디오 시간 값 (0 ~ audio_duration) """
        audio_duration = len(self.audio_data) / self.sample_rate  # 전체 오디오 길이 (초)
        return ((gl_x + 1.0) / 2.0) * audio_duration

    def pixelToTime(self, pixel_x):
        """ 🎯 화면의 x 좌표(픽셀 단위)를 오디오의 시간(초)으로 변환 """
        widget_width = self.width()  # 현재 위젯의 가로 크기 (픽셀)
        audio_duration = len(self.audio_data) / self.sample_rate  # 전체 오디오 길이 (초)
        
        # 🔹 픽셀을 오디오 시간으로 변환
        time_x = (pixel_x / widget_width) * audio_duration 
        
        return time_x  # 변환된 시간 반환
    
    def eventFilter(self, obj, event):
        """ 🎯 마우스 오버 & 이동 감지 (클릭 없이도 커서 변경) """
        if event.type() == QEvent.HoverMove:
            self.updateCursor(event.pos().x())  # 마우스 위치를 전달하여 커서 변경
            return True  # 이벤트 처리 완료

        return super().eventFilter(obj, event)  # 기본 이벤트 처리
    
    def update_mid_handle(self, new_time):
        """ 🎯 미드핸들 위치 업데이트 """
        self.mid_time = new_time
        #print(f"🔵 미드핸들 업데이트: {self.mid_time}초")  # 🎯 디버깅
