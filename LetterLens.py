import os
import cv2
import base64
import numpy as np
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.utils import secure_filename
import pytesseract
from reportlab.lib.pagesizes import letter # type: ignore
from reportlab.pdfgen import canvas # type: ignore
from io import BytesIO
from flask import send_file
from collections import Counter
import re
import os
from PIL import Image
from helpers import extract_text_from_image, extract_text_from_pdf, check_continuity, analyze_continuity_per_word, analyze_word_continuity_from_text
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Ajusta la ruta según sea necesario
#pytesseract.pytesseract.tesseract_cmd = 'tesseract'
# Configuración del entorno
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/imagenes'  # Carpeta para imágenes subidas
app.config['TEMP_LETTER_FOLDER'] = 'static/temp_letters'  # Carpeta para letras recortadas temporalmente
app.secret_key = 'supersecretkey'

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# Asegúrate de crear el directorio para las letras temporales si no existe
if not os.path.exists(app.config['TEMP_LETTER_FOLDER']):
    os.makedirs(app.config['TEMP_LETTER_FOLDER'])

# Función para verificar las extensiones permitidas
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Ruta para la página principal con formulario de carga de imagen
@app.route('/')
def index():
    cleanup_temp_images()
    return render_template('index.html')

@app.route('/process_image', methods=['POST'])
def process_image():
    if 'image' not in request.files:
        flash('No se encontró el archivo.')
        return redirect(request.url)
    
    file = request.files['image']
    if file.filename == '':
        flash('No seleccionaste ningún archivo.')
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        image = cv2.imread(filepath)
        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, thresh_image = cv2.threshold(gray_image, 150, 255, cv2.THRESH_BINARY_INV)
        
        custom_config = r'--oem 3 --psm 6'
        recognized_text = pytesseract.image_to_string(thresh_image, lang='spa', config=custom_config)
    
        # Extraer cada letra y su posición
        boxes = pytesseract.image_to_boxes(thresh_image, lang='spa')
        letters = []

        # equipo3
        ###################
        areas = []  # Lista para almacenar las áreas de las letras detectadas
        classified_letters = {"pequenia": [], "mediana": [], "grande": []}
        
        for box in boxes.splitlines():
            b = box.split()
            char = b[0]
            x, y, w, h = int(b[1]), int(b[2]), int(b[3]), int(b[4])
            cropped_letter = image[image.shape[0] - h:image.shape[0] - y, x:w]

            # equipo3
            ###################
            width = w - x
            height = h - y
            area = width * height
            areas.append(area)  # Agregar área a la lista

            # Guardar la letra recortada como archivo temporal
            temp_letter_path = os.path.join(app.config['TEMP_LETTER_FOLDER'], f"{char}_{x}_{y}.png")
            cv2.imwrite(temp_letter_path, cropped_letter)

            # Convertir la imagen a base64 para mostrar en la interfaz
            _, buffer = cv2.imencode('.png', cropped_letter)
            letter_base64 = base64.b64encode(buffer).decode('utf-8')
            letters.append({'char': char, 'img_data': letter_base64, 'path': temp_letter_path, 'coords': (x, y, w, h), 'area': area})
        
        # equipo3
        ###################
        if areas:
            avg_area = sum(areas) / len(areas)  # Área promedio
            small_threshold = avg_area * 0.5   # Definir límite para letras pequeñas
            medium_threshold = avg_area * 1.5  # Definir límite para letras medianas
        else:
            small_threshold = 0
            medium_threshold = 0
        print(areas)

        for letter in letters:
            if letter['area'] < small_threshold:
                classified_letters["pequenia"].append(letter['path'])
            elif letter['area'] < medium_threshold:
                classified_letters["mediana"].append(letter['path'])
            else:
                classified_letters["grande"].append(letter['path'])

        max_length = 0
        max_length = max(len(classified_letters["pequenia"]), len(classified_letters["mediana"]), len(classified_letters["grande"]))
        
        #equipo 5
        # Llamar a la función para identificar las letras en el texto reconocido
        text = process_image_text(filepath)
        letter_counts = count_letters(text)
       
        #equipo 6
        #obtiene los angulos de cada letra
        angles = get_letter_angles(filepath)
        
        #asocia las letras con su respectivo angulo
        letters_with_angles = [{'char': letter['char'], 'path': letter['path'], 'angle': angle['angle']} 
                       for letter, angle in zip(letters, angles)]

        #Equipo 7
        # Realizar análisis de continuidad del trazo
        word_continuity_results = analyze_word_continuity_from_text(recognized_text)
        continuity_results = check_continuity(filepath)
        
        # Guardar los datos en la sesión
        session['recognized_text'] = recognized_text
        session['letters'] = [{'char': letter['char'], 'path': letter['path']} for letter in letters]
        session['image_path'] = filename
        
        # Renderizar el resultado con los análisis de continuidad
        return render_template('index.html', 
                               letters_with_angles=letters_with_angles, 
                               recognized_text=recognized_text, 
                               letters=letters, 
                               image_path=filename, 
                               letter_counts=letter_counts,
                               lista_pequenias=classified_letters["pequenia"],
                               lista_medianas=classified_letters["mediana"],
                               lista_grandes=classified_letters["grande"],
                               max_length=max_length,
                               word_continuity_results=word_continuity_results,
                               continuity_results=continuity_results)
    
    else:
        flash('Formato de archivo no permitido. Solo se aceptan archivos PNG, JPG y JPEG.')
        return redirect(request.url)


