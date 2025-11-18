#!/usr/bin/env python3
"""
환경 설정 확인 스크립트
실행 전 모든 것이 준비되었는지 확인합니다.
"""
import sys
import subprocess
import importlib.util

def check_python_version():
    """Python 버전 확인"""
    print("=" * 60)
    print("1. Python 버전 확인")
    print("=" * 60)
    version = sys.version_info
    print(f"Python {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8 이상이 필요합니다!")
        return False
    else:
        print("✅ Python 버전 OK")
        return True

def check_package(package_name, import_name=None):
    """패키지 설치 확인"""
    if import_name is None:
        import_name = package_name
    
    spec = importlib.util.find_spec(import_name)
    if spec is None:
        print(f"❌ {package_name} 설치 안 됨")
        return False
    else:
        try:
            module = importlib.import_module(import_name)
            version = getattr(module, '__version__', 'unknown')
            print(f"✅ {package_name} {version}")
            return True
        except:
            print(f"⚠️  {package_name} 설치됨 (버전 확인 불가)")
            return True

def check_packages():
    """필수 패키지 확인"""
    print("\n" + "=" * 60)
    print("2. 필수 패키지 확인")
    print("=" * 60)
    
    packages = [
        ('torch', 'torch'),
        ('numpy', 'numpy'),
        ('matplotlib', 'matplotlib'),
        ('tensorboard', 'tensorboard'),
    ]
    
    all_ok = True
    for package_name, import_name in packages:
        if not check_package(package_name, import_name):
            all_ok = False
    
    return all_ok

def check_cuda():
    """CUDA 사용 가능 확인"""
    print("\n" + "=" * 60)
    print("3. GPU (CUDA) 확인")
    print("=" * 60)
    
    try:
        import torch
        if torch.cuda.is_available():
            print(f"✅ CUDA 사용 가능")
            print(f"   GPU: {torch.cuda.get_device_name(0)}")
            print(f"   메모리: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
            return True
        else:
            print("⚠️  CUDA 사용 불가 (CPU로 학습됩니다)")
            print("   학습 시간이 매우 오래 걸립니다 (40-60시간)")
            return False
    except:
        print("❌ PyTorch 설치 확인 불가")
        return False

def check_files():
    """필수 파일 확인"""
    print("\n" + "=" * 60)
    print("4. 필수 파일 확인")
    print("=" * 60)
    
    import os
    files = [
        'config.py',
        'model.py',
        'agent.py',
        'replay_buffer.py',
        'game_interface.py',
        'train.py',
        'test.py',
        'play_agent.py',
        'requirements.txt',
    ]
    
    all_ok = True
    for file in files:
        if os.path.exists(file):
            print(f"✅ {file}")
        else:
            print(f"❌ {file} 없음")
            all_ok = False
    
    return all_ok

def check_port():
    """포트 사용 확인"""
    print("\n" + "=" * 60)
    print("5. 포트 사용 확인")
    print("=" * 60)
    
    import socket
    
    ports = [12345, 12346]
    all_ok = True
    
    for port in ports:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        
        if result == 0:
            print(f"✅ 포트 {port}: 게임 서버 실행 중")
        else:
            print(f"⚠️  포트 {port}: 게임 서버 대기 중")
            all_ok = False
    
    if not all_ok:
        print("\n💡 C++ 게임을 먼저 실행하세요!")
    
    return all_ok

def main():
    """메인 함수"""
    print("\n" + "🔍 CrazyArcade 강화학습 환경 확인\n")
    
    results = []
    
    # 1. Python 버전
    results.append(("Python 버전", check_python_version()))
    
    # 2. 패키지
    results.append(("필수 패키지", check_packages()))
    
    # 3. CUDA
    results.append(("GPU (CUDA)", check_cuda()))
    
    # 4. 파일
    results.append(("필수 파일", check_files()))
    
    # 5. 포트
    results.append(("게임 서버", check_port()))
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("📊 결과 요약")
    print("=" * 60)
    
    for name, ok in results:
        status = "✅" if ok else "❌"
        print(f"{status} {name}")
    
    # 최종 판정
    print("\n" + "=" * 60)
    all_ok = all(ok for _, ok in results[:-1])  # 포트는 제외
    
    if all_ok:
        print("🎉 모든 준비 완료!")
        print("\n다음 명령어로 학습을 시작하세요:")
        print("  python train.py")
    else:
        print("⚠️  일부 항목에 문제가 있습니다.")
        print("\n해결 방법:")
        
        if not results[0][1]:  # Python
            print("  - Python 3.8 이상 설치")
        
        if not results[1][1]:  # 패키지
            print("  - pip install -r requirements.txt")
        
        if not results[2][1]:  # CUDA
            print("  - GPU 드라이버 설치 또는 CPU로 학습")
        
        if not results[3][1]:  # 파일
            print("  - 파일 누락 확인")
    
    if not results[4][1]:  # 포트
        print("\n게임 서버 시작 방법:")
        print("  1. Visual Studio에서 2weeks_project_ver2.sln 열기")
        print("  2. F5 눌러서 게임 실행")
        print("  3. 게임이 실행되면 다시 이 스크립트 실행")
    
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()
