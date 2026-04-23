import base64
import os

# Шлях до твого шрифту
font_path = "app/static/fonts/times.ttf"

if os.path.exists(font_path):
    with open(font_path, "rb") as font_file:
        encoded_string = base64.b64encode(font_file.read()).decode('utf-8')
        # Записуємо результат у текстовий файл, щоб було зручно копіювати
        with open("base64_font.txt", "w") as f:
            f.write(encoded_string)
    print("Готово! Код шрифту збережено у файл base64_font.txt")
else:
    print("Файл times.ttf не знайдено за вказаним шляхом!")