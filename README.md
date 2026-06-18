

## Requisitos
- Python 3.11+  
- Entorno virtual recomendado (`.venv`)

## Aplicacion
Esta aplicacion separa la interfaz grafica de la logica de descarga.

### Caracteristicas
- Pega una o mas URLs de YouTube o YouTube Music.
- Descarga el audio y lo convierte a MP3.
- Escribe metadatos ID3 basicos: Title y Contributing artist.
- Ejecuta la descarga en segundo plano para no bloquear la interfaz.

### Dependencias externas
- `ffmpeg` se resuelve automaticamente. Si esta en el PATH se usa ese binario; si no, la app intenta usar una copia empaquetada por Python.

```bash
# Crear entorno virtual
python -m venv .venv

# Activar entorno en Windows
.venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar la aplicacion
python src/main.py
```