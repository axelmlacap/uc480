OCT software
============

To do
-----

Importantes:
1.	[FFT] Utilizar ifft en lugar de fft. Reimplementar eje x.
1.	Implementar correciones en cámara (FPN, salt and pepper) y en espectro (compensar filtros y ¿responsividad?)
1.	[SpectrumAnalyzer] Invertir ejes para que, post calibración, los datos queden en longitud de onda crecientes

Secundarias:
1.	Que los widgets de la barra lateral puedan expandirse/contraerse
1.	[Buffer] Debería incluír el contenedor de datos (un array Data de numpy)
1.	[Buffer] El índice del buffer es, en realidad, el índice para las operaciones tipo set. Debería haber un análogo para operaciones tipo get (con sus respectivos índices) que permitan implementar funcionalidades tipo FIFO o LIFO.
1.	[SpectraAnalyzer] Filtro tipo boxcar
1.	[SpectraAnalyzer] ROI independiente
1.	[SpectraAnalyzerUi] Settear calibraciones (abrir una ventana)
1.	[SpectraSave] Incorporar opción para guardado de único archivo y que sea la opción por defecto (luego borrar la sección de guardado de SpectraAnalyzer)
				  Cambiar el checkbox "enable" por un botón tipo start/stop
				  Agregar alerta si ningún checkbox (processed, reference, dark, raw) está seleccionado
1.	[CameraControl] Admitir tiempo de exposición automático a partir de evitar que la cámara sature
1.	[SpectraAnalyzer] Incluir monitor de timing (tiempo de adquisición, tiempo de procesado, overload, frames perdidos, etc.)