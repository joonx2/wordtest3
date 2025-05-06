THEME_COLORS = {
    "basic": {
        "gradient_bg": """
            qradialgradient(
                cx: 0.3, cy: 0.3, radius: 1.0, 
                stop: 0 #D9D9D9, 
                stop: 0.5 #F5F5F5, 
                stop: 1 #ECECEC
            );
        """,
        "main_bg": "#E6E6E6",               # 기존보다 약간 톤 다운
        "main_text": "#2E2E2E",             # 대비 강화 (더 진한 회색)
        "button_bg": "#DDDDDD",             # 중간톤 회색
        "button_text": "#2E2E2E",           # 진한 텍스트
        "button_hover_bg": "#B0B0B0",       # 약간 더 선명하게
        "button_hover_text": "#1A1A1A",
        "button_disible_bg": "#BEBEBE",
        "button_disible_text": "#FFFFFF",
        "textedit_bg": "#F0F0F0",           # 눈에 피로가 덜한 회백색
        "textedit_text": "#2E2E2E",
        "label_text": "#1A1A1A",            # 명도 높인 진회색
        "scroll": "#888888",                # 너무 진하지 않게
        "table_headerview_bg": "#F5F5F5",   # 상단 바와 조화
        "table_headerview_text": "#2E2E2E",
        "drop_down_select_bg": "#C4C4C4",
        "drop_down_select_text": "#1A1A1A",
    },
    "dark": {
        "gradient_bg": """
            qradialgradient(
                cx: 0.3, cy: 0.3, radius: 1.0, 
                stop: 0 #252525, 
                stop: 0.5 #141414, 
                stop: 1 #252525
            );
        """,
        "main_bg": "#191919",
        "main_text": "#C8C8C8",
        "button_bg": "#303030",
        "button_text": "#C8C8C8",
        "button_hover_bg": "#1D1D1D",
        "button_hover_text": "#C8C8C8",
        "button_disible_bg": "#5E5E5E",
        "button_disible_text": "#353535",
        "textedit_bg": "#2F2F2F",
        "textedit_text": "#C8C8C8",
        "label_text": "#C8C8C8",
        "scroll": "#141414",
        "table_headerview_bg": "#191919",
        "table_headerview_text": "#C8C8C8",
        "drop_down_select_bg": "#131313",
        "drop_down_select_text": "#C8C8C8",
    },
    "cyan": {
        "gradient_bg": """
            qconicalgradient(
                cx: 0.5, cy: 0.5, angle: 0,
                stop: 0.0 #009AA9,
                stop: 0.25 #008996,
                stop: 0.5 #008996,
                stop: 0.75 #00747F,
                stop: 1.0 #006D77
        );
        """,
        "main_bg": "#006D77",
        "main_text": "#F5DEB3",
        "button_bg": "#006D77",
        "button_text": "#F5DEB3",
        "button_hover_bg": "#56B6BF",
        "button_hover_text": "#F5DEB3",
        "button_disible_bg": "#009AA9",
        "button_disible_text": "#F5DEB3",
        "textedit_bg": "#20B2AA",
        "textedit_text": "#F5DEB3",
        "label_text": "#F5DEB3",
        "scroll": "#F5DEB3",
        "table_headerview_bg": "#006D77",
        "table_headerview_text": "#F5DEB3",
        "drop_down_select_bg": "#F5DEB3",
        "drop_down_select_text": "#323232",
    },
    "pink": {
        "gradient_bg": """
            qlineargradient(
                x1: 0, y1: 1, x2: 0, y2: 0, 
                stop: 0 #E8B5C6, stop: 0.5 #F6CED8, stop: 1 #FADADD
            );
        """,
        "main_bg": "#F6CED8",             # 💡 밝은 톤이지만 눈부시지 않게
        "main_text": "#4A2C2A",           # 진한 브라운핑크톤
        "button_bg": "#F4C6CC",           # 부드러운 인디핑크
        "button_text": "#4A2C2A",
        "button_hover_bg": "#F8A8B8",     # 포인트로 톤 살짝 높임
        "button_hover_text": "#3A1F1F",
        "button_disible_bg": "#E2A8B0",
        "button_disible_text": "#FFFFFF", # 대비 ↑
        "textedit_bg": "#FBE9EC",         # 매우 연한 분홍빛
        "textedit_text": "#4A2C2A",
        "label_text": "#3A1F1F",
        "scroll": "#D48F99",              # 연한 장미빛 → 튀지 않게
        "table_headerview_bg": "#F4C6CC", # 버튼과 어울리게 통일
        "table_headerview_text": "#4A2C2A",
        "drop_down_select_bg": "#F8A8B8",
        "drop_down_select_text": "#3A1F1F",
    },
    "blue": {
        "gradient_bg": """
            qlineargradient(
                x1: 0, y1: 1, x2: 0, y2: 0, 
                stop: 0 #3B4D61, stop: 0.5 #4A6589, stop: 1 #667CA5
            );
        """,
        "main_bg": "#4A6589",              # 어스름 저녁 하늘 느낌
        "main_text": "#EAF1F7",            # 부드러운 밝은 회청색
        "button_bg": "#3B4D61",            # 살짝 어두운 바다빛 남색
        "button_text": "#EAF1F7",
        "button_hover_bg": "#546E8B",      # 부드럽게 진해지는 남청색
        "button_hover_text": "#FFFFFF",
        "button_disible_bg": "#2A3C4F",
        "button_disible_text": "#9BB2C5",
        "textedit_bg": "#3F566E",          # 어두운 하늘과 조화
        "textedit_text": "#EAF1F7",
        "label_text": "#EAF1F7",
        "scroll": "#839DBB",               # 흐린 달빛빛 하늘 포인트
        "table_headerview_bg": "#3B4D61",
        "table_headerview_text": "#EAF1F7",
        "drop_down_select_bg": "#546E8B",
        "drop_down_select_text": "#FFFFFF",
    },
    "fire": {
        "gradient_bg": """
            qradialgradient(
                cx1: 1, cy1: 1, radius: 1.5, 
                stop: 0 #312944,   
                stop: 0.5 #252745,
                stop: 1 #FF6B00                  
        );
        """,
        "main_bg": "#3D2C43",
        "main_text": "#FFDEAD",
        "button_bg": "#252745",
        "button_text": "#FFDEAD",
        "button_hover_bg": "#FF6B00",
        "button_hover_text": "#FFD700",
        "button_disible_bg": "#15161F",
        "button_disible_text": "#252745",
        "textedit_bg": "#252745",
        "textedit_text": "#FFDEAD",
        "label_text": "#FFDEAD",
        "scroll": "#C14726",
        "table_headerview_bg": "#2C2C54",
        "table_headerview_text": "#FFDEAD",
        "drop_down_select_bg": "#FF6B00",
        "drop_down_select_text": "#FFD700",
    },
    "magma": {
        "gradient_bg": """
            qlineargradient(
                x1: 0, y1: 1, x2: 0, y2: 0, 
                stop: 0 #4F4F4F, stop: 0.5 #171717, stop: 1 #2E2B2B                  
        );
        """,
        "main_bg": "#2E2B2B",
        "main_text": "#FFD700",
        "button_bg": "#4B4745",
        "button_text": "#FFD700",
        "button_hover_bg": "#FF4500",
        "button_hover_text": "#FFD700",
        "button_disible_bg": "#4F4F4F",
        "button_disible_text": "#171717",
        "textedit_bg": "#4F4F4F",
        "textedit_text": "#FFD700",
        "label_text": "#FFD700",
        "scroll": "#FF4500",
        "table_headerview_bg": "#4F4F4F",
        "table_headerview_text": "#FFD700",
        "drop_down_select_bg": "#FF4500",
        "drop_down_select_text": "#FFD700",
    },
    "ice": {
        "gradient_bg": """
            qconicalgradient(
                cx: 0.5, cy: 0.5, angle: 120,
                stop: 0 #1B232F, stop: 0.5 #2C3E50, stop: 1 #446A89
            );
        """,
        "main_bg": "#1C2632",               # ❄️ 차가운 어둠, 진청남
        "main_text": "#B6CFE2",             # 🧊 은은하게 빛나는 서리색
        "button_bg": "#2F445A",             # 묵직한 블루그레이
        "button_text": "#D1E5F0",
        "button_hover_bg": "#3C5A72",       # 조금 밝아지며 광택 느낌
        "button_hover_text": "#FFFFFF",
        "button_disible_bg": "#1A1F26",     # 어두운 얼음 회색
        "button_disible_text": "#5E7385",   # 절망 속의 희미한 색
        "textedit_bg": "#2A3C4D",           # ❄️ 창문처럼 싸늘한 배경
        "textedit_text": "#C1D9EB",
        "label_text": "#B6CFE2",
        "scroll": "#4A6377",                # 차가운 금속 느낌
        "table_headerview_bg": "#2F445A",
        "table_headerview_text": "#D1E5F0",
        "drop_down_select_bg": "#3C5A72",
        "drop_down_select_text": "#E0F0FF",
    },
    "space": {
        "gradient_bg": """
            qradialgradient(
                cx: 0.5, cy: 0.5, radius: 0.8, 
                stop: 0 #110022, 
                stop: 0.5 #331166, 
                stop: 1 #000000
            );
        """,
        "main_bg": "#110022",
        "main_text": "#FFFFF0",
        "button_bg": "#1B1F3A",
        "button_text": "#DDE6ED",
        "button_hover_bg": "#FF9500",
        "button_hover_text": "#DDE6ED",
        "button_disible_bg": "#2B3A4A",
        "button_disible_text": "#4A4E69",
        "textedit_bg": "#2E1A47",
        "textedit_text": "#DDE6ED",
        "label_text": "#FF9500",
        "scroll": "#2D3A4A",
        "table_headerview_bg": "#1A1F2B",
        "table_headerview_text": "#FF9500",
        "drop_down_select_bg": "#2E1A47",
        "drop_down_select_text": "#DDE6ED",
    },
    "forest": {
        "gradient_bg": """
            qradialgradient(
                cx: 0.5, cy: 0.5, radius: 0.8, 
                stop: 0 #A3DA89, 
                stop: 0.5 #1B3A2D, 
                stop: 1 #3A251B
            );
        """,
        "main_bg": "#1B3A2D",
        "main_text": "#00aa00",
        "button_bg": "#2F5D44",
        "button_text": "#A3DA89",
        "button_hover_bg": "#FFE985",
        "button_hover_text": "#2F5D44",
        "button_disible_bg": "#3A251B",
        "button_disible_text": "#A3DA89",
        "textedit_bg": "#2F5D44",
        "textedit_text": "#A3DA89",
        "label_text": "#D1E8A2",
        "scroll": "#2F5D44",
        "table_headerview_bg": "#2F5D44",
        "table_headerview_text": "#D1E8A2",
        "drop_down_select_bg": "#F7F4A5",
        "drop_down_select_text": "#2F5D44",
    },
    "rainy": {
        "gradient_bg": """
            qradialgradient(
                cx: 1, cy: 1, radius: 1.5, 
                stop: 0 #3A3D4A, 
                stop: 0.5 #5B6770, 
                stop: 1 #2D4059
            );
        """,
        "main_bg": "#3A3D4A",
        "main_text": "#A9C9FF",
        "button_bg": "#5B6770",
        "button_text": "#A9C9FF",
        "button_hover_bg": "#255F99",
        "button_hover_text": "#A9C9FF",
        "button_disible_bg": "#2D4059",
        "button_disible_text": "#5A6E82",
        "textedit_bg": "#5A6E82",
        "textedit_text": "#A9C9FF",
        "label_text": "#A9C9FF",
        "scroll": "#2C3A47",
        "table_headerview_bg": "#3A3D4A",
        "table_headerview_text": "#A9C9FF",
        "drop_down_select_bg": "#1A1C23",
        "drop_down_select_text": "#8B9EB6",
    },
    "desert": {
        "gradient_bg": """
            qlineargradient(
                x1: 0, y1: 1, x2: 0, y2: 0, 
                stop: 0 #F3D19C,   /* 모래색 */
                stop: 0.5 #EFC78C,
                stop: 1 #A7D8F8    /* 푸른 하늘 */
            );
        """,
        "main_bg": "#F6E4BD",             # 부드러운 사막 베이스
        "main_text": "#4B371C",           # 짙은 나무빛 (가독성 좋음)

        "button_bg": "#EFC78C",           # 따뜻한 사막빛 버튼
        "button_text": "#3E2D1C",
        "button_hover_bg": "#79B7E0",     # 푸른 하늘색 → 대비되는 포인트
        "button_hover_text": "#FFFFFF",

        "button_disible_bg": "#D5B98C",   # 색을 낮춘 모래빛
        "button_disible_text": "#A0886A",

        "textedit_bg": "#D6EEF8",         # 하늘빛 + 오아시스 느낌
        "textedit_text": "#2F2F2F",

        "label_text": "#5A4229",          # 나무 그림자색
        "scroll": "#79B7E0",              # 하늘 포인트
        "table_headerview_bg": "#E0BA84", 
        "table_headerview_text": "#3C2B1A",

        "drop_down_select_bg": "#B3E5FC",  # 푸른 하늘의 강조
        "drop_down_select_text": "#2F2F2F",
    },
    "choco": {
        "gradient_bg": """
            qradialgradient(
                cx: 0.45, cy: 0.45, radius: 1.0,
                stop: 0 #1E120D,
                stop: 0.5 #2C1A13,
                stop: 1 #0E0704
            );
        """,
        "main_bg": "#24120A",              # 거의 99% 다크초코 느낌
        "main_text": "#F6EBDC",            # 살짝 바랜 화이트초코 (너무 새하얘지 않게)

        "button_bg": "#3C2415",            # 구운 카카오 껍질 느낌
        "button_text": "#FFEFD8",
        "button_hover_bg": "#7A5133",      # 로스팅 진한 컬러 (카라멜 테두리 느낌)
        "button_hover_text": "#24120A",

        "button_disible_bg": "#2C1A13",
        "button_disible_text": "#8A776B",

        "textedit_bg": "#3A2014",          # 묵직한 퐁당쇼콜라 느낌
        "textedit_text": "#FFF1E6",

        "label_text": "#CBAA88",           # 마카다미아 + 카라멜 드리즐 같은 톤
        "scroll": "#5E3A29",               # 쿠키 틈 사이처럼 깊이감
        "table_headerview_bg": "#382217",
        "table_headerview_text": "#FFEFD8",

        "drop_down_select_bg": "#4B2E1C",  # 브라우니 크러스트
        "drop_down_select_text": "#F6EBDC",
    },
    "admiral": {
        "gradient_bg": """
            qlineargradient(
                x1: 0, y1: 0, x2: 1, y2: 1,
                stop: 0 #0C1A33,   /* 짙은 해군 블루 */
                stop: 0.5 #102F4E,
                stop: 1 #08101E    /* 깊은 심해색 */
            );
        """,
        "main_bg": "#0E1C2F",              # 해군 제복의 바탕색
        "main_text": "#FFD700",            # 황금 자수 느낌

        "button_bg": "#1A2F4D",            # 품격 있는 다크블루
        "button_text": "#FFECB3",          # 금사 같은 글자
        "button_hover_bg": "#2F486E",      # 살짝 밝아지는 제복 톤
        "button_hover_text": "#FFFFFF",    # 반짝이는 듯한 효과

        "button_disible_bg": "#1A1F2B",    # 칙칙해진 제복 (비활성)
        "button_disible_text": "#7A8899",

        "textedit_bg": "#1D314E",          # 장교의 필기용 노트
        "textedit_text": "#FFF2CC",

        "label_text": "#FFCC66",           # 금빛 장식
        "scroll": "#3A5372",               # 장교 계급장 느낌
        "table_headerview_bg": "#132742",
        "table_headerview_text": "#FFD700",

        "drop_down_select_bg": "#253C5E",
        "drop_down_select_text": "#FFECB3",
    },
    "royal": {
        "gradient_bg": """
            qradialgradient(
                cx: 0.5, cy: 0.5, radius: 0.8,
                stop: 0 #220000,
                stop: 0.5 #3B0D0D,
                stop: 1 #120101
            );
        """,
        "main_bg": "#2C0606",               # 거의 검붉은 배경 (진한 다크와인)
        "main_text": "#F8E9C7",             # 따뜻한 금빛 아이보리

        "button_bg": "#4B1010",             # 고급 벨벳 진홍
        "button_text": "#F1D9AC",
        "button_hover_bg": "#B58E40",       # 무광 골드 느낌 (눈부심 없음)
        "button_hover_text": "#2C0606",

        "button_disible_bg": "#1F0B0B",
        "button_disible_text": "#8A7463",

        "textedit_bg": "#3F1111",           # 붉은 어두운 나무 느낌
        "textedit_text": "#FDF4DC",

        "label_text": "#D8B76D",            # 포인트 금사 느낌
        "scroll": "#592424",
        "table_headerview_bg": "#360A0A",
        "table_headerview_text": "#F1D9AC",

        "drop_down_select_bg": "#4A1A1A",
        "drop_down_select_text": "#F8E9C7",
    },
    "priest": {
        "gradient_bg": """
            qlineargradient(
                x1: 0, y1: 1, x2: 1, y2: 0,
                stop: 0 #E8D3FF,
                stop: 0.5 #F4E6FF,
                stop: 1 #E0C6FF
            );
        """,
        "main_bg": "#F1DEFF",             # 🟣 밝은 연보라 (토가 빛)
        "main_text": "#5A3060",           # 🔤 선명한 로열 자주색

        "button_bg": "#E2C1F9",           # 밝은 라벤더
        "button_text": "#5A3060",         # 통일감 있는 짙은 텍스트
        "button_hover_bg": "#FFD700",     # 포인트용 황금색
        "button_hover_text": "#4A2B45",

        "button_disible_bg": "#D8C2E8",
        "button_disible_text": "#9A7DA5",

        "textedit_bg": "#F3E4FF",         # ✏️ 글쓰기 배경
        "textedit_text": "#4A2B45",       

        "label_text": "#4A2B45",          # 🔤 고정 포인트 (금색 대신 진한 자주)
        "scroll": "#B292D6",
        "table_headerview_bg": "#E5CBFF",
        "table_headerview_text": "#5A3060",

        "drop_down_select_bg": "#EAD6FF",
        "drop_down_select_text": "#5A3060",
    },
    "egyptian": {
        "gradient_bg": """
            qlineargradient(
                x1: 0, y1: 0, x2: 1, y2: 1,
                stop: 0 #7A5D00,
                stop: 0.5 #B28D14,
                stop: 1 #3D3002
            );
        """,
        "main_bg": "#3C2F00",              # 무게감 있는 황금 갈색 베이스
        "main_text": "#D7C063",            # 빛바랜 순금 (차분한 포인트)

        "button_bg": "#D7A400",            # 눌러진 황동 느낌
        "button_text": "#F6F1C2",
        "button_hover_bg": "#002244",      # 고대 벽화의 남색 강조
        "button_hover_text": "#EAD389",

        "button_disible_bg": "#574412",
        "button_disible_text": "#A59B7D",

        "textedit_bg": "#5A480D",          # 고대 파피루스+흙벽 느낌
        "textedit_text": "#F2E9B1",

        "label_text": "#F2E9B1",           # 중후한 앤틱 골드
        "scroll": "#735F2C",
        "table_headerview_bg": "#4A3A10",
        "table_headerview_text": "#F6F1C2",

        "drop_down_select_bg": "#6D5815",
        "drop_down_select_text": "#F2E9B1",
    },
    "gems": {
        "gradient_bg": """
            qlineargradient(
                x1: 0, y1: 0, x2: 1, y2: 1,
                stop: 0 #F2CB49,
                stop: 0.5 #C0970C,
                stop: 1 #BFA865
            );
        """,
        "main_bg": "#B28A3E",              # 🌟 부드럽고 은은한 황금빛
        "main_text": "#FFE5AC",            # 묵직한 브라운 골드

        "button_bg": "#0077B6",            # 사파이어 블루 💙
        "button_text": "#FFF6E5",
        "button_hover_bg": "#9C0D38",      # 루비 레드 ❤️
        "button_hover_text": "#FFF6E5",

        "button_disible_bg": "#6C757D",    # 다크 실버톤
        "button_disible_text": "#D3D3D3",

        "textedit_bg": "#D0F0C0",          # 비취 계열 옥빛 💚
        "textedit_text": "#1B2A21",

        "label_text": "#8B5CF6",           # 아메시스트 퍼플 💜
        "scroll": "#C62828",               # 루비 Scroll
        "table_headerview_bg": "#B3E5FC",  # 토파즈 라이트 블루
        "table_headerview_text": "#003366",

        "drop_down_select_bg": "#F8C8DC",  # 로즈 쿼츠 핑크 💗
        "drop_down_select_text": "#3E2B20",
    },
    "baduk_stone": {
        "gradient_bg": """
            qlineargradient(
                x1: 0, y1: 0, x2: 1, y2: 1,
                stop: 0 #D7B98E,
                stop: 1 #C49E6C
            );
        """,
        "main_bg": "#E6D3A8",                
        "main_text": "#555555",              

        "button_bg": "#F8F8F8",             
        "button_text": "#1A1A1A",          
        "button_hover_bg": "#222222",      
        "button_hover_text": "#EEEEEE",    

        "button_disible_bg": "#777777",    
        "button_disible_text": "#333333",    

        "textedit_bg": "#FAF3DC",            
        "textedit_text": "#2A1E13",

        "label_text": "#2A1E13",             
        "scroll": "#9C8253",                
        "table_headerview_bg": "#E6D3A8",    
        "table_headerview_text": "#2A1E13",

        "drop_down_select_bg": "#E6D3A8",
        "drop_down_select_text": "#1C1409"
    },
}