#equipo 5
def process_image_text(image_path):

    img = Image.open(image_path)

    # Convertir a RGB para asegurar compatibilidad con OCR
    img = img.convert("RGB")

    # Aumentar la resolución simulando dpi=300 (redimensionar)
    scale_factor = 300 / 72  # Factor basado en la resolución estándar de 72 dpi
    new_size = (int(img.width * scale_factor), int(img.height * scale_factor))
    img = img.resize(new_size, Image.LANCZOS)  # LANCZOS para mejor calidad

    # Aplicar OCR
    text = pytesseract.image_to_string(img, lang='spa', config='--psm 6')

    return text
    
def count_letters(text):
# Contar letras especificadas
    counts = Counter(re.findall(r'[A-Za-zÑñ]', text))
    letter_counts = {chr(i): counts.get(chr(i), 0) for i in range(ord('A'), ord('Z') + 1)}
    letter_counts.update({chr(i): counts.get(chr(i), 0) for i in range(ord('a'), ord('z') + 1)})
    letter_counts['Ñ'] = counts.get('Ñ', 0)
    letter_counts['ñ'] = counts.get('ñ', 0)
    return letter_counts


#funcion para obtener el angulo de cada letra
def get_letter_angles(image_path):
    image = cv2.imread(image_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    letter_angles = []
    
    for contour in contours:
        if cv2.contourArea(contour) > 10:  # Filtrar ruido
            rect = cv2.minAreaRect(contour)
            angle = rect[-1]
            
            # Ajustar el ángulo para que sea consistente
            if angle < -45:
                angle += 90
            
            letter_angles.append({'angle': angle})

    return letter_angles

@app.route('/process_corrections', methods=['POST'])
def process_corrections():
    action = request.form.get('action')
    letters = session.get('letters', [])
    
    if action.startswith('remove_'):
        # Extraer el path de la letra a eliminar
        letra_path = action.split('_', 1)[1]
        
        # Buscar y eliminar la letra correspondiente
        letra_a_eliminar = next((letter for letter in letters if letter['path'] == letra_path), None)
        if letra_a_eliminar:
            letters.remove(letra_a_eliminar)
            if os.path.exists(letra_a_eliminar['path']):
                os.remove(letra_a_eliminar['path'])
        
        # Actualizar la sesión
        session['letters'] = letters
        flash('Letra eliminada correctamente.')

    elif action == 'save':
        # Guardar correcciones realizadas
        for idx, letter in enumerate(letters):
            corrected_char = request.form.get(f'letters[{idx}]')
            if corrected_char and corrected_char != letter['char']:
                # Construir rutas absolutas usando os.path.join
                old_path = os.path.abspath(letter['path'])
                
                # Mantener el directorio y reemplazar solo el nombre del archivo
                directory = os.path.dirname(old_path)  # Obtener el directorio
                old_filename = os.path.basename(old_path)  # Obtener el nombre del archivo
                new_filename = old_filename.replace(letter['char'], corrected_char)  # Reemplazar el carácter
                new_path = os.path.join(directory, new_filename)  # Crear la nueva ruta
                
                # Renombrar el archivo en el sistema
                if os.path.exists(old_path):
                    os.rename(old_path, new_path)
                
                # Actualizar el carácter y la ruta en la lista de letras
                letters[idx]['char'] = corrected_char
                letters[idx]['path'] = new_path

        # Actualizar la sesión
        session['letters'] = letters
        flash('Correcciones guardadas correctamente.')

    # Recuperar los datos necesarios para volver a renderizar la página
    recognized_text = session.get('recognized_text')
    filename = session.get('image_path')
    
    # Reconstruir las imágenes en base64 para la plantilla
    letters_with_images = []
    for letter in letters:
        if os.path.exists(letter['path']):
            with open(letter['path'], "rb") as img_file:
                letter_base64 = base64.b64encode(img_file.read()).decode('utf-8')
            letters_with_images.append({'char': letter['char'], 'img_data': letter_base64, 'path': letter['path']})

    return render_template('index.html', recognized_text=recognized_text, letters=letters_with_images, image_path=filename)

# Ruta para limpiar las imágenes temporales
@app.route('/cleanup_temp_images')
def cleanup_temp_images():
    # Eliminar todas las imágenes temporales
    for filename in os.listdir(app.config['TEMP_LETTER_FOLDER']):
        file_path = os.path.join(app.config['TEMP_LETTER_FOLDER'], filename)
        if os.path.isfile(file_path):
            os.remove(file_path)
    
    flash('Las imágenes temporales se han eliminado.')
    return redirect(url_for('index'))

@app.route('/download_pdf')
def download_pdf():
    # Crear un buffer de memoria para el archivo PDF
    pdf_buffer = BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=letter)
    width, height = letter

    # Establecer el título en la parte superior
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, height - 40, "Reporte de Caracteres Segmentados")
    
    # Agregar una línea divisoria para el encabezado
    c.setStrokeColorRGB(0, 0, 0)  # Color de la línea (negro)
    c.setLineWidth(1)
    c.line(100, height - 50, width - 100, height - 50)  # Línea horizontal
    c.setFont("Helvetica", 12)

    # Y inicial de la posición para las letras
    y_position = height - 70
    letters = session.get('letters', [])
    
    # Agregar las letras y sus imágenes recortadas al PDF
    for letter_data in letters:
        char = letter_data['char']
        # Agregar la letra como texto en negrita
        c.setFont("Helvetica-Bold", 12)
        c.drawString(100, y_position, f"Letra: {char}")
        y_position -= 20

        # Agregar las imágenes de las letras al PDF (si las hay)
        letter_image_path = letter_data['path']
        if os.path.exists(letter_image_path):
            c.drawImage(letter_image_path, 200, y_position, width=50, height=50)
            y_position -= 60

        # Asegurar que no se sobrepasen los límites de la página
        if y_position < 100:
            c.showPage()  # Crear una nueva página si es necesario
            y_position = height - 40
            c.setFont("Helvetica-Bold", 16)
            c.drawString(100, height - 40, "Reporte de Caracteres Segmentados")
            c.setFont("Helvetica", 12)
            c.line(100, height - 50, width - 100, height - 50)

    c.save()

    # Regresar al cliente el archivo PDF generado
    pdf_buffer.seek(0)
    return send_file(pdf_buffer, as_attachment=True, download_name="segmentados.pdf", mimetype="application/pdf")

# Ejecutar la aplicación
if __name__ == '__main__':
    app.run(debug=True)
