import qrcode
import subprocess
import re

# ADB 명령을 실행하여 포트 정보를 가져오는 함수
def get_adb_port():
    result = subprocess.run(['adb', 'shell', 'netstat', '-tuln'], capture_output=True, text=True)
    output = result.stdout
    # 정규 표현식을 사용하여 5555 포트 찾기
    match = re.search(r'127\.0\.0\.1:(\d+)', output)
    if match:
        return match.group(1)
    return None

# IP 주소 설정 (기기에서 확인한 IP 주소로 변경)
ip_address = "192.168.219.124"

# 포트 가져오기
port = get_adb_port()

if port:
    adb_connect_info = f"{ip_address}:{port}"
    print(f"ADB 연결 정보: {adb_connect_info}")

    # QR 코드 생성
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )

    qr.add_data(adb_connect_info)
    qr.make(fit=True)

    # QR 코드 이미지 생성 및 표시
    img = qr.make_image(fill='black', back_color='white')
    img.show()
else:
    print("포트를 찾을 수 없습니다.")
