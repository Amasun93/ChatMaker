from pathlib import Path
import time

from unihiker import GUI


ROOT = Path(__file__).resolve().parent
SCREEN_WIDTH = 240
SCREEN_HEIGHT = 320


def main():
    gui = GUI()
    gui.draw_text(
        text="ChatMaker 已启动",
        x=SCREEN_WIDTH // 2,
        y=SCREEN_HEIGHT // 2,
        font_size=18,
        color="#16324f",
        origin="center",
    )
    gui.update()
    print("CHATMAKER_M10_READY")
    while True:
        time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("用户停止")